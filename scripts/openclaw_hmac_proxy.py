#!/usr/bin/env python3
"""HMAC proxy entre cloudflared (TryCloudflare) e gateway OpenClaw.

Camadas de validacao em cada request:
  1. Path prefix secreto (deve bater com OPENCLAW_PATH_PREFIX)
  2. Header X-Timestamp dentro de janela de 60s
  3. Header X-Nonce nao usado nos ultimos 120s (anti-replay)
  4. Header X-Signature = HMAC-SHA256(secret, ts || \\n || nonce || \\n || method || \\n || path || \\n || body)

Se TUDO valido: encaminha request ao gateway OpenClaw 127.0.0.1:18789, mantendo
headers Authorization (Bearer) e qualquer outro original. Resposta retorna ao
cliente intacta.

Configuracao via env (lidas no boot):
  OPENCLAW_HMAC_SECRET (obrigatorio, >= 32 bytes recomendado)
  OPENCLAW_PATH_PREFIX (obrigatorio, ex: /x7g9a2)
  OPENCLAW_PROXY_PORT  (default 18790)
  OPENCLAW_GATEWAY_PORT (default 18789)
  OPENCLAW_HMAC_TIMESTAMP_WINDOW_SEC (default 60)
  OPENCLAW_HMAC_NONCE_TTL_SEC (default 120, deve ser >= window * 2)

Roda como user service (NAO precisa root). Sugestao: systemd user unit em
~/.config/systemd/user/openclaw-hmac-proxy.service

Uso standalone:
  $ export OPENCLAW_HMAC_SECRET="<64-char-base64>"
  $ export OPENCLAW_PATH_PREFIX="/x7g9a2"
  $ python3 scripts/openclaw_hmac_proxy.py

Logs estruturados em stderr. NAO loga secrets nem body completo.
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import os
import sys
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request as urlreq
from urllib.error import HTTPError, URLError


# ─── Config ──────────────────────────────────────────────────────────────

_SECRET = os.environ.get("OPENCLAW_HMAC_SECRET", "").encode("utf-8")
_PATH_PREFIX = os.environ.get("OPENCLAW_PATH_PREFIX", "").rstrip("/")
_PROXY_PORT = int(os.environ.get("OPENCLAW_PROXY_PORT", "18790"))
_GATEWAY_PORT = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789"))
_TS_WINDOW = int(os.environ.get("OPENCLAW_HMAC_TIMESTAMP_WINDOW_SEC", "60"))
_NONCE_TTL = int(os.environ.get("OPENCLAW_HMAC_NONCE_TTL_SEC", "120"))
_GATEWAY_BASE = f"http://127.0.0.1:{_GATEWAY_PORT}"
_MAX_BODY_BYTES = 5 * 1024 * 1024  # 5MB


logging.basicConfig(
    level=os.environ.get("OPENCLAW_PROXY_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("openclaw-hmac-proxy")


# ─── Validacao boot ──────────────────────────────────────────────────────

def _validate_config() -> None:
    if len(_SECRET) < 32:
        raise SystemExit(
            "OPENCLAW_HMAC_SECRET ausente ou < 32 bytes. "
            "Gere com: python -c 'import secrets;print(secrets.token_urlsafe(48))'"
        )
    if not _PATH_PREFIX or not _PATH_PREFIX.startswith("/") or len(_PATH_PREFIX) < 6:
        raise SystemExit(
            "OPENCLAW_PATH_PREFIX ausente ou muito curto. "
            "Use string aleatoria de 6-12 chars com '/' inicial. Ex: /x7g9a2"
        )
    if _NONCE_TTL < _TS_WINDOW * 2:
        raise SystemExit(
            f"OPENCLAW_HMAC_NONCE_TTL_SEC ({_NONCE_TTL}) deve ser >= 2x do "
            f"OPENCLAW_HMAC_TIMESTAMP_WINDOW_SEC ({_TS_WINDOW}) para evitar "
            "replay com nonces fora da janela de TS"
        )


# ─── Anti-replay: cache de nonces TTL ───────────────────────────────────

class _NonceCache:
    """Set de nonces vistos com expiracao automatica."""

    def __init__(self, ttl_sec: int) -> None:
        self._ttl = ttl_sec
        self._lock = threading.Lock()
        self._data: OrderedDict[str, float] = OrderedDict()

    def check_and_add(self, nonce: str) -> bool:
        """True = nonce novo (aceitar). False = ja visto (rejeitar)."""
        now = time.monotonic()
        with self._lock:
            # Expira entradas antigas (FIFO + TTL)
            while self._data:
                _oldest_nonce, ts = next(iter(self._data.items()))
                if now - ts > self._ttl:
                    self._data.popitem(last=False)
                else:
                    break
            if nonce in self._data:
                return False
            self._data[nonce] = now
            return True


_nonce_cache = _NonceCache(_NONCE_TTL)


# ─── Validacao HMAC ──────────────────────────────────────────────────────

def _expected_signature(ts: str, nonce: str, method: str, path: str, body: bytes) -> str:
    """HMAC-SHA256 com mensagem canonica."""
    msg = b"\n".join([
        ts.encode("utf-8"),
        nonce.encode("utf-8"),
        method.encode("utf-8"),
        path.encode("utf-8"),
        body,
    ])
    return hmac.new(_SECRET, msg, hashlib.sha256).hexdigest()


def _check_timestamp(ts_str: str) -> bool:
    try:
        ts = int(ts_str)
    except (TypeError, ValueError):
        return False
    now = int(time.time())
    return abs(now - ts) <= _TS_WINDOW


# ─── HTTP handler ────────────────────────────────────────────────────────

class _ProxyHandler(BaseHTTPRequestHandler):
    """Request handler unico para todos os metodos."""

    server_version = "OpenClaw-HMAC-Proxy/1.0"
    sys_version = ""

    # ─── Helpers ─────────────────────────────────────────────────────

    def _reject(self, status: int, reason: str) -> None:
        client_ip = self.client_address[0] if self.client_address else "?"
        logger.warning(
            "REJECT %d path=%s reason=%s client=%s ua=%r",
            status, self.path, reason, client_ip,
            self.headers.get("User-Agent", "")[:80],
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "16")
        self.end_headers()
        self.wfile.write(b'{"error":"deny"}')

    def _read_body(self) -> bytes | None:
        length_hdr = self.headers.get("Content-Length")
        if length_hdr is None:
            return b""
        try:
            length = int(length_hdr)
        except ValueError:
            return None
        if length < 0 or length > _MAX_BODY_BYTES:
            return None
        if length == 0:
            return b""
        return self.rfile.read(length)

    # ─── Forward ─────────────────────────────────────────────────────

    def _forward(self, method: str, gateway_path: str, body: bytes) -> None:
        url = f"{_GATEWAY_BASE}{gateway_path}"
        # Remove headers hop-by-hop e os de validacao HMAC (gateway nao precisa)
        skip_headers = {
            "host", "connection", "content-length", "transfer-encoding",
            "x-timestamp", "x-nonce", "x-signature",
        }
        fwd_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in skip_headers
        }
        req = urlreq.Request(url, data=body, method=method, headers=fwd_headers)
        try:
            with urlreq.urlopen(req, timeout=20) as resp:
                self.send_response(resp.status)
                for hk, hv in resp.headers.items():
                    if hk.lower() in {"transfer-encoding", "connection"}:
                        continue
                    self.send_header(hk, hv)
                self.end_headers()
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except HTTPError as exc:
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            err_body = exc.read() or b'{"error":"upstream"}'
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
        except URLError as exc:
            logger.error("Upstream unreachable: %s", exc)
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            body = b'{"error":"gateway_unreachable"}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    # ─── Validacao + dispatch ────────────────────────────────────────

    def _handle(self, method: str) -> None:
        # 1. Path prefix
        if not self.path.startswith(_PATH_PREFIX + "/") and self.path != _PATH_PREFIX:
            self._reject(404, "path_prefix_mismatch")
            return
        gateway_path = self.path[len(_PATH_PREFIX):] or "/"

        # 2. Headers obrigatorios
        ts = self.headers.get("X-Timestamp", "")
        nonce = self.headers.get("X-Nonce", "")
        sig = self.headers.get("X-Signature", "")
        if not ts or not nonce or not sig:
            self._reject(401, "missing_hmac_headers")
            return

        # 3. Janela de tempo
        if not _check_timestamp(ts):
            self._reject(401, "timestamp_out_of_window")
            return

        # 4. Body (max 5MB)
        body = self._read_body()
        if body is None:
            self._reject(413, "body_too_large_or_invalid")
            return

        # 5. Signature (compara em tempo constante)
        expected = _expected_signature(ts, nonce, method, gateway_path, body)
        if not hmac.compare_digest(expected, sig):
            self._reject(401, "signature_mismatch")
            return

        # 6. Anti-replay
        if not _nonce_cache.check_and_add(nonce):
            self._reject(401, "nonce_replayed")
            return

        # 7. Forward
        client_ip = self.client_address[0] if self.client_address else "?"
        logger.info(
            "OK method=%s gw_path=%s body_bytes=%d client=%s",
            method, gateway_path, len(body), client_ip,
        )
        self._forward(method, gateway_path, body)

    # HTTP method handlers
    def do_GET(self) -> None: self._handle("GET")
    def do_POST(self) -> None: self._handle("POST")
    def do_PUT(self) -> None: self._handle("PUT")
    def do_DELETE(self) -> None: self._handle("DELETE")
    def do_PATCH(self) -> None: self._handle("PATCH")
    def do_HEAD(self) -> None: self._handle("HEAD")
    def do_OPTIONS(self) -> None: self._handle("OPTIONS")

    # Silencia logs default (usamos logger proprio)
    def log_message(self, format: str, *args) -> None: # noqa: A002
        pass


# ─── Main ────────────────────────────────────────────────────────────────

def main() -> None:
    _validate_config()
    server = ThreadingHTTPServer(("127.0.0.1", _PROXY_PORT), _ProxyHandler)
    logger.info(
        "openclaw-hmac-proxy listening on 127.0.0.1:%d -> %s, "
        "path_prefix=%s, ts_window=%ds, nonce_ttl=%ds",
        _PROXY_PORT, _GATEWAY_BASE, _PATH_PREFIX, _TS_WINDOW, _NONCE_TTL,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutdown via SIGINT")
        server.server_close()


if __name__ == "__main__":
    main()
