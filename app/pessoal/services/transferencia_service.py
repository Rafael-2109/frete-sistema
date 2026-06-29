"""Casamento de transferencias entre contas proprias (ex.: deposito Bradesco <-> NuConta).

Uma transferencia entre contas do mesmo dono aparece em duas pontas:
- DEBITO na conta de origem (sai dinheiro)
- CREDITO na conta de destino (entra dinheiro)

Casar as duas pontas marca AMBAS como eh_transferencia_propria=True + excluir_relatorio=True
(saem do relatorio de competencia e do fluxo de caixa, em ambas as pontas) e grava o
vinculo reversivel em PessoalTransacao.transferencia_par_id.

Heuristica de sugestao:
- valor identico nas duas pontas
- contas correntes proprias DIFERENTES
- datas dentro de uma janela (default 5 dias)
- bonus forte quando o memo de uma ponta cita o numero da conta da contraparte
  (ex.: NuConta "...BCO BRADESCO ... Conta: 128948-9")
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Optional

from app import db
from app.pessoal.models import PessoalConta, PessoalTransacao

logger = logging.getLogger(__name__)

_RE_NUM_CONTA = re.compile(r'\d[\d.\-]{4,}\d')


# =============================================================================
# HELPERS
# =============================================================================
def _ids_contas_corrente() -> list[int]:
    return [
        x[0] for x in db.session.query(PessoalConta.id).filter(
            PessoalConta.tipo == 'conta_corrente',
        ).all()
    ]


def _memo_cita_numero(texto: Optional[str], numero_conta: Optional[str]) -> bool:
    """True se o texto cita o numero_conta informado (so digitos, len>=6)."""
    if not texto or not numero_conta:
        return False
    alvo = re.sub(r'\D', '', numero_conta)
    if len(alvo) < 6:
        return False
    return any(re.sub(r'\D', '', c) == alvo for c in _RE_NUM_CONTA.findall(texto))


def _texto(t: PessoalTransacao) -> str:
    return t.historico_completo or t.historico or ''


# =============================================================================
# SUGESTAO DE PARES
# =============================================================================
def sugerir_pares(
    janela_dias: int = 5,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    max_sugestoes: int = 200,
) -> list[dict]:
    """Sugere pares (debito, credito) de transferencia entre contas correntes proprias.

    Considera apenas transacoes ainda NAO pareadas (transferencia_par_id IS NULL).
    Greedy: cada credito entra em no maximo 1 sugestao por rodada.
    """
    cc_ids = _ids_contas_corrente()
    if len(cc_ids) < 2:
        return []

    base = PessoalTransacao.query.filter(
        PessoalTransacao.conta_id.in_(cc_ids),
        PessoalTransacao.transferencia_par_id.is_(None),
    )
    if data_inicio:
        base = base.filter(PessoalTransacao.data >= data_inicio - timedelta(days=janela_dias))
    if data_fim:
        base = base.filter(PessoalTransacao.data <= data_fim + timedelta(days=janela_dias))

    debitos = base.filter(PessoalTransacao.tipo == 'debito').order_by(
        PessoalTransacao.data.asc()).all()
    creditos = base.filter(PessoalTransacao.tipo == 'credito').order_by(
        PessoalTransacao.data.asc()).all()
    if not debitos or not creditos:
        return []

    # Mapa conta_id -> numero_conta (para o bonus de memo cruzado)
    contas = {c.id: c for c in PessoalConta.query.filter(PessoalConta.id.in_(cc_ids)).all()}

    usados_credito: set[int] = set()
    sugestoes: list[dict] = []

    for d in debitos:
        if len(sugestoes) >= max_sugestoes:
            break
        melhor = None
        melhor_score = None
        for c in creditos:
            if c.id in usados_credito:
                continue
            if c.conta_id == d.conta_id:
                continue
            if d.valor != c.valor:
                continue
            dist = abs((d.data - c.data).days)
            if dist > janela_dias:
                continue
            conta_d = contas.get(d.conta_id)
            conta_c = contas.get(c.conta_id)
            cruzado = (
                _memo_cita_numero(_texto(c), conta_d.numero_conta if conta_d else None)
                or _memo_cita_numero(_texto(d), conta_c.numero_conta if conta_c else None)
            )
            score = (1000 if cruzado else 0) - dist
            if melhor_score is None or score > melhor_score:
                melhor_score = score
                melhor = (c, dist, cruzado)

        if melhor is None:
            continue
        c, dist, cruzado = melhor
        usados_credito.add(c.id)
        sugestoes.append({
            'debito': {
                'id': d.id,
                'data': d.data.isoformat() if d.data else None,
                'data_br': d.data.strftime('%d/%m/%Y') if d.data else None,
                'historico': d.historico,
                'valor': float(d.valor),
                'conta_id': d.conta_id,
                'conta_nome': contas[d.conta_id].nome if d.conta_id in contas else None,
            },
            'credito': {
                'id': c.id,
                'data': c.data.isoformat() if c.data else None,
                'data_br': c.data.strftime('%d/%m/%Y') if c.data else None,
                'historico': c.historico,
                'valor': float(c.valor),
                'conta_id': c.conta_id,
                'conta_nome': contas[c.conta_id].nome if c.conta_id in contas else None,
            },
            'valor': float(d.valor),
            'dist_dias': dist,
            'memo_cruzado': cruzado,
            'score': melhor_score,
        })

    sugestoes.sort(key=lambda s: s['score'], reverse=True)
    return sugestoes


# =============================================================================
# VINCULAR / DESVINCULAR
# =============================================================================
def _recalcular_excluir(t: PessoalTransacao) -> None:
    """Recalcula excluir_relatorio a partir dos motivos remanescentes."""
    from app.pessoal.services.categorizacao_service import eh_categoria_desconsiderar
    motivo = (
        t.eh_transferencia_propria
        or t.eh_pagamento_cartao
        or eh_categoria_desconsiderar(t.categoria_id)
        or float(t.valor_compensado or 0) >= float(t.valor or 0) > 0
    )
    t.excluir_relatorio = bool(motivo)


def vincular(debito_id: int, credito_id: int, commit: bool = True) -> dict:
    """Casa as duas pontas de uma transferencia entre contas proprias.

    Marca ambas eh_transferencia_propria + excluir_relatorio e grava o par cruzado.
    """
    if debito_id == credito_id:
        raise ValueError('debito_id e credito_id devem ser diferentes.')

    deb = db.session.get(PessoalTransacao, debito_id)
    cre = db.session.get(PessoalTransacao, credito_id)
    if not deb or not cre:
        raise ValueError('Transacao nao encontrada.')
    if deb.tipo != 'debito':
        raise ValueError(f'debito_id={debito_id} nao e debito (tipo={deb.tipo}).')
    if cre.tipo != 'credito':
        raise ValueError(f'credito_id={credito_id} nao e credito (tipo={cre.tipo}).')
    if deb.conta_id == cre.conta_id:
        raise ValueError('As duas pontas devem ser de contas diferentes.')
    if deb.transferencia_par_id or cre.transferencia_par_id:
        raise ValueError('Uma das transacoes ja esta pareada. Desvincule antes.')

    deb.transferencia_par_id = cre.id
    cre.transferencia_par_id = deb.id
    for t in (deb, cre):
        t.eh_transferencia_propria = True
        t.excluir_relatorio = True

    logger.info(
        'transferencia_vinculada debito=%d credito=%d valor=%.2f',
        debito_id, credito_id, float(deb.valor),
    )
    if commit:
        db.session.commit()
    return {
        'debito_id': debito_id,
        'credito_id': credito_id,
        'valor': float(deb.valor),
    }


def desvincular(transacao_id: int, commit: bool = True) -> dict:
    """Desfaz o casamento de uma transferencia (limpa o par e reverte as flags)."""
    t = db.session.get(PessoalTransacao, transacao_id)
    if not t:
        raise ValueError('Transacao nao encontrada.')

    par_id = t.transferencia_par_id
    par = db.session.get(PessoalTransacao, par_id) if par_id else None

    for x in (t, par):
        if x is None:
            continue
        x.transferencia_par_id = None
        x.eh_transferencia_propria = False
        _recalcular_excluir(x)

    logger.info('transferencia_desvinculada tx=%d par=%s', transacao_id, par_id or '-')
    if commit:
        db.session.commit()
    return {'transacao_id': transacao_id, 'par_id': par_id}


# =============================================================================
# LISTAGEM
# =============================================================================
def listar_pares(limit: int = 200) -> list[dict]:
    """Lista os pares de transferencia ja casados (1 linha por par)."""
    pareadas = PessoalTransacao.query.filter(
        PessoalTransacao.transferencia_par_id.isnot(None),
        PessoalTransacao.tipo == 'debito',  # 1 linha por par (lado debito)
    ).order_by(PessoalTransacao.data.desc()).limit(limit).all()
    if not pareadas:
        return []

    par_ids = [d.transferencia_par_id for d in pareadas]
    creditos = {
        c.id: c for c in PessoalTransacao.query.filter(
            PessoalTransacao.id.in_(par_ids),
        ).all()
    }

    out = []
    for d in pareadas:
        c = creditos.get(d.transferencia_par_id)
        out.append({
            'debito': {
                'id': d.id,
                'data_br': d.data.strftime('%d/%m/%Y') if d.data else None,
                'historico': d.historico,
                'valor': float(d.valor),
                'conta_nome': d.conta.nome if d.conta else None,
            },
            'credito': {
                'id': c.id,
                'data_br': c.data.strftime('%d/%m/%Y') if c and c.data else None,
                'historico': c.historico if c else None,
                'valor': float(c.valor) if c else None,
                'conta_nome': c.conta.nome if c and c.conta else None,
            } if c else None,
            'valor': float(d.valor),
        })
    return out
