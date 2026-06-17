"""Matriz de distancias par-a-par entre as PARADAS do mapa (clientes com
coordenadas), nao mais por num_pedido — alinha com o fluxo por lotes/CarVia
(item #3)."""
from unittest.mock import patch
from app.carteira.services.mapa_service import MapaService


def _fake_dm():
    leg = lambda m, s: {'status': 'OK', 'distance': {'value': m}, 'duration': {'value': s}}
    return {'status': 'OK', 'rows': [
        {'elements': [leg(0, 0), leg(20000, 1800)]},
        {'elements': [leg(20000, 1800), leg(0, 0)]},
    ]}


def test_matriz_clientes_processa():
    svc = MapaService()
    clientes = [{'id': 'a', 'lat': -23.4, 'lng': -46.8, 'nome': 'Cli A'},
                {'id': 'b', 'lat': -23.5, 'lng': -46.6, 'nome': 'Cli B'}]
    with patch('app.carteira.services.mapa_service.requests.get') as mg:
        mg.return_value.status_code = 200
        mg.return_value.json.return_value = _fake_dm()
        m = svc.calcular_matriz_clientes(clientes)
    assert m['pedidos'] == ['Cli A', 'Cli B']           # labels = nome do cliente
    assert m['distancias'][0][1] == 20.0
    assert m['resumo']['distancia_media_km'] == 20.0
    assert m['resumo']['pares_proximos'][0]['origem'] == 'Cli A'


def test_matriz_clientes_minimo_2():
    svc = MapaService()
    m = svc.calcular_matriz_clientes([{'id': 'a', 'lat': -23.4, 'lng': -46.8, 'nome': 'A'}])
    assert 'erro' in m
