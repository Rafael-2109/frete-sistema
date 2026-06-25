"""
Helper para envio de mensagens WhatsApp via Evolution API.

Evolution API (https://github.com/EvolutionAPI/evolution-api) e um gateway
WhatsApp self-hosted baseado em Baileys (mesmo modelo nao-oficial do OpenClaw),
porem rodando 24/7 num servidor — NAO depende do PC do operador estar ligado.
Este helper e o caminho de SAIDA (outbound) quando WHATSAPP_TRANSPORT=n8n.

Diferenca de papeis na arquitetura N8N:
    - INBOUND  (WhatsApp -> agente): Evolution -> webhook -> N8N -> Flask
      (POST /api/whatsapp/n8n/inbound). O N8N normaliza o evento.
    - OUTBOUND (agente -> WhatsApp): Flask -> Evolution API DIRETO (este modulo).
      Um hop a menos: a resposta nao depende do N8N estar de pe.

Espelha a estrutura de `app/utils/whatsapp_notify.py` (gateway OpenClaw):
mesmo rate limiter por target, mesmas excecoes (reaproveitadas dali) e mesmo
`is_configured()` para health checks.

Uso simples:
    from app.utils.whatsapp_evolution import send_whatsapp_evolution
    send_whatsapp_evolution("5511991642998", "VCD123 entregue")

Para grupo, target = JID Baileys terminando em @g.us:
    send_whatsapp_evolution("120363339022740964@g.us", "Alerta: ruptura X")

Configuracao via env:
    EVOLUTION_API_URL    (obrigatorio — ex: https://evo.seudominio.com)
    EVOLUTION_API_KEY    (obrigatorio — apikey global ou da instancia)
    EVOLUTION_INSTANCE   (obrigatorio — nome da instancia, ex: "nacom")
    EVOLUTION_NOTIFY_ENABLED (default: true; "false" desabilita silenciosamente)

Endpoint usado (Evolution API v2):
    POST {EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}
    Header: apikey: <EVOLUTION_API_KEY>
    Body:   {"number": "<target>", "text": "<msg>"}

Limites Baileys empiricos (mesmos do OpenClaw, ver whatsapp_notify):
    - <= 1 msg/s por target
    - <= 30 msgs/min por target
Diferente do OpenClaw, a Evolution NAO chunka >4096 chars sozinha; este
helper fragmenta mensagens longas em blocos <= 4000 chars (split por linha).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque

import requests

# Reusa as excecoes do helper OpenClaw — contrato identico para o caller
# (services._send_whatsapp_reply trata WhatsAppNotifyError de ambos os modos).
from app.utils.whatsapp_notify import (
    WhatsAppAuthError,
    WhatsAppNotifyError,
    WhatsAppRateLimitError,
)

logger = logging.getLogger(__name__)


# ─── Configuracao ────────────────────────────────────────────────────────

_API_URL = os.environ.get("EVOLUTION_API_URL", "").rstrip("/")
_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "")
_ENABLED = os.environ.get("EVOLUTION_NOTIFY_ENABLED", "true").lower() != "false"

# Rate limit empirico Baileys (mesmo do OpenClaw)
_RATE_PER_SECOND = 1
_RATE_PER_MINUTE = 30
_HTTP_TIMEOUT = 15.0

# Evolution nao chunka sozinha — fragmentamos no helper.
_MAX_CHUNK = 4000


# ─── Token bucket por target (espelha whatsapp_notify) ────────────────────

class _PerTargetRateLimiter:
    """Sliding window por target (thread-safe). Janelas de 1s e 60s."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[deque, deque]] = {}

    def check_and_consume(self, target: str) -> None:
        now = time.monotonic()
        with self._lock:
            sec_q, min_q = self._windows.setdefault(target, (deque(), deque()))
            while sec_q and sec_q[0] < now - 1.0:
                sec_q.popleft()
            while min_q and min_q[0] < now - 60.0:
                min_q.popleft()
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


# ─── Normalizacao de target ───────────────────────────────────────────────

def _normalize_number(target: str) -> str:
    """Converte o target para o formato que a Evolution espera no campo `number`.

    Evolution aceita:
        - DM: digitos do telefone com DDI, SEM '+' (ex: "5511991642998")
        - Grupo: JID completo terminando em "@g.us"

    Aceita entradas variadas vindas do banco/inbound:
        "+5511991642998"            -> "5511991642998"
        "5511991642998@s.whatsapp.net" -> "5511991642998"
        "120363...@g.us"            -> mantem (grupo)
    """
    t = target.strip()
    if t.endswith("@g.us"):
        return t  # grupo: JID completo
    # DM: remove sufixo @s.whatsapp.net / @c.us e tudo que nao for digito
    if "@" in t:
        t = t.split("@", 1)[0]
    digits = "".join(c for c in t if c.isdigit())
    return digits


