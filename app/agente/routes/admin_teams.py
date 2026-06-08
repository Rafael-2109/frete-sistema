"""
Dashboard de Observabilidade do canal Teams — admin only (F2).

Pagina: GET /agente/admin/teams
APIs JSON (todas admin-only):
  GET /agente/api/admin/teams/overview     — KPIs operacionais (volume/status/latencia/fila/usuarios)
  GET /agente/api/admin/teams/timeseries   — serie temporal de volume
  GET /agente/api/admin/teams/users        — top usuarios por volume
  GET /agente/api/admin/teams/stuck        — tasks travadas (snapshot, threshold_min)
  GET /agente/api/admin/teams/recent       — drill-down ultimas tasks (status opcional)
  GET /agente/api/admin/teams/cost         — custo/tokens (AgentStep channel='teams')
  GET /agente/api/admin/teams/tools        — ferramentas mais usadas no Teams
  GET /agente/api/admin/teams/skills       — efetividade de skills em sessoes Teams

Pattern de auth: @login_required + check inline perfil='administrador'
(espelha admin_metrics.py / admin_session_store.py — abort(403) nao funciona
aqui pois o global exception handler re-raise HTTPException).

Le de `teams_observability_service` (teams_tasks + agent_step channel='teams'
+ agent_skill_effectiveness). Funciona com tabelas vazias (mostra estado vazio).

Query params:
  period: '24h' | '7d' | '30d' (default 7d)
  status: filtro opcional p/ /recent
  threshold_min: int p/ /stuck (default 10)
"""
import logging

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.agente.routes import agente_bp
from app.agente.services import teams_observability_service as svc

logger = logging.getLogger('sistema_fretes')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_admin():
    """Retorna (response, 403) se NAO for admin; None se autorizado."""
    if not current_user.is_authenticated or getattr(current_user, 'perfil', None) != 'administrador':
        return jsonify({
            'success': False,
            'error': 'Acesso restrito a administradores',
        }), 403
    return None


def _period() -> str:
    period = (request.args.get('period') or '7d').strip()
    return period if period in ('24h', '7d', '30d') else '7d'


def _json(fn, *args, **kwargs):
    """Wrapper padrao: auth admin + chama service + jsonify (captura erros)."""
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail
    try:
        data = fn(*args, **kwargs)
        return jsonify({'success': True, 'data': data})
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[admin_teams] {getattr(fn, '__name__', 'endpoint')} falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------

@agente_bp.route('/admin/teams', methods=['GET'])
@login_required
def admin_teams_page():
    """Renderiza o dashboard. Auth via template (403 se nao admin)."""
    if getattr(current_user, 'perfil', None) != 'administrador':
        return render_template('agente/admin_teams.html', forbidden=True), 403
    return render_template('agente/admin_teams.html', forbidden=False)


# ---------------------------------------------------------------------------
# APIs JSON
# ---------------------------------------------------------------------------

@agente_bp.route('/api/admin/teams/overview', methods=['GET'])
@login_required
def api_admin_teams_overview():
    return _json(svc.get_overview, _period())


@agente_bp.route('/api/admin/teams/timeseries', methods=['GET'])
@login_required
def api_admin_teams_timeseries():
    return _json(svc.get_timeseries, _period())


@agente_bp.route('/api/admin/teams/users', methods=['GET'])
@login_required
def api_admin_teams_users():
    return _json(svc.get_top_users, _period())


@agente_bp.route('/api/admin/teams/stuck', methods=['GET'])
@login_required
def api_admin_teams_stuck():
    try:
        threshold = int(request.args.get('threshold_min', 10))
    except (TypeError, ValueError):
        threshold = 10
    return _json(svc.get_stuck_tasks, threshold)


@agente_bp.route('/api/admin/teams/recent', methods=['GET'])
@login_required
def api_admin_teams_recent():
    status = (request.args.get('status') or '').strip() or None
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
    except (TypeError, ValueError):
        limit = 50
    return _json(svc.get_recent_tasks, limit, status)


@agente_bp.route('/api/admin/teams/cost', methods=['GET'])
@login_required
def api_admin_teams_cost():
    return _json(svc.get_cost_quality_overview, _period())


@agente_bp.route('/api/admin/teams/tools', methods=['GET'])
@login_required
def api_admin_teams_tools():
    return _json(svc.get_tools_usage, _period())


@agente_bp.route('/api/admin/teams/skills', methods=['GET'])
@login_required
def api_admin_teams_skills():
    return _json(svc.get_skill_effectiveness, _period())
