"""
Endpoint admin de debug forense de subagentes (#1, SDK 0.1.60).

Permite admin investigar respostas do agente sem re-executar a sessao:
lista todos os subagentes de uma sessao, mostra tool_calls em ordem
cronologica com args/results raw (sem mascaramento PII), custo e duracao.

Pattern de auth: @login_required + inline check perfil='administrador' → 403.
Flag: USE_SUBAGENT_DEBUG_ENDPOINT (default true).
"""
import logging

from flask import jsonify
from flask_login import current_user, login_required

from app.agente.config.feature_flags import USE_SUBAGENT_DEBUG_ENDPOINT
from app.agente.routes import agente_bp
from app.agente.sdk.subagent_reader import (
    get_session_subagents_summary,
    get_subagent_summary,
)

logger = logging.getLogger('sistema_fretes')


# NOTA: abort(403) re-raise como 500 — global exception handler (app/__init__.py)
# so trata 404 especialmente, outros HTTPException sao tratados como unhandled.
# Para 403: usar `return jsonify(), 403` inline (pattern admin_learning.py).
# Para 404: abort(404) funciona (handler delega para handle_404), mas usar
# return jsonify() mantem consistencia do pattern em todo o modulo.


@agente_bp.route(
    '/api/admin/sessions/<session_id>/subagents',
    methods=['GET'],
)
@login_required
def api_admin_list_subagents(session_id: str):
    """Lista subagentes de uma sessao com metadata resumida."""
    if not USE_SUBAGENT_DEBUG_ENDPOINT:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    summaries = get_session_subagents_summary(session_id, include_pii=True)

    return jsonify({
        'success': True,
        'session_id': session_id,
        'count': len(summaries),
        'subagents': [s.to_dict(include_cost=True) for s in summaries],
    })


@agente_bp.route(
    '/api/admin/sessions/<session_id>/subagents/<agent_id>',
    methods=['GET'],
)
@login_required
def api_admin_subagent_detail(session_id: str, agent_id: str):
    """Detalhe completo de um subagente — tools, findings, cost, tokens."""
    if not USE_SUBAGENT_DEBUG_ENDPOINT:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    summary = get_subagent_summary(
        session_id, agent_id, include_pii=True, max_tool_chars=2000
    )

    if summary.status == 'error':
        return jsonify({
            'success': False,
            'error': f'Subagent {agent_id} nao encontrado na sessao {session_id}',
        }), 404

    return jsonify({
        'success': True,
        'session_id': session_id,
        'subagent': summary.to_dict(include_cost=True),
    })


@agente_bp.route('/api/admin/debug/subagent-fs', methods=['GET'])
@login_required
def api_admin_debug_subagent_fs():
    """
    Diagnostico: verifica se filesystem do SDK esta presente no container.

    Retorna:
    - projects_dir_exists: ~/.claude/projects/ existe?
    - project_dirs: quantos projetos, exemplo de session_ids
    - subagent_jsonls: quantos transcripts JSONL de subagents foram escritos
    - redis_url_set: REDIS_URL env var esta definida?
    """
    import os
    from pathlib import Path

    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Admin only'}), 403

    result = {
        'projects_dir_exists': False,
        'projects_dir': str(Path.home() / '.claude' / 'projects'),
        'project_dirs_count': 0,
        'project_sample': [],
        'subagent_sessions_count': 0,
        'subagent_jsonls_count': 0,
        'sample_subagent_jsonl': None,
        'redis_url_set': bool(os.environ.get('REDIS_URL')),
        'home_dir': str(Path.home()),
    }

    projects_dir = Path.home() / '.claude' / 'projects'
    if projects_dir.exists():
        result['projects_dir_exists'] = True
        project_dirs = [p for p in projects_dir.iterdir() if p.is_dir()]
        result['project_dirs_count'] = len(project_dirs)
        result['project_sample'] = [p.name for p in project_dirs[:3]]

        # Busca JSONLs de subagents
        subagent_jsonls = []
        for proj in project_dirs:
            for sess_dir in proj.iterdir():
                if not sess_dir.is_dir():
                    continue
                sub_dir = sess_dir / 'subagents'
                if sub_dir.exists():
                    result['subagent_sessions_count'] += 1
                    for jsonl in sub_dir.rglob('*.jsonl'):
                        subagent_jsonls.append(str(jsonl))
        result['subagent_jsonls_count'] = len(subagent_jsonls)
        if subagent_jsonls:
            result['sample_subagent_jsonl'] = subagent_jsonls[0]

    return jsonify({'success': True, 'debug': result})


@agente_bp.route(
    '/api/admin/sessions/<session_id>/subagents/<agent_id>/messages',
    methods=['GET'],
)
@login_required
def api_admin_subagent_messages(session_id: str, agent_id: str):
    """Mensagens brutas do JSONL (para debug profundo)."""
    if not USE_SUBAGENT_DEBUG_ENDPOINT:
        return jsonify({'success': False, 'error': 'Feature desabilitada'}), 404
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    from claude_agent_sdk import get_subagent_messages

    try:
        messages = list(get_subagent_messages(session_id, agent_id))
    except Exception as e:
        logger.error(f"[admin_subagents] get_subagent_messages falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'count': len(messages),
        'messages': [
            {
                'role': getattr(m, 'role', None),
                'content': getattr(m, 'content', None),
                'timestamp': (
                    getattr(m, 'timestamp', None).isoformat()
                    if getattr(m, 'timestamp', None) else None
                ),
            }
            for m in messages
        ],
    })
