"""
Endpoint admin observability do SessionStore (R6).

Expoe metricas agregadas da tabela claude_session_store:
- Total rows, sessions, projects
- Rows por hora (ultimas 24h)
- Types distribution
- Top 10 sessions por volume de entries
- Subagent vs main transcripts split
- Status do pool asyncpg (via flag + presenca)

Pattern de auth: @login_required + inline check perfil='administrador' → 403
(consistent com admin_subagents.py — abort(403) nao funciona aqui pois
global exception handler reraise HTTPException).

Flag: AGENT_SDK_SESSION_STORE_ENABLED controla se o store esta ativo;
endpoint funciona mesmo com flag OFF (mostra tabela vazia).
"""
import logging

from flask import jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import text

from app import db
from app.agente.config.feature_flags import AGENT_SDK_SESSION_STORE_ENABLED
from app.agente.routes import agente_bp

logger = logging.getLogger('sistema_fretes')


def _require_admin():
    """Retorna tuple (response, status) se NAO for admin, None se autorizado.

    Pattern inline (abort() quebra por causa do global exception handler).
    """
    if current_user.perfil != 'administrador':
        return jsonify({
            'success': False,
            'error': 'Acesso restrito a administradores',
        }), 403
    return None


@agente_bp.route('/api/admin/session-store/stats', methods=['GET'])
@login_required
def api_admin_session_store_stats():
    """Retorna metricas agregadas da tabela claude_session_store.

    Queries todas indexed (PK composta + partial index em subpath='').
    Tempo de execucao esperado < 200ms ate ~1M rows.
    """
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        # 1. Totais
        totals = db.session.execute(text("""
            SELECT
                COUNT(*)::bigint AS total_rows,
                COUNT(DISTINCT session_id)::bigint AS total_sessions,
                COUNT(DISTINCT project_key)::bigint AS total_projects,
                COUNT(*) FILTER (WHERE subpath = '')::bigint AS main_entries,
                COUNT(*) FILTER (WHERE subpath <> '')::bigint AS subagent_entries,
                COUNT(DISTINCT session_id) FILTER (WHERE subpath <> '')::bigint AS sessions_com_subagents
            FROM claude_session_store
        """)).mappings().one()

        # 2. Atividade ultimas 24h (por hora)
        hourly = db.session.execute(text("""
            SELECT
                to_char(date_trunc('hour', to_timestamp(mtime / 1000.0)), 'YYYY-MM-DD HH24:00') AS hora,
                COUNT(*)::bigint AS rows,
                COUNT(DISTINCT session_id)::bigint AS sessions
            FROM claude_session_store
            WHERE mtime > (EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours') * 1000)::bigint
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT 24
        """)).mappings().all()

        # 3. Types distribution (so main transcripts) — R6.3: cap 50 types
        types = db.session.execute(text("""
            SELECT
                COALESCE(entry->>'type', '<unknown>') AS type,
                COUNT(*)::bigint AS count
            FROM claude_session_store
            WHERE subpath = ''
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 50
        """)).mappings().all()

        # 4. Top 10 sessions por volume
        top_sessions = db.session.execute(text("""
            SELECT
                session_id,
                project_key,
                COUNT(*)::bigint AS entries,
                to_timestamp(MIN(mtime) / 1000.0)::timestamp AS primeiro,
                to_timestamp(MAX(mtime) / 1000.0)::timestamp AS ultimo,
                EXTRACT(EPOCH FROM (
                    to_timestamp(MAX(mtime) / 1000.0) - to_timestamp(MIN(mtime) / 1000.0)
                ))::int AS spread_seg
            FROM claude_session_store
            WHERE subpath = ''
            GROUP BY session_id, project_key
            ORDER BY entries DESC
            LIMIT 10
        """)).mappings().all()

        # 5. Projects (multi-tenancy) — R6.3: cap 100 projects
        projects = db.session.execute(text("""
            SELECT
                project_key,
                COUNT(DISTINCT session_id)::bigint AS sessions,
                COUNT(*)::bigint AS entries,
                to_timestamp(MAX(mtime) / 1000.0)::timestamp AS ultimo
            FROM claude_session_store
            GROUP BY project_key
            ORDER BY entries DESC
            LIMIT 100
        """)).mappings().all()

        # 6. Atividade ultimos 7 dias (por dia) — R6.3: cap 7 dias
        daily = db.session.execute(text("""
            SELECT
                to_char(date_trunc('day', to_timestamp(mtime / 1000.0)), 'YYYY-MM-DD') AS dia,
                COUNT(*)::bigint AS rows,
                COUNT(DISTINCT session_id)::bigint AS sessions
            FROM claude_session_store
            WHERE mtime > (EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days') * 1000)::bigint
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT 7
        """)).mappings().all()

        return jsonify({
            'success': True,
            'flag_enabled': AGENT_SDK_SESSION_STORE_ENABLED,
            'totals': dict(totals),
            'hourly_24h': [dict(r) for r in hourly],
            'daily_7d': [dict(r) for r in daily],
            'types_distribution': [dict(r) for r in types],
            'top_sessions': [
                {
                    **dict(r),
                    'primeiro': r['primeiro'].isoformat() if r['primeiro'] else None,
                    'ultimo': r['ultimo'].isoformat() if r['ultimo'] else None,
                }
                for r in top_sessions
            ],
            'projects': [
                {
                    **dict(r),
                    'ultimo': r['ultimo'].isoformat() if r['ultimo'] else None,
                }
                for r in projects
            ],
        })
    except Exception as e:
        # FIX P2 (R6.4): nao vazar PG error text para frontend
        logger.error(f"[ADMIN_SESSION_STORE] erro em stats: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Erro interno — ver logs do servidor',
        }), 500


