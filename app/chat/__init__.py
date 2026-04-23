from flask import Blueprint

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Import routes para registro (lazy, apos blueprint existir)
from app.chat.routes import thread_routes, message_routes, stream_routes, share_routes  # noqa: E402,F401
