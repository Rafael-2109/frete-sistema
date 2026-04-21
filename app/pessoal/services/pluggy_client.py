"""Cliente Pluggy — wrapper sobre pluggy_sdk com cache Redis de api_key.

Pluggy API Key expira em 2h. Cacheamos em Redis com TTL 100min
(margem de seguranca) para evitar POST /auth a cada request.

Uso:
    from app.pessoal.services.pluggy_client import get_pluggy_client
    client = get_pluggy_client()
    token = client.create_connect_token(client_user_id="55")

Documentacao: https://docs.pluggy.ai/docs/authentication
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterator, Optional

import requests

logger = logging.getLogger(__name__)


# TTL do cache da api_key (Pluggy expira em 2h = 7200s; cacheamos 100min = 6000s)
API_KEY_TTL_SECONDS = 6000
API_KEY_REDIS_KEY = "pluggy:api_key"


@dataclass
class ConnectTokenResult:
    access_token: str
    raw: dict[str, Any]


class PluggyClientError(Exception):
    """Erro generico do cliente Pluggy."""


class PluggyClient:
    """Cliente HTTP minimalista da Pluggy API v1.

    Usamos requests direto ao inves do pluggy-sdk completo porque:
    - Controle total do cache Redis da api_key
    - Menos dependencias indiretas (pluggy-sdk traz 20+ transitivas)
    - API Pluggy e simples (REST JSON, ~15 endpoints usados)
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_host: Optional[str] = None,
        redis_conn=None,
    ):
        self.client_id = client_id or os.environ.get("PLUGGY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("PLUGGY_CLIENT_SECRET")
        self.api_host = (api_host or os.environ.get("PLUGGY_API_HOST") or
                         "https://api.pluggy.ai").rstrip("/")
        self._redis = redis_conn
        self._api_key_memory: Optional[str] = None
        self._api_key_memory_expires_at: Optional[datetime] = None

        if not self.client_id or not self.client_secret:
            raise PluggyClientError(
                "PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET sao obrigatorios no env."
            )

    # ------------------------------------------------------------------
    # Auth + cache
    # ------------------------------------------------------------------
    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from app.portal.workers import get_redis_connection
            self._redis = get_redis_connection()
        except Exception as exc:
            logger.warning(f"Redis indisponivel para cache api_key: {exc}")
            self._redis = None
        return self._redis

    def _get_api_key_from_cache(self) -> Optional[str]:
        # Memory first
        if (self._api_key_memory and self._api_key_memory_expires_at
                and datetime.utcnow() < self._api_key_memory_expires_at):
            return self._api_key_memory
        # Redis
        redis_conn = self._get_redis()
        if redis_conn is None:
            return None
        try:
            cached = redis_conn.get(API_KEY_REDIS_KEY)
            if cached:
                if isinstance(cached, bytes):
                    return cached.decode("utf-8")
                if isinstance(cached, str):
                    return cached
                return str(cached)
        except Exception as exc:
            logger.warning(f"Erro ao ler api_key do Redis: {exc}")
        return None

    def _store_api_key(self, api_key: str) -> None:
        self._api_key_memory = api_key
        self._api_key_memory_expires_at = (
            datetime.utcnow() + timedelta(seconds=API_KEY_TTL_SECONDS)
        )
        redis_conn = self._get_redis()
        if redis_conn is not None:
            try:
                redis_conn.setex(API_KEY_REDIS_KEY, API_KEY_TTL_SECONDS, api_key)
            except Exception as exc:
                logger.warning(f"Erro ao gravar api_key no Redis: {exc}")

    def _authenticate(self) -> str:
        """POST /auth → api_key. Chamada rara (a cada 100min)."""
        url = f"{self.api_host}/auth"
        payload = {"clientId": self.client_id, "clientSecret": self.client_secret}
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            raise PluggyClientError(
                f"POST /auth falhou {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json()
        api_key = data.get("apiKey")
        if not api_key:
            raise PluggyClientError(f"Resposta /auth sem apiKey: {data}")
        self._store_api_key(api_key)
        logger.info("Pluggy api_key autenticada e cacheada.")
        return api_key

    def _get_api_key(self) -> str:
        cached = self._get_api_key_from_cache()
        if cached:
            return cached
        return self._authenticate()

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------
    def _request(
        self, method: str, path: str, *,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        use_api_key: bool = True,
        retry_on_401: bool = True,
    ) -> dict:
        url = f"{self.api_host}{path}"
        headers = {"Content-Type": "application/json"}
        if use_api_key:
            headers["X-API-KEY"] = self._get_api_key()

        resp = requests.request(
            method, url, headers=headers, params=params, json=json_body, timeout=30,
        )

        # 401 — api_key expirada antes do TTL; refresh e retry 1x
        if resp.status_code == 401 and use_api_key and retry_on_401:
            logger.warning("Pluggy retornou 401 — refazendo /auth e retry.")
            self._authenticate()
            return self._request(
                method, path, params=params, json_body=json_body,
                use_api_key=True, retry_on_401=False,
            )

        if not resp.ok:
            raise PluggyClientError(
                f"{method} {path} falhou {resp.status_code}: {resp.text[:500]}"
            )

        try:
            return resp.json()
        except json.JSONDecodeError:
            return {}

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------
    def create_connect_token(
        self,
        client_user_id: Optional[str] = None,
        item_id: Optional[str] = None,
        oauth_redirect_uri: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> ConnectTokenResult:
        """POST /connect_token — token valido por 30min para widget.

        Se item_id informado, o token permite atualizar/re-conectar item existente.
        """
        body: dict[str, Any] = {"options": {}}
        if client_user_id:
            body["options"]["clientUserId"] = client_user_id
        if oauth_redirect_uri:
            body["options"]["oauthRedirectUri"] = oauth_redirect_uri
        if webhook_url:
            body["options"]["webhookUrl"] = webhook_url
        if item_id:
            body["itemId"] = item_id

        data = self._request("POST", "/connect_token", json_body=body)
        token = data.get("accessToken") or data.get("connectToken")
        if not token:
            raise PluggyClientError(f"Resposta connect_token sem accessToken: {data}")
        return ConnectTokenResult(access_token=token, raw=data)

    def get_item(self, item_id: str) -> dict:
        return self._request("GET", f"/items/{item_id}")

    def delete_item(self, item_id: str) -> dict:
        return self._request("DELETE", f"/items/{item_id}")

    def trigger_item_update(self, item_id: str) -> dict:
        """PATCH /items/{id} — dispara nova sync manual."""
        return self._request("PATCH", f"/items/{item_id}", json_body={})

    def list_accounts(self, item_id: str) -> list[dict]:
        data = self._request("GET", "/accounts", params={"itemId": item_id})
        return data.get("results", [])

    def get_account(self, account_id: str) -> dict:
        return self._request("GET", f"/accounts/{account_id}")

    def list_transactions(
        self,
        account_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 500,
    ) -> dict:
        """GET /transactions — paginado. Retorna {results, total, totalPages, page}."""
        params: dict[str, Any] = {
            "accountId": account_id,
            "page": page,
            "pageSize": page_size,
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._request("GET", "/transactions", params=params)

    def iter_transactions(
        self,
        account_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page_size: int = 500,
    ) -> Iterator[dict]:
        """Iterador sobre TODAS as paginas de transactions."""
        page = 1
        while True:
            data = self.list_transactions(
                account_id, from_date=from_date, to_date=to_date,
                page=page, page_size=page_size,
            )
            results = data.get("results", [])
            if not results:
                break
            for tx in results:
                yield tx
            total_pages = data.get("totalPages") or 1
            if page >= total_pages:
                break
            page += 1

    def list_categories(self, parent_id: Optional[str] = None) -> list[dict]:
        params = {"parentId": parent_id} if parent_id else None
        data = self._request("GET", "/categories", params=params)
        return data.get("results", [])

    def list_connectors(self, countries: Optional[list[str]] = None) -> list[dict]:
        params: dict[str, Any] = {}
        if countries:
            params["countries"] = ",".join(countries)
        data = self._request("GET", "/connectors", params=params)
        return data.get("results", [])

    def get_credit_card_bills(self, account_id: str) -> list[dict]:
        data = self._request("GET", f"/accounts/{account_id}/bills")
        return data.get("results", [])


# ------------------------------------------------------------------
# Singleton helper
# ------------------------------------------------------------------
_client_singleton: Optional[PluggyClient] = None


def get_pluggy_client() -> PluggyClient:
    """Retorna instancia singleton do cliente Pluggy."""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = PluggyClient()
    return _client_singleton
