"""Geocoding de enderecos de loja AssaiLoja (CNPJ -> lat/lng).

Estrategia:
- Se GOOGLE_MAPS_API_KEY estiver configurada: usa Google Geocoding API (preciso, pago).
- Fallback: Nominatim (OpenStreetMap) - gratis, rate limit 1 req/s, requer User-Agent.

Cacheia resultado em AssaiLoja.latitude / longitude / geocoded_at / geocoding_provider.
Reexecuta apenas se ja geocodado e forcar=False.

NAO importar do app.hora — fronteira clara entre modulos.
"""
from __future__ import annotations

import logging
import os
import time
from decimal import Decimal
from typing import Optional, Tuple

import requests

from app import db
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger(__name__)

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
GOOGLE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
TIMEOUT_S = 10
USER_AGENT = 'frete_sistema/motos_assai (+https://nacom.goya)'


class GeocodingError(Exception):
    """Falha ao geocodar endereco."""


def _montar_endereco(loja) -> str:
    """Monta string de endereco para busca.
    AssaiLoja tem 'endereco' (logradouro+numero combinado), bairro, cidade, uf.
    """
    partes = [
        loja.endereco,
        loja.bairro,
        loja.cidade,
        loja.uf,
        'Brasil',
    ]
    return ', '.join([p.strip() for p in partes if p and p.strip()])


def _geocodar_google(endereco: str, api_key: str) -> Tuple[float, float]:
    params = {'address': endereco, 'key': api_key, 'region': 'br', 'language': 'pt-BR'}
    try:
        resp = requests.get(GOOGLE_URL, params=params, timeout=TIMEOUT_S)
    except requests.RequestException as exc:
        raise GeocodingError(f'Google: erro de rede — {exc}')
    if resp.status_code != 200:
        raise GeocodingError(f'Google: HTTP {resp.status_code}')
    data = resp.json()
    status = data.get('status')
    if status == 'ZERO_RESULTS':
        raise GeocodingError(f'Google: endereco nao encontrado — {endereco!r}')
    if status != 'OK':
        raise GeocodingError(f'Google: status={status} ({data.get("error_message", "")})')
    loc = data['results'][0]['geometry']['location']
    return float(loc['lat']), float(loc['lng'])


def _geocodar_nominatim(endereco: str) -> Tuple[float, float]:
    params = {'q': endereco, 'format': 'json', 'countrycodes': 'br', 'limit': 1}
    headers = {'User-Agent': USER_AGENT}
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=TIMEOUT_S)
    except requests.RequestException as exc:
        raise GeocodingError(f'Nominatim: erro de rede — {exc}')
    if resp.status_code == 429:
        raise GeocodingError('Nominatim: rate limit (1 req/s). Aguarde.')
    if resp.status_code != 200:
        raise GeocodingError(f'Nominatim: HTTP {resp.status_code}')
    data = resp.json()
    if not data:
        raise GeocodingError(f'Nominatim: endereco nao encontrado — {endereco!r}')
    return float(data[0]['lat']), float(data[0]['lon'])


def geocodar_loja(loja, forcar: bool = False) -> Optional[Tuple[Decimal, Decimal]]:
    """Geocoda uma AssaiLoja e salva coordenadas no banco.

    Args:
        loja: instancia AssaiLoja.
        forcar: se True, re-geocoda mesmo com cache existente.

    Returns:
        (lat, lng) em Decimal ou None se endereco insuficiente.
    """
    # Cache hit
    if not forcar and loja.latitude is not None and loja.longitude is not None:
        return (loja.latitude, loja.longitude)

    endereco = _montar_endereco(loja)
    if not endereco or len(endereco) < 10:
        logger.info('Loja %s sem endereco suficiente para geocodar: %r', loja.id, endereco)
        return None

    api_key = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()
    provider = None
    lat = lng = None

    if api_key:
        try:
            lat, lng = _geocodar_google(endereco, api_key)
            provider = 'google'
        except GeocodingError as exc:
            logger.warning('Google geocoding falhou para loja %s: %s', loja.id, exc)

    if lat is None:
        # Fallback Nominatim (gratuito). Sleep 1s para respeitar rate limit.
        time.sleep(1.0)
        try:
            lat, lng = _geocodar_nominatim(endereco)
            provider = 'nominatim'
        except GeocodingError as exc:
            logger.warning('Nominatim falhou para loja %s: %s', loja.id, exc)
            raise

    loja.latitude = Decimal(str(lat))
    loja.longitude = Decimal(str(lng))
    loja.geocoded_at = agora_brasil_naive()
    loja.geocoding_provider = provider
    db.session.commit()

    logger.info(
        'Loja %s geocodada via %s: %s, %s',
        loja.id, provider, lat, lng,
    )
    return (loja.latitude, loja.longitude)


def geocodar_lote(lojas, forcar: bool = False) -> dict:
    """Geocoda varias AssaiLojas sequencialmente.

    Returns:
        dict com chaves 'ok' (int), 'erro' (int), 'ja_geocodadas' (int).
    """
    resultado = {'ok': 0, 'erro': 0, 'ja_geocodadas': 0}
    for loja in lojas:
        if not forcar and loja.latitude is not None and loja.longitude is not None:
            resultado['ja_geocodadas'] += 1
            continue
        try:
            coords = geocodar_loja(loja, forcar=forcar)
            if coords is not None:
                resultado['ok'] += 1
            else:
                resultado['erro'] += 1
        except GeocodingError:
            resultado['erro'] += 1
    return resultado
