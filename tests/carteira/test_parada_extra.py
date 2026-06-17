"""Parada extra por CNPJ (ReceitaWS) ou endereco livre: geocodifica um ponto que
entra na rota/custo mas NAO e cotavel (placeholder) — item #5."""
import json
from unittest.mock import patch


def test_parada_extra_por_cnpj(client, db):
    fake = {'status': 'OK', 'nome': 'EMPRESA X', 'logradouro': 'RUA A', 'numero': '10',
            'bairro': 'CENTRO', 'municipio': 'SAO PAULO', 'uf': 'SP', 'cep': '01000-000'}
    with patch('app.utils.api_receita.APIReceita.buscar_cnpj', return_value=fake), \
         patch('app.carteira.routes.mapa_routes.mapa_service.geocodificar_endereco',
               return_value=(-23.5, -46.6)):
        r = client.post('/carteira/mapa/api/parada-extra',
                        data=json.dumps({'cnpj': '12.345.678/0001-99'}),
                        content_type='application/json')
    assert r.status_code == 200
    b = r.get_json()
    assert b['sucesso'] is True
    assert b['coordenadas'] == {'lat': -23.5, 'lng': -46.6}
    assert b['nome'] == 'EMPRESA X'
    assert b['cidade'] == 'SAO PAULO' and b['uf'] == 'SP'


def test_parada_extra_por_endereco(client, db):
    with patch('app.carteira.routes.mapa_routes.mapa_service.geocodificar_endereco',
               return_value=(-23.4, -46.8)):
        r = client.post('/carteira/mapa/api/parada-extra',
                        data=json.dumps({'endereco': 'Av Paulista, 1000, SP'}),
                        content_type='application/json')
    assert r.status_code == 200
    assert r.get_json()['coordenadas']['lng'] == -46.8


def test_parada_extra_sem_dados_400(client, db):
    r = client.post('/carteira/mapa/api/parada-extra', data=json.dumps({}),
                    content_type='application/json')
    assert r.status_code == 400
