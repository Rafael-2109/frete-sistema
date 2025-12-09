"""
Serviços do Módulo Odoo
=======================

Serviços para integração com o Odoo ERP.
Contém lógica de negócio e processamento de dados.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService
# REMOVIDO: ManufaturaOdooService - integração Manufatura/Odoo deprecated
from app.odoo.services.pedido_sync_service import PedidoSyncService

__all__ = [
    'CarteiraService',
    'FaturamentoService',
    # REMOVIDO: 'ManufaturaOdooService',
    'PedidoSyncService'
] 