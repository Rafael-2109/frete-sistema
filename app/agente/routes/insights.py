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


@agente_bp.route('/api/insights/cache-performance', methods=['GET'])
@login_required
def api_insights_cache_performance():
    """
    G9 (2026-04-15): Cache hit rate e economia estimada.

    Le do cost_tracker em memoria (runtime-only — nao persistido em DB).
    Cobertura temporal limitada a CostTracker.clear_old_entries (7 dias
    default). Para analise historica longa, sera necessaria migration
    DB futura (fora do escopo G2/G9 atual).

    GET /agente/api/insights/cache-performance?days=1&user_id=123

    Params:
        days: janela de dias (default 1, max 7 — limite do tracker)
        user_id: filtrar por usuario (opcional)

    Response:
        {
          "success": true,
          "data": {
            "period": {"days": 1, "start": "...", "end": "..."},
            "totals": {
              "input_tokens": 12345,
              "output_tokens": 2345,
              "cache_read_tokens": 9876,
              "cache_creation_tokens": 1234,
              "cost_usd": 0.1234
            },
            "cache_hit_rate": 0.44,
            "estimated_savings_usd": 0.0389,
            "verdict": "good|weak|cold",
            "by_user": {...},
            "by_tool": {...}
          }
        }
    """
    from app.agente.config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        from datetime import timedelta
        from app.utils.timezone import agora_utc_naive
        from app.agente.sdk.cost_tracker import get_cost_tracker

        days = request.args.get('days', 1, type=int)
        days = min(max(days, 1), 7)  # tracker mantem ~7 dias por default
        user_id = request.args.get('user_id', None, type=int)

        since = agora_utc_naive() - timedelta(days=days)

        tracker = get_cost_tracker()
        summary = tracker.get_summary(user_id=user_id, since=since)
        data = summary.to_dict()

        # Verdict textual para o dashboard — threshold empirico
        hit_rate = data.get('cache_hit_rate', 0)
        if data.get('total_requests', 0) == 0:
            verdict = 'sem_dados'
        elif hit_rate >= 0.40:
            verdict = 'bom'  # >=40% ja economiza significativamente
        elif hit_rate >= 0.15:
            verdict = 'fraco'  # cache existe mas subutilizado
        else:
            verdict = 'frio'  # cache nao esta funcionando (ou prompts voláteis)

        return jsonify({
            'success': True,
            'data': {
                'period': {
                    'days': days,
                    'start': data.get('period_start'),
                    'end': data.get('period_end'),
                },
                'totals': {
                    'requests': data.get('total_requests', 0),
                    'input_tokens': data.get('total_input_tokens', 0),
                    'output_tokens': data.get('total_output_tokens', 0),
                    'cache_read_tokens': data.get('total_cache_read_tokens', 0),
                    'cache_creation_tokens': data.get('total_cache_creation_tokens', 0),
                    'cost_usd': data.get('total_cost_usd', 0),
                },
                'cache_hit_rate': hit_rate,
                'estimated_savings_usd': data.get('estimated_savings_usd', 0),
                'verdict': verdict,
                'by_user': data.get('by_user', {}),
                'by_tool': data.get('by_tool', {}),
                'note': (
                    'Metricas runtime-only (cost_tracker em memoria). '
                    'Cobertura limitada a ~7 dias. Historico longo '
                    'requer migration DB futura.'
                ),
            },
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro em cache-performance: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
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
