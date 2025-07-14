"""
Utilitários do Módulo Odoo
==========================

Utilitários para integração com o Odoo ERP.
Inclui conexão, mapeamento de campos e validadores.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.mappers import (
    get_carteira_mapper,
    get_faturamento_mapper,
    get_faturamento_produto_mapper
)

__all__ = [
    'get_odoo_connection',
    'get_carteira_mapper',
    'get_faturamento_mapper',
    'get_faturamento_produto_mapper'
] 