"""Fecho da cadeia documental CarVia a partir de uma entidade.

Eixo = NFs. De NFs deriva operações (CarviaOperacaoNf), faturas
(operacao.fatura_cliente_id) e cotações (CarviaPedidoItem.numero_nf, elo
textual). SOT único — consumido por comprovante_service e carta_correcao_service
(evita duplicar a lógica de cadeia em dois lugares).
"""
from app import db


def resolver_cadeia_nf(entidade_tipo, entidade_id):
    """Conjunto de (tipo, id) no fecho da cadeia ligado a esta entidade.
    Inclui a própria entidade de origem."""
    from app.carvia.models import (
        CarviaNf, CarviaOperacao, CarviaOperacaoNf,
        CarviaPedido, CarviaPedidoItem,
    )
    rel = {(entidade_tipo, entidade_id)}

    nf_ids = set()
    if entidade_tipo == 'nf':
        nf_ids.add(entidade_id)
    elif entidade_tipo == 'operacao':
        nf_ids.update(
            r.nf_id for r in
            CarviaOperacaoNf.query.filter_by(operacao_id=entidade_id).all()
        )
    elif entidade_tipo == 'fatura_cliente':
        op_ids = [
            o.id for o in
            CarviaOperacao.query.filter_by(fatura_cliente_id=entidade_id).all()
        ]
        if op_ids:
            nf_ids.update(
                r.nf_id for r in CarviaOperacaoNf.query.filter(
                    CarviaOperacaoNf.operacao_id.in_(op_ids)
                ).all()
            )
    elif entidade_tipo == 'cotacao':
        numeros = [
            i.numero_nf
            for p in CarviaPedido.query.filter_by(cotacao_id=entidade_id).all()
            for i in p.itens if i.numero_nf
        ]
        if numeros:
            nf_ids.update(
                nf.id for nf in
                CarviaNf.query.filter(CarviaNf.numero_nf.in_(numeros)).all()
            )

    if not nf_ids:
        return rel

    numeros_nf = set()
    for nf in CarviaNf.query.filter(CarviaNf.id.in_(nf_ids)).all():
        rel.add(('nf', nf.id))
        if nf.numero_nf:
            numeros_nf.add(nf.numero_nf)

    op_ids = set()
    for r in CarviaOperacaoNf.query.filter(CarviaOperacaoNf.nf_id.in_(nf_ids)).all():
        rel.add(('operacao', r.operacao_id))
        op_ids.add(r.operacao_id)

    if op_ids:
        for op in CarviaOperacao.query.filter(CarviaOperacao.id.in_(op_ids)).all():
            if op.fatura_cliente_id:
                rel.add(('fatura_cliente', op.fatura_cliente_id))

    if numeros_nf:
        rows = db.session.query(CarviaPedido.cotacao_id).join(
            CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
        ).filter(
            CarviaPedidoItem.numero_nf.in_(list(numeros_nf))
        ).distinct().all()
        for (cot_id,) in rows:
            if cot_id:
                rel.add(('cotacao', cot_id))

    return rel
