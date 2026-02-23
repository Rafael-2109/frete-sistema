"""
Motor de categorizacao automatica para transacoes pessoais.

Pipeline de 5 camadas executado na importacao:
- Layer 0: Exclusao empresarial (La Famiglia, etc.)
- Layer 1: Match exato PADRAO (substring case-insensitive)
- Layer 2: Match fuzzy PADRAO (rapidfuzz token_set_ratio >= 85)
- Layer 3: Match RELATIVO (identifica regra, NAO aplica categoria)
- Layer 4: Heuristicas de contexto (pagamento cartao, investimento, etc.)
- Layer 5: Nao resolvido -> PENDENTE

Atribuicao de membro (separada):
1. Cartao: titular do parser -> membro_id automatico
2. CC PIX/TED: fuzzy match nome no historico/descricao vs membros
3. Sem info: NULL, requer manual
"""
from dataclasses import dataclass
from typing import Optional
from rapidfuzz import fuzz
from unidecode import unidecode

from app import db
from app.pessoal.models import (
    PessoalTransacao, PessoalCategoria, PessoalRegraCategorizacao,
    PessoalExclusaoEmpresa, PessoalMembro, PessoalConta,
)
from app.pessoal.constants import (
    PADROES_PAGAMENTO_CARTAO, PADROES_TRANSFERENCIA_PROPRIA, PADROES_INVESTIMENTO,
)


@dataclass
class ResultadoCategorizacao:
    """Resultado do pipeline de categorizacao."""
    categoria_id: Optional[int] = None
    regra_id: Optional[int] = None
    categorizacao_auto: bool = False
    categorizacao_confianca: Optional[float] = None
    membro_id: Optional[int] = None
    membro_auto: bool = False
    excluir_relatorio: bool = False
    eh_pagamento_cartao: bool = False
    eh_transferencia_propria: bool = False
    status: str = 'PENDENTE'
    sugestao_categorias: Optional[list] = None  # For RELATIVO rules


def categorizar_transacao(transacao: PessoalTransacao) -> ResultadoCategorizacao:
    """Executa pipeline completo de categorizacao."""
    resultado = ResultadoCategorizacao()
    historico = _normalizar(transacao.historico_completo or transacao.historico or '')

    # Layer 0: Exclusao empresarial
    exclusoes = PessoalExclusaoEmpresa.query.filter_by(ativo=True).all()
    for excl in exclusoes:
        if _normalizar(excl.padrao) in historico:
            resultado.excluir_relatorio = True
            resultado.status = 'CATEGORIZADO'
            return resultado

    # Layer 1: Match exato PADRAO (substring)
    # Ordenar por comprimento DESC: padroes mais longos = mais especificos = testados primeiro
    # Ex: "IFD DROGARIA" (14 chars) antes de "IFD" (3 chars)
    regras_padrao = PessoalRegraCategorizacao.query.filter_by(
        tipo_regra='PADRAO', ativo=True
    ).order_by(
        db.func.length(PessoalRegraCategorizacao.padrao_historico).desc(),
        PessoalRegraCategorizacao.confianca.desc(),
        PessoalRegraCategorizacao.vezes_usado.desc(),
    ).all()

    for regra in regras_padrao:
        padrao_norm = _normalizar(regra.padrao_historico)
        if padrao_norm and padrao_norm in historico:
            resultado.categoria_id = regra.categoria_id
            resultado.regra_id = regra.id
            resultado.categorizacao_auto = True
            resultado.categorizacao_confianca = 100.0
            resultado.status = 'CATEGORIZADO'
            # Incrementar uso
            regra.vezes_usado = (regra.vezes_usado or 0) + 1
            return resultado

    # Layer 2: Match fuzzy PADRAO (rapidfuzz >= 85)
    melhor_score = 0
    melhor_regra = None
    for regra in regras_padrao:
        padrao_norm = _normalizar(regra.padrao_historico)
        if not padrao_norm:
            continue
        score = fuzz.token_set_ratio(padrao_norm, historico)
        if score >= 85 and score > melhor_score:
            melhor_score = score
            melhor_regra = regra

    if melhor_regra:
        resultado.categoria_id = melhor_regra.categoria_id
        resultado.regra_id = melhor_regra.id
        resultado.categorizacao_auto = True
        resultado.categorizacao_confianca = float(melhor_score)
        resultado.status = 'CATEGORIZADO'
        melhor_regra.vezes_usado = (melhor_regra.vezes_usado or 0) + 1
        return resultado

    # Layer 3: Match RELATIVO (sugere, nao aplica)
    regras_relativo = PessoalRegraCategorizacao.query.filter_by(
        tipo_regra='RELATIVO', ativo=True
    ).all()

    for regra in regras_relativo:
        padrao_norm = _normalizar(regra.padrao_historico)
        if padrao_norm and padrao_norm in historico:
            cat_ids = regra.get_categorias_restritas()
            if cat_ids:
                categorias = PessoalCategoria.query.filter(
                    PessoalCategoria.id.in_(cat_ids)
                ).all()
                resultado.sugestao_categorias = [c.to_dict() for c in categorias]
            resultado.regra_id = regra.id
            # NAO define categoria — usuario precisa escolher
            resultado.status = 'PENDENTE'
            return resultado

    # Layer 4: Heuristicas de contexto
    for padrao in PADROES_PAGAMENTO_CARTAO:
        if _normalizar(padrao) in historico:
            resultado.eh_pagamento_cartao = True
            resultado.excluir_relatorio = True
            resultado.status = 'CATEGORIZADO'
            return resultado

    for padrao in PADROES_TRANSFERENCIA_PROPRIA:
        if _normalizar(padrao) in historico:
            resultado.eh_transferencia_propria = True
            resultado.excluir_relatorio = True
            resultado.status = 'CATEGORIZADO'
            return resultado

    for padrao in PADROES_INVESTIMENTO:
        if _normalizar(padrao) in historico:
            # Buscar categoria Investimento
            cat_inv = PessoalCategoria.query.filter_by(nome='Investimento').first()
            if cat_inv:
                resultado.categoria_id = cat_inv.id
                resultado.categorizacao_auto = True
                resultado.categorizacao_confianca = 90.0
            resultado.excluir_relatorio = True
            resultado.status = 'CATEGORIZADO'
            return resultado

    # Layer 5: Nao resolvido
    resultado.status = 'PENDENTE'
    return resultado


