"""Backends do motor de roteirizacao.

- directions_chunking_backend: usa Google Directions (key atual). <=23
  intermediarios = 1 request com optimize:true. Acima = chunking sequencial.
- route_optimization_backend: Google Route Optimization API (optimizeTours,
  SKU Single Vehicle). Otimizacao GLOBAL real, sem teto de 25 paradas. Requer
  projeto (env ROUTE_OPTIMIZATION_PROJECT) + credencial da service account, por
  uma de duas vias: GOOGLE_CREDENTIALS_JSON (conteudo do JSON da SA na propria
  env var — usado no Render) ou ADC padrao (GOOGLE_APPLICATION_CREDENTIALS
  apontando um arquivo/Secret File). GOOGLE_CREDENTIALS_JSON tem prioridade.
- default_backend: usa Route Optimization se configurado; senao (ou em erro)
  cai para directions_chunking_backend.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)
_BASE_DIRECTIONS = "https://maps.googleapis.com/maps/api/directions/json"
_RO_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
# Janela global (sem time windows nos shipments) — 7 dias cobrem o tempo de
# viagem de qualquer rota de entrega e ficam dentro do maximo da API.
_RO_GLOBAL_START = "2024-01-01T00:00:00Z"
_RO_GLOBAL_END = "2024-01-08T00:00:00Z"


def _api_key():
    return os.getenv('GOOGLE_MAPS_API_KEY', '')


def _ro_project():
    return os.getenv('ROUTE_OPTIMIZATION_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')


def _route_optimization_ativo():
    """True se ha projeto GCP configurado (a credencial vem via ADC/google-auth)."""
    return bool(_ro_project())


def _parse_latlng(s):
    """'lat,lng' -> (float, float). Lanca ValueError se nao for coordenada."""
    lat, lng = str(s).split(',')
    return float(lat), float(lng)


def _parse_duration_s(dur):
    """'1800s' -> 1800.0; aceita None/numero."""
    if dur is None:
        return 0.0
    s = str(dur).strip().rstrip('s')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _ro_token():
    """Access token OAuth2 da service account com scope cloud-platform.

    Prioriza GOOGLE_CREDENTIALS_JSON (conteudo do JSON da SA como env var — usado
    no Render, onde nao subimos Secret File); senao cai para ADC padrao
    (GOOGLE_APPLICATION_CREDENTIALS apontando arquivo, ou metadata server)."""
    from google.auth.transport.requests import Request as GoogleAuthRequest
    cred_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if cred_json:
        import json
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(
            json.loads(cred_json), scopes=[_RO_SCOPE])
    else:
        import google.auth
        creds, _ = google.auth.default(scopes=[_RO_SCOPE])
    creds.refresh(GoogleAuthRequest())
    return creds.token


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


def route_optimization_backend(origem, destino, waypoints, inclui_volta=False):
    """Google Route Optimization API (optimizeTours, 1 veiculo). origem/destino
    sao 'lat,lng'. Otimiza a ordem GLOBAL das paradas (sem teto de 25)."""
    project = _ro_project()
    if not project:
        raise RuntimeError("ROUTE_OPTIMIZATION_PROJECT nao configurado")
    o_lat, o_lng = _parse_latlng(origem)

    shipments = [{
        'label': str(i),
        'deliveries': [{
            'arrivalWaypoint': {'location': {'latLng': {
                'latitude': p['lat'], 'longitude': p['lng']}}}
        }],
    } for i, p in enumerate(waypoints)]

    vehicle = {'startWaypoint': {'location': {'latLng': {
        'latitude': o_lat, 'longitude': o_lng}}}}
    if inclui_volta:
        vehicle['endWaypoint'] = {'location': {'latLng': {
            'latitude': o_lat, 'longitude': o_lng}}}

    body = {
        'timeout': '20s',
        'model': {
            'shipments': shipments,
            'vehicles': [vehicle],
            'globalStartTime': _RO_GLOBAL_START,
            'globalEndTime': _RO_GLOBAL_END,
        },
        'populatePolylines': True,
    }
    url = f"https://routeoptimization.googleapis.com/v1/projects/{project}:optimizeTours"
    headers = {'Authorization': f'Bearer {_ro_token()}', 'Content-Type': 'application/json'}
    resp = requests.post(url, json=body, headers=headers, timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(f"RouteOptimization HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    routes = data.get('routes') or []
    if not routes:
        raise RuntimeError("RouteOptimization sem routes")
    route = routes[0]

    # ordem = sequencia de visits (deliveries); shipmentIndex omitido = 0 (proto JSON)
    ordem_indices, visto = [], set()
    for v in route.get('visits', []):
        idx = v.get('shipmentIndex', 0)
        if idx not in visto:
            visto.add(idx)
            ordem_indices.append(idx)
    # paradas nao roteadas (skipped) — anexa no fim para nao sumir
    for i in range(len(waypoints)):
        if i not in visto:
            ordem_indices.append(i)

    metrics = route.get('metrics', {}) or {}
    dist_km = (metrics.get('travelDistanceMeters', 0) or 0) / 1000.0
    tempo_min = _parse_duration_s(metrics.get('travelDuration') or metrics.get('totalDuration')) / 60.0
    polyline = (route.get('routePolyline') or {}).get('points', '')
    return {
        'ordem_indices': ordem_indices,
        'distancia_km': round(dist_km, 2),
        'tempo_min': round(tempo_min, 1),
        'polyline': polyline,
        'trechos': 1,
    }


def default_backend(origem, destino, waypoints, inclui_volta=False):
    """Route Optimization se configurado; senao (ou em erro) Directions+chunking."""
    if _route_optimization_ativo():
        try:
            return route_optimization_backend(origem, destino, waypoints, inclui_volta)
        except Exception as e:
            logger.warning("Route Optimization falhou (%s) — fallback Directions+chunking", e)
    return directions_chunking_backend(origem, destino, waypoints, inclui_volta)
