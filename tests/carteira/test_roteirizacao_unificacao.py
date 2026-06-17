"""Unificacao desenho x custo (R1): backends passam a expor `legs` (trechos com
segundos/metros reais) e `bounds`, e o motor ganha modo `respeitar_ordem`
(usado pelo drag-and-drop manual). Cobre itens #1 (volta no desenho), #4 (ordem
manual) e #12 ("tempo ate aqui" via segundos reais)."""
from unittest.mock import patch
from app.carteira.services import roteirizacao_backends as b
from app.carteira.services.roteirizacao_service import otimizar_rota


def _fake_dir(n_legs=3):
    legs = [{'distance': {'value': 10000, 'text': '10 km'},
             'duration': {'value': 600, 'text': '10 min'},
             'start_address': f'A{i}', 'end_address': f'B{i}'} for i in range(n_legs)]
    return {'status': 'OK', 'routes': [{
        'legs': legs,
        'waypoint_order': list(range(max(0, n_legs - 1))),
        'overview_polyline': {'points': 'abc'},
        'bounds': {'northeast': {'lat': -23.0, 'lng': -46.0},
                   'southwest': {'lat': -23.6, 'lng': -46.9}},
    }]}


def test_directions_expoe_legs_e_bounds():
    paradas = [{'id': str(i), 'lat': -23 - i * 0.01, 'lng': -46 - i * 0.01} for i in range(3)]
    with patch.object(b.requests, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = _fake_dir(3)
        r = b.directions_chunking_backend('CD', None, paradas, inclui_volta=False)
    assert len(r['legs']) == 3
    assert r['legs'][0]['duracao_s'] == 600
    assert r['legs'][0]['distancia_m'] == 10000
    assert r['legs'][0]['duracao'] == '10 min'
    assert r['bounds']['southwest']['lat'] == -23.6
    assert r['bounds']['northeast']['lng'] == -46.0


def test_directions_respeitar_ordem_nao_envia_optimize():
    paradas = [{'id': str(i), 'lat': -23 - i * 0.01, 'lng': -46 - i * 0.01} for i in range(4)]
    with patch.object(b.requests, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = _fake_dir(4)
        r = b.directions_chunking_backend('CD', None, paradas, inclui_volta=False,
                                          respeitar_ordem=True)
        params = mock_get.call_args.kwargs['params']
    assert r['ordem_indices'] == [0, 1, 2, 3]
    assert 'optimize:true' not in params.get('waypoints', '')


def test_route_optimization_expoe_legs_de_transitions(monkeypatch):
    monkeypatch.setenv('ROUTE_OPTIMIZATION_PROJECT', 'proj-x')
    resp = {'routes': [{
        'visits': [{'shipmentIndex': 1}, {'shipmentIndex': 0}],
        'transitions': [
            {'travelDuration': '300s', 'travelDistanceMeters': 5000},
            {'travelDuration': '600s', 'travelDistanceMeters': 8000},
            {'travelDuration': '0s', 'travelDistanceMeters': 0},
        ],
        'metrics': {'travelDistanceMeters': 13000, 'travelDuration': '900s'},
        'routePolyline': {'points': 'abc'},
    }]}
    paradas = [{'lat': -23.1, 'lng': -46.1}, {'lat': -23.3, 'lng': -46.3}]
    with patch.object(b, '_ro_token', return_value='tok'), \
         patch.object(b.requests, 'post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = resp
        r = b.route_optimization_backend('-23.0,-46.0', None, paradas, inclui_volta=False)
    assert len(r['legs']) >= 2
    assert r['legs'][0]['duracao_s'] == 300
    assert r['bounds']['southwest']['lat'] <= -23.3
    assert r['bounds']['northeast']['lat'] >= -23.0


def test_otimizar_repassa_legs_bounds_e_respeitar_ordem():
    paradas = [{'id': 'A', 'lat': -23.4, 'lng': -46.8},
               {'id': 'B', 'lat': -23.5, 'lng': -46.6}]
    captured = {}

    def fake_backend(origem, destino, waypoints, inclui_volta, respeitar_ordem=False):
        captured['respeitar_ordem'] = respeitar_ordem
        return {'ordem_indices': [0, 1], 'distancia_km': 42.0, 'tempo_min': 60.0,
                'polyline': 'xyz', 'trechos': 1,
                'legs': [{'duracao_s': 600, 'distancia_m': 10000,
                          'duracao': '10 min', 'distancia': '10 km'}],
                'bounds': {'southwest': {'lat': -23.5, 'lng': -46.8},
                           'northeast': {'lat': -23.4, 'lng': -46.6}}}

    r = otimizar_rota(paradas, origem='CD', respeitar_ordem=True, backend=fake_backend)
    assert captured['respeitar_ordem'] is True
    assert r['legs'][0]['duracao_s'] == 600
    assert r['bounds']['northeast']['lng'] == -46.6
    assert r['ordem'] == ['A', 'B']
