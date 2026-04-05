"""Feedback do usuario sobre respostas do Agente."""

import logging

from flask import request, jsonify
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/feedback', methods=['POST'])
@login_required
def api_feedback():
    """
    Recebe feedback do usuário sobre a resposta.

    POST /agente/api/feedback
    {
        "session_id": "uuid-da-sessao",
        "type": "positive" | "negative" | "correction" | "preference",
        "data": {
            "correction": "texto da correção",  // para type=correction
            "key": "communication",              // para type=preference
            "value": "direto"                    // para type=preference
        }
    }

    Apenas correction e preference salvam memórias.
    positive/negative são apenas logados (analytics futuro).
    """
    try:
        from app.agente.models import AgentMemory

        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Body é obrigatório'
            }), 400

        session_id = data.get('session_id')
        feedback_type = data.get('type')
        feedback_data = data.get('data', {})

        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id é obrigatório'
            }), 400

        if feedback_type not in ['positive', 'negative', 'correction', 'preference']:
            return jsonify({
                'success': False,
                'error': 'type deve ser: positive, negative, correction ou preference'
            }), 400

        user_id = current_user.id
        result = {'processed': True, 'action': feedback_type, 'memory_path': None}

        # Sessao E (#17): Feedback positivo estruturado (antes era apenas logado)
        if feedback_type == 'positive':
            try:
                from app.agente.models import AgentSession
                session_record = AgentSession.query.filter_by(
                    session_id=session_id, user_id=user_id
                ).first()
                if session_record and session_record.data:
                    feedbacks = session_record.data.get('feedbacks', [])
                    feedbacks.append({
                        'type': 'positive',
                        'context': feedback_data.get('context', '')[:500],
                        'message_text': feedback_data.get('message_text', '')[:500],
                        'timestamp': agora_utc_naive().isoformat(),
                    })
                    session_record.data['feedbacks'] = feedbacks
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(session_record, 'data')
                    db.session.commit()
                    logger.info(
                        f"[FEEDBACK] Positivo registrado: session={session_id[:8]}..."
                    )
            except Exception as pos_err:
                logger.debug(f"[FEEDBACK] Erro ao persistir positivo (ignorado): {pos_err}")

        # Feedback negativo enriquecido: persistir no session data + incrementar correction_count
        if feedback_type == 'negative':
            try:
                from app.agente.models import AgentSession
                session_record = AgentSession.query.filter_by(
                    session_id=session_id, user_id=user_id
                ).first()
                if session_record and session_record.data:
                    # Registrar feedback estruturado no session data
                    feedbacks = session_record.data.get('feedbacks', [])
                    feedbacks.append({
                        'type': 'negative',
                        'context': feedback_data.get('context', '')[:500],
                        'error_category': feedback_data.get('error_category', ''),
                        'correction': feedback_data.get('correction', ''),
                        'source': feedback_data.get('source', 'thumbs_down'),
                        'timestamp': agora_utc_naive().isoformat(),
                    })
                    session_record.data['feedbacks'] = feedbacks
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(session_record, 'data')
                    db.session.commit()
                    logger.info(
                        f"[FEEDBACK] Negativo estruturado registrado: "
                        f"session={session_id[:8]}... category={feedback_data.get('error_category', 'none')}"
                    )
            except Exception as neg_err:
                logger.debug(f"[FEEDBACK] Erro ao persistir negativo (ignorado): {neg_err}")

        # Salva correções e preferências diretamente
        if feedback_type == 'correction':
            correction_text = feedback_data.get('correction', '')
            if correction_text:
                path = f"/memories/corrections/feedback_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xml"
                content = f"""<correction>
<text>{correction_text}</text>
<context>{feedback_data.get('context', '')}</context>
<source>user_feedback</source>
<created_at>{agora_utc_naive().isoformat()}</created_at>
</correction>"""
                AgentMemory.create_file(user_id, path, content)
                db.session.commit()
                result['memory_path'] = path

                # Incrementar correction_count nas memórias recentemente injetadas
                try:
                    from app.agente.tools.memory_mcp_tool import _track_correction_feedback
                    _track_correction_feedback(user_id, path, correction_text)
                except Exception as fb_err:
                    logger.debug(f"[FEEDBACK] Correction tracking falhou (ignorado): {fb_err}")

        elif feedback_type == 'preference':
            pref_key = feedback_data.get('key', 'general')
            pref_value = feedback_data.get('value', '')
            if pref_value:
                path = '/memories/preferences.xml'
                content = f"""<preferences>
<{pref_key}>{pref_value}</{pref_key}>
<source>user_feedback</source>
<updated_at>{agora_utc_naive().isoformat()}</updated_at>
</preferences>"""
                existing = AgentMemory.get_by_path(user_id, path)
                if existing:
                    existing.content = content
                else:
                    AgentMemory.create_file(user_id, path, content)
                db.session.commit()
                result['memory_path'] = path

        logger.info(
            f"[AGENTE] Feedback recebido | user={user_id} "
            f"session={session_id[:8]}... type={feedback_type}"
        )

        return jsonify({
            'success': True,
            'processed': result.get('processed', False),
            'action': result.get('action'),
            'memory_path': result.get('memory_path'),
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao processar feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