@agente_bp.route('/api/admin/session-store/sessions/<session_id>', methods=['GET'])
@login_required
def api_admin_session_store_detail(session_id: str):
    """Retorna metadata + primeiras/ultimas entries de uma session no store.

    Util para debug forense — ver o que o batcher realmente persistiu.
    """
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        meta = db.session.execute(text("""
            SELECT
                session_id,
                project_key,
                COUNT(*)::bigint AS total_entries,
                COUNT(*) FILTER (WHERE subpath = '')::bigint AS main_entries,
                array_agg(DISTINCT subpath ORDER BY subpath) AS subpaths,
                to_timestamp(MIN(mtime) / 1000.0)::timestamp AS primeiro,
                to_timestamp(MAX(mtime) / 1000.0)::timestamp AS ultimo
            FROM claude_session_store
            WHERE session_id = :sid
            GROUP BY session_id, project_key
        """), {'sid': session_id}).mappings().first()

        if meta is None:
            return jsonify({
                'success': False,
                'error': f'session_id {session_id} nao encontrada no store',
            }), 404

        # Primeiras 5 + ultimas 5 entries (main transcript)
        preview = db.session.execute(text("""
            (
                SELECT seq, subpath, entry->>'type' AS type, entry->>'uuid' AS uuid,
                       entry->>'timestamp' AS timestamp
                FROM claude_session_store
                WHERE session_id = :sid AND subpath = ''
                ORDER BY seq ASC
                LIMIT 5
            )
            UNION ALL
            (
                SELECT seq, subpath, entry->>'type' AS type, entry->>'uuid' AS uuid,
                       entry->>'timestamp' AS timestamp
                FROM claude_session_store
                WHERE session_id = :sid AND subpath = ''
                ORDER BY seq DESC
                LIMIT 5
            )
            ORDER BY seq
        """), {'sid': session_id}).mappings().all()

        return jsonify({
            'success': True,
            'meta': {
                **dict(meta),
                'primeiro': meta['primeiro'].isoformat() if meta['primeiro'] else None,
                'ultimo': meta['ultimo'].isoformat() if meta['ultimo'] else None,
            },
            'preview': [dict(r) for r in preview],
        })
    except Exception as e:
        logger.error(
            f"[ADMIN_SESSION_STORE] erro em detail {session_id}: {e}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Erro interno — ver logs do servidor',
        }), 500


@agente_bp.route('/admin/session-store', methods=['GET'])
@login_required
def admin_session_store_page():
    """Pagina HTML com dashboard admin do SessionStore."""
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    return render_template('agente/admin_session_store.html')
