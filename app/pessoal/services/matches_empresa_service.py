"""Service de matches empresa pendentes (2+ pontas por dia, requer vinculacao manual).

Complementa compensacao_service:
- compensar_automatico + backfill: casa apenas 1x1 intra-day (sem ambiguidade)
- Este service: lista dias ambiguos + permite vincular manualmente
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import func

from app import db
from app.pessoal.models import (
    PessoalCategoria, PessoalConta, PessoalTransacao,
)


def _ids_categorias_empresa() -> tuple[Optional[int], Optional[int]]:
    """Retorna (id_entrada, id_saida) do grupo Movimentacoes Empresa."""
    cats = PessoalCategoria.query.filter_by(
        grupo='Movimentacoes Empresa', ativa=True,
    ).all()
    ent = next((c.id for c in cats if c.compensavel_tipo == 'E'), None)
    sai = next((c.id for c in cats if c.compensavel_tipo == 'S'), None)
    return ent, sai


def _tx_to_dict(t: PessoalTransacao) -> dict:
    compensado = float(t.valor_compensado or 0)
    restante = float(t.valor) - compensado
    return {
        'id': t.id,
        'data': t.data.isoformat() if t.data else None,
        'data_br': t.data.strftime('%d/%m/%Y') if t.data else None,
        'tipo': t.tipo,
        'valor': float(t.valor),
        'valor_compensado': compensado,
        'valor_restante': round(restante, 2),
        'historico': t.historico,
        'descricao': t.descricao,
        'conta_id': t.conta_id,
        'conta_nome': t.conta.nome if t.conta else None,
    }


def listar_dias_pendentes(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    apenas_ambiguos: bool = True,
) -> list[dict]:
    """Lista dias com transacoes empresa que ainda tem residuo pendente.

    Args:
        apenas_ambiguos: se True, so mostra dias com 2+ pontas (entrada OU saida).
            Se False, inclui dias com 1x1 tambem (redundante com auto-match, mas util
            para debugar).
    """
    ent_id, sai_id = _ids_categorias_empresa()
    if not ent_id or not sai_id:
        raise RuntimeError(
            "Categorias do grupo 'Movimentacoes Empresa' nao encontradas. "
            "Rode: python scripts/migrations/pessoal_movimentacoes_empresa.py"
        )

    cc_ids = [r[0] for r in db.session.query(PessoalConta.id).filter(
        PessoalConta.tipo == 'conta_corrente',
    ).all()]

    # valor > COALESCE(valor_compensado, 0) — defensivo contra rows sem default
    q = PessoalTransacao.query.filter(
        PessoalTransacao.conta_id.in_(cc_ids),
        PessoalTransacao.categoria_id.in_([ent_id, sai_id]),
        PessoalTransacao.valor > func.coalesce(PessoalTransacao.valor_compensado, 0),
    )
    if data_inicio:
        q = q.filter(PessoalTransacao.data >= data_inicio)
    if data_fim:
        q = q.filter(PessoalTransacao.data <= data_fim)

    por_dia_ent: dict[date, list[PessoalTransacao]] = defaultdict(list)
    por_dia_sai: dict[date, list[PessoalTransacao]] = defaultdict(list)
    for t in q.order_by(PessoalTransacao.data.desc(), PessoalTransacao.id.asc()).all():
        if t.categoria_id == ent_id:
            por_dia_ent[t.data].append(t)
        else:
            por_dia_sai[t.data].append(t)

    todos_dias = sorted(
        set(por_dia_ent.keys()) | set(por_dia_sai.keys()),
        reverse=True,
    )

    resultado = []
    for dia in todos_dias:
        ent = por_dia_ent.get(dia, [])
        sai = por_dia_sai.get(dia, [])
        n_pontas = len(ent) + len(sai)

        if apenas_ambiguos and n_pontas <= 2 and (len(ent) <= 1 and len(sai) <= 1):
            # 1x1 ja seria coberto por auto-match — pular
            continue

        soma_ent = sum(float(t.valor) - float(t.valor_compensado or 0) for t in ent)
        soma_sai = sum(float(t.valor) - float(t.valor_compensado or 0) for t in sai)

        resultado.append({
            'data': dia.isoformat(),
            'data_br': dia.strftime('%d/%m/%Y'),
            'entradas': [_tx_to_dict(t) for t in ent],
            'saidas': [_tx_to_dict(t) for t in sai],
            'n_entradas': len(ent),
            'n_saidas': len(sai),
            'soma_entradas': round(soma_ent, 2),
            'soma_saidas': round(soma_sai, 2),
            'diff': round(soma_ent - soma_sai, 2),
            'soma_bate': abs(soma_ent - soma_sai) < 1.0,
        })
    return resultado
