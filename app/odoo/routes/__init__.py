"""
Rotas do Módulo Odoo
====================

Rotas para integração com o Odoo ERP organizadas por domínio.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from app.odoo.routes.carteira import carteira_bp
from app.odoo.routes.faturamento import faturamento_bp

__all__ = [
    'carteira_bp',
    'faturamento_bp'
] 