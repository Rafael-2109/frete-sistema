"""
Módulo de integração Odoo para Sistema de Fretes

Este módulo contém as rotas API para sincronização com o Odoo:
- Carteira de pedidos
- Faturamento consolidado
- Faturamento por produto
"""

from app.api.odoo.routes import odoo_bp

__all__ = ['odoo_bp'] 