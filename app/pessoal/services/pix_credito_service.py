"""Casamento e tratamento do "Pix no Credito" do Nubank (Caso 1).

Uma operacao Pix no Credito gera um TRIO espalhado em 2 contas Nubank:
  A. NuConta credito  "Valor adicionado na conta por cartao de credito ...Pix no Credito"  (+V)     funding
  B. NuConta debito   "Transferencia enviada pelo Pix - <BENEF> ..."                          (-V)     despesa principal
  C. Cartao Nubank    "<BENEF>"                                                               (-(V+j)) compra (principal + juros)

Tratamento (deteccao POS-importacao, automatica — roda no fim de cada importacao):
- A funding      -> excluir_relatorio (ja marcado pela heuristica Layer 0.6) + vincula ao grupo
- B pix-saida    -> despesa PRINCIPAL na data da operacao (mantem visivel) + vincula ao grupo
- C compra cartao -> SPLIT: vira o principal (valor=V, excluir_relatorio=True, pois o principal ja
                    esta no Pix-saida) + nova linha de JUROS (valor=j, visivel, categoria Juros & Multa).
                    A soma principal+juros == valor original -> a fatura do cartao continua fechando
                    (fatura_service soma por importacao_id, sem filtrar excluir_relatorio).

Por que o principal fica no Pix-saida (B) e nao na compra (C): B sempre existe na data certa;
C (fatura do cartao) chega atrasada ou pode faltar. Quando C ainda nao existe, o trio nao e
fechado — funding fica excluido (heuristica) e o Pix-saida fica como despesa; o juros entra
quando a fatura e importada e a proxima deteccao fecha o trio.

Idempotente: pernas ja vinculadas (pix_credito_grupo != NULL) sao puladas.
Analogo arquitetural: transferencia_service.py (casamento pos-importacao por valor + janela).
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal
from uuid import uuid4

from app import db
from app.pessoal.models import PessoalConta, PessoalCategoria, PessoalTransacao
from app.pessoal.constants import PADROES_FUNDING_PIX_CREDITO
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

_JANELA_PIX = 2          # funding <-> pix-saida ocorrem no mesmo dia (validado: ±2 cobre folga)
_JANELA_COMPRA = 10      # pix-saida <-> compra cartao: a compra posta ate ~9 dias depois
# Teto de juros (fracao do principal). Juros real de Pix no Credito observado < 15%;
# uma "compra" com juros acima disso e quase sempre casamento errado (nome repetido,
# ex.: mesmo beneficiario recebendo varios Pix). Protege contra juros inventado.
_TETO_JUROS = Decimal('0.5')


def _norm(texto: str) -> str:
    """Normaliza para comparacao (sem unidecode pesado — upper + colapsa espacos)."""
    if not texto:
        return ''
    from unidecode import unidecode
    return re.sub(r'\s+', ' ', unidecode(texto).upper().strip())


def _eh_funding(texto: str) -> bool:
    h = _norm(texto)
    return any(_norm(p) in h for p in PADROES_FUNDING_PIX_CREDITO)


# Marca carimbada por _split_compra na observacao da compra-principal.
_MARCA_COMPRA_PRINCIPAL = '[Pix no Credito: original'


def deve_permanecer_excluida_pix_credito(transacao) -> bool:
    """Guard (B2): True se a transacao e uma perna do Pix-no-Credito cuja exclusao do
    relatorio e ESTRUTURAL e NAO deve ser desfeita por recategorizacao/descategorizacao
    manual — senao o principal (ja contado no Pix-saida) passa a contar 2x.

    Protege:
    - compra-principal do split (observacao carimbada por _split_compra)
    - funding de liquidez (credito NuConta "Valor adicionado ... cartao de credito")

    NAO protege juros nem Pix-saida (sao despesa VISIVEL). Puro: le atributos, sem DB.
    """
    if not getattr(transacao, 'eh_pix_credito', False):
        return False
    if transacao.observacao and _MARCA_COMPRA_PRINCIPAL in transacao.observacao:
        return True
    if _eh_funding(transacao.historico_completo or transacao.historico or ''):
        return True
    return False


def _beneficiario(texto: str) -> str:
    """Extrai o nome do beneficiario de 'Transferencia enviada pelo Pix - NOME - ...'.

    IGNORECASE: em producao historico_completo vem normalizado (MAIUSCULO, 'PIX').
    """
    if not texto:
        return ''
    m = re.search(r'pix\s*-\s*([^-]+?)\s*-', texto, re.IGNORECASE)
    if m:
        return _norm(m.group(1))
    # Fallback: tudo apos "Pix - "
    m = re.search(r'pix\s*-\s*(.+)', texto, re.IGNORECASE)
    return _norm(m.group(1)) if m else ''


def _contas_nubank():
    """(ids de NuConta corrente, ids de cartao Nubank) — contas banco 'nubank'."""
    contas = PessoalConta.query.filter(PessoalConta.banco.ilike('nubank')).all()
    nuconta_ids = [c.id for c in contas if c.tipo == 'conta_corrente']
    cartao_ids = [c.id for c in contas if c.tipo == 'cartao_credito']
    return nuconta_ids, cartao_ids


def _categoria_juros_id():
    """ID da categoria de juros (grupo Financeiro, nome com 'Juros'). None se nao existir."""
    cat = PessoalCategoria.query.filter(
        PessoalCategoria.grupo == 'Financeiro',
        PessoalCategoria.nome.ilike('%juros%'),
        PessoalCategoria.ativa.is_(True),
    ).first()
    return cat.id if cat else None


def detectar_e_processar(janela_dias: int = _JANELA_COMPRA, commit: bool = True) -> dict:
    """Detecta trios "Pix no Credito" e aplica funding-exclusao + split principal/juros.

    Idempotente: so processa fundings ainda nao vinculados (pix_credito_grupo IS NULL).

    Returns: {'trios_processados': N, 'splits': M, 'parciais': K}
    """
    nuconta_ids, cartao_ids = _contas_nubank()
    if not nuconta_ids:
        return {'trios_processados': 0, 'splits': 0, 'parciais': 0}

    # Fundings ainda nao vinculados
    candidatos = PessoalTransacao.query.filter(
        PessoalTransacao.conta_id.in_(nuconta_ids),
        PessoalTransacao.tipo == 'credito',
        PessoalTransacao.pix_credito_grupo.is_(None),
    ).order_by(PessoalTransacao.data.asc()).all()
    fundings = [f for f in candidatos if _eh_funding(f.historico_completo or f.historico)]
    if not fundings:
        return {'trios_processados': 0, 'splits': 0, 'parciais': 0}

    # Pix-saidas candidatos (debito NuConta, nao vinculado)
    pix_saidas = PessoalTransacao.query.filter(
        PessoalTransacao.conta_id.in_(nuconta_ids),
        PessoalTransacao.tipo == 'debito',
        PessoalTransacao.pix_credito_grupo.is_(None),
    ).all()
    pix_saidas = [p for p in pix_saidas
                  if 'ENVIADA PELO PIX' in _norm(p.historico_completo or p.historico)]

    # Compras de cartao candidatas (debito cartao Nubank, nao processadas)
    compras = []
    if cartao_ids:
        compras = PessoalTransacao.query.filter(
            PessoalTransacao.conta_id.in_(cartao_ids),
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.eh_pix_credito.is_(False),
        ).all()

    cat_juros_id = _categoria_juros_id()
    pix_usados: set[int] = set()
    compra_usadas: set[int] = set()
    agora = agora_utc_naive()

    splits = 0
    parciais = 0

    for f in fundings:
        # 1. Casar o Pix-saida (mesma NuConta, mesmo valor, mesma data ±_JANELA_PIX)
        pix = _melhor_pix_saida(f, pix_saidas, pix_usados)
        if not pix:
            continue  # funding sem par

        benef = _beneficiario(pix.historico_completo or pix.historico)

        # 2. Casar a compra no cartao (mesmo beneficiario, valor >= principal, data na janela)
        compra = _melhor_compra(pix, benef, compras, compra_usadas, janela_dias)

        # Funding e sempre excluido (perna de liquidez), completo ou parcial.
        f.excluir_relatorio = True

        if compra is None:
            # PARCIAL: a compra (fatura do cartao) ainda nao existe. NAO forma grupo —
            # o trio fica "aberto" e fecha numa proxima deteccao quando a compra chegar.
            # (Marcar grupo aqui impediria o reprocessamento futuro.)
            parciais += 1
            continue

        # COMPLETO: forma o grupo, marca as 3 pernas e splita a compra.
        grupo = uuid4().hex  # 32 chars (<= VARCHAR 40)
        pix_usados.add(pix.id)
        compra_usadas.add(compra.id)
        f.eh_pix_credito = True
        f.pix_credito_grupo = grupo
        pix.eh_pix_credito = True
        pix.pix_credito_grupo = grupo
        # pix-saida permanece como a despesa PRINCIPAL (nao toca excluir_relatorio/categoria)
        _split_compra(compra, pix, grupo, benef, cat_juros_id, agora)
        splits += 1

    if commit:
        db.session.commit()

    logger.info(
        'pix_credito: %d splits, %d parciais (sem cartao importado ainda)',
        splits, parciais,
    )
    return {'trios_processados': splits + parciais, 'splits': splits, 'parciais': parciais}


def reabrir_parciais(commit: bool = True) -> dict:
    """Limpa o vinculo de grupos PARCIAIS (sem perna no cartao) marcados por uma versao
    anterior do detector, para que a proxima deteccao os feche quando a compra chegar.

    Idempotente. Nao re-inclui o funding no relatorio (continua excluido pela heuristica).
    """
    _, cartao_ids = _contas_nubank()
    grupos = [g for (g,) in db.session.query(PessoalTransacao.pix_credito_grupo).filter(
        PessoalTransacao.pix_credito_grupo.isnot(None)).distinct().all()]
    reabertos = 0
    for g in grupos:
        tem_cartao = cartao_ids and PessoalTransacao.query.filter_by(pix_credito_grupo=g).filter(
            PessoalTransacao.conta_id.in_(cartao_ids)).count() > 0
        if tem_cartao:
            continue  # grupo completo (com split) — preservar
        for t in PessoalTransacao.query.filter_by(pix_credito_grupo=g).all():
            t.pix_credito_grupo = None
            t.eh_pix_credito = False
        reabertos += 1
    if commit:
        db.session.commit()
    logger.info('pix_credito: %d grupos parciais reabertos', reabertos)
    return {'parciais_reabertos': reabertos}


def _melhor_pix_saida(funding, pix_saidas, usados):
    """Pix-saida de mesmo valor e data proxima na MESMA NuConta (mais proximo em data)."""
    melhor = None
    melhor_dist = None
    for p in pix_saidas:
        if p.id in usados:
            continue
        if p.conta_id != funding.conta_id:
            continue
        if p.valor != funding.valor:
            continue
        dist = abs((p.data - funding.data).days)
        if dist > _JANELA_PIX:
            continue
        if melhor_dist is None or dist < melhor_dist:
            melhor_dist = dist
            melhor = p
    return melhor


def _melhor_compra(pix, benef, compras, usadas, janela_dias):
    """Compra no cartao do mesmo beneficiario, valor >= principal, data na janela.

    Preferencia: menor juros (valor - principal) e, em empate, menor distancia de data.
    """
    if not benef:
        return None
    melhor = None
    melhor_chave = None
    for c in compras:
        if c.id in usadas:
            continue
        if c.valor < pix.valor:  # juros nunca negativo
            continue
        dist = abs((c.data - pix.data).days)
        if dist > janela_dias:
            continue
        hist = _norm(c.historico_completo or c.historico)
        if benef not in hist and hist not in benef:
            continue
        juros = c.valor - pix.valor
        # Teto de juros: protege contra casamento errado (nome repetido casa compra
        # de outro Pix, gerando juros desproporcional).
        if juros > pix.valor * _TETO_JUROS:
            continue
        chave = (juros, dist)
        if melhor_chave is None or chave < melhor_chave:
            melhor_chave = chave
            melhor = c
    return melhor


def _split_compra(compra, pix, grupo, benef, cat_juros_id, agora):
    """Splita a compra do cartao em principal (excluido) + linha de juros (visivel)."""
    valor_original = compra.valor
    principal = pix.valor
    juros = (valor_original - principal)

    # A compra original vira o PRINCIPAL (ja contado no Pix-saida -> excluir do relatorio)
    compra.eh_pix_credito = True
    compra.pix_credito_grupo = grupo
    compra.excluir_relatorio = True
    compra.valor = principal
    compra.observacao = (
        (compra.observacao or '')
        + f' [Pix no Credito: original R${valor_original}, principal R${principal}, '
        f'juros R${juros}; principal lancado no Pix NuConta id={pix.id}]'
    ).strip()

    if juros > Decimal('0'):
        linha_juros = PessoalTransacao(
            importacao_id=compra.importacao_id,  # MESMA fatura: a soma fecha
            conta_id=compra.conta_id,
            data=compra.data,
            historico=f'Juros Pix no Credito - {benef}'[:500],
            historico_completo=f'JUROS PIX NO CREDITO - {benef}'[:1000],
            valor=juros,
            tipo='debito',
            status='CATEGORIZADO',
            excluir_relatorio=False,
            categoria_id=cat_juros_id,
            categorizacao_auto=True,
            eh_pix_credito=True,
            pix_credito_grupo=grupo,
            origem_import=compra.origem_import,
            hash_transacao=f'pixjuros-{grupo}',
            observacao=f'Juros do Pix no Credito (split da compra cartao id={compra.id})',
            categorizado_em=agora,
            categorizado_por='sistema (pix no credito)',
        )
        db.session.add(linha_juros)


def reverter_grupo(grupo: str, commit: bool = True) -> dict:
    """Desfaz o tratamento de um grupo (auditoria/correcao manual).

    Remove a linha de juros sintetica, restaura o valor da compra e limpa as marcas.
    Nao re-inclui o funding no relatorio (a heuristica continua excluindo-o).
    """
    linhas = PessoalTransacao.query.filter_by(pix_credito_grupo=grupo).all()
    juros = next((t for t in linhas if t.hash_transacao == f'pixjuros-{grupo}'), None)
    restaurada = 0
    for t in linhas:
        if t is juros:
            continue
        # restaurar valor da compra a partir da observacao
        m = re.search(r'original R\$([\d.]+)', t.observacao or '')
        if m:
            t.valor = Decimal(m.group(1))
            t.excluir_relatorio = False
            restaurada += 1
        t.eh_pix_credito = False
        t.pix_credito_grupo = None
    if juros is not None:
        db.session.delete(juros)
    if commit:
        db.session.commit()
    return {'grupo': grupo, 'compras_restauradas': restaurada, 'juros_removido': juros is not None}