def _chunk_text(text: str, limit: int = _MAX_CHUNK) -> list[str]:
    """Fragmenta texto em blocos <= limit, quebrando por linha quando possivel."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    buf = ""
    for line in text.split("\n"):
        # Linha unica maior que o limite: corte duro
        if len(line) > limit:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(line), limit):
                chunks.append(line[i:i + limit])
            continue
        candidate = f"{buf}\n{line}" if buf else line
        if len(candidate) > limit:
            chunks.append(buf)
            buf = line
        else:
            buf = candidate
    if buf:
        chunks.append(buf)
    return chunks


# ─── Funcao publica ──────────────────────────────────────────────────────

def send_whatsapp_evolution(
    target: str,
    text: str,
    *,
    skip_rate_limit: bool = False,
    timeout: float = _HTTP_TIMEOUT,
) -> dict:
    """Envia mensagem WhatsApp via Evolution API.

    Args:
        target: Numero E.164 (DM, com ou sem '+', com ou sem @s.whatsapp.net)
            ou JID de grupo terminando em "@g.us".
        text: Texto da mensagem. Fragmentado em blocos <= 4000 chars.
        skip_rate_limit: True desabilita o rate limit local (usar quando a
            resposta ja e reativa a um inbound, nao gera flood independente —
            mesmo criterio do helper OpenClaw).
        timeout: Timeout HTTP em segundos.

    Returns:
        dict: {"ok": True, "chunks": N, "results": [...]} em sucesso.
              {"ok": False, "skipped": True, ...} se desabilitado.

    Raises:
        WhatsAppAuthError: 401/403 da Evolution (apikey invalida).
        WhatsAppRateLimitError: limite local excedido.
        WhatsAppNotifyError: outras falhas (rede, 5xx, config ausente).
    """
    if not _ENABLED:
        logger.info(
            f"[WHATSAPP-EVO] Notify desabilitado (EVOLUTION_NOTIFY_ENABLED=false). "
            f"Skip target={_redact(target)} text_len={len(text)}"
        )
        return {"ok": False, "skipped": True, "reason": "disabled"}

    if not (_API_URL and _API_KEY and _INSTANCE):
        raise WhatsAppNotifyError(
            "Evolution API nao configurada. Defina EVOLUTION_API_URL, "
            "EVOLUTION_API_KEY e EVOLUTION_INSTANCE no ambiente."
        )

    if not target or not target.strip():
        raise WhatsAppNotifyError("target vazio")
    if not text or not text.strip():
        raise WhatsAppNotifyError("text vazio")

    number = _normalize_number(target)
    if not number:
        raise WhatsAppNotifyError(f"target invalido apos normalizacao: {target!r}")

    if not skip_rate_limit:
        _rate_limiter.check_and_consume(number)

    url = f"{_API_URL}/message/sendText/{_INSTANCE}"
    headers = {
        "apikey": _API_KEY,
        "Content-Type": "application/json",
    }

    chunks = _chunk_text(text)
    results = []
    for idx, chunk in enumerate(chunks):
        payload = {"number": number, "text": chunk}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            raise WhatsAppNotifyError(
                f"Falha de rede ao chamar Evolution API: {exc}"
            ) from exc

        if resp.status_code in (401, 403):
            raise WhatsAppAuthError(
                f"Evolution API rejeitou apikey (HTTP {resp.status_code}). "
                f"Verifique EVOLUTION_API_KEY / instancia."
            )
        if resp.status_code >= 500:
            raise WhatsAppNotifyError(
                f"Evolution API retornou {resp.status_code}: {resp.text[:300]}"
            )
        if resp.status_code >= 400:
            raise WhatsAppNotifyError(
                f"Evolution API rejeitou request (HTTP {resp.status_code}): "
                f"{resp.text[:300]}"
            )

        try:
            results.append(resp.json())
        except ValueError:
            results.append({"raw": resp.text[:300]})

        # Espacamento minimo entre chunks para nao estourar 1 msg/s no mesmo target
        if idx < len(chunks) - 1 and not skip_rate_limit:
            time.sleep(1.05)

    logger.info(
        f"[WHATSAPP-EVO] Mensagem enviada target={_redact(number)} "
        f"len={len(text)} chunks={len(chunks)}"
    )
    return {"ok": True, "chunks": len(chunks), "results": results}


def _redact(target: str) -> str:
    """Mascara o numero pra log (mantem 4 ultimos digitos)."""
    digits = "".join(c for c in target if c.isdigit())
    if len(digits) <= 4:
        return target
    return f"***{digits[-4:]}"


def is_configured() -> bool:
    """True se a Evolution API esta configurada (helper para health checks)."""
    return bool(_API_URL and _API_KEY and _INSTANCE) and _ENABLED
