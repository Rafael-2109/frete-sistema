"""Wrapper HTTP autenticado para a API TagPlus.

- Resolve token (refresh se necessario)
- Adiciona X-Api-Version: 2.0
- Em 401 persistente, forca um refresh e re-tenta uma vez
- Timeout default 60s; sobrescrever via kwarg
"""
from __future__ import annotations

import logging
import os

import requests

from app.hora.models.tagplus import HoraTagPlusConta
from app.hora.services.tagplus.oauth_client import OAuthClient

logger = logging.getLogger(__name__)


class ApiClient:
    DEFAULT_TIMEOUT = 60

    def __init__(self, conta: HoraTagPlusConta):
        self.conta = conta
        self.oauth = OAuthClient(conta)
        self.base = os.environ.get('HORA_TAGPLUS_BASE_URL', 'https://api.tagplus.com.br')

    def _headers(self, extra: dict | None = None, *, content_type: bool = True) -> dict:
        token_plain = self.oauth.get_access_token_plain()
        headers = {
            'Authorization': f'Bearer {token_plain}',
            'X-Api-Version': '2.0',
            'Accept': 'application/json',
        }
        if content_type:
            headers['Content-Type'] = 'application/json; charset=utf-8'
        if extra:
            headers.update(extra)
        return headers

    # ----- Verbs -----

    def get(self, path: str, params: dict | None = None, **kwargs) -> requests.Response:
        return self._request('GET', path, params=params, content_type=False, **kwargs)

    def post(
        self,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
        **kwargs,
    ) -> requests.Response:
        return self._request('POST', path, json=json, extra_headers=headers, **kwargs)

    def patch(
        self,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
        **kwargs,
    ) -> requests.Response:
        return self._request('PATCH', path, json=json, extra_headers=headers, **kwargs)

    def put(
        self,
        path: str,
        json: dict | None = None,
        **kwargs,
    ) -> requests.Response:
        return self._request('PUT', path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request('DELETE', path, content_type=False, **kwargs)

    # ----- Core -----

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        extra_headers: dict | None = None,
        content_type: bool = True,
        timeout: int | None = None,
    ) -> requests.Response:
        url = self.base + path
        timeout = timeout or self.DEFAULT_TIMEOUT
        headers = self._headers(extra_headers, content_type=content_type)

        r = requests.request(
            method, url, headers=headers, json=json, params=params, timeout=timeout,
        )

        # 401: forcar refresh e re-tentar uma vez (cobre token expirado mas valido em cache local).
        if r.status_code == 401:
            logger.warning(
                'TagPlus 401 em %s %s — forcando refresh e retry',
                method, path,
            )
            self.oauth._do_refresh()  # noqa: SLF001
            headers = self._headers(extra_headers, content_type=content_type)
            r = requests.request(
                method, url, headers=headers, json=json, params=params, timeout=timeout,
            )

        return r
