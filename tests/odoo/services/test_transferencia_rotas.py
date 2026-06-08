"""Tests das rotas de transferencia de saldo (estoque_bp).

conftest define LOGIN_DISABLED=True e WTF_CSRF_ENABLED=False, entao o `client`
acessa as rotas sem login nem CSRF. Os testes validam caminhos que retornam
ANTES de tocar current_user.nome ou o service.
"""


def test_rota_lotes_sem_codigo(client):
    resp = client.get('/estoque/transferencia-saldo/api/lotes')
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_rota_executar_qty_invalida(client):
    # qty<=0 e validado antes de instanciar o service / usar current_user
    resp = client.post('/estoque/transferencia-saldo/api/executar',
                       json={'cod_origem': '1', 'cod_destino': '2', 'qty': 0})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is False


def test_rota_executar_sem_codigos(client):
    resp = client.post('/estoque/transferencia-saldo/api/executar',
                       json={'qty': 5})
    assert resp.get_json()['success'] is False
