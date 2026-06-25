"""Decorators de autenticacao do canal WhatsApp.

require_plugin_token: valida Authorization Bearer contra OPENCLAW_PLUGIN_TOKEN.
O token e shared secret entre o plugin OpenClaw `nacom-bridge` (config.json) e
o Flask. Espelha pattern do `app/teams/bot_routes.py:require_bot_api_key`.

require_n8n_token: valida Authorization Bearer contra N8N_INBOUND_TOKEN.
Shared secret entre o workflow N8N (no HTTP Request node) e o Flask, usado
quando WHATSAPP_TRANSPORT=n8n. Mesmo pattern de comparacao constant-time.
"""

import functools
import hmac
import logging
import os

from flask import jsonify, request

logger = logging.getLogger(__name__)

OPENCLAW_PLUGIN_TOKEN = os.environ.get("OPENCLAW_PLUGIN_TOKEN", "")
N8N_INBOUND_TOKEN = os.environ.get("N8N_INBOUND_TOKEN", "")


def require_plugin_token(f):
    """Valida Authorization: Bearer <token> contra OPENCLAW_PLUGIN_TOKEN.

    Retorna 500 se token nao configurado no servidor (defesa contra deploy
    sem env var) e 401 se Authorization invalido/ausente.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not OPENCLAW_PLUGIN_TOKEN:
            logger.error("[WHATSAPP] OPENCLAW_PLUGIN_TOKEN nao configurada")
            return jsonify({"error": "plugin token nao configurado no servidor"}), 500

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("[WHATSAPP] Authorization header ausente/malformado")
            return jsonify({"error": "Authorization Bearer obrigatorio"}), 401

        token = auth_header[len("Bearer "):].strip()
        if not hmac.compare_digest(token, OPENCLAW_PLUGIN_TOKEN):
            logger.warning("[WHATSAPP] Token invalido recebido do plugin")
            return jsonify({"error": "token invalido"}), 401

        return f(*args, **kwargs)
    return decorated


def require_n8n_token(f):
    """Valida Authorization: Bearer <token> contra N8N_INBOUND_TOKEN.

    Usado no endpoint /api/whatsapp/n8n/inbound (transporte N8N + Evolution).
    Retorna 500 se token nao configurado no servidor e 401 se Authorization
    invalido/ausente. Mesmo contrato do require_plugin_token.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not N8N_INBOUND_TOKEN:
            logger.error("[WHATSAPP] N8N_INBOUND_TOKEN nao configurada")
            return jsonify({"error": "n8n token nao configurado no servidor"}), 500

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("[WHATSAPP] Authorization header ausente/malformado (n8n)")
            return jsonify({"error": "Authorization Bearer obrigatorio"}), 401

        token = auth_header[len("Bearer "):].strip()
        if not hmac.compare_digest(token, N8N_INBOUND_TOKEN):
            logger.warning("[WHATSAPP] Token invalido recebido do n8n")
            return jsonify({"error": "token invalido"}), 401

        return f(*args, **kwargs)
    return decorated
