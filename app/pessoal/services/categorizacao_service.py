"""
Motor de categorizacao automatica para transacoes pessoais.

Pipeline executado na importacao:
- Layer 0: Exclusao empresarial (La Famiglia, etc.)
- Layer 0.5 (F2): Parcela — herda categoria de outra parcela ja categorizada
- Layer 1 (F1): Match por CPF/CNPJ (quando transacao e regra tem cpf_cnpj)
- Layer 1 (F4): Match exato PADRAO (substring, respeita valor_min/valor_max)
- Layer 2 (F4): Match fuzzy PADRAO (rapidfuzz >= 85, respeita valor_min/valor_max)
- Layer 3: Match RELATIVO (identifica regra, NAO aplica categoria)
- Layer 4: Heuristicas de contexto (pagamento cartao, investimento, etc.)
- Layer 5: Nao resolvido -> PENDENTE

Atribuicao de membro (separada):
1. Cartao: titular do parser -> membro_id automatico
2. CC PIX/TED: fuzzy match nome no historico/descricao vs membros
3. Sem info: NULL, requer manual
"""
from dataclasses import dataclass
from decimal import Decimal
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


_CACHE_IDS_DESCONSIDERAR: Optional[set] = None


def _ids_desconsiderar() -> set:
    """Cache de IDs de categorias no grupo 'Desconsiderar' (invalida no reload)."""
    global _CACHE_IDS_DESCONSIDERAR
    if _CACHE_IDS_DESCONSIDERAR is None:
        _CACHE_IDS_DESCONSIDERAR = {
            c.id for c in PessoalCategoria.query.filter_by(grupo='Desconsiderar').all()
        }
    return _CACHE_IDS_DESCONSIDERAR


def invalidar_cache_desconsiderar() -> None:
    """Forca re-leitura do cache (chamar apos editar categoria no grupo Desconsiderar)."""
    global _CACHE_IDS_DESCONSIDERAR
    _CACHE_IDS_DESCONSIDERAR = None


def eh_categoria_desconsiderar(categoria_id) -> bool:
    """True se a categoria pertence ao grupo 'Desconsiderar'."""
    return bool(categoria_id) and categoria_id in _ids_desconsiderar()


def _valor_no_range(valor, valor_min, valor_max) -> bool:
    """F4: Verifica se valor da transacao esta no range da regra.

    Range aberto (NULL em min ou max) nao restringe aquele lado.
    Retorna True se regra nao tem nenhuma restricao de valor.
    """
    if valor_min is None and valor_max is None:
        return True
    if valor is None:
        return False
    v = Decimal(str(valor))
    if valor_min is not None and v < Decimal(str(valor_min)):
        return False
    if valor_max is not None and v > Decimal(str(valor_max)):
        return False
    return True


def _aplicar_regra(resultado: ResultadoCategorizacao,
                    regra: PessoalRegraCategorizacao,
                    confianca: float) -> ResultadoCategorizacao:
    """Popula resultado com os dados de uma regra vencedora e incrementa vezes_usado."""
    resultado.categoria_id = regra.categoria_id
    resultado.regra_id = regra.id
    resultado.categorizacao_auto = True
    resultado.categorizacao_confianca = confianca
    resultado.status = 'CATEGORIZADO'
    if eh_categoria_desconsiderar(regra.categoria_id):
        resultado.excluir_relatorio = True
    regra.vezes_usado = (regra.vezes_usado or 0) + 1
    return resultado


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

    # Layer 0.5 (F2): Parcela — herdar categoria de outra parcela da mesma compra.
    # Se esta transacao tem identificador_parcela, procura OUTRA transacao na mesma
    # conta com mesmo identificador ja CATEGORIZADA e copia categoria/membro.
    if transacao.identificador_parcela:
        irma = PessoalTransacao.query.filter(
            PessoalTransacao.identificador_parcela == transacao.identificador_parcela,
            PessoalTransacao.conta_id == transacao.conta_id,
            PessoalTransacao.id != transacao.id,
            PessoalTransacao.categoria_id.isnot(None),
            PessoalTransacao.status == 'CATEGORIZADO',
            PessoalTransacao.excluir_relatorio.is_(False),
        ).order_by(PessoalTransacao.data.asc()).first()
        if irma and irma.categoria_id:
            resultado.categoria_id = irma.categoria_id
            resultado.regra_id = irma.regra_id
            resultado.membro_id = irma.membro_id
            resultado.membro_auto = True if irma.membro_id else False
            resultado.categorizacao_auto = True
            resultado.categorizacao_confianca = 100.0
            resultado.status = 'CATEGORIZADO'
            if eh_categoria_desconsiderar(irma.categoria_id):
                resultado.excluir_relatorio = True
            return resultado

    # Carregar regras PADRAO ativas ordenadas (compartilhado por F1, Layer 1, Layer 2)
    regras_padrao = PessoalRegraCategorizacao.query.filter_by(
        tipo_regra='PADRAO', ativo=True
    ).order_by(
        db.func.length(PessoalRegraCategorizacao.padrao_historico).desc(),
        PessoalRegraCategorizacao.confianca.desc(),
        PessoalRegraCategorizacao.vezes_usado.desc(),
    ).all()

    # Layer 1 (F1): Match por CPF/CNPJ — mais estavel que nome
    if transacao.cpf_cnpj_parte:
        for regra in regras_padrao:
            if (regra.cpf_cnpj_padrao
                    and regra.cpf_cnpj_padrao == transacao.cpf_cnpj_parte
                    and _valor_no_range(transacao.valor, regra.valor_min, regra.valor_max)):
                return _aplicar_regra(resultado, regra, 100.0)

    # Layer 1: Match exato PADRAO (substring)
    # Ordenar por comprimento DESC: padroes mais longos = mais especificos = testados primeiro
    # Ex: "IFD DROGARIA" (14 chars) antes de "IFD" (3 chars)
    for regra in regras_padrao:
        padrao_norm = _normalizar(regra.padrao_historico)
        if (padrao_norm and padrao_norm in historico
                and _valor_no_range(transacao.valor, regra.valor_min, regra.valor_max)):
            return _aplicar_regra(resultado, regra, 100.0)

    # Layer 2: Match fuzzy PADRAO (rapidfuzz >= 85)
    melhor_score = 0
    melhor_regra = None
    for regra in regras_padrao:
        padrao_norm = _normalizar(regra.padrao_historico)
        if not padrao_norm:
            continue
        if not _valor_no_range(transacao.valor, regra.valor_min, regra.valor_max):
            continue
        score = fuzz.token_set_ratio(padrao_norm, historico)
        if score >= 85 and score > melhor_score:
            melhor_score = score
            melhor_regra = regra

    if melhor_regra:
        return _aplicar_regra(resultado, melhor_regra, float(melhor_score))

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
