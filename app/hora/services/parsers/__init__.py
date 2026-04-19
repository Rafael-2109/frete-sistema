"""Parsers do módulo HORA.

Padrão: adapters finos sobre parsers CarVia (não duplicar código).
"""
from app.hora.services.parsers.danfe_adapter import parse_danfe_to_hora_payload
from app.hora.services.parsers.pedido_xlsx_parser import (
    CNPJ_MATRIZ_HORA,
    cnpj_matriz_presente,
    parse_pedido_xlsx,
    resolver_loja_por_cnpj,
    resolver_loja_por_apelido,
    PedidoParseError,
    PedidoExtraido,
    ItemPedidoExtraido,
)

__all__ = [
    'CNPJ_MATRIZ_HORA',
    'cnpj_matriz_presente',
    'parse_danfe_to_hora_payload',
    'parse_pedido_xlsx',
    'resolver_loja_por_cnpj',
    'resolver_loja_por_apelido',
    'PedidoParseError',
    'PedidoExtraido',
    'ItemPedidoExtraido',
]
