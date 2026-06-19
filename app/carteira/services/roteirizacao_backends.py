"""Backends do motor de roteirizacao.

- directions_chunking_backend: usa Google Directions (key atual). <=23
  intermediarios = 1 request com optimize:true. Acima = chunking sequencial.
  `respeitar_ordem=True` desliga o optimize:true (mede a sequencia dada, usado
  pelo drag-and-drop manual). Expoe `legs` (trechos com segundos/metros reais) e
  `bounds` para o desenho no mapa.
- route_optimization_backend: Google Route Optimization API (optimizeTours,
  SKU Single Vehicle). Otimizacao GLOBAL real, sem teto de 25 paradas. Requer
  projeto (env ROUTE_OPTIMIZATION_PROJECT) + credencial da service account, por
  uma de duas vias: GOOGLE_CREDENTIALS_JSON (conteudo do JSON da SA na propria
  env var — usado no Render) ou ADC padrao (GOOGLE_APPLICATION_CREDENTIALS
  apontando um arquivo/Secret File). GOOGLE_CREDENTIALS_JSON tem prioridade.
- default_backend: usa Route Optimization se configurado; senao (ou em erro)
  cai para directions_chunking_backend. Com respeitar_ordem=True usa SEMPRE
  Directions (Route Optimization nao fixa ordem barata).
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


def _fmt_min(segundos):
    """Segundos -> texto curto de tempo ('1h 14min' / '14 min')."""
    m = int(round((segundos or 0) / 60.0))
    if m >= 60:
        return f"{m // 60}h {m % 60:02d}min"
    return f"{m} min"


def _fmt_km(metros):
    """Metros -> texto curto de distancia ('12,3 km')."""
    return f"{(metros or 0) / 1000.0:.1f} km".replace('.', ',')


def _merge_bounds(acc, rb):
    """Une o bounds {northeast,southwest} de um trecho ao acumulado."""
    if not rb or 'northeast' not in rb or 'southwest' not in rb:
        return acc
    ne, sw = rb['northeast'], rb['southwest']
    if acc is None:
        return {'northeast': dict(ne), 'southwest': dict(sw)}
    acc['northeast']['lat'] = max(acc['northeast']['lat'], ne['lat'])
    acc['northeast']['lng'] = max(acc['northeast']['lng'], ne['lng'])
    acc['southwest']['lat'] = min(acc['southwest']['lat'], sw['lat'])
    acc['southwest']['lng'] = min(acc['southwest']['lng'], sw['lng'])
    return acc


def _leg_de_directions(l):
    """Trecho Directions -> formato unificado (segundos/metros reais + texto)."""
    dur_s = l['duration']['value']
    dist_m = l['distance']['value']
    return {
        'duracao_s': dur_s,
        'distancia_m': dist_m,
        'duracao': l['duration'].get('text') or _fmt_min(dur_s),
        'distancia': l['distance'].get('text') or _fmt_km(dist_m),
        'inicio': l.get('start_address'),
        'fim': l.get('end_address'),
    }


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


def directions_chunking_backend(origem, destino, waypoints, inclui_volta=False,
                                respeitar_ordem=False):
    """Ordem + metricas via Directions API, com chunking de 23.

    respeitar_ordem=True: nao envia optimize:true (mede a sequencia recebida).
    Retorna tambem `legs` (trechos com duracao_s/distancia_m) e `bounds`."""
    from app.carteira.services.roteirizacao_service import _chunk_waypoints

    pontos = list(waypoints)
    final = destino or (f"{pontos[-1]['lat']},{pontos[-1]['lng']}" if pontos else origem)

    blocos = _chunk_waypoints(pontos, tam=23)
    ordem_indices, dist_total, tempo_total, polylines = [], 0.0, 0.0, []
    legs_out, bounds_acc = [], None
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
            params['waypoints'] = (wp if respeitar_ordem else 'optimize:true|' + wp)
        resp = requests.get(_BASE_DIRECTIONS, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Directions HTTP {resp.status_code}")
        data = resp.json()
        if data.get('status') != 'OK' or not data.get('routes'):
            raise RuntimeError(f"Directions status {data.get('status')}")
        route = data['routes'][0]
        dist_total += sum(l['distance']['value'] for l in route['legs']) / 1000.0
        tempo_total += sum(l['duration']['value'] for l in route['legs']) / 60.0
        legs_out.extend(_leg_de_directions(l) for l in route['legs'])
        bounds_acc = _merge_bounds(bounds_acc, route.get('bounds'))
        polylines.append(route['overview_polyline']['points'])
        if respeitar_ordem:
            order = list(range(len(intermediarios)))
        else:
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
        # LISTA de segmentos encoded (1 por bloco do chunking). NAO juntar numa
        # string com separador: '|' (ASCII 124) faz parte do alfabeto do encoded
        # polyline (63-126), entao um split('|') no front quebraria a rota.
        'polyline': polylines,
        'trechos': len(blocos),
        'legs': legs_out,
        'bounds': bounds_acc,
    }


def route_optimization_backend(origem, destino, waypoints, inclui_volta=False,
                               respeitar_ordem=False):
    """Google Route Optimization API (optimizeTours, 1 veiculo). origem/destino
    sao 'lat,lng'. Otimiza a ordem GLOBAL das paradas (sem teto de 25).
    `respeitar_ordem` e ignorado (a API nao fixa ordem barata; o default_backend
    encaminha esse modo ao Directions)."""
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
        'populateTransitionPolylines': True,
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

    # legs por trecho a partir das transitions (alinhadas a sequencia de visits:
    # transitions[i] antecede visits[i]); usado pelo "tempo ate aqui".
    legs_out = []
    for t in route.get('transitions', []):
        ds = _parse_duration_s(t.get('travelDuration'))
        dm = t.get('travelDistanceMeters', 0) or 0
        legs_out.append({
            'duracao_s': ds, 'distancia_m': dm,
            'duracao': _fmt_min(ds), 'distancia': _fmt_km(dm),
            'inicio': None, 'fim': None,
        })

    # bounds a partir das coordenadas (origem + paradas)
    lats = [o_lat] + [p['lat'] for p in waypoints]
    lngs = [o_lng] + [p['lng'] for p in waypoints]
    bounds = {'northeast': {'lat': max(lats), 'lng': max(lngs)},
              'southwest': {'lat': min(lats), 'lng': min(lngs)}}

    metrics = route.get('metrics', {}) or {}
    dist_km = (metrics.get('travelDistanceMeters', 0) or 0) / 1000.0
    tempo_min = _parse_duration_s(metrics.get('travelDuration') or metrics.get('totalDuration')) / 60.0
    polyline = (route.get('routePolyline') or {}).get('points', '')
    return {
        'ordem_indices': ordem_indices,
        'distancia_km': round(dist_km, 2),
        'tempo_min': round(tempo_min, 1),
        # LISTA de segmentos encoded (1 trecho unico aqui). Ver nota no
        # directions_chunking_backend: '|' nao serve de separador.
        'polyline': [polyline] if polyline else [],
        'trechos': 1,
        'legs': legs_out,
        'bounds': bounds,
    }


def default_backend(origem, destino, waypoints, inclui_volta=False, respeitar_ordem=False):
    """Route Optimization se configurado; senao (ou em erro) Directions+chunking.
    No modo `respeitar_ordem` usa SEMPRE Directions (Route Optimization reordena)."""
    if respeitar_ordem:
        return directions_chunking_backend(origem, destino, waypoints, inclui_volta,
                                           respeitar_ordem=True)
    if _route_optimization_ativo():
        try:
            return route_optimization_backend(origem, destino, waypoints, inclui_volta)
        except Exception as e:
            logger.warning("Route Optimization falhou (%s) — fallback Directions+chunking", e)
    return directions_chunking_backend(origem, destino, waypoints, inclui_volta)
