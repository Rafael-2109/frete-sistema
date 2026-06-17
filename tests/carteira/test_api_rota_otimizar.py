import json
from unittest.mock import patch
from app.veiculos.models import Veiculo


def test_api_otimizar_retorna_custo(client, db):
    v = Veiculo(nome='TOCO_API', peso_maximo=6500, custo_km=3.0,
                custo_motorista_dia=200, custo_fixo_dia=50,
                depreciacao_mensal=3000, capacidade_pallets=14, ativo=True)
    db.session.add(v)
    db.session.flush()

    payload = {
        'clientes': [
            {'id': 'A', 'lat': -23.4, 'lng': -46.8, 'peso': 1000, 'pallet': 4, 'm3': 5},
            {'id': 'B', 'lat': -23.5, 'lng': -46.6, 'peso': 800, 'pallet': 3, 'm3': 4},
        ],
        'veiculo_id': v.id, 'inclui_volta': False, 'dias_viagem': 1,
    }
    fake = {'ordem': ['A', 'B'], 'distancia_km': 100.0, 'tempo_min': 120.0,
            'polyline': 'p', 'trechos': 1}
    with patch('app.carteira.routes.mapa_routes.otimizar_rota', return_value=fake):
        resp = client.post('/carteira/mapa/api/rota/otimizar',
                           data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['sucesso'] is True
    assert body['rota']['distancia_km'] == 100.0
    # combustivel 100*3=300; motorista 1*200; fixo 1*50; deprec 3000/30*1=100 => 650 + pedagio
    assert body['custo']['combustivel'] == 300.0
    assert body['custo']['total'] >= 650.0
    assert body['veiculo']['nome'] == 'TOCO_API'
