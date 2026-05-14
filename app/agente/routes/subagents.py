"""
Rota user-facing para lazy-fetch de detalhes de subagente (#6 UI).

Usado quando o usuario clica "expandir" na linha do subagente no chat.
Verifica dono da sessao (ou admin), aplica sanitizacao PII automatica
para non-admin e retorna summary completo.

Padrao de resposta:
- 404 se USE_SUBAGENT_UI=false OU sessao nao encontrada OU subagent nao encontrado
- 403 se user nao e dono E nao e admin
- 200 com summary sanitizado (ou raw para admin)

2026-05-14: Adicionados endpoints novos para enriquecer modal de transcript:
- GET /api/sessions/<sid>/subagents/<aid>/transcript (P0.1)
- POST /api/sessions/<sid>/subagents/<aid>/pii-toggle (Fase 1)
- PATCH /api/sessions/<sid>/subagents/<aid> (Fase 2 — rename/tag)
- GET /api/sessions/<sid>/subagents/<aid>/output_file (Fase 2 — download)
"""
import logging

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.utils.redis_cache import redis_cache
from app.agente.config.feature_flags import USE_SUBAGENT_UI
from app.agente.models import AgentSession
from app.agente.routes import agente_bp
from app.agente.routes.chat import _sanitize_subagent_summary_for_user
from app.agente.sdk.subagent_reader import (
    _is_safe_id,
    get_subagent_summary,
    get_subagent_transcript,
)
from app.utils.timezone import agora_brasil_naive

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


# ═══════════════════════════════════════════════════════════════════════════
# 2026-05-14: novos endpoints para modal de transcript (P0.1, Fase 1)
# Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md
# ═══════════════════════════════════════════════════════════════════════════


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/transcript',
    methods=['GET'],
)
@login_required
def api_subagent_transcript(session_id: str, agent_id: str):
    """Retorna timeline cronologica completa do subagent (P0.1).

    Autorizacao: dono OU admin. Non-admin recebe PII mascarada.
    Admin com Redis token agent:pii_unmask:* recebe raw.
    """
    from app.agente.config.feature_flags import USE_SUBAGENT_MODAL

    if not USE_SUBAGENT_MODAL:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        return jsonify({'success': False, 'error': 'IDs invalidos'}), 404

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    is_admin = getattr(current_user, 'perfil', None) == 'administrador'
    if not is_admin and sess.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': 'Acesso restrito ao dono da sessao ou administrador',
        }), 403

    # include_pii apenas para admin com Redis token valido (defesa em profundidade)
    include_pii = False
    if is_admin:
        try:
            rc = redis_cache.client
            tk = f'agent:pii_unmask:{current_user.id}:{session_id}:{agent_id}'
            include_pii = bool(rc.exists(tk))
        except Exception as e:
            logger.warning(f"[transcript] Redis exists falhou: {e}")
            include_pii = False

    try:
        entries = get_subagent_transcript(
            session_id, agent_id,
            include_pii=include_pii,
            max_content_chars=4000,
        )
    except Exception as e:
        logger.error(f"[transcript] get_subagent_transcript falhou: {e}")
        return jsonify({
            'success': False,
            'error': 'Nao foi possivel carregar o transcript. Tente novamente em instantes.',
        }), 500

    if not entries:
        return jsonify({
            'success': False,
            'error': 'Transcript nao encontrado. A sessao pode ter sido arquivada.',
        }), 404

    # Telemetria contador diario
    try:
        from datetime import date
        rc = redis_cache.client
        if rc is not None:
            rc.hincrby('agent:metrics:subagent_modal:daily', date.today().isoformat(), 1)
    except Exception:
        pass

    logger.info(
        f"[transcript] user_id={current_user.id} "
        f"session={session_id[:16]} agent={agent_id[:12]} "
        f"include_pii={include_pii} entries={len(entries)}"
    )

    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'include_pii': include_pii,
        'transcript': [e.to_dict() for e in entries],
    })


@agente_bp.route(
    '/api/sessions/<session_id>/subagents/<agent_id>/pii-toggle',
    methods=['POST'],
)
@login_required
def api_subagent_pii_toggle(session_id: str, agent_id: str):
    """Admin liga/desliga visualizacao raw de PII no modal de transcript.

    - Apenas admin (perfil='administrador'). Non-admin -> 403.
    - Rate limit 10 toggles/min/user.
    - Registra audit em agent_sessions.data['subagent_pii_audit'] (FIFO 100).
    - Marca Redis SETEX agent:pii_unmask:{user_id}:{sid}:{aid} 300 "1".
    """
    from app.agente.config.feature_flags import USE_SUBAGENT_MODAL

    if not USE_SUBAGENT_MODAL:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404

    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        return jsonify({'success': False, 'error': 'IDs invalidos'}), 404

    if getattr(current_user, 'perfil', None) != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    body = request.get_json(silent=True) or {}
    enabled = bool(body.get('enabled', False))

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if sess is None:
        return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

    # Rate limit Redis: 10/min/user
    try:
        rc = redis_cache.client
        if rc is not None:
            rk = f'agent:pii_toggle_rate:{current_user.id}'
            count = rc.incr(rk)
            if count == 1:
                rc.expire(rk, 60)
            if count > 10:
                return jsonify({
                    'success': False,
                    'error': 'Muitas trocas em sequencia. Aguarde 1 minuto.',
                }), 429
    except Exception as e:
        logger.warning(f"[pii_toggle] rate limit Redis falhou: {e}")

    # Audit log FIFO max 100
    audit = sess.data.setdefault('subagent_pii_audit', [])
    audit.append({
        'agent_id': agent_id,
        'user_id': current_user.id,
        'enabled': enabled,
        'timestamp': agora_brasil_naive().isoformat(),
        'session_id': session_id,
    })
    if len(audit) > 100:
        del audit[:len(audit) - 100]
    flag_modified(sess, 'data')
    db.session.commit()

    # Redis token TTL 5min
    try:
        rc = redis_cache.client
        if rc is not None:
            tk = f'agent:pii_unmask:{current_user.id}:{session_id}:{agent_id}'
            if enabled:
                rc.setex(tk, 300, '1')
            else:
                rc.delete(tk)
    except Exception as e:
        logger.error(f"[pii_toggle] Redis SETEX falhou: {e}")
        return jsonify({'success': False, 'error': 'Recurso temporariamente indisponivel'}), 500

    logger.info(
        f"[pii_toggle] user_id={current_user.id} "
        f"session={session_id[:16]} agent={agent_id[:12]} enabled={enabled}"
    )
    return jsonify({'success': True, 'enabled': enabled, 'expires_in': 300})
