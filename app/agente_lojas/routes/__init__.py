"""
Rotas do Agente Lojas HORA — Blueprint agente_lojas_bp.

Prefix: /agente-lojas
Autorizacao: sistema_lojas=True OU perfil='administrador'

Estrutura:
    - chat.py      GET /  + POST /api/chat (SSE)
    - sessions.py  GET/DELETE /api/sessions (filtrado por agente='lojas')
    - health.py    GET /api/health
"""
import os
from flask import Blueprint

agente_lojas_bp = Blueprint(
    'agente_lojas',
    __name__,
    url_prefix='/agente-lojas',
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
)

# Sub-modulos registram rotas importando o blueprint acima
from app.agente_lojas.routes import chat  # noqa: F401, E402
from app.agente_lojas.routes import sessions  # noqa: F401, E402
from app.agente_lojas.routes import health  # noqa: F401, E402
