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

    # ═══════════════════════════════════════════════════════════════════
    # Investigacao SQL direta (agent tool allowlist bloqueia agent_sessions)
    # ═══════════════════════════════════════════════════════════════════
    try:
        from sqlalchemy import text
        from app import db

        # 1. Indice GIN criado? (migration Task 1.5)
        idx_rows = db.session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'agent_sessions'
              AND indexname LIKE '%subagent%'
        """)).fetchall()
        result['sql_indexes_subagent'] = [r.indexname for r in idx_rows]

        # 2. Alguma sessao recente tem subagent_costs persistido? (Task 1.6)
        cost_rows = db.session.execute(text("""
            SELECT
                session_id,
                user_id,
                created_at,
                (data ? 'subagent_costs') AS tem_cost,
                COALESCE(
                    jsonb_array_length(data->'subagent_costs'->'entries'),
                    0
                ) AS num_entries
            FROM agent_sessions
            WHERE created_at > now() - interval '4 hours'
            ORDER BY created_at DESC
            LIMIT 10
        """)).fetchall()
        result['sql_recent_sessions'] = [
            {
                'session_id': r.session_id[:16] + '...',
                'user_id': r.user_id,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'tem_cost': bool(r.tem_cost),
                'num_entries': r.num_entries,
            }
            for r in cost_rows
        ]

        # 3. Alguma sessao tem subagent_validations? (Task 4.1)
        val_row = db.session.execute(text("""
            SELECT COUNT(*) AS n
            FROM agent_sessions
            WHERE data ? 'subagent_validations'
              AND created_at > now() - interval '24 hours'
        """)).fetchone()
        result['sql_sessions_with_validation'] = val_row.n if val_row else 0

    except Exception as sql_err:
        result['sql_error'] = f'{type(sql_err).__name__}: {sql_err}'

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

    # T4b (2026-04-17): SessionMessage do SDK 0.1.60 tem shape
    # SessionMessage(type, uuid, session_id, message, parent_tool_use_id)
    # onde `message` e dict Anthropic. Nao acessar .role/.content direto.
    # FONTE: claude_agent_sdk/types.py:1134-1155.
    def _serialize_msg(m):
        msg_dict = getattr(m, 'message', None)
        if isinstance(msg_dict, dict):
            return {
                'type': getattr(m, 'type', None),
                'uuid': getattr(m, 'uuid', None),
                'role': msg_dict.get('role'),
                'model': msg_dict.get('model'),
                'content': msg_dict.get('content'),
                'usage': msg_dict.get('usage'),
            }
        # Fallback legacy
        return {
            'type': getattr(m, 'type', None),
            'role': getattr(m, 'role', None),
            'content': getattr(m, 'content', None),
        }

    return jsonify({
        'success': True,
        'session_id': session_id,
        'agent_id': agent_id,
        'count': len(messages),
        'messages': [_serialize_msg(m) for m in messages],
    })


@agente_bp.route('/api/admin/debug/subagent-smoketest', methods=['GET'])
@login_required
def api_admin_subagent_smoketest():
    """
    T12 (2026-04-17): healthcheck post-deploy para pipeline de subagente.

    Percorre as ultimas 20 sessoes com `subagent_costs` populado,
    executa `list_subagents` + `get_subagent_summary` da primeira que
    encontrar, e retorna relatorio.

    Criterio de "healthy":
    - list_subagents() retorna >= 1 agent_id
    - get_subagent_summary retorna status='done' com tools_used > 0 OU findings > 0
    - cost_usd > 0 em pelo menos 1 entry de subagent_costs

    Uso: `curl /agente/api/admin/debug/subagent-smoketest` logado como admin.
    Rodar em post-deploy hook; rollback se healthy=False por 15min+.
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Admin only'}), 403

    from sqlalchemy import text as _sql_text
    from app import db
    from app.agente.sdk.subagent_reader import (
        list_session_subagents,
        get_subagent_summary,
    )

    report: dict = {
        'healthy': False,
        'session_id': None,
        'list_subagents_count': 0,
        'summary_status': None,
        'tools_used': 0,
        'findings_len': 0,
        'cost_usd': 0.0,
        'num_turns': 0,
        'entries_in_db': 0,
        'error': None,
    }

    try:
        row = db.session.execute(_sql_text("""
            SELECT session_id,
                   jsonb_array_length(data->'subagent_costs'->'entries') AS n_entries
            FROM agent_sessions
            WHERE data ? 'subagent_costs'
              AND jsonb_array_length(data->'subagent_costs'->'entries') > 0
              AND updated_at > now() - interval '24 hours'
            ORDER BY updated_at DESC
            LIMIT 1
        """)).fetchone()

        if row is None:
            report['error'] = (
                'Nenhuma sessao com subagent_costs nas ultimas 24h. '
                'Pipeline pode estar quebrado OU nao houve uso.'
            )
            return jsonify({'success': True, 'report': report})

        report['session_id'] = row.session_id
        report['entries_in_db'] = row.n_entries

        # list_subagents
        agent_ids = list_session_subagents(row.session_id)
        report['list_subagents_count'] = len(agent_ids)

        if not agent_ids:
            report['error'] = 'list_subagents retornou vazio para sessao com entries no DB'
            return jsonify({'success': True, 'report': report})

        # get_subagent_summary do primeiro agent
        summary = get_subagent_summary(
            session_id=row.session_id,
            agent_id=agent_ids[0],
            include_pii=True,
        )
        report['summary_status'] = summary.status
        report['tools_used'] = len(summary.tools_used)
        report['findings_len'] = len(summary.findings_text or '')
        report['cost_usd'] = round(summary.cost_usd, 6)
        report['num_turns'] = summary.num_turns

        # Healthy se: summary bem formado + cost calculado
        report['healthy'] = (
            summary.status == 'done'
            and (summary.num_turns > 0 or summary.cost_usd > 0)
            and (len(summary.tools_used) > 0 or len(summary.findings_text or '') > 0)
        )

    except Exception as e:
        logger.error(f"[subagent_smoketest] falhou: {e}")
        report['error'] = f'{type(e).__name__}: {str(e)[:300]}'

    return jsonify({'success': True, 'report': report})
