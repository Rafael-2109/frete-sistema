"""Helper para identificar chassi protegido (vinculado a pedido/NF entrada).

Chassi vinculado a HoraPedidoItem ou HoraNfEntradaItem e fonte de verdade.
Backfill de NFe de venda NUNCA sobrescreve atributos de HoraMoto desse chassi.
"""
from __future__ import annotations

from typing import List

from app import db
from app.hora.models import HoraNfEntradaItem, HoraPedidoItem, HoraRecebimentoConferencia


def chassi_protegido(numero_chassi: str | None) -> bool:
    """True se chassi tem registro em HoraPedidoItem, HoraNfEntradaItem ou
    numa conferencia de recebimento ativa (substituida=False).

    A terceira fonte cobre motos chegadas via recebimento provisório (sem NF):
    nesse fluxo ainda não existe HoraPedidoItem nem HoraNfEntradaItem, mas a
    conferencia ativa já é evidência suficiente para travar o backfill TagPlus.
    """
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return False
    em_pedido = db.session.query(HoraPedidoItem.id).filter(
        HoraPedidoItem.numero_chassi == chassi,
    ).limit(1).first() is not None
    if em_pedido:
        return True
    em_nf = db.session.query(HoraNfEntradaItem.id).filter(
        HoraNfEntradaItem.numero_chassi == chassi,
    ).limit(1).first() is not None
    if em_nf:
        return True
    em_conferencia = db.session.query(HoraRecebimentoConferencia.id).filter_by(
        numero_chassi=chassi, substituida=False,
    ).limit(1).first() is not None
    return em_conferencia


def chassi_em_pedido(numero_chassi: str | None) -> bool:
    """True se o chassi consta em alguma linha de pedido de compra (HoraPedidoItem).

    Diferente de `chassi_protegido`: NÃO considera HoraNfEntradaItem (que daria
    sempre True ao validar o próprio item da NF).
    """
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return False
    return db.session.query(HoraPedidoItem.id).filter(
        HoraPedidoItem.numero_chassi == chassi,
    ).limit(1).first() is not None


def motivos_protecao(numero_chassi: str | None) -> List[dict]:
    """Lista motivos. Retorna [] se nao protegido."""
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return []
    motivos: List[dict] = []
    for pi in HoraPedidoItem.query.filter(HoraPedidoItem.numero_chassi == chassi).all():
        motivos.append({
            'origem': 'pedido',
            'pedido_id': pi.pedido_id,
            'item_id': pi.id,
        })
    for ni in HoraNfEntradaItem.query.filter(HoraNfEntradaItem.numero_chassi == chassi).all():
        motivos.append({
            'origem': 'nf_entrada',
            'nf_id': ni.nf_id,
            'item_id': ni.id,
        })
    for ci in HoraRecebimentoConferencia.query.filter_by(
        numero_chassi=chassi, substituida=False,
    ).all():
        motivos.append({
            'origem': 'recebimento_conferencia',
            'recebimento_id': ci.recebimento_id,
            'conferencia_id': ci.id,
        })
    return motivos
