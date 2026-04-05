"""Dashboard de Insights do Agente (admin only)."""

import logging

from flask import request, jsonify, render_template
from flask_login import login_required, current_user

from app.agente.routes import agente_bp

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/insights', methods=['GET'])
@login_required
def pagina_insights():
    """
    P2-2: Página de analytics do agente (admin only).

    GET /agente/insights

    Requer:
    - Perfil 'administrador'
    - Flag USE_AGENT_INSIGHTS ativa
    """
    from app.agente.config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    return render_template('agente/insights.html')


@agente_bp.route('/api/insights/data', methods=['GET'])
@login_required
def api_insights_data():
    """
    API unificada de dados de insights (inclui friccao e recomendacoes).

    GET /agente/api/insights/data?days=30&compare=true&user_id=123

    Params:
        days: Periodo em dias (default 30, max 90)
        compare: Se 'true', inclui deltas vs periodo anterior (default true)
        user_id: Filtrar por usuario especifico (opcional)

    Response:
        JSON com secoes: overview, costs, tools, users, sessions, daily,
        friction, recommendations, deltas, health_score, resolution_rate,
        model_distribution, topics, adoption_rate
    """
    from app.agente.config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)

        compare = request.args.get('compare', 'true').lower() == 'true'
        filter_user_id = request.args.get('user_id', None, type=int)

        from app.agente.services.insights_service import get_insights_data

        data = get_insights_data(
            days=days,
            user_id=filter_user_id,
            compare=compare,
        )

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao gerar insights: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# TODO: wire no insights dashboard — metricas exclusivas nao disponiveis em /data
@agente_bp.route('/api/insights/memory', methods=['GET'])
@login_required
def api_insights_memory():
    """
    Métricas de qualidade do sistema de memória (T2-5).

    GET /agente/api/insights/memory?days=30&user_id=123

    Returns:
        JSON com métricas: utilization_rate, corrections_count,
        avg_importance_score, decay_distribution, orphan_embeddings, categories
    """
    from app.agente.config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)
        user_id = request.args.get('user_id', None, type=int)

        from app.agente.services.insights_service import get_memory_metrics

        data = get_memory_metrics(days=days, user_id=user_id)

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro nas metricas de memoria: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/insights/routing', methods=['GET'])
@login_required
def api_insights_routing():
    """
    Métricas de saúde do roteamento — custo $0.

    GET /agente/api/insights/routing?days=30&user_id=123
    """
    from app.agente.config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)
        user_id = request.args.get('user_id', None, type=int)

        from app.agente.services.insights_service import get_routing_metrics

        data = get_routing_metrics(days=days, user_id=user_id)

        # Detect service-level error (internal catch returns {'error': '...'})
        if data.get('error'):
            return jsonify({
                'success': False,
                'error': data['error'],
            }), 500

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro nas metricas de routing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