def atribuir_membro(transacao: PessoalTransacao, titular_cartao: str = None,
                     ultimos_digitos: str = None) -> tuple[Optional[int], bool]:
    """Atribui membro da familia a transacao.

    Returns: (membro_id, membro_auto)
    """
    # 1. Cartao: titular do parser
    if titular_cartao:
        membros = PessoalMembro.query.filter_by(ativo=True).all()
        for membro in membros:
            nome_upper = _normalizar(membro.nome_completo or membro.nome)
            titular_upper = _normalizar(titular_cartao)
            if nome_upper and titular_upper:
                # Match nome completo
                if nome_upper in titular_upper or titular_upper in nome_upper:
                    return (membro.id, True)
                # Match primeiro nome
                primeiro_nome = _normalizar(membro.nome)
                if primeiro_nome in titular_upper:
                    return (membro.id, True)

    # 2. Se cartao com digitos conhecidos, buscar conta -> membro
    if ultimos_digitos:
        conta = PessoalConta.query.filter_by(
            ultimos_digitos_cartao=ultimos_digitos, ativa=True
        ).first()
        if conta and conta.membro_id:
            return (conta.membro_id, True)

    # 3. CC PIX/TED: fuzzy match nome no historico
    historico = _normalizar(transacao.historico_completo or transacao.historico or '')
    if historico:
        membros = PessoalMembro.query.filter_by(ativo=True).all()
        for membro in membros:
            nome_completo = _normalizar(membro.nome_completo or '')
            nome = _normalizar(membro.nome)
            if nome_completo and nome_completo in historico:
                return (membro.id, True)
            if nome and len(nome) > 3 and nome in historico:
                return (membro.id, True)

    # 4. Sem info
    return (None, False)


def categorizar_lote(transacoes: list[PessoalTransacao]) -> dict:
    """Categoriza uma lista de transacoes. Retorna estatisticas."""
    stats = {'total': 0, 'categorizados': 0, 'pendentes': 0, 'excluidos': 0}

    for transacao in transacoes:
        stats['total'] += 1
        resultado = categorizar_transacao(transacao)

        transacao.categoria_id = resultado.categoria_id
        transacao.regra_id = resultado.regra_id
        transacao.categorizacao_auto = resultado.categorizacao_auto
        transacao.categorizacao_confianca = resultado.categorizacao_confianca
        transacao.excluir_relatorio = resultado.excluir_relatorio
        transacao.eh_pagamento_cartao = resultado.eh_pagamento_cartao
        transacao.eh_transferencia_propria = resultado.eh_transferencia_propria
        transacao.status = resultado.status

        if resultado.excluir_relatorio:
            stats['excluidos'] += 1
        elif resultado.status == 'CATEGORIZADO':
            stats['categorizados'] += 1
        else:
            stats['pendentes'] += 1

    return stats


def _normalizar(texto: str) -> str:
    """Normaliza texto para comparacao: upper, unidecode, colapsar espacos."""
    if not texto:
        return ''
    import re
    texto = unidecode(texto).upper().strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto
