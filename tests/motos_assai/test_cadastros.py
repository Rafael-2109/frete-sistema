def test_lista_lojas_acesso(login_admin):
    r = login_admin.get('/motos-assai/lojas')
    assert r.status_code == 200


def test_lista_modelos_acesso(login_admin):
    r = login_admin.get('/motos-assai/modelos')
    assert r.status_code == 200


def test_dashboard_renderiza(login_admin):
    r = login_admin.get('/motos-assai/')
    assert r.status_code == 200
    assert b'Opera' in r.data


def test_api_testar_regex(login_admin):
    r = login_admin.post('/motos-assai/modelos/api/testar-regex',
                         json={'regex': r'^LA\d+$', 'chassi': 'LA12345'})
    assert r.status_code == 200
    body = r.get_json()
    assert body['ok'] is True
    assert body['bate'] is True


def test_api_testar_regex_no_match(login_admin):
    r = login_admin.post('/motos-assai/modelos/api/testar-regex',
                         json={'regex': r'^LA\d+$', 'chassi': 'XX12345'})
    assert r.status_code == 200
    body = r.get_json()
    assert body['bate'] is False


def test_api_testar_regex_invalido(login_admin):
    r = login_admin.post('/motos-assai/modelos/api/testar-regex',
                         json={'regex': '[invalid', 'chassi': 'X'})
    assert r.status_code == 400
