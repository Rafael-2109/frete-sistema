#!/usr/bin/env python3
"""Watcher de URL do TryCloudflare quick tunnel.

Quick tunnels do cloudflared (sem named tunnel) geram URL volatil que muda
em todo restart. Este script:

  1. Le journalctl do cloudflared (ou de qualquer arquivo de log) e extrai
     a URL ativa (regex *.trycloudflare.com).
  2. Compara com a ultima URL conhecida (estado em ~/.openclaw/url_watcher.state).
  3. Quando muda: chama Render API PATCH /v1/services/<id>/env-vars para
     atualizar OPENCLAW_GATEWAY_URL em todos os services configurados.
  4. Render redeploy automatico (~9 min).

Configuracao via env vars (lidas no boot):
  RENDER_API_KEY          obrigatorio (criar em https://dashboard.render.com/u/account/api-keys)
  RENDER_SERVICE_IDS      obrigatorio, csv (ex: srv-d13m38vfte5s738t6p60,srv-d2muidggjchc73d4segg)
  OPENCLAW_PATH_PREFIX    obrigatorio (mesmo do helper/proxy)
  CHECK_INTERVAL_SEC      default 30
  CLOUDFLARED_LOG_CMD     default 'journalctl -u cloudflared -n 200 --no-pager'
                          (alternativa: 'tail -n 200 /var/log/cloudflared.log')

Estado persistente:
  ~/.openclaw/url_watcher.state — ultimo URL enviado ao Render (texto puro)

Uso standalone:
  $ export RENDER_API_KEY=rnd_xxx
  $ export RENDER_SERVICE_IDS=srv-d13m...,srv-d2mu...
  $ export OPENCLAW_PATH_PREFIX=/x7g9a2
  $ python3 scripts/openclaw_url_watcher.py

Logs em stderr.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib import request as urlreq
from urllib.error import HTTPError, URLError


# ─── Config ──────────────────────────────────────────────────────────────

_RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "").strip()
_RENDER_SERVICE_IDS = [
    s.strip() for s in os.environ.get("RENDER_SERVICE_IDS", "").split(",") if s.strip()
]
_PATH_PREFIX = os.environ.get("OPENCLAW_PATH_PREFIX", "").rstrip("/")
_CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL_SEC", "30"))
_LOG_CMD = os.environ.get(
    "CLOUDFLARED_LOG_CMD",
    "journalctl -u cloudflared -n 200 --no-pager",
)
_STATE_FILE = Path.home() / ".openclaw" / "url_watcher.state"


logging.basicConfig(
    level=os.environ.get("URL_WATCHER_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("openclaw-url-watcher")


# Match URLs trycloudflare.com (varios subdominios randomicos com '-')
_URL_REGEX = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE)


# ─── Validacao boot ──────────────────────────────────────────────────────

def _validate_config() -> None:
    if not _RENDER_API_KEY:
        raise SystemExit("RENDER_API_KEY ausente. Crie em https://dashboard.render.com/u/account/api-keys")
    if not _RENDER_SERVICE_IDS:
        raise SystemExit("RENDER_SERVICE_IDS ausente (csv de srv-...)")
    if not _PATH_PREFIX:
        raise SystemExit("OPENCLAW_PATH_PREFIX ausente (mesmo do proxy/helper)")


# ─── Extrai URL ativa do log ─────────────────────────────────────────────

def _read_log_lines() -> list[str]:
    """Roda CLOUDFLARED_LOG_CMD e retorna linhas. Retorna [] em erro."""
    try:
        result = subprocess.run(
            _LOG_CMD, shell=True, capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            logger.warning("log_cmd retornou %d: %s", result.returncode, result.stderr.strip()[:200])
            return []
        return result.stdout.splitlines()
    except Exception as exc:
        logger.error("falha ao rodar log_cmd: %s", exc)
        return []


def _extract_active_url(lines: list[str]) -> str | None:
    """Retorna a URL trycloudflare mais recente (ultima ocorrencia no log)."""
    for line in reversed(lines):
        m = _URL_REGEX.search(line)
        if m:
            return m.group(0)
    return None


# ─── Estado persistente ──────────────────────────────────────────────────

def _read_state() -> str:
    try:
        return _STATE_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except Exception as exc:
        logger.warning("state read falhou: %s", exc)
        return ""


def _write_state(url: str) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(url, encoding="utf-8")
    try:
        os.chmod(_STATE_FILE, 0o600)
    except OSError:
        pass


# ─── Render API ──────────────────────────────────────────────────────────

def _build_full_url(quick_url: str) -> str:
    """Quick URL + PATH_PREFIX = URL final usada como OPENCLAW_GATEWAY_URL.

    Helper whatsapp_notify ja apenda PATH_PREFIX automaticamente quando
    HMAC esta ativo. Logo, OPENCLAW_GATEWAY_URL deve ser SO o origin da
    quick URL (sem path).
    """
    return quick_url.rstrip("/")


def _patch_render_env(service_id: str, value: str) -> bool:
    """PUT /v1/services/<id>/env-vars/OPENCLAW_GATEWAY_URL = {value}.

    CRITICO — usar endpoint SINGULAR (`/env-vars/<key>`), NAO plural
    (`/env-vars`). O endpoint plural com PUT *substitui TODAS* as env
    vars do service (incidente 2026-05-09 — apagou ~100 vars do servico
    de producao). Endpoint singular atualiza/cria apenas a chave alvo.

    Ref: https://api-docs.render.com/reference/update-env-var
    """
    key = "OPENCLAW_GATEWAY_URL"
    url = f"https://api.render.com/v1/services/{service_id}/env-vars/{key}"
    payload = {"value": value}
    data = json.dumps(payload).encode("utf-8")
    req = urlreq.Request(
        url, data=data, method="PUT",
        headers={
            "Authorization": f"Bearer {_RENDER_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlreq.urlopen(req, timeout=20) as resp:
            if 200 <= resp.status < 300:
                logger.info("render PUT ok service=%s key=%s status=%d",
                            service_id, key, resp.status)
                return True
            logger.error("render PUT failed service=%s key=%s status=%d",
                         service_id, key, resp.status)
            return False
    except HTTPError as exc:
        body = exc.read()[:300] if exc else b""
        logger.error("render PUT http_err service=%s key=%s code=%d body=%s",
                     service_id, key, exc.code, body.decode("utf-8", "replace"))
        return False
    except URLError as exc:
        logger.error("render PUT url_err service=%s key=%s err=%s",
                     service_id, key, exc)
        return False


def _update_all_services(value: str) -> bool:
    """True se TODOS os services aceitaram. False se algum falhou."""
    ok = True
    for svc in _RENDER_SERVICE_IDS:
        if not _patch_render_env(svc, value):
            ok = False
    return ok


# ─── Main loop ───────────────────────────────────────────────────────────

def main() -> None:
    _validate_config()
    logger.info(
        "openclaw-url-watcher starting interval=%ds services=%s",
        _CHECK_INTERVAL, _RENDER_SERVICE_IDS,
    )

    last_known = _read_state()
    if last_known:
        logger.info("estado anterior: %s", last_known)

    while True:
        lines = _read_log_lines()
        active_url = _extract_active_url(lines)

        if not active_url:
            logger.debug("nenhuma URL trycloudflare encontrada no log")
        else:
            full = _build_full_url(active_url)
            if full != last_known:
                logger.info("URL mudou: %s -> %s", last_known or "<nada>", full)
                if _update_all_services(full):
                    _write_state(full)
                    last_known = full
                    logger.info("Render env atualizado em todos os services. Redeploy ~9min.")
                else:
                    logger.error("falha em algum service. Tentara novamente no proximo ciclo.")

        time.sleep(_CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("shutdown via SIGINT")
