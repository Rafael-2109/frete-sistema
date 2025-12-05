"""
Módulo de integração com Odoo para criação de pedidos de venda
"""

from .models import RegistroPedidoOdoo
from .service import (
    OdooIntegrationService,
    ResultadoCriacaoPedido,
    get_odoo_service,
    criar_pedido_odoo
)

__all__ = [
    'RegistroPedidoOdoo',
    'OdooIntegrationService',
    'ResultadoCriacaoPedido',
    'get_odoo_service',
    'criar_pedido_odoo'
]
