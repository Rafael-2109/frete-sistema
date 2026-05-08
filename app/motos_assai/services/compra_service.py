"""Consolida N pedidos VOE em 1 PO Motochefe.

Regras:
- Pedidos devem estar em status ABERTO
- Numero do PO Motochefe: auto MA-AAAA-NNNN (sequencial por ano)
- Após consolidação: pedidos passam a EM_PRODUCAO; PO em ABERTA
- N:N via assai_compra_motochefe_pedido
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from flask import render_template
from sqlalchemy import func, extract

from app import db
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.models import (
    AssaiCompraMotochefe, AssaiCompraMotochefePedido,
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiModelo,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,
    COMPRA_STATUS_ABERTA,
)


class CompraValidationError(Exception):
    """Erro de validação na consolidação."""


def listar_pedidos_consolidaveis() -> List[AssaiPedidoVenda]:
    """Pedidos em status ABERTO disponíveis para virar PO Motochefe."""
    return (
        AssaiPedidoVenda.query
        .filter_by(status=PEDIDO_STATUS_ABERTO)
        .order_by(AssaiPedidoVenda.criado_em.desc())
        .all()
    )


def calcular_totalizadores_por_modelo(pedido_ids: List[int]) -> List[Dict[str, Any]]:
    """SUM por modelo dos pedidos selecionados (preview antes de confirmar)."""
    if not pedido_ids:
        return []
    rows = (
        db.session.query(
            AssaiModelo.id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            func.sum(AssaiPedidoVendaItem.qtd_pedida).label('qtd_total'),
            func.sum(AssaiPedidoVendaItem.valor_total).label('valor_total'),
        )
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.modelo_id == AssaiModelo.id)
        .filter(AssaiPedidoVendaItem.pedido_id.in_(pedido_ids))
        .group_by(AssaiModelo.id, AssaiModelo.codigo, AssaiModelo.nome)
        .order_by(AssaiModelo.codigo)
        .all()
    )
    return [
        {
            'modelo_id': r.id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_total': int(r.qtd_total or 0),
            'valor_total': r.valor_total or Decimal('0'),
        }
        for r in rows
    ]


def gerar_numero_po(hoje: Optional[date] = None) -> str:
    """Gera numero MA-YYYY-NNNN sequencial dentro do ano."""
    hoje = hoje or agora_brasil_naive().date()
    ano = hoje.year
    count = (
        AssaiCompraMotochefe.query
        .filter(extract('year', AssaiCompraMotochefe.criada_em) == ano)
        .count()
    )
    return f'MA-{ano}-{count + 1:04d}'


def criar_consolidado(
    pedido_ids: List[int],
    motochefe_cnpj: Optional[str],
    criada_por_id: int,
) -> AssaiCompraMotochefe:
    """Cria PO Motochefe consolidado."""
    if not pedido_ids:
        raise CompraValidationError('Selecione ao menos 1 pedido.')

    pedidos = AssaiPedidoVenda.query.filter(AssaiPedidoVenda.id.in_(pedido_ids)).all()
    if len(pedidos) != len(pedido_ids):
        raise CompraValidationError(
            f'Pedidos não encontrados: esperava {len(pedido_ids)}, achei {len(pedidos)}.'
        )

    nao_abertos = [p for p in pedidos if p.status != PEDIDO_STATUS_ABERTO]
    if nao_abertos:
        nums = ', '.join(p.numero for p in nao_abertos)
        raise CompraValidationError(
            f'Pedidos não estão em ABERTO: {nums}'
        )

    # Cria header
    compra = AssaiCompraMotochefe(
        numero=gerar_numero_po(),
        data_emissao=agora_brasil_naive().date(),
        motochefe_cnpj=motochefe_cnpj,
        status=COMPRA_STATUS_ABERTA,
        criada_por_id=criada_por_id,
    )
    db.session.add(compra)
    db.session.flush()

    # N:N + transição de status
    for p in pedidos:
        db.session.add(AssaiCompraMotochefePedido(compra_id=compra.id, pedido_id=p.id))
        p.status = PEDIDO_STATUS_EM_PRODUCAO

    db.session.commit()
    return compra


def get_compra(compra_id: int) -> AssaiCompraMotochefe:
    return AssaiCompraMotochefe.query.get_or_404(compra_id)


def listar_compras() -> List[AssaiCompraMotochefe]:
    return (
        AssaiCompraMotochefe.query
        .order_by(AssaiCompraMotochefe.criada_em.desc())
        .limit(250)
        .all()
    )


def gerar_pdf_po(compra_id: int) -> bytes:
    """Renderiza template e converte para PDF via WeasyPrint. Retorna bytes."""
    from weasyprint import HTML

    compra = AssaiCompraMotochefe.query.get_or_404(compra_id)

    pedido_ids = [link.pedido_id for link in compra.pedido_links]
    totais = calcular_totalizadores_por_modelo(pedido_ids)

    # Por pedido: lojas e itens
    pedidos_info = []
    for link in compra.pedido_links:
        p = link.pedido
        qtd_lojas = (
            db.session.query(func.count(func.distinct(AssaiPedidoVendaItem.loja_id)))
            .filter(AssaiPedidoVendaItem.pedido_id == p.id)
            .scalar() or 0
        )
        qtd_items = (
            AssaiPedidoVendaItem.query.filter_by(pedido_id=p.id).count()
        )
        pedidos_info.append({
            'pedido': p, 'qtd_lojas': qtd_lojas, 'qtd_items': qtd_items,
        })

    html_str = render_template(
        'motos_assai/compras/pdf_template.html',
        compra=compra,
        totais=totais,
        pedidos=pedidos_info,
        gerado_em=agora_brasil_naive().strftime('%d/%m/%Y %H:%M'),
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    if not pdf_bytes:
        raise RuntimeError(f'WeasyPrint retornou vazio ao gerar PDF da compra {compra.numero}')
    return pdf_bytes
