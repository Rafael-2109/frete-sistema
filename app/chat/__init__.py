# pyright: reportUnusedImport=false
from flask import Blueprint

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Imports sao lazy/side-effect: registram as rotas no blueprint acima.
from app.chat.routes import (  # noqa: E402,F401
    thread_routes,
    message_routes,
    stream_routes,
    share_routes,
)
