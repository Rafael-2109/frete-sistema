"""Testa StockPickingService — wrapper para stock.picking de transferencia."""
import pytest
from unittest.mock import MagicMock
from app.odoo.services.stock_picking_service import StockPickingService


# ============================================================
# criar_transferencia (Task 3.1)
# ============================================================

def test_criar_transferencia_basico():
    odoo = MagicMock()
    odoo.create.return_value = 9999
    svc = StockPickingService(odoo=odoo)
    linhas = [
        {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'L1'},
        {'product_id': 1002, 'quantity': 10.0},
    ]
    picking_id = svc.criar_transferencia(
        company_origem_id=1, company_destino_id=4,
        location_origem_id=8, location_destino_id=32,
        linhas=linhas, picking_type_id=99,
    )
    assert picking_id == 9999
    args = odoo.create.call_args[0]
    assert args[0] == 'stock.picking'
    payload = args[1]
    assert payload['location_id'] == 8
    assert payload['location_dest_id'] == 32
    assert payload['picking_type_id'] == 99
    assert payload['company_id'] == 1
    assert len(payload['move_ids']) == 2


def test_criar_transferencia_validacoes():
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='linhas'):
        svc.criar_transferencia(1, 4, 8, 32, linhas=[], picking_type_id=99)
