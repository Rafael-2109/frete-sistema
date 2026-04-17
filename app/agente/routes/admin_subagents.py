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
    Diagnostico: verifica onde o SDK Claude escreve transcripts no container.

    Descobre qual path esta sendo usado pelo CLI do SDK — importante para
    descobrir se o container nao tem o diretorio criado OU se o SDK usa
    HOME/CLAUDE_CONFIG_DIR diferente do esperado.
    """
    import os
    import subprocess
    from pathlib import Path

    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Admin only'}), 403

    result = {
        'env': {
            'HOME': os.environ.get('HOME'),
            'CLAUDE_CONFIG_DIR': os.environ.get('CLAUDE_CONFIG_DIR'),
            'ANTHROPIC_API_KEY_set': bool(os.environ.get('ANTHROPIC_API_KEY')),
            'REDIS_URL_set': bool(os.environ.get('REDIS_URL')),
            'USER': os.environ.get('USER'),
            'PWD': os.environ.get('PWD'),
        },
        'python_home': str(Path.home()),
        'python_cwd': os.getcwd(),
        'paths_checked': {},
        'jsonl_found': [],
    }

    # Lista paths candidatos onde o SDK pode ter escrito
    candidates = [
        Path.home() / '.claude',
        Path('/opt/render/.claude'),
        Path('/opt/render/project/src/.claude'),
        Path('/tmp/.claude'),
        Path('/root/.claude'),
        Path('/home/render/.claude'),
    ]
    if os.environ.get('CLAUDE_CONFIG_DIR'):
        candidates.insert(0, Path(os.environ['CLAUDE_CONFIG_DIR']))

    for cand in candidates:
        info = {'exists': False, 'is_dir': False, 'children': [], 'error': None}
        try:
            info['exists'] = cand.exists()
            if info['exists'] and cand.is_dir():
                info['is_dir'] = True
                try:
                    info['children'] = [p.name for p in list(cand.iterdir())[:10]]
                except (OSError, PermissionError) as e:
                    info['children'] = f'<{type(e).__name__}>'
                # Busca JSONLs em profundidade
                try:
                    for jsonl in cand.rglob('*.jsonl'):
                        result['jsonl_found'].append(str(jsonl))
                        if len(result['jsonl_found']) >= 5:
                            break
                except (OSError, PermissionError):
                    pass
        except (OSError, PermissionError) as e:
            info['error'] = f'{type(e).__name__}: {e}'
        result['paths_checked'][str(cand)] = info

    # Tenta achar JSONLs em qualquer lugar via find (com timeout)
    try:
        out = subprocess.run(
            ['find', '/opt/render', '/tmp', '-name', '*.jsonl',
             '-path', '*subagents*', '-type', 'f'],
            capture_output=True, text=True, timeout=5
        )
        jsonls_found = [p for p in out.stdout.strip().split('\n') if p]
        result['find_subagents_jsonl'] = jsonls_found[:10]
    except Exception as e:
        result['find_error'] = str(e)

    # Verifica se o CLI esta instalado
    try:
        out = subprocess.run(
            ['which', 'claude'], capture_output=True, text=True, timeout=2
        )
        result['claude_cli_path'] = out.stdout.strip() or None
    except Exception:
        result['claude_cli_path'] = None

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
