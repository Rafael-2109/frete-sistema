"""Testes do drill-down de movimentações Odoo."""
from unittest.mock import patch, MagicMock
from app.inventario.services.movimentacoes_odoo_service import (
    MovimentacoesOdooService,
)


def _mk_odoo(qtde=150, limit_returned=100):
    odoo = MagicMock()
    odoo.search_count.return_value = qtde

    # O servico usa search_read('stock.move.line', ...) para as ROWS (com
    # offset/limit/order) e read('product.product', ...) para enriquecer.
    # search() fica apenas para stock.move (filtro tipo) e res.users (filtro
    # usuario). Mock anterior assumia search+read (padrao antigo) e devolvia
    # search_read=[] -> rows vazias -> assert len(rows)==N falhava.
    def _rows(n):
        return [{'id': i, 'date': '2026-05-18 10:00:00',
                 'company_id': [4, 'CD'],
                 'product_id': [100, '[X] X'],
                 'lot_id': [50, 'L01'], 'qty_done': 5.0,
                 'location_id': [10, 'CD/Estoque'],
                 'location_dest_id': [20, 'CD/Saida'],
                 'move_id': [200, 'MOVE'],
                 'create_uid': [1, 'admin']}
                for i in range(1, n + 1)]

    def _search_read(model, *args, **kwargs):
        if model == 'stock.move.line':
            return _rows(min(qtde, limit_returned))
        return []
    odoo.search_read = MagicMock(side_effect=_search_read)

    def _search(model, *args, **kwargs):
        return []
    odoo.search = MagicMock(side_effect=_search)

    def _read(model, ids, fields):
        if model == 'product.product':
            return [{'id': 100, 'default_code': 'X', 'name': 'X'}]
        return []
    odoo.read = MagicMock(side_effect=_read)
    return odoo


def test_paginacao_default_100(db):
    odoo = _mk_odoo(qtde=150, limit_returned=100)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        out = MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'page': 1, 'page_size': 100,
        })
    assert out['total'] == 150
    assert out['page_size'] == 100
    assert len(out['rows']) == 100


def test_paginacao_500(db):
    odoo = _mk_odoo(qtde=1500, limit_returned=500)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        out = MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'page': 1, 'page_size': 500,
        })
    assert out['page_size'] == 500
    assert len(out['rows']) == 500


def test_filtro_empresa(db):
    odoo = _mk_odoo(qtde=10, limit_returned=10)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'empresa': 'CD',
        })
    flat = str(odoo.search_count.call_args)
    assert 'company_id' in flat
    assert '4' in flat


def test_filtro_tipo_producao(db):
    odoo = _mk_odoo(qtde=5, limit_returned=5)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'tipo': 'PRODUCAO',
        })
    # Tipo=PRODUCAO faz um search('stock.move', ...) antes do search_count
    flat = ''.join(str(c) for c in odoo.search.call_args_list)
    assert 'production_id' in flat or 'raw_material' in flat
