"""TransferenciaSaldoCodigoService — transfere saldo entre CÓDIGOS mantendo lote.

Em CD/Estoque (company 4, loc 32). É uma TROCA DE CÓDIGO: mesmo nome de lote em
produtos diferentes (origem→destino). Diferente de StockInternalTransferService
(mesmo produto, lotes diferentes). Orquestra 2 ajustes atômicos:
  1. reduzir quant origem (lote X)
  2. garantir lote X no produto destino (criar com validade do origem) + aumentar

Desacoplado da UI (sem flask/request/current_user): `usuario` entra por parâmetro.
Tela web e futura skill do gestor-estoque-odoo consomem o mesmo service.

Spec: docs/superpowers/specs/2026-05-22-transferencia-saldo-codigos-odoo-design.md
"""
import logging
from typing import Any, Dict, List, Optional

from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.services.stock_quant_adjustment_service import (
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

CASAS = 6


class TransferenciaSaldoCodigoService:
    """Transfere saldo entre códigos mantendo o lote, em CD/Estoque."""

    CD_COMPANY_ID = 4
    CD_ESTOQUE_LOC = COMPANY_LOCATIONS[4]  # 32

    def __init__(self, odoo=None, adjustment_svc=None, lot_svc=None):
        self.odoo = odoo or get_odoo_connection()
        self.lot_svc = lot_svc or StockLotService(odoo=self.odoo)
        self.adjustment_svc = adjustment_svc or StockQuantAdjustmentService(
            odoo=self.odoo, lot_svc=self.lot_svc)

    def resolver_produto(self, cod) -> Dict[str, Any]:
        """default_code -> dados do produto. Erro se 0 ou >1 ativo."""
        cod = str(cod).strip()
        res = self.odoo.search_read(
            'product.product', [['default_code', '=', cod]],
            ['id', 'default_code', 'name', 'active', 'tracking',
             'uom_id', 'use_expiration_date'], limit=0)
        ativos = [p for p in res if p.get('active')]
        candidatos = ativos or res
        if not candidatos:
            raise ValueError(f'Produto {cod} nao encontrado no Odoo')
        if len(candidatos) > 1:
            raise ValueError(
                f'Produto {cod} ambiguo: {len(candidatos)} produtos')
        p = candidatos[0]
        return {
            'product_id': p['id'], 'cod': p['default_code'], 'name': p.get('name'),
            'tracking': p.get('tracking'),
            'uom': p['uom_id'][1] if p.get('uom_id') else None,
            'use_expiration_date': bool(p.get('use_expiration_date')),
        }
