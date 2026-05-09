"""Blueprint do canal WhatsApp via OpenClaw + Baileys.

Recebe inbound do plugin OpenClaw `nacom-bridge` e responde via gateway local.
Espelha o padrao do `app/teams/` — leia `app/whatsapp/CLAUDE.md` antes de mexer.
"""
from flask import Blueprint

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')

from app.whatsapp import bot_routes  # noqa: E402, F401
