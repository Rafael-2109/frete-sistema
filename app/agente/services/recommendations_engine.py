"""
Motor de recomendacoes acionaveis para o Dashboard de Insights.

Sistema rule-based que recebe metricas computadas e gera 0-5 recomendacoes
ordenadas por severidade. Cada recomendacao responde: "E dai? O que eu faco?"

Severidades:
    critical - Requer acao imediata
    warning  - Atencao necessaria
    info     - Oportunidade de melhoria
    success  - Agente saudavel (reforco positivo)

Uso:
    from .recommendations_engine import generate_recommendations
    recs = generate_recommendations(metrics)
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Limites maximos de recomendacoes por severidade
MAX_RECOMMENDATIONS = 5


def generate_recommendations(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Gera recomendacoes acionaveis baseadas nas metricas.

    Args:
        metrics: Dict com metricas computadas pelo insights_service:
            - resolution_rate (float 0-100)
            - cost_per_resolution (float USD)
            - friction_score (float 0-100)
            - adoption_rate (float 0-100)
            - model_distribution (dict {model: {count, cost}})
            - health_score (float 0-100)
            - deltas (dict com variacoes percentuais)
            - overview (dict com total_sessions, etc.)

    Returns:
        Lista de recomendacoes ordenadas por severidade (critical primeiro)
    """
    recommendations = []

    try:
        resolution_rate = metrics.get('resolution_rate', 0)
        friction_score = metrics.get('friction', {}).get('friction_score', 0)
        adoption_rate = metrics.get('adoption_rate', 0)
        model_dist = metrics.get('model_distribution', {})
        deltas = metrics.get('deltas', {})
        overview = metrics.get('overview', {})
        total_sessions = overview.get('total_sessions', 0)

        # Sem dados suficientes
        if total_sessions < 3:
            return [{
                'severity': 'info',
                'icon': 'fa-info-circle',
                'title': 'Dados insuficientes',
                'description': (
                    f'Apenas {total_sessions} sessao(oes) no periodo. '
                    'Aguarde mais uso para gerar recomendacoes significativas.'
                ),
                'metric_value': total_sessions,
                'threshold': 3,
                'action': None,
            }]

        # ── Regra 1: Taxa de resolucao baixa ──
        if resolution_rate < 60:
            recommendations.append({
                'severity': 'critical',
                'icon': 'fa-exclamation-circle',
                'title': 'Taxa de resolucao baixa',
                'description': (
                    f'Apenas {resolution_rate:.0f}% das sessoes resultam em resolucao efetiva. '
                    'Revise as sessoes sem uso de ferramentas na aba de Friccao. '
                    'O agente pode nao estar compreendendo as solicitacoes.'
                ),
                'metric_value': resolution_rate,
                'threshold': 60.0,
                'action': {
                    'type': 'filter_sessions',
                    'target': 'no_tools,abandoned',
                    'label': 'Ver sessoes problematicas',
                },
            })

        # ── Regra 2: Taxa de resolucao caiu vs periodo anterior ──
        delta_resolution = deltas.get('resolution_rate')
        if delta_resolution is not None and delta_resolution < -20:
            recommendations.append({
                'severity': 'warning',
                'icon': 'fa-arrow-down',
                'title': 'Resolucao caiu significativamente',
                'description': (
                    f'A taxa de resolucao caiu {abs(delta_resolution):.1f}% em relacao ao periodo anterior. '
                    'Verifique se houve mudanca no system prompt, skills ou modelos.'
                ),
                'metric_value': delta_resolution,
                'threshold': -20.0,
                'action': {
                    'type': 'switch_tab',
                    'target': 'sessions',
                    'label': 'Ver sessoes',
                },
            })

        # ── Regra 3: Custo medio subiu ──
        delta_cost = deltas.get('avg_cost_per_session')
        if delta_cost is not None and delta_cost > 50:
            recommendations.append({
                'severity': 'warning',
                'icon': 'fa-dollar-sign',
                'title': 'Custo por sessao subiu',
                'description': (
                    f'O custo medio por sessao aumentou {delta_cost:.0f}% vs periodo anterior. '
                    'Verifique o mix de modelos e sessoes excessivamente longas.'
                ),
                'metric_value': delta_cost,
                'threshold': 50.0,
                'action': {
                    'type': 'switch_tab',
                    'target': 'sessions',
                    'label': 'Ver sessoes por custo',
                },
            })

        # ── Regra 4: Friccao alta ──
        if friction_score >= 50:
            recommendations.append({
                'severity': 'warning',
                'icon': 'fa-exclamation-triangle',
                'title': 'Friccao alta detectada',
                'description': (
                    f'Score de friccao em {friction_score:.0f}/100. '
                    'Ha queries repetidas, sessoes abandonadas ou sinais de frustracao. '
                    'Analise a aba Friccao para detalhes.'
                ),
                'metric_value': friction_score,
                'threshold': 50.0,
                'action': {
                    'type': 'switch_tab',
                    'target': 'friction',
                    'label': 'Ver friccao',
                },
            })

        # ── Regra 5: Adocao baixa ──
        if adoption_rate < 50 and adoption_rate > 0:
            recommendations.append({
                'severity': 'info',
                'icon': 'fa-users',
                'title': 'Adocao pode melhorar',
                'description': (
                    f'Apenas {adoption_rate:.0f}% dos usuarios ativos usam o agente. '
                    'Considere treinamento ou comunicacao sobre as capacidades disponiveis.'
                ),
                'metric_value': adoption_rate,
                'threshold': 50.0,
                'action': {
                    'type': 'switch_tab',
                    'target': 'users',
                    'label': 'Ver usuarios',
                },
            })

        # ── Regra 6: Modelo caro dominante ──
        total_model_sessions = sum(
            m.get('count', 0) for m in model_dist.values()
        )
        if total_model_sessions > 0:
            for model_name, model_data in model_dist.items():
                if 'opus' in model_name.lower():
                    opus_pct = (model_data.get('count', 0) / total_model_sessions) * 100
                    if opus_pct > 80:
                        recommendations.append({
                            'severity': 'info',
                            'icon': 'fa-microchip',
                            'title': 'Modelo premium dominante',
                            'description': (
                                f'{opus_pct:.0f}% das sessoes usam Opus (mais caro). '
                                'Para consultas simples (SQL, estoque), Sonnet oferece '
                                'resultado similar com custo ~5x menor.'
                            ),
                            'metric_value': opus_pct,
                            'threshold': 80.0,
                            'action': {
                                'type': 'scroll_to',
                                'target': 'modelChart',
                                'label': 'Ver modelos',
                            },
                        })
                    break

        # ── Regra 7: Agente saudavel (positivo) ──
        if resolution_rate > 85 and friction_score < 15 and not recommendations:
            recommendations.append({
                'severity': 'success',
                'icon': 'fa-check-circle',
                'title': 'Agente operando bem',
                'description': (
                    f'Taxa de resolucao em {resolution_rate:.0f}% e friccao baixa ({friction_score:.0f}/100). '
                    'O agente esta atendendo bem a equipe.'
                ),
                'metric_value': resolution_rate,
                'threshold': 85.0,
                'action': None,
            })

    except Exception as e:
        logger.error(f"[RECOMMENDATIONS] Erro ao gerar recomendacoes: {e}")
        return []

    # Ordenar por severidade e limitar
    severity_order = {'critical': 0, 'warning': 1, 'info': 2, 'success': 3}
    recommendations.sort(key=lambda r: severity_order.get(r['severity'], 99))

    return recommendations[:MAX_RECOMMENDATIONS]
