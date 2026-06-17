"""Backends do motor de roteirizacao.

- directions_chunking_backend: usa Google Directions (key atual). <=23
  intermediarios = 1 request com optimize:true. Acima = chunking sequencial.
- _route_optimization_backend: PLUG do Google Route Optimization API
  (SKU Single Vehicle). Requer service account/OAuth2 (risco R1). Stub ate habilitar.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)
_BASE_DIRECTIONS = "https://maps.googleapis.com/maps/api/directions/json"


def _api_key():
    return os.getenv('GOOGLE_MAPS_API_KEY', '')


def directions_chunking_backend(origem, destino, waypoints, inclui_volta=False):
    """Retorna ordem otimizada + metricas via Directions API, com chunking de 23."""
    from app.carteira.services.roteirizacao_service import _chunk_waypoints

    pontos = list(waypoints)
    final = destino or (f"{pontos[-1]['lat']},{pontos[-1]['lng']}" if pontos else origem)

    blocos = _chunk_waypoints(pontos, tam=23)
    ordem_indices, dist_total, tempo_total, polylines = [], 0.0, 0.0, []
    cursor_origem = origem

    for bi, bloco in enumerate(blocos):
        ultimo_bloco = (bi == len(blocos) - 1)
        usar_destino_fixo = ultimo_bloco and bool(destino)  # destino=CD (volta)
        base = pontos.index(bloco[0])
        if usar_destino_fixo:
            intermediarios = bloco               # todos otimizados; fim = CD
            destino_bloco = final
            ponto_destino_idx = None             # CD nao e ponto da lista
        else:
            intermediarios = bloco[:-1]          # otimiza todos menos o ultimo
            destino_bloco = f"{bloco[-1]['lat']},{bloco[-1]['lng']}"
            ponto_destino_idx = base + len(bloco) - 1  # ultimo ponto do bloco
        wp = '|'.join(f"{p['lat']},{p['lng']}" for p in intermediarios)
        params = {
            'origin': cursor_origem, 'destination': destino_bloco,
            'key': _api_key(), 'mode': 'driving', 'units': 'metric',
            'avoid': 'ferries', 'language': 'pt-BR',
        }
        if wp:
            params['waypoints'] = 'optimize:true|' + wp
        resp = requests.get(_BASE_DIRECTIONS, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Directions HTTP {resp.status_code}")
        data = resp.json()
        if data.get('status') != 'OK' or not data.get('routes'):
            raise RuntimeError(f"Directions status {data.get('status')}")
        route = data['routes'][0]
        dist_total += sum(l['distance']['value'] for l in route['legs']) / 1000.0
        tempo_total += sum(l['duration']['value'] for l in route['legs']) / 60.0
        polylines.append(route['overview_polyline']['points'])
        order = route.get('waypoint_order', list(range(len(intermediarios))))
        ordem_indices.extend(base + idx for idx in order)
        if ponto_destino_idx is not None:
            ordem_indices.append(ponto_destino_idx)  # ponto que virou destino do bloco
        cursor_origem = destino_bloco

    # dedup preservando ordem (overlap pode repetir o ponto de juncao)
    visto, ordem_final = set(), []
    for i in ordem_indices:
        if i not in visto:
            visto.add(i)
            ordem_final.append(i)

    return {
        'ordem_indices': ordem_final,
        'distancia_km': round(dist_total, 2),
        'tempo_min': round(tempo_total, 1),
        'polyline': polylines[0] if len(polylines) == 1 else '|'.join(polylines),
        'trechos': len(blocos),
    }


def _route_optimization_backend(origem, destino, waypoints, inclui_volta=False):
    """PLUG futuro: Google Route Optimization API (Single Vehicle). Requer
    service account/OAuth2 (R1). Habilitar quando credencial existir."""
    raise NotImplementedError("Route Optimization API pendente de service account (R1)")
