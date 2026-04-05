"""CRUD de sessoes do Agente."""

import logging

from flask import request, jsonify
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/sessions', methods=['GET'])
@login_required
def api_list_sessions():
    """
    Lista sessões do usuário com busca opcional.

    GET /agente/api/sessions?limit=50&q=texto
    """
    try:
        from app.agente.models import AgentSession

        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)
        search_query = request.args.get('q', '', type=str).strip()

        if search_query and len(search_query) >= 2:
            # Sessao B: busca server-side por titulo e ultima mensagem
            # Escapar wildcards literais para evitar scans caros
            safe_query = search_query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            search_term = f'%{safe_query}%'
            sessions = AgentSession.query.filter(
                AgentSession.user_id == current_user.id,
                db.or_(
                    AgentSession.title.ilike(search_term, escape='\\'),
                    AgentSession.last_message.ilike(search_term, escape='\\'),
                )
            ).order_by(
                AgentSession.updated_at.desc(),
            ).limit(limit).all()
        else:
            sessions = AgentSession.list_for_user(
                user_id=current_user.id,
                limit=limit,
            )

        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
            'query': search_query or None,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao listar sessões: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<session_id>/messages', methods=['GET'])
@login_required
def api_get_session_messages(session_id: str):
    """
    FEAT-030: Retorna histórico de mensagens de uma sessão.

    GET /agente/api/sessions/{session_id}/messages

    Response:
    {
        "success": true,
        "session_id": "abc123",
        "messages": [
            {
                "id": "msg_xxx",
                "role": "user",
                "content": "...",
                "timestamp": "2025-12-05T10:00:00Z"
            },
            {
                "id": "msg_yyy",
                "role": "assistant",
                "content": "...",
                "timestamp": "2025-12-05T10:00:15Z",
                "tokens": {"input": 150, "output": 320}
            }
        ]
    }
    """
    try:
        from app.agente.models import AgentSession

        # Busca por session_id (string UUID)
        session = AgentSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        messages = session.get_messages()

        response_data = {
            'success': True,
            'session_id': session_id,
            'title': session.title,
            'messages': messages,
            'total_tokens': session.get_total_tokens(),
        }

        # P0-2: Inclui summary se disponível
        if session.summary:
            response_data['summary'] = session.summary
            response_data['summary_updated_at'] = (
                session.summary_updated_at.isoformat()
                if session.summary_updated_at else None
            )

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao buscar mensagens: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<int:session_db_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_db_id: int):
    """
    Exclui uma sessão.

    DELETE /agente/api/sessions/123  (ID do banco, não session_id)
    """
    try:
        from app.agente.models import AgentSession

        session = AgentSession.query.filter_by(
            id=session_db_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        db.session.delete(session)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Sessão excluída'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao excluir sessão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<int:session_db_id>/rename', methods=['PUT'])
@login_required
def api_rename_session(session_db_id: int):
    """
    Renomeia uma sessão.

    PUT /agente/api/sessions/123/rename
    {"title": "Novo título"}
    """
    try:
        from app.agente.models import AgentSession

        data = request.get_json()
        new_title = data.get('title', '').strip()

        if not new_title:
            return jsonify({
                'success': False,
                'error': 'Título é obrigatório'
            }), 400

        session = AgentSession.query.filter_by(
            id=session_db_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        session.title = new_title[:200]
        db.session.commit()

        return jsonify({
            'success': True,
            'session': session.to_dict()
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao renomear sessão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/summaries', methods=['GET'])
@login_required
def api_list_session_summaries():
    """
    Lista sessoes com resumos estruturados.

    GET /agente/api/sessions/summaries?limit=20

    Response:
    {
        "success": true,
        "sessions": [
            {
                "id": N,
                "session_id": "...",
                "title": "...",
                "message_count": N,
                "created_at": "...",
                "summary": {
                    "resumo_geral": "...",
                    "pedidos_tratados": [...],
                    "decisoes_tomadas": [...],
                    "tarefas_pendentes": [...],
                    "alertas": [...]
                }
            }
        ]
    }
    """
    try:
        from app.agente.models import AgentSession

        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)

        sessions = AgentSession.query.filter(
            AgentSession.user_id == current_user.id,
            AgentSession.summary.isnot(None),
        ).order_by(
            AgentSession.updated_at.desc(),
        ).limit(limit).all()

        result = []
        for s in sessions:
            result.append({
                'id': s.id,
                'session_id': s.session_id,
                'title': s.title or 'Sem titulo',
                'message_count': s.message_count or 0,
                'total_cost_usd': float(s.total_cost_usd or 0),
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                'summary': s.summary,
                'summary_updated_at': (
                    s.summary_updated_at.isoformat()
                    if s.summary_updated_at else None
                ),
            })

        return jsonify({'success': True, 'sessions': result})

    except Exception as e:
        logger.error(f"[SUMMARIES] Erro ao listar resumos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
