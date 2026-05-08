#!/usr/bin/env python3
"""
Script: acompanhando_pedido_compra_assai.py

Consulta pedidos VOE Q.P.A. e compras Motochefe.

Exit codes:
    0 - sucesso
    1 - validacao
    2 - erro infra
"""
import sys
import os
import json
import argparse
import contextlib
import io
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

with contextlib.redirect_stdout(io.StringIO()):
    from app import create_app, db  # noqa: E402

from sqlalchemy import func  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _serializar_pedido(p, com_vinculos=True):
    from app.motos_assai.models import (
        AssaiPedidoVendaItem, AssaiCompraMotochefePedido, AssaiCompraMotochefe,
    )

    total_itens = AssaiPedidoVendaItem.query.filter_by(pedido_id=p.id).count()
    lojas = (
        db.session.query(AssaiPedidoVendaItem.loja_id)
        .filter_by(pedido_id=p.id).distinct().count()
    )
    total_qtd = (
        db.session.query(func.sum(AssaiPedidoVendaItem.qtd_pedida))
        .filter_by(pedido_id=p.id).scalar() or 0
    )

    compras_vinc = []
    if com_vinculos:
        rows = (
            db.session.query(AssaiCompraMotochefe)
            .join(
                AssaiCompraMotochefePedido,
                AssaiCompraMotochefePedido.compra_id == AssaiCompraMotochefe.id,
            )
            .filter(AssaiCompraMotochefePedido.pedido_id == p.id)
            .all()
        )
        compras_vinc = [
            {'id': c.id, 'numero': c.numero, 'status': c.status}
            for c in rows
        ]

    return {
        'id': p.id,
        'numero': p.numero,
        'status': p.status,
        'criado_em': p.criado_em,
        'lojas_distintas': lojas,
        'total_itens': total_itens,
        'total_qtd': int(total_qtd),
        'compras_vinculadas': compras_vinc,
    }


def _serializar_compra(c, com_vinculos=True):
    from app.motos_assai.models import AssaiCompraMotochefePedido, AssaiPedidoVenda

    pedidos_vinc = []
    if com_vinculos:
        rows = (
            db.session.query(AssaiPedidoVenda)
            .join(
                AssaiCompraMotochefePedido,
                AssaiCompraMotochefePedido.pedido_id == AssaiPedidoVenda.id,
            )
            .filter(AssaiCompraMotochefePedido.compra_id == c.id)
            .all()
        )
        pedidos_vinc = [
            {'id': p.id, 'numero': p.numero, 'status': p.status}
            for p in rows
        ]

    return {
        'id': c.id,
        'numero': c.numero,
        'status': c.status,
        'data_emissao': c.data_emissao,
        'criada_em': c.criada_em,
        'pedidos_vinculados': pedidos_vinc,
    }


def _run(args):
    from app.motos_assai.models import (
        AssaiPedidoVenda, AssaiCompraMotochefe,
        PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
        COMPRA_STATUS_FECHADA, COMPRA_STATUS_CANCELADA,
    )

    pedidos = []
    compras = []

    if args.pedido_id:
        p = AssaiPedidoVenda.query.get(args.pedido_id)
        if p:
            pedidos = [_serializar_pedido(p)]
    elif args.numero_pedido:
        p = AssaiPedidoVenda.query.filter_by(numero=args.numero_pedido).first()
        if p:
            pedidos = [_serializar_pedido(p)]
    elif args.compra_id:
        c = AssaiCompraMotochefe.query.get(args.compra_id)
        if c:
            compras = [_serializar_compra(c)]
    elif args.numero_compra:
        c = AssaiCompraMotochefe.query.filter_by(numero=args.numero_compra).first()
        if c:
            compras = [_serializar_compra(c)]
    elif args.somente_abertos:
        pedidos = [
            _serializar_pedido(p)
            for p in AssaiPedidoVenda.query
                .filter(~AssaiPedidoVenda.status.in_([
                    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
                ]))
                .order_by(AssaiPedidoVenda.id.desc())
                .limit(50)
                .all()
        ]
        compras = [
            _serializar_compra(c)
            for c in AssaiCompraMotochefe.query
                .filter(~AssaiCompraMotochefe.status.in_([
                    COMPRA_STATUS_FECHADA, COMPRA_STATUS_CANCELADA,
                ]))
                .order_by(AssaiCompraMotochefe.id.desc())
                .limit(50)
                .all()
        ]
    else:
        # Default: ultimos 20 de cada (sem vinculos para reduzir queries)
        pedidos = [
            _serializar_pedido(p, com_vinculos=False)
            for p in AssaiPedidoVenda.query.order_by(AssaiPedidoVenda.id.desc()).limit(20).all()
        ]
        compras = [
            _serializar_compra(c, com_vinculos=False)
            for c in AssaiCompraMotochefe.query.order_by(AssaiCompraMotochefe.id.desc()).limit(20).all()
        ]

    return {
        'pedidos': pedidos,
        'compras': compras,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='acompanhando_pedido_compra_assai')
    parser.add_argument('--pedido-id', type=int, help='ID do pedido VOE')
    parser.add_argument('--numero-pedido', help='Numero do pedido (ex VOE-12345)')
    parser.add_argument('--compra-id', type=int, help='ID da compra Motochefe')
    parser.add_argument('--numero-compra', help='Numero da compra MA-AAAA-NNNN')
    parser.add_argument('--somente-abertos', action='store_true',
                        help='Pedidos != FATURADO/CANCELADO + compras != FECHADA/CANCELADA')
    args = parser.parse_args()

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
