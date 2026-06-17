from unittest.mock import patch
from app.carteira.services import roteirizacao_backends as b

PARADAS = [{'lat': -23.1, 'lng': -46.1}, {'lat': -23.2, 'lng': -46.2}, {'lat': -23.3, 'lng': -46.3}]

_RESP_OK = {
    'routes': [{
        'visits': [{'shipmentIndex': 1}, {'shipmentIndex': 0}, {'shipmentIndex': 2}],
        'metrics': {'travelDistanceMeters': 12500, 'travelDuration': '1800s'},
        'routePolyline': {'points': 'abc'},
    }]
}


def test_route_optimization_monta_request_e_parseia(monkeypatch):
    monkeypatch.setenv('ROUTE_OPTIMIZATION_PROJECT', 'proj-x')
    with patch.object(b, '_ro_token', return_value='tok'), \
         patch.object(b.requests, 'post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = _RESP_OK
        r = b.route_optimization_backend('-23.0,-46.0', None, PARADAS, inclui_volta=False)

    assert r['ordem_indices'] == [1, 0, 2]
    assert r['distancia_km'] == 12.5
    assert r['tempo_min'] == 30.0
    assert r['polyline'] == 'abc'
    # body correto
    body = mock_post.call_args.kwargs['json']
    assert len(body['model']['shipments']) == 3
    assert 'endWaypoint' not in body['model']['vehicles'][0]  # sem volta
    assert body['model']['vehicles'][0]['startWaypoint']['location']['latLng']['latitude'] == -23.0
    # auth header
    assert mock_post.call_args.kwargs['headers']['Authorization'] == 'Bearer tok'


def test_route_optimization_volta_adiciona_endwaypoint(monkeypatch):
    monkeypatch.setenv('ROUTE_OPTIMIZATION_PROJECT', 'proj-x')
    with patch.object(b, '_ro_token', return_value='tok'), \
         patch.object(b.requests, 'post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = _RESP_OK
        b.route_optimization_backend('-23.0,-46.0', '-23.0,-46.0', PARADAS, inclui_volta=True)
    body = mock_post.call_args.kwargs['json']
    assert 'endWaypoint' in body['model']['vehicles'][0]


def test_default_backend_sem_projeto_usa_directions(monkeypatch):
    monkeypatch.delenv('ROUTE_OPTIMIZATION_PROJECT', raising=False)
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
    fake_dir = {'ordem_indices': [0, 1, 2], 'distancia_km': 5.0, 'tempo_min': 10.0,
                'polyline': 'd', 'trechos': 1}
    with patch.object(b, 'directions_chunking_backend', return_value=fake_dir) as mock_dir, \
         patch.object(b, 'route_optimization_backend') as mock_ro:
        r = b.default_backend('-23,-46', None, PARADAS, False)
    assert mock_dir.called
    assert not mock_ro.called
    assert r['polyline'] == 'd'


def test_default_backend_com_projeto_usa_route_opt(monkeypatch):
    monkeypatch.setenv('ROUTE_OPTIMIZATION_PROJECT', 'proj-x')
    fake_ro = {'ordem_indices': [2, 1, 0], 'distancia_km': 9.0, 'tempo_min': 20.0,
               'polyline': 'r', 'trechos': 1}
    with patch.object(b, 'route_optimization_backend', return_value=fake_ro) as mock_ro, \
         patch.object(b, 'directions_chunking_backend') as mock_dir:
        r = b.default_backend('-23,-46', None, PARADAS, False)
    assert mock_ro.called
    assert not mock_dir.called
    assert r['polyline'] == 'r'


def test_default_backend_fallback_em_erro(monkeypatch):
    monkeypatch.setenv('ROUTE_OPTIMIZATION_PROJECT', 'proj-x')
    fake_dir = {'ordem_indices': [0], 'distancia_km': 1.0, 'tempo_min': 2.0, 'polyline': 'd', 'trechos': 1}
    with patch.object(b, 'route_optimization_backend', side_effect=RuntimeError('boom')), \
         patch.object(b, 'directions_chunking_backend', return_value=fake_dir) as mock_dir:
        r = b.default_backend('-23,-46', None, PARADAS, False)
    assert mock_dir.called
    assert r['polyline'] == 'd'
