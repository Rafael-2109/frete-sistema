import json
from unittest.mock import patch


def test_adicionar_cliente_por_lote(client, db):
    fake_clientes = [{'cliente_id': 'abc', 'cliente': {'nome': 'X'},
                      'coordenadas': {'lat': -23.4, 'lng': -46.8},
                      'totais': {'peso': 100, 'pallet': 2, 'valor': 500, 'qtd_pedidos': 1},
                      'pedidos': [], 'endereco': {}}]
    with patch('app.carteira.routes.mapa_routes.mapa_service.obter_clientes_para_mapa',
               return_value=fake_clientes):
        r = client.post('/carteira/mapa/api/rota/adicionar-cliente',
                        data=json.dumps({'lotes': ['LX']}), content_type='application/json')
    assert r.status_code == 200
    body = r.get_json()
    assert body['sucesso'] is True
    assert body['clientes'][0]['cliente_id'] == 'abc'


def test_adicionar_sem_lote_400(client, db):
    r = client.post('/carteira/mapa/api/rota/adicionar-cliente',
                    data=json.dumps({}), content_type='application/json')
    assert r.status_code == 400


def test_adicionar_nao_encontrado_404(client, db):
    with patch('app.carteira.routes.mapa_routes.mapa_service.obter_clientes_para_mapa',
               return_value=[]):
        r = client.post('/carteira/mapa/api/rota/adicionar-cliente',
                        data=json.dumps({'lotes': ['NAO_EXISTE']}), content_type='application/json')
    assert r.status_code == 404
