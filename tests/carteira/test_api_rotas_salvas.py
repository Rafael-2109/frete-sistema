import json
from app.carteira.models import RotaSalva


def test_salvar_listar_carregar_excluir(client, db):
    payload = {'nome': 'Rota Teste', 'inclui_volta': True, 'dias_viagem': 2,
               'lotes': ['L1', 'L2'], 'ordem_otimizada': ['L2', 'L1'],
               'distancia_km': 100.0, 'custo': {'total': 800.0, 'combustivel': 300.0}}
    # salvar
    r = client.post('/carteira/mapa/api/rota/salvar', data=json.dumps(payload),
                    content_type='application/json')
    assert r.status_code == 200
    rid = r.get_json()['id']
    assert RotaSalva.query.get(rid) is not None
    # listar
    r2 = client.get('/carteira/mapa/api/rotas')
    nomes = [x['nome'] for x in r2.get_json()['rotas']]
    assert 'Rota Teste' in nomes
    # carregar
    r3 = client.get(f'/carteira/mapa/api/rota/{rid}')
    body = r3.get_json()['rota']
    assert body['lotes'] == ['L1', 'L2']
    assert float(body['custo_total']) == 800.0
    # excluir
    r4 = client.delete(f'/carteira/mapa/api/rota/{rid}')
    assert r4.get_json()['sucesso'] is True
    assert RotaSalva.query.get(rid) is None


def test_salvar_sem_lotes_400(client, db):
    r = client.post('/carteira/mapa/api/rota/salvar', data=json.dumps({'nome': 'X'}),
                    content_type='application/json')
    assert r.status_code == 400
