"""StockPickingService — gerencia stock.picking de transferencia.

Generaliza padroes em:
- app/pallet/services/emissao_nf_pallet.py:115-177 (criar_picking -> validar_picking)
- app/recebimento/services/recebimento_lf_odoo_service.py:2273-2611 (saida +
  liberar_faturamento + aguardar_invoice do robo CIEL IT)

Padrao: create -> action_confirm -> action_assign -> preencher qty_done ->
button_validate -> action_liberar_faturamento -> aguardar invoice do robo CIEL IT.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.2
"""
import logging
from typing import Any, Dict, List, Optional

from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class StockPickingService:
    """Gerencia stock.picking no Odoo de forma reutilizavel."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def criar_transferencia(
        self,
        company_origem_id: int,
        company_destino_id: int,
        location_origem_id: int,
        location_destino_id: int,
        linhas: List[Dict[str, Any]],
        picking_type_id: int,
        partner_id: Optional[int] = None,
        scheduled_date: Optional[str] = None,
        origin: Optional[str] = None,
    ) -> int:
        """Cria picking de transferencia (saida).

        Args:
            company_origem_id: company emissora.
            company_destino_id: company destino (documental, nao vai no payload
                — apenas log).
            location_origem_id: stock.location origem.
            location_destino_id: stock.location destino.
            linhas: [{'product_id': int, 'quantity': float,
                      'lot_name': str|None, 'lot_id': int|None,
                      'uom_id': int|None, 'name': str|None}, ...]
            picking_type_id: stock.picking.type id (saida da company origem).
            partner_id: parceiro destino (opcional, mas obrigatorio para
                operacoes fiscais).
            scheduled_date: 'YYYY-MM-DD HH:MM:SS' (Odoo espera UTC).
            origin: campo origin do picking (rastreabilidade).

        Returns:
            picking_id (int).

        Raises:
            ValueError: se linhas vazias.
        """
        if not linhas:
            raise ValueError('linhas vazias — picking exige ao menos 1 produto')

        move_ids = []
        for linha in linhas:
            product_id = linha['product_id']
            qty = float(linha['quantity'])
            move_payload = {
                'name': linha.get('name', f'Transf produto {product_id}'),
                'product_id': product_id,
                'product_uom_qty': qty,
                'location_id': location_origem_id,
                'location_dest_id': location_destino_id,
                'company_id': company_origem_id,
            }
            if linha.get('uom_id'):
                move_payload['product_uom'] = linha['uom_id']
            move_ids.append((0, 0, move_payload))

        picking_payload = {
            'location_id': location_origem_id,
            'location_dest_id': location_destino_id,
            'picking_type_id': picking_type_id,
            'company_id': company_origem_id,
            'move_ids': move_ids,
        }
        if partner_id:
            picking_payload['partner_id'] = partner_id
        if scheduled_date:
            picking_payload['scheduled_date'] = scheduled_date
        if origin:
            picking_payload['origin'] = origin

        picking_id = self.odoo.create('stock.picking', picking_payload)
        logger.info(
            f'Picking criado: id={picking_id} origem_company={company_origem_id} '
            f'destino_company={company_destino_id} linhas={len(linhas)}'
        )
        return picking_id
