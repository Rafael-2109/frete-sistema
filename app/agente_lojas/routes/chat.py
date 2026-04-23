"""
Chat do Agente Lojas HORA — SSE stub (M0).

M0: stub funcional que valida auth, persiste sessao com agente='lojas' e
devolve resposta de eco para smoketest. Integracao real com AgentClient
entra em M1 junto com as primeiras skills (consultando-estoque-loja,
rastreando-chassi).

Razao para stub em M0:
- Modulo HORA ainda esta em fase P2 (migrations ja feitas, mas services
  de consulta nao existem)
- Sem skills registradas nao faz sentido ligar o SDK gigante
- Valida o caminho auth -> menu -> endpoint sem risco de regressao
  no agente logistico (`app/agente/`)

POST /agente-lojas/api/chat
    { "message": "...", "session_id": "uuid" }
    -> text/event-stream
"""
import json
import logging
import uuid
from typing import Generator

from flask import request, jsonify, render_template, Response, stream_with_context
from flask_login import current_user

from app.agente_lojas.routes import agente_lojas_bp
from app.agente_lojas.decorators import require_acesso_agente_lojas
from app.agente_lojas.config.settings import AGENTE_ID
from app.agente_lojas.services.scope_injector import build_loja_context_block
from app.agente.models import AgentSession
from app import db

logger = logging.getLogger('sistema_fretes')


def _sse(event_type: str, payload: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


@agente_lojas_bp.route('/', methods=['GET'])
@require_acesso_agente_lojas
def pagina_chat():
    """Pagina de chat do Agente Lojas HORA."""
    loja_context = build_loja_context_block(
        perfil=current_user.perfil,
        loja_hora_id=getattr(current_user, 'loja_hora_id', None),
    )
    return render_template(
        'agente_lojas/chat.html',
        loja_context_preview=loja_context,
    )


@agente_lojas_bp.route('/api/chat', methods=['POST'])
@require_acesso_agente_lojas
def api_chat():
    """Chat SSE stub (M0) — persiste sessao com agente='lojas' e ecoa."""
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        session_id = data.get('session_id') or str(uuid.uuid4())

        if not message:
            return jsonify({
                'success': False,
                'error': 'Campo "message" e obrigatorio',
            }), 400

        user_id = current_user.id
        perfil = current_user.perfil
        loja_hora_id = getattr(current_user, 'loja_hora_id', None)

        # Persiste sessao particionada (agente='lojas')
        session, created = AgentSession.get_or_create(
            session_id=session_id,
            user_id=user_id,
            channel='web',
        )
        if created or session.agente != AGENTE_ID:
            session.agente = AGENTE_ID
            db.session.commit()

        loja_ctx = build_loja_context_block(perfil=perfil, loja_hora_id=loja_hora_id)

        def _gen() -> Generator[str, None, None]:
            yield _sse('start', {'session_id': session_id, 'agente': AGENTE_ID})
            yield _sse('text', {
                'content': (
                    "Agente Lojas HORA em M0 (esqueleto). Integracao com skills "
                    "e SDK chega em M1.\n\n"
                    f"Voce disse: {message!r}\n\n"
                    f"Seu escopo de loja:\n{loja_ctx}"
                ),
            })
            yield _sse('done', {
                'session_id': session_id,
                'message_count': (session.message_count or 0) + 1,
                'stage': 'M0',
            })

        return Response(
            stream_with_context(_gen()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
        )

    except Exception as e:
        logger.exception("[AGENTE_LOJAS] Erro em api_chat: %s", e)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
