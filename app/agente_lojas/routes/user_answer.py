"""
POST /agente-lojas/api/user-answer — resposta do usuario para AskUserQuestion.

Quando o agente chama AskUserQuestion, o callback can_use_tool fica
bloqueado em async_wait_for_answer (event_queue ja emitiu o evento SSE
para o frontend). Este endpoint desbloqueia o callback com as respostas.

Reusa pending_questions do agente Nacom (registry global keyed por
session_id UUID — cross-agente safe).
"""
import logging

from flask import jsonify, request
from flask_login import current_user

from app.agente_lojas.routes import agente_lojas_bp
from app.agente_lojas.decorators import require_acesso_agente_lojas
from app.agente_lojas.config.settings import AGENTE_ID
from app.agente.models import AgentSession

logger = logging.getLogger('sistema_fretes')


@agente_lojas_bp.route('/api/user-answer', methods=['POST'])
@require_acesso_agente_lojas
def api_user_answer():
    """Recebe resposta do usuario para AskUserQuestion.

    POST /agente-lojas/api/user-answer
    {
        "session_id": "uuid",
        "answers": { "Pergunta 1": "Opcao A", ... }
    }

    Response:
        200: {success: True}
        400: payload invalido
        403: sessao nao pertence ao usuario / nao eh do agente lojas
        404: sem pergunta pendente para a sessao
    """
    try:
        data = request.get_json(silent=True) or {}
        answer_session_id = data.get('session_id')
        answers = data.get('answers') or {}

        if not answer_session_id:
            return jsonify({
                'success': False,
                'error': 'session_id obrigatorio',
            }), 400

        if not answers or not isinstance(answers, dict):
            return jsonify({
                'success': False,
                'error': 'answers deve ser dict nao-vazio',
            }), 400

        # Validacao de ownership: sessao deve ser do usuario E do agente='lojas'
        # (filtro adicional para nao aceitar resposta de sessao do agente Nacom)
        session_record = AgentSession.query.filter_by(
            session_id=answer_session_id,
            user_id=current_user.id,
            agente=AGENTE_ID,
        ).first()
        if not session_record:
            logger.warning(
                "[AGENTE_LOJAS] user-answer: sessao %s nao pertence ao "
                "user_id=%s ou nao eh do agente lojas",
                answer_session_id[:8], current_user.id,
            )
            return jsonify({
                'success': False,
                'error': 'Sessao nao encontrada',
            }), 403

        from app.agente.sdk.pending_questions import submit_answer

        submitted = submit_answer(answer_session_id, answers)

        if not submitted:
            return jsonify({
                'success': False,
                'error': 'Nenhuma pergunta pendente para esta sessao',
            }), 404

        logger.info(
            "[AGENTE_LOJAS] user-answer recebido: session=%s... keys=%s",
            answer_session_id[:8], list(answers.keys()),
        )
        return jsonify({'success': True}), 200

    except Exception as e:
        logger.exception("[AGENTE_LOJAS] Erro em user-answer: %s", e)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
