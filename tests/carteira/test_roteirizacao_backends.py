from unittest.mock import patch
from app.carteira.services import roteirizacao_backends as b


def _fake_directions_response(n_legs=2):
    legs = [{'distance': {'value': 10000}, 'duration': {'value': 600}} for _ in range(n_legs)]
    return {
        'status': 'OK',
        'routes': [{
            'legs': legs,
            'waypoint_order': list(range(max(0, n_legs - 1))),
            'overview_polyline': {'points': 'abc'},
        }],
    }


def test_backend_single_request_ate_23():
    paradas = [{'id': str(i), 'lat': -23 - i * 0.01, 'lng': -46 - i * 0.01} for i in range(3)]
    with patch.object(b.requests, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = _fake_directions_response(n_legs=3)
        r = b.directions_chunking_backend('CD', None, paradas, inclui_volta=False)
    assert r['trechos'] == 1
    assert r['distancia_km'] == 30.0  # 3 legs * 10km
    assert len(r['ordem_indices']) == len(paradas)
