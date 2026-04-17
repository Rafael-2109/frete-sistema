"""
Rotas do Agente — modularizado.

Blueprint: agente_bp
Prefix: /agente

Estrutura:
- _constants.py              - Constantes (UPLOAD_FOLDER, timeouts, thresholds)
- _helpers.py                - Helpers compartilhados (Teams + cross-module)
- chat.py                    - Core SSE: api_chat, streaming engine, interrupt, user_answer
- sessions.py                - CRUD sessoes: list, messages, delete, rename, summaries
- admin_learning.py          - Admin: session messages, generate/save correction
- files.py                   - Upload/download/list/delete + helpers de arquivo
- health.py                  - api_health com cache
- feedback.py                - api_feedback 4 tipos
- insights.py                - pagina_insights + APIs dados
- intelligence_report.py     - D7 cron bridge, csrf.exempt
- improvement_dialogue.py    - D8 cron bridge + admin, csrf.exempt
- memories.py                - CRUD memorias + users + review
- briefing.py                - api_get_briefing
- _deprecated.py             - Scaffolding async migration (quarentena)
"""

import os
from flask import Blueprint

# Blueprint do agente
agente_bp = Blueprint(
    'agente',
    __name__,
    url_prefix='/agente',
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
)

# Sub-modulos importam blueprint e registram rotas
from app.agente.routes import chat  # noqa: F401, E402
from app.agente.routes import sessions  # noqa: F401, E402
from app.agente.routes import admin_learning  # noqa: F401, E402
from app.agente.routes import admin_subagents  # noqa: F401 — registra rotas admin de subagentes
from . import subagents  # noqa: F401 — rota user-facing para UI #6
from app.agente.routes import files  # noqa: F401, E402
from app.agente.routes import health  # noqa: F401, E402
from app.agente.routes import feedback  # noqa: F401, E402
from app.agente.routes import insights  # noqa: F401, E402
from app.agente.routes import intelligence_report  # noqa: F401, E402
from app.agente.routes import improvement_dialogue  # noqa: F401, E402
from app.agente.routes import memories  # noqa: F401, E402
from app.agente.routes import briefing  # noqa: F401, E402
from app.agente.routes import _deprecated  # noqa: F401, E402

# Re-export: helpers usados por app/teams/services.py
# Mantem compatibilidade: from app.agente.routes import run_post_session_processing
from app.agente.routes._helpers import (  # noqa: F401, E402
    run_post_session_processing,
    _calculate_cost,
    _track_memory_effectiveness,
)
