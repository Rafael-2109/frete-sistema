"""Smoke HTTP da tela de transferencia de estoque: auth (admin/non-admin) + contrato JSON.

Usa o `client` do conftest (LOGIN_DISABLED + CSRF off). current_user via patch do _get_user.
Odoo mockado por patch de get_odoo_connection no modulo de rotas.
"""
from unittest.mock import MagicMock, patch


def _admin():
    u = MagicMock(); u.is_authenticated = True; u.perfil = 'administrador'
    u.id = 1; u.nome = 'Admin'; return u


def _normal():
    u = MagicMock(); u.is_authenticated = True; u.perfil = 'vendedor'
    u.id = 2; u.nome = 'Vendedor'; return u


def test_tela_admin_200(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/estoque/transferencia-estoque')
    assert resp.status_code == 200


def test_tela_non_admin_redirect(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.get('/estoque/transferencia-estoque')
    assert resp.status_code == 302  # require_admin redireciona


def test_dados_codigo_non_admin_403(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.get('/estoque/transferencia-estoque/api/dados-codigo?codigo=1&empresa=FB')
    assert resp.status_code == 403


def test_dados_codigo_agrupa_por_local_e_lote(client):
    fake_quants = {'total_quants': 3, 'quants': [
        {'id': 1, 'cod': '4729098', 'product_name': 'AZEITE', 'tracking': 'lot',
         'pid': 100, 'company_id': 4, 'empresa': 'CD', 'location_id': 32,
         'location_name': 'CD/Estoque', 'lot_id': 56426, 'lote': '139/26',
         'quantity': 800.0, 'reserved_quantity': 200.0, 'available': 600.0},
        {'id': 2, 'cod': '4729098', 'product_name': 'AZEITE', 'tracking': 'lot',
         'pid': 100, 'company_id': 4, 'empresa': 'CD', 'location_id': 32,
         'location_name': 'CD/Estoque', 'lot_id': 56427, 'lote': '140/26',
         'quantity': 400.0, 'reserved_quantity': 0.0, 'available': 400.0},
        {'id': 3, 'cod': '4729098', 'product_name': 'AZEITE', 'tracking': 'lot',
         'pid': 100, 'company_id': 4, 'empresa': 'CD', 'location_id': 31090,
         'location_name': 'CD/Indisponivel', 'lot_id': 30856, 'lote': 'MIGRAÇÃO',
         'quantity': 50.0, 'reserved_quantity': 0.0, 'available': 50.0},
    ]}
    svc = MagicMock(); svc.listar_quants.return_value = fake_quants
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.StockQuantQueryService', return_value=svc):
        resp = client.get('/estoque/transferencia-estoque/api/dados-codigo?codigo=4729098&empresa=CD')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True
    assert d['produto']['cod'] == '4729098'
    locais = {l['location_name']: l for l in d['por_local']}
    assert locais['CD/Estoque']['qty'] == 1200.0
    assert locais['CD/Estoque']['disponivel'] == 1000.0
    assert locais['CD/Indisponivel']['is_indisp'] is True
    lotes = {l['lote']: l for l in d['por_lote']}
    assert lotes['MIGRAÇÃO']['is_migracao'] is True
    assert d['reservada_total'] == 200.0


def test_autocomplete_produto_filtra_min_chars(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/produto?q=a')
    assert resp.status_code == 200
    assert resp.get_json() == []  # < 2 chars


def test_autocomplete_produto_ok(client):
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'default_code': '4729098', 'name': 'AZEITE', 'tracking': 'lot'},
        {'id': 101, 'default_code': None, 'name': 'SEM CODIGO', 'tracking': 'none'},
    ]
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=odoo):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/produto?q=azeite')
    out = resp.get_json()
    assert len(out) == 1  # sem default_code é descartado
    assert out[0]['cod'] == '4729098' and out[0]['product_id'] == 100
    assert out[0]['label'].startswith('4729098')


def test_autocomplete_local_por_empresa(client):
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 32, 'complete_name': 'CD/Estoque'},
        {'id': 31090, 'complete_name': 'CD/Indisponivel'},
    ]
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=odoo):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/local?q=cd&empresa=CD')
    out = resp.get_json()
    assert {o['location_id'] for o in out} == {32, 31090}
    # domain usou company_id da empresa CD (4)
    domain = odoo.search_read.call_args[0][1]
    assert ['company_id', '=', 4] in domain


def test_autocomplete_local_empresa_invalida(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/local?q=x&empresa=ZZ')
    assert resp.status_code == 200 and resp.get_json() == []
