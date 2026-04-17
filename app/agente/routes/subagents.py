"""
Rota user-facing para lazy-fetch de detalhes de subagente (#6 UI).

Usado quando o usuario clica "expandir" na linha do subagente no chat.
Verifica dono da sessao (ou admin), aplica sanitizacao PII automatica
para non-admin e retorna summary completo.

Padrao de resposta:
- 404 se USE_SUBAGENT_UI=false OU sessao nao encontrada OU subagent nao encontrado
- 403 se user nao e dono E nao e admin
- 200 com summary sanitizado (ou raw para admin)
"""
import logging

from flask import jsonify
from flask_login import current_user, login_required

from app.agente.config.feature_flags import USE_SUBAGENT_UI
from app.agente.models import AgentSession
from app.agente.routes import agente_bp
from app.agente.routes.chat import _sanitize_subagent_summary_for_user
from app.agente.sdk.subagent_reader import get_subagent_summary

logger = logging.getLogger('sistema_fretes')


def _get_session(session_id: str):
    """Wrapper testavel para AgentSession.query.filter_by().first()."""
    return AgentSession.query.filter_by(session_id=session_id).first()


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/summary',
    methods=['GET'],
)
@login_required
def api_user_subagent_summary(session_id: str, agent_id: str):
    """
    Lazy-fetch do summary completo do subagent para o frontend.

    Autorizacao: dono da sessao OU admin. Admin ve tudo raw + cost.
    User normal: PII mascarada, cost_usd removido.
    """
    if not USE_SUBAGENT_UI:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    sess = _get_session(session_id)
    if sess is None:
        return jsonify({
            'success': False,
            'error': f'Sessao {session_id} nao encontrada'
        }), 404

    is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    if not is_admin and sess.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'Acesso restrito ao dono da sessao ou administrador'
        }), 403

    summary = get_subagent_summary(
        session_id=session_id,
        agent_id=agent_id,
        include_pii=True,  # sanitizacao aplicada abaixo por perfil
        max_tool_chars=1000,
    )

    if summary.status == 'error':
        return jsonify({
            'success': False,
            'error': f'Subagent {agent_id} nao encontrado',
        }), 404

    payload = _sanitize_subagent_summary_for_user(
        summary.to_dict(), current_user
    )
    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'subagent': payload,
    })
