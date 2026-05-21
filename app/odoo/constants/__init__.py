"""Constantes consolidadas Odoo (operacoes fiscais, locations).

Origem dos dados: docs/inventario-2026-05/00-decisoes/D000-D002 (audit F0).
"""
from .operacoes_fiscais import (  # noqa: F401
    MATRIZ_INTERCOMPANY,
    CODIGO_PARA_COMPANY_ID,
    COMPANY_PARTNER_ID,
    get_operacao,
    resolver_operacao_por_tipo_produto,
    resolver_fiscal_position,
    resolver_entrada,
)
from .locations import COMPANY_LOCATIONS, get_location_id  # noqa: F401
