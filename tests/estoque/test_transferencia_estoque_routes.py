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
    # por_local_lote: granularidade combinada (1 célula por location×lot)
    ll = {(c['location_name'], c['lote']): c for c in d['por_local_lote']}
    assert len(d['por_local_lote']) == 3
    assert ll[('CD/Estoque', '139/26')]['qty'] == 800.0
    assert ll[('CD/Estoque', '139/26')]['disponivel'] == 600.0
    assert ll[('CD/Estoque', '140/26')]['qty'] == 400.0
    assert ll[('CD/Indisponivel', 'MIGRAÇÃO')]['is_indisp'] is True
    assert ll[('CD/Indisponivel', 'MIGRAÇÃO')]['is_migracao'] is True


def test_simular_modo1_local_destino_vazio_erro_amigavel(client):
    """Local destino vazio (autocomplete não selecionou) → mensagem clara, sem crash int('')."""
    payload = {'modo': '1', 'empresa': 'FB', 'cod_origem': '4729098',
               'lote_nome': '139/26', 'location_id_origem': 8,
               'location_id_destino': '', 'qty': 100}
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.resolver_produto',
               return_value={'pid': 100, 'tracking': 'lot', 'name': 'AZEITE'}), \
         patch('app.estoque.transferencia_estoque_routes.StockLotService') as LotCls:
        LotCls.return_value.buscar_por_nome.return_value = 56426
        resp = client.post('/estoque/transferencia-estoque/api/simular', json=payload)
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is False
    assert 'local destino' in d['message'].lower()


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


def test_simular_modo3_propaga_dry_run(client):
    """Simular (modo 3) chama transferir_v2 com dry_run=True e retorna preview."""
    svc3 = MagicMock()
    svc3.transferir_v2.return_value = {
        'status': 'DRY_RUN_OK', 'cod_origem': '4729098', 'cod_destino': '4759098',
        'lote_nome_origem': '139/26', 'lote_nome_destino': '139/26',
        'origem_antes': 800.0, 'origem_apos': 700.0,
        'destino_antes': 0.0, 'destino_apos': 100.0, 'lote_criado': True,
        'aviso_par': True}
    payload = {'modo': '3', 'empresa': 'CD', 'cod_origem': '4729098',
               'cod_destino': '4759098', 'lote_nome_origem': '139/26',
               'lote_nome_destino': '139/26', 'location_id_origem': 32,
               'location_id_destino': 32, 'qty': 100}
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.StockLotService'), \
         patch('app.estoque.transferencia_estoque_routes.TransferenciaSaldoCodigoService', return_value=svc3):
        resp = client.post('/estoque/transferencia-estoque/api/simular', json=payload)
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True and d['aviso_par'] is True
    assert d['preview']['destino']['lote_criado'] is True
    assert svc3.transferir_v2.call_args.kwargs['dry_run'] is True
    assert svc3.transferir_v2.call_args.kwargs['company_id'] == 4


def test_executar_modo1_chama_transferir_entre_locations(client):
    """Executar (modo 1) resolve produto/lote e chama o átomo com dry_run=False."""
    svc1 = MagicMock()
    svc1.transferir_entre_locations.return_value = {
        'status': 'EXECUTADO',
        'reducao_origem': {'qty_antes': 500.0, 'qty_apos': 400.0},
        'aumento_destino': {'qty_antes': 0.0, 'qty_apos': 100.0}}
    payload = {'modo': '1', 'empresa': 'FB', 'cod_origem': '4729098',
               'lote_nome': '139/26', 'location_id_origem': 8,
               'location_id_destino': 4066, 'qty': 100}
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.resolver_produto',
               return_value={'pid': 100, 'tracking': 'lot', 'name': 'AZEITE'}), \
         patch('app.estoque.transferencia_estoque_routes.StockLotService') as LotCls, \
         patch('app.estoque.transferencia_estoque_routes.StockInternalTransferService', return_value=svc1):
        LotCls.return_value.buscar_por_nome.return_value = 56426
        resp = client.post('/estoque/transferencia-estoque/api/executar', json=payload)
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True
    kw = svc1.transferir_entre_locations.call_args.kwargs
    assert kw['dry_run'] is False and kw['company_id'] == 1
    assert kw['location_id_origem'] == 8 and kw['location_id_destino'] == 4066
    assert kw['lot_id'] == 56426


def test_executar_non_admin_403(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.post('/estoque/transferencia-estoque/api/executar', json={'modo': '1'})
    assert resp.status_code == 403


def test_simular_qty_invalida(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.post('/estoque/transferencia-estoque/api/simular',
                           json={'modo': '1', 'empresa': 'FB', 'cod_origem': '1', 'qty': 0})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is False
