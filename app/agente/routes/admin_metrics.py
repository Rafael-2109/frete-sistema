"""
Dashboard de Metricas de Subagents — admin only.

Pagina: GET /agente/admin/metrics
APIs JSON (todas admin-only):
  GET /agente/api/admin/metrics/overview
  GET /agente/api/admin/metrics/by-agent
  GET /agente/api/admin/metrics/timeseries
  GET /agente/api/admin/metrics/anomalies
  GET /agente/api/admin/metrics/cooccurrence
  GET /agente/api/admin/metrics/hourly
  GET /agente/api/admin/metrics/sparklines
  GET /agente/api/admin/metrics/drilldown/<agent_type>
  GET /agente/api/admin/metrics/filters
  GET /agente/api/admin/metrics/status

Pattern de auth: @login_required + inline check perfil='administrador'
(consistent com admin_session_store.py — abort(403) nao funciona aqui
pois global exception handler reraise HTTPException).

Le exclusivamente da tabela agent_invocation_metrics (populada pelo
hook A1/A2). Dashboard funciona com tabela vazia (mostra estado vazio).

Query params universais:
  period: '24h' | '7d' | '30d' (default 7d)
  source: 'production' | 'dev' | 'all' (default all)
  agent_types: CSV (ex: 'analista-carteira,raio-x-pedido')
  user_ids: CSV (ex: '5,12,18')
"""
import logging
from typing import List, Optional

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.agente.routes import agente_bp
from app.agente.services import metrics_dashboard_service as svc

logger = logging.getLogger('sistema_fretes')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_admin():
    """Retorna tuple (response, status) se NAO for admin, None se autorizado."""
    if not current_user.is_authenticated or current_user.perfil != 'administrador':
        return jsonify({
            'success': False,
            'error': 'Acesso restrito a administradores',
        }), 403
    return None


def _parse_csv_param(name: str) -> Optional[List[str]]:
    """Le query param CSV e retorna lista, ou None se vazio."""
    raw = (request.args.get(name) or '').strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    return parts or None


def _parse_csv_int_param(name: str) -> Optional[List[int]]:
    """Idem mas converte para int."""
    parts = _parse_csv_param(name)
    if not parts:
        return None
    out: List[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except (TypeError, ValueError):
            continue
    return out or None


def _common_filters():
    """Extrai filtros padrao do request.args."""
    period = (request.args.get('period') or '7d').strip()
    if period not in ('24h', '7d', '30d'):
        period = '7d'

    source = (request.args.get('source') or 'all').strip()
    if source not in ('production', 'dev', 'all'):
        source = 'all'

    return {
        'period': period,
        'source': source,
        'agent_types': _parse_csv_param('agent_types'),
        'user_ids': _parse_csv_int_param('user_ids'),
    }


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------

@agente_bp.route('/admin/metrics', methods=['GET'])
@login_required
def admin_metrics_page():
    """Renderiza dashboard. Auth via template (mostra 403 se nao admin)."""
    if current_user.perfil != 'administrador':
        return render_template(
            'agente/admin_metrics.html',
            forbidden=True,
        ), 403
    return render_template('agente/admin_metrics.html', forbidden=False)


# ---------------------------------------------------------------------------
# APIs JSON
# ---------------------------------------------------------------------------

@agente_bp.route('/api/admin/metrics/status', methods=['GET'])
@login_required
def api_admin_metrics_status():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        data = svc.get_table_status()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.exception(f"[admin_metrics] status falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/filters', methods=['GET'])
@login_required
def api_admin_metrics_filters():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        period = (request.args.get('period') or '30d').strip()
        if period not in ('24h', '7d', '30d'):
            period = '30d'
        data = svc.get_filter_options(period=period)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.exception(f"[admin_metrics] filters falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/overview', methods=['GET'])
@login_required
def api_admin_metrics_overview():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        data = svc.get_overview(**f)
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] overview falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/by-agent', methods=['GET'])
@login_required
def api_admin_metrics_by_agent():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        data = svc.get_by_agent_type(**f)
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] by-agent falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/timeseries', methods=['GET'])
@login_required
def api_admin_metrics_timeseries():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        # Time series sempre usa periodo do filtro
        data = svc.get_timeseries(**f)
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] timeseries falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/anomalies', methods=['GET'])
@login_required
def api_admin_metrics_anomalies():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        # Anomalies fixa janela: 24h sobre baseline P95(7d)
        data = svc.get_anomalies(
            source=f['source'],
            agent_types=f['agent_types'],
            user_ids=f['user_ids'],
        )
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] anomalies falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/cooccurrence', methods=['GET'])
@login_required
def api_admin_metrics_cooccurrence():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        # Co-occurrence ignora filtros de user e agent_type (matriz e global)
        data = svc.get_cooccurrence(period=f['period'], source=f['source'])
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] cooccurrence falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/hourly', methods=['GET'])
@login_required
def api_admin_metrics_hourly():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        data = svc.get_hourly_heatmap(**f)
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] hourly falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/sparklines', methods=['GET'])
@login_required
def api_admin_metrics_sparklines():
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        data = svc.get_sparklines(**f)
        return jsonify({'success': True, 'data': data, 'filters': f})
    except Exception as e:
        logger.exception(f"[admin_metrics] sparklines falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/metrics/drilldown/<agent_type>', methods=['GET'])
@login_required
def api_admin_metrics_drilldown(agent_type: str):
    auth_fail = _require_admin()
    if auth_fail is not None:
        return auth_fail

    try:
        f = _common_filters()
        limit = request.args.get('limit', 20, type=int)
        data = svc.get_drilldown(
            agent_type=agent_type,
            period=f['period'],
            source=f['source'],
            limit=limit,
        )
        return jsonify({
            'success': True,
            'data': data,
            'filters': {**f, 'agent_type': agent_type, 'limit': limit},
        })
    except Exception as e:
        logger.exception(f"[admin_metrics] drilldown falhou: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
