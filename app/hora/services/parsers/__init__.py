"""Parsers do módulo HORA.

Padrão: adapters finos sobre parsers CarVia (não duplicar código).
"""
from app.hora.services.parsers.danfe_adapter import parse_danfe_to_hora_payload
from app.hora.services.parsers.pedido_xlsx_parser import (
    parse_pedido_xlsx,
    resolver_loja_por_cnpj,
    PedidoParseError,
    PedidoExtraido,
    ItemPedidoExtraido,
)

__all__ = [
    'parse_danfe_to_hora_payload',
    'parse_pedido_xlsx',
    'resolver_loja_por_cnpj',
    'PedidoParseError',
    'PedidoExtraido',
    'ItemPedidoExtraido',
]
