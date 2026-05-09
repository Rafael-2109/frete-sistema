"""
Helper para envio de mensagens WhatsApp via gateway local OpenClaw.

OpenClaw e plataforma local instalada em ~/.openclaw/ que roda WhatsApp Web
via Baileys e expoe gateway HTTP em loopback:18789. Este helper encapsula
o POST /api/tools/invoke com token bucket por target para evitar ban Baileys
(WhatsApp pode flagar numero por flood).

Uso simples:
    from app.utils.whatsapp_notify import send_whatsapp
    send_whatsapp("+5511991642998", "VCD123 entregue")

Para grupo, target = JID Baileys terminando em @g.us:
    send_whatsapp("120363339022740964@g.us", "Alerta logistica: ruptura X")

Configuracao via env:
    OPENCLAW_GATEWAY_URL  (default: http://127.0.0.1:18789)
    OPENCLAW_GATEWAY_TOKEN (obrigatorio — token Bearer do gateway)
    OPENCLAW_NOTIFY_ENABLED (default: true; "false" desabilita silenciosamente)

Limites Baileys empiricos (ver memoria openclaw_whatsapp_integration):
    - <= 1 msg/s por target
    - <= 30 msgs/min por target
    - OpenClaw ja chunka mensagens > 4096 chars automaticamente

Erros:
    - Falha de rede / 5xx: WhatsAppNotifyError
    - 401/403: WhatsAppAuthError (token invalido)
    - Rate limit local excedido: WhatsAppRateLimitError
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque

import requests

logger = logging.getLogger(__name__)


# ─── Configuracao ────────────────────────────────────────────────────────

_GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
_GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
_ENABLED = os.environ.get("OPENCLAW_NOTIFY_ENABLED", "true").lower() != "false"

# Rate limit empirico Baileys
_RATE_PER_SECOND = 1
_RATE_PER_MINUTE = 30
_HTTP_TIMEOUT = 10.0


# ─── Excecoes ────────────────────────────────────────────────────────────

class WhatsAppNotifyError(RuntimeError):
    """Falha generica ao enviar mensagem WhatsApp."""


class WhatsAppAuthError(WhatsAppNotifyError):
    """Token do gateway invalido ou ausente (401/403)."""


class WhatsAppRateLimitError(WhatsAppNotifyError):
    """Rate limit local excedido (defesa pre-Baileys)."""


# ─── Token bucket por target ─────────────────────────────────────────────

class _PerTargetRateLimiter:
    """Sliding window por target (thread-safe).

    Mantem dois deques de timestamps: um para janela 1s e outro para 60s.
    Se exceder qualquer janela, levanta WhatsAppRateLimitError.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[deque, deque]] = {}

    def check_and_consume(self, target: str) -> None:
        now = time.monotonic()
        with self._lock:
            sec_q, min_q = self._windows.setdefault(target, (deque(), deque()))
            # Limpa entradas fora da janela
            while sec_q and sec_q[0] < now - 1.0:
                sec_q.popleft()
            while min_q and min_q[0] < now - 60.0:
                min_q.popleft()
            # Verifica limites
            if len(sec_q) >= _RATE_PER_SECOND:
                raise WhatsAppRateLimitError(
                    f"Rate limit por segundo excedido para {target} "
                    f"({_RATE_PER_SECOND}/s). Aguarde antes de reenviar."
                )
            if len(min_q) >= _RATE_PER_MINUTE:
                raise WhatsAppRateLimitError(
                    f"Rate limit por minuto excedido para {target} "
                    f"({_RATE_PER_MINUTE}/min). Aguarde antes de reenviar."
                )
            sec_q.append(now)
            min_q.append(now)


_rate_limiter = _PerTargetRateLimiter()


# ─── Funcao publica ──────────────────────────────────────────────────────

def send_whatsapp(
    target: str,
    text: str,
    *,
    skip_rate_limit: bool = False,
    timeout: float = _HTTP_TIMEOUT,
) -> dict:
    """Envia mensagem WhatsApp via gateway OpenClaw.

    Args:
        target: Numero E.164 (DM, ex: "+5511991642998") ou JID grupo
            (ex: "120363339022740964@g.us"). Aceita formato com ou sem "+".
        text: Texto da mensagem. OpenClaw chunka >4096 chars automaticamente.
        skip_rate_limit: True desabilita rate limit local (usar APENAS para
            envio em massa via fila externa que ja garante throttling).
        timeout: Timeout HTTP em segundos.

    Returns:
        dict: resposta JSON do gateway (`{"ok": true, "result": {...}}`).

    Raises:
        WhatsAppAuthError: 401/403 do gateway.
        WhatsAppRateLimitError: limite local excedido.
        WhatsAppNotifyError: outras falhas (rede, 5xx, token ausente).

    Exemplo:
        >>> from app.utils.whatsapp_notify import send_whatsapp
        >>> send_whatsapp("+5511991642998", "VCD123 saiu para entrega")
    """
    if not _ENABLED:
        logger.info(
            f"[WHATSAPP] Notify desabilitado (OPENCLAW_NOTIFY_ENABLED=false). "
            f"Skip target={_redact(target)} text_len={len(text)}"
        )
        return {"ok": False, "skipped": True, "reason": "disabled"}

    if not _GATEWAY_TOKEN:
        raise WhatsAppNotifyError(
            "OPENCLAW_GATEWAY_TOKEN nao configurado. "
            "Configure em .env: cat ~/.openclaw/openclaw.json | jq .gateway.auth.token"
        )

    if not target or not target.strip():
        raise WhatsAppNotifyError("target vazio")
    if not text or not text.strip():
        raise WhatsAppNotifyError("text vazio")

    target_norm = target.strip()
    if not skip_rate_limit:
        _rate_limiter.check_and_consume(target_norm)

    payload = {
        "tool": "message",
        "params": {
            "action": "send",
            "channel": "whatsapp",
            "target": target_norm,
            "message": text,
        },
    }

    url = f"{_GATEWAY_URL.rstrip('/')}/api/tools/invoke"
    headers = {
        "Authorization": f"Bearer {_GATEWAY_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise WhatsAppNotifyError(
            f"Falha de rede ao chamar gateway OpenClaw: {exc}"
        ) from exc

    if resp.status_code in (401, 403):
        raise WhatsAppAuthError(
            f"Gateway OpenClaw rejeitou token (HTTP {resp.status_code}). "
            f"Verifique OPENCLAW_GATEWAY_TOKEN."
        )
    if resp.status_code >= 500:
        raise WhatsAppNotifyError(
            f"Gateway OpenClaw retornou {resp.status_code}: {resp.text[:300]}"
        )
    if resp.status_code >= 400:
        # 400 (validacao) — propaga texto pra debug
        raise WhatsAppNotifyError(
            f"Gateway OpenClaw rejeitou request (HTTP {resp.status_code}): "
            f"{resp.text[:300]}"
        )

    try:
        body = resp.json()
    except ValueError:
        raise WhatsAppNotifyError(
            f"Gateway OpenClaw retornou body nao-JSON: {resp.text[:300]}"
        )

    logger.info(
        f"[WHATSAPP] Mensagem enviada target={_redact(target_norm)} "
        f"len={len(text)} ok={body.get('ok')}"
    )
    return body


def _redact(target: str) -> str:
    """Mascara o numero pra log (mantem 4 ultimos digitos)."""
    digits = "".join(c for c in target if c.isdigit())
    if len(digits) <= 4:
        return target
    return f"***{digits[-4:]}"


def is_configured() -> bool:
    """True se token esta configurado (helper para health checks)."""
    return bool(_GATEWAY_TOKEN) and _ENABLED
