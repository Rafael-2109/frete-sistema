"""
Sessoes do Agente Lojas HORA — listagem e remocao filtradas por agente='lojas'.

IMPORTANTE: TODAS as queries DEVEM filtrar por `agente=AGENTE_ID` para nao
misturar com sessoes do agente logistico.
"""
import logging

from flask import jsonify, request
from flask_login import current_user

from app.agente_lojas.routes import agente_lojas_bp
from app.agente_lojas.decorators import require_acesso_agente_lojas
from app.agente_lojas.config.settings import AGENTE_ID
from app.agente.models import AgentSession
from app import db

logger = logging.getLogger('sistema_fretes')


@agente_lojas_bp.route('/api/sessions', methods=['GET'])
@require_acesso_agente_lojas
def api_list_sessions():
    """Lista sessoes do Agente Lojas HORA para o usuario corrente."""
    try:
        limit = min(int(request.args.get('limit', 50)), 200)

        query = AgentSession.query.filter_by(
            user_id=current_user.id,
            agente=AGENTE_ID,
        ).order_by(AgentSession.updated_at.desc()).limit(limit)

        sessions = [s.to_dict() for s in query.all()]
        return jsonify({
            'success': True,
            'sessions': sessions,
            'count': len(sessions),
            'agente': AGENTE_ID,
        }), 200

    except Exception as e:
        logger.exception("[AGENTE_LOJAS] Erro em list_sessions: %s", e)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@agente_lojas_bp.route('/api/sessions/<session_id>', methods=['DELETE'])
@require_acesso_agente_lojas
def api_delete_session(session_id: str):
    """Remove sessao do usuario corrente (restrito a agente='lojas')."""
    try:
        session = AgentSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id,
            agente=AGENTE_ID,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessao nao encontrada',
            }), 404

        db.session.delete(session)
        db.session.commit()
        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        logger.exception("[AGENTE_LOJAS] Erro em delete_session: %s", e)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
