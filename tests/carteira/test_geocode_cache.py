from unittest.mock import patch
import requests
from app.carteira.models import GeocodeCache
from app.carteira.services.mapa_service import MapaService

ENDERECO = 'Rua X, 1, Sao Paulo, SP, Brasil'
_FAKE = {'status': 'OK', 'results': [{'geometry': {'location': {'lat': -23.4, 'lng': -46.8}}}]}


def test_geocode_grava_e_le_do_banco(db):
    svc = MapaService()
    svc.geocoding_cache.clear()  # zera L1 p/ forcar caminho do banco

    with patch.object(requests, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = _FAKE
        lat1, lng1 = svc.geocodificar_endereco(ENDERECO)
    assert (lat1, lng1) == (-23.4, -46.8)

    row = GeocodeCache.query.filter_by(endereco=ENDERECO).first()
    assert row is not None and row.lat == -23.4

    # segunda chamada (L1 limpo) le do banco, sem chamar Google
    svc.geocoding_cache.clear()
    with patch.object(requests, 'get') as mock_get2:
        lat2, lng2 = svc.geocodificar_endereco(ENDERECO)
        assert mock_get2.call_count == 0
    assert (lat2, lng2) == (-23.4, -46.8)
