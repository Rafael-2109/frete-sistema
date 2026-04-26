"""Worker RQ para emissao TagPlus.

Funcoes invocadas por jobs RQ:
  - processar_emissao(emissao_id)        — POST /nfes
  - processar_webhook(conta_id, event_type, data)  — handler webhook
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _ensure_app_context():
    """Garante app_context. RQ pode invocar fora do contexto Flask."""
    from flask import current_app
    try:
        current_app._get_current_object()  # noqa: SLF001
        return None  # ja temos contexto
    except RuntimeError:
        from app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        return ctx


def processar_emissao(emissao_id: int) -> None:
    """Job RQ: chama EmissorNfeHora.processar."""
    ctx = _ensure_app_context()
    try:
        from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
        EmissorNfeHora.processar(emissao_id)
    finally:
        if ctx is not None:
            ctx.pop()


def processar_webhook(conta_id: int, event_type: str, data: list) -> None:
    """Job RQ: chama WebhookHandler.processar."""
    ctx = _ensure_app_context()
    try:
        from app.hora.services.tagplus.webhook_handler import WebhookHandler
        WebhookHandler.processar(conta_id, event_type, data)
    finally:
        if ctx is not None:
            ctx.pop()
