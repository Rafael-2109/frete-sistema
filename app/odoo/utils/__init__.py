"""
Utilitários do Módulo Odoo
==========================

Utilitários para integração com o Odoo ERP.
Inclui conexão, mapeamento de campos e validadores.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.carteira_mapper import CarteiraMapper
from app.odoo.utils.faturamento_mapper import FaturamentoMapper

# Funções de conveniência para manter compatibilidade
def get_carteira_mapper():
    """Obtém instância do mapeador de carteira"""
    return CarteiraMapper()

def get_faturamento_mapper():
    """Obtém instância do mapeador de faturamento"""
    return FaturamentoMapper()

# Manter compatibilidade com get_faturamento_produto_mapper (mesmo que FaturamentoMapper)
def get_faturamento_produto_mapper():
    """Obtém instância do mapeador de faturamento por produto"""
    return FaturamentoMapper()

__all__ = [
    'get_odoo_connection',
    'get_carteira_mapper',
    'get_faturamento_mapper', 
    'get_faturamento_produto_mapper',
    'FaturamentoMapper',
    'CarteiraMapper'
] 