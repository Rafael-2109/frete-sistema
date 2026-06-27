"""Dispatcher transport-aware do envio WhatsApp (outbound).

Ponto unico que os emissores (HORA: notificacao NF/pedido, recibo) usam para
enviar, sem se acoplar a um gateway especifico. Roteia por:

  - **transporte**: OpenClaw (gateway local, depende do PC ligado) vs Evolution
    API (24/7 num host gerenciado). Resolvido por parametro `transport` ou, na
    ausencia, pela env `HORA_WHATSAPP_TRANSPORT` (default "openclaw"). A env e
    PROPRIA do HORA — independente do `WHATSAPP_TRANSPORT` do canal do agente,
    permitindo migrar o envio do HORA sem tocar no agente.
  - **mídia vs texto**: com `anexo_b64`, usa o caminho de documento de cada
    transporte; sem anexo, o caminho de texto.

Contrato de retorno/erros identico ao dos helpers subjacentes: retorna dict com
`ok` e levanta `WhatsAppNotifyError` (e subclasses) em falha — os call-sites do
HORA ja tratam essa excecao.
"""
from __future__ import annotations

import os
from typing import Optional

from app.utils.whatsapp_notify import send_whatsapp, WhatsAppNotifyError
from app.utils.whatsapp_evolution import (
    send_whatsapp_evolution,
    send_media_evolution,
)

TRANSPORT_OPENCLAW = "openclaw"
TRANSPORT_EVOLUTION = "evolution"
# "n8n" e' aceito como alias de Evolution (o seletor historico do canal do
# agente, app/whatsapp/services.py, usa "n8n" para o outbound via Evolution).
_EVOLUTION_ALIASES = {TRANSPORT_EVOLUTION, "n8n"}


def _resolve_transport(transport: Optional[str]) -> str:
    raw = transport or os.environ.get("HORA_WHATSAPP_TRANSPORT", TRANSPORT_OPENCLAW)
    return raw.strip().lower()


def send_whatsapp_unificado(
    target: str,
    text: str,
    *,
    anexo_b64: Optional[str] = None,
    anexo_filename: Optional[str] = None,
    anexo_mimetype: str = "application/pdf",
    transport: Optional[str] = None,
    skip_rate_limit: bool = False,
) -> dict:
    """Envia uma mensagem WhatsApp pelo transporte ativo.

    Args:
        target: Numero E.164 (DM) ou JID de grupo ("@g.us").
        text: Texto da mensagem (vira legenda quando ha anexo).
        anexo_b64: Conteudo do arquivo em base64. Se None, envia so texto.
        anexo_filename: Nome do arquivo (usado quando ha anexo).
        anexo_mimetype: MIME type do anexo (default "application/pdf").
        transport: "openclaw" | "evolution"/"n8n". None => env HORA_WHATSAPP_TRANSPORT.
        skip_rate_limit: True desabilita o rate limit local (resposta reativa).

    Returns:
        dict: resposta do helper subjacente (sempre com chave `ok`).

    Raises:
        WhatsAppNotifyError: transporte desconhecido ou falha de envio.
        WhatsAppAuthError / WhatsAppRateLimitError: propagadas dos helpers.
    """
    t = _resolve_transport(transport)

    if t in _EVOLUTION_ALIASES:
        if anexo_b64:
            return send_media_evolution(
                target, text,
                anexo_b64=anexo_b64,
                anexo_filename=anexo_filename or "documento.pdf",
                anexo_mimetype=anexo_mimetype,
                skip_rate_limit=skip_rate_limit,
            )
        return send_whatsapp_evolution(target, text, skip_rate_limit=skip_rate_limit)

    if t == TRANSPORT_OPENCLAW:
        return send_whatsapp(
            target, text,
            skip_rate_limit=skip_rate_limit,
            anexo_b64=anexo_b64,
            anexo_filename=anexo_filename,
            anexo_mimetype=anexo_mimetype,
        )

    raise WhatsAppNotifyError(
        f"HORA_WHATSAPP_TRANSPORT desconhecido: {t!r} "
        f"(use 'openclaw' ou 'evolution')"
    )


def transporte_ativo() -> str:
    """Transporte que sera usado quando `transport` nao for passado (para health/log)."""
    return _resolve_transport(None)
