"""Testes do SnapshotOdooService com mock Odoo."""
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.inventario.models import InventarioSnapshotOdoo
from app.inventario.services.snapshot_odoo_service import SnapshotOdooService


def _mk_odoo_mock_estoque_simples():
    """Mock que devolve 2 quants — FB e LF — do mesmo produto."""
    odoo = MagicMock()
    state = {'searches': 0}

    def _search(model, *args, **kwargs):
        state['searches'] += 1
        if model == 'stock.quant':
            return [10, 20]
        return []

    def _read(model, ids, fields):
        if model == 'stock.quant':
            return [
                {'id': 10, 'company_id': [1, 'FB'],
                 'product_id': [100, '[4320147] PROD'],
                 'location_id': [50, 'FB/Estoque'], 'quantity': 150.0},
                {'id': 20, 'company_id': [5, 'LF'],
                 'product_id': [100, '[4320147] PROD'],
                 'location_id': [60, 'LF/Estoque'], 'quantity': 30.0},
            ]
        if model == 'product.product':
            return [{'id': 100, 'name': 'PROD AZEITONA',
                     'default_code': '4320147'}]
        if model == 'res.company':
            return []
        return []

    odoo.search = MagicMock(side_effect=_search)
    odoo.read = MagicMock(side_effect=_read)
    odoo.search_read = MagicMock(return_value=[])
    return odoo


def test_refresh_grava_estoque_por_empresa(db, ciclo):
    odoo = _mk_odoo_mock_estoque_simples()
    with patch('app.inventario.services.snapshot_odoo_service.get_odoo_connection',
               return_value=odoo), \
         patch.object(SnapshotOdooService, '_baixar_apontamentos',
                      return_value={}), \
         patch.object(SnapshotOdooService, '_baixar_compras',
                      return_value={}):
        resultado = SnapshotOdooService.refresh(ciclo.id, job=None)
    assert resultado.get('inseridos', 0) >= 1
    s = InventarioSnapshotOdoo.query.filter_by(
        ciclo_id=ciclo.id, cod_produto='4320147').first()
    assert s is not None
    assert s.estoque_fb == Decimal('150')
    assert s.estoque_lf == Decimal('30')
    assert s.estoque_cd == Decimal('0')


def test_refresh_idempotente(db, ciclo):
    odoo = _mk_odoo_mock_estoque_simples()
    with patch('app.inventario.services.snapshot_odoo_service.get_odoo_connection',
               return_value=odoo), \
         patch.object(SnapshotOdooService, '_baixar_apontamentos',
                      return_value={}), \
         patch.object(SnapshotOdooService, '_baixar_compras',
                      return_value={}):
        SnapshotOdooService.refresh(ciclo.id, job=None)
        SnapshotOdooService.refresh(ciclo.id, job=None)
    cnt = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo.id).count()
    assert cnt == 1


def test_refresh_filtra_indisponivel(db, ciclo):
    odoo = MagicMock()
    odoo.search = MagicMock(return_value=[10, 20])
    odoo.read = MagicMock(side_effect=lambda model, ids, fields: {
        'stock.quant': [
            {'id': 10, 'company_id': [1, 'FB'], 'product_id': [100, '[X] X'],
             'location_id': [50, 'FB/Estoque'], 'quantity': 100.0},
            {'id': 20, 'company_id': [1, 'FB'], 'product_id': [100, '[X] X'],
             'location_id': [99, 'FB/Indisponivel'], 'quantity': 999.0},
        ],
        'product.product': [{'id': 100, 'name': 'X', 'default_code': '1X'}],
    }.get(model, []))
    odoo.search_read = MagicMock(return_value=[])
    with patch('app.inventario.services.snapshot_odoo_service.get_odoo_connection',
               return_value=odoo), \
         patch.object(SnapshotOdooService, '_baixar_apontamentos',
                      return_value={}), \
         patch.object(SnapshotOdooService, '_baixar_compras',
                      return_value={}):
        SnapshotOdooService.refresh(ciclo.id, job=None)
    s = InventarioSnapshotOdoo.query.filter_by(
        ciclo_id=ciclo.id, cod_produto='1X').first()
    assert s.estoque_fb == Decimal('100')
