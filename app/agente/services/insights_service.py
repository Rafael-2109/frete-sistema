"""
Dashboard de Insights do Agente — Service Layer.

Gera metricas acionaveis sobre uso do agente. Cada metrica responde:
"E dai? O que eu faco a respeito?"

Metricas calculadas:
- Taxa de Resolucao (% sessoes com uso efetivo de tools)
- Custo por Resolucao (USD / sessao resolvida)
- Health Score composto (0-100)
- Comparacao periodo-a-periodo (deltas %)
- Distribuicao de modelos (Opus/Sonnet/Haiku)
- Topicos abordados (de summaries)
- Friccao integrada (inline, nao endpoint separado)
- Recomendacoes acionaveis (via recommendations_engine)

Uso:
    Chamado por GET /agente/api/insights/data?days=30&compare=true
"""

import logging
from collections import Counter
from datetime import timedelta
from typing import Dict, Any, List, Optional

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def get_insights_data(
    days: int = 30,
    user_id: Optional[int] = None,
    compare: bool = True,
) -> Dict[str, Any]:
    """
    Gera dados completos de insights do agente.

    Args:
        days: Periodo de analise em dias (default 30)
        user_id: Filtrar por usuario especifico (None = todos)
        compare: Se True, busca periodo anterior e computa deltas

    Returns:
        Dict com secoes: overview, costs, tools, sessions, users,
        daily, friction, recommendations, deltas, health_score,
        resolution_rate, model_distribution, topics
    """
    try:
        from ..models import AgentSession

        now = agora_utc_naive()
        since = now - timedelta(days=days)

        # ── Query periodo atual ──
        base_query = AgentSession.query.filter(
            AgentSession.created_at >= since
        )
        if user_id:
            base_query = base_query.filter(AgentSession.user_id == user_id)

        sessions = base_query.all()

        if not sessions:
            return _empty_insights(days)

        # ── Computar metricas do periodo atual ──
        current = _compute_all(sessions, days)

        # ── Periodo anterior para comparacao ──
        if compare:
            prev_start = since - timedelta(days=days)
            prev_query = AgentSession.query.filter(
                AgentSession.created_at >= prev_start,
                AgentSession.created_at < since,
            )
            if user_id:
                prev_query = prev_query.filter(AgentSession.user_id == user_id)

            prev_sessions = prev_query.all()

            if prev_sessions:
                previous = _compute_all(prev_sessions, days)
                current['deltas'] = _compute_deltas(current, previous)
            else:
                current['deltas'] = _null_deltas()
        else:
            current['deltas'] = _null_deltas()

        # ── Friccao integrada ──
        try:
            from .friction_analyzer import analyze_friction
            friction_data = analyze_friction(days=days, user_id=user_id)
            current['friction'] = friction_data
        except Exception as e:
            logger.warning(f"[INSIGHTS] Erro na analise de friccao: {e}")
            current['friction'] = {
                'friction_score': 0,
                'total_sessions_analyzed': 0,
                'repeated_queries': [],
                'abandoned_sessions': [],
                'frustration_signals': [],
                'no_tool_sessions': [],
                'summary': 'Analise de friccao indisponivel.',
            }

        # ── Adocao ──
        current['adoption_rate'] = _calc_adoption_rate(sessions)

        # ── Health Score ──
        current['health_score'] = _calc_health_score(
            resolution_rate=current['resolution_rate'],
            friction_score=current['friction'].get('friction_score', 0),
            cost_delta=current['deltas'].get('avg_cost_per_session'),
            adoption_rate=current['adoption_rate'],
        )

        # ── Recomendacoes ──
        try:
            from .recommendations_engine import generate_recommendations
            current['recommendations'] = generate_recommendations(current)
        except Exception as e:
            logger.warning(f"[INSIGHTS] Erro ao gerar recomendacoes: {e}")
            current['recommendations'] = []

        return current

    except Exception as e:
        logger.error(f"[INSIGHTS] Erro ao gerar insights: {e}")
        return _empty_insights(days)


# =============================================================================
# COMPUTACAO UNIFICADA
# =============================================================================

def _compute_all(sessions: List, days: int) -> Dict[str, Any]:
    """Computa TODAS as metricas para uma lista de sessoes."""
    overview = _calc_overview(sessions, days)
    cost_data = _calc_costs(sessions, days)
    tool_data = _calc_tools(sessions)
    user_data = _calc_users(sessions)
    session_data = _calc_sessions(sessions)
    daily_data = _calc_daily(sessions, days)
    resolution_rate = _calc_resolution_rate(sessions)
    model_dist = _calc_model_distribution(sessions)
    topics = _calc_topics(sessions)

    cost_per_res = 0.0
    resolved_count = _count_resolved(sessions)
    total_cost = float(overview['total_cost_usd'])
    if resolved_count > 0:
        cost_per_res = round(total_cost / resolved_count, 4)

    return {
        'period_days': days,
        'generated_at': agora_utc_naive().isoformat(),
        'overview': overview,
        'costs': cost_data,
        'tools': tool_data,
        'users': user_data,
        'sessions': session_data,
        'daily': daily_data,
        'resolution_rate': round(resolution_rate, 1),
        'resolved_sessions': resolved_count,
        'cost_per_resolution': cost_per_res,
        'model_distribution': model_dist,
        'topics': topics,
    }


# =============================================================================
# METRICAS NOVAS
# =============================================================================

def _calc_resolution_rate(sessions: List) -> float:
    """
    Calcula taxa de resolucao: % de sessoes onde agente usou tools
    E teve >= 4 mensagens (ida-e-volta real).

    Returns:
        Percentual 0-100
    """
    if not sessions:
        return 0.0

    resolved = _count_resolved(sessions)
    return (resolved / len(sessions)) * 100


def _count_resolved(sessions: List) -> int:
    """Conta sessoes consideradas 'resolvidas'."""
    count = 0
    for s in sessions:
        if (s.message_count or 0) < 4:
            continue

        messages = s.get_messages() if s.data else []
        has_tools = False
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('tools_used'):
                has_tools = True
                break

        if has_tools:
            count += 1

    return count


def _calc_model_distribution(sessions: List) -> Dict[str, Dict[str, Any]]:
    """
    Agrupa sessoes por modelo: contagem e custo.

    Returns:
        Dict {model_name: {count, cost_usd, pct}}
    """
    dist: Dict[str, Dict] = {}

    for s in sessions:
        model = s.model or 'desconhecido'
        if model not in dist:
            dist[model] = {'count': 0, 'cost_usd': 0.0}
        dist[model]['count'] += 1
        dist[model]['cost_usd'] += float(s.total_cost_usd or 0)

    total = len(sessions)
    for model_data in dist.values():
        model_data['cost_usd'] = round(model_data['cost_usd'], 4)
        model_data['pct'] = round(
            (model_data['count'] / total) * 100, 1
        ) if total else 0

    return dist


def _calc_topics(sessions: List) -> List[Dict[str, Any]]:
    """
    Extrai topicos abordados de summaries.

    Returns:
        Lista de {topic, count} ordenada por count DESC, top 15
    """
    topic_counter: Counter = Counter()

    for s in sessions:
        if not s.summary:
            continue

        summary = s.summary
        if isinstance(summary, dict):
            topicos = summary.get('topicos_abordados', [])
            if isinstance(topicos, list):
                for t in topicos:
                    if isinstance(t, str) and t.strip():
                        topic_counter[t.strip()] += 1

    result = [
        {'topic': topic, 'count': count}
        for topic, count in topic_counter.most_common(15)
    ]
    return result


def _calc_adoption_rate(sessions: List) -> float:
    """
    Calcula taxa de adocao: usuarios ativos com agente / total usuarios do sistema.

    Returns:
        Percentual 0-100
    """
    try:
        from app.auth.models import Usuario

        active_agent_users = len(set(s.user_id for s in sessions if s.user_id))
        total_active_users = Usuario.query.filter(
            Usuario.ativo == True  # noqa: E712
        ).count()

        if total_active_users == 0:
            return 0.0

        return round((active_agent_users / total_active_users) * 100, 1)
    except Exception:
        return 0.0


def _calc_health_score(
    resolution_rate: float,
    friction_score: float,
    cost_delta: Optional[float],
    adoption_rate: float,
) -> float:
    """
    Calcula score de saude composto (0-100).

    Formula:
        resolution_rate * 0.35
        + (100 - friction_score) * 0.25
        + cost_stability * 0.20
        + adoption_rate * 0.20

    cost_stability: 100 se custo estavel/desceu, penaliza se subiu muito.
    """
    # Cost stability: quanto mais subiu, pior (0-100)
    if cost_delta is None:
        cost_stability = 70.0  # neutro
    elif cost_delta <= 0:
        cost_stability = 100.0  # custo desceu → otimo
    elif cost_delta <= 25:
        cost_stability = 75.0  # subiu pouco → ok
    elif cost_delta <= 50:
        cost_stability = 50.0  # subiu moderado
    elif cost_delta <= 100:
        cost_stability = 25.0  # subiu muito
    else:
        cost_stability = 0.0  # disparou

    score = (
        resolution_rate * 0.35
        + (100 - friction_score) * 0.25
        + cost_stability * 0.20
        + adoption_rate * 0.20
    )

    return round(min(max(score, 0), 100), 1)


# =============================================================================
# DELTAS PERIODO-A-PERIODO
# =============================================================================

def _compute_deltas(current: Dict, previous: Dict) -> Dict[str, Optional[float]]:
    """
    Computa deltas percentuais entre periodo atual e anterior.

    Returns:
        Dict com chaves: total_sessions, total_cost_usd, resolution_rate,
        avg_cost_per_session, unique_users, friction_score
    """
    deltas = {}

    # Helper: computa delta % com protecao contra zero
    def pct_delta(curr_val, prev_val):
        if prev_val == 0 or prev_val is None:
            return None
        return round(((curr_val - prev_val) / abs(prev_val)) * 100, 1)

    co = current.get('overview', {})
    po = previous.get('overview', {})

    deltas['total_sessions'] = pct_delta(
        co.get('total_sessions', 0), po.get('total_sessions', 0)
    )
    deltas['total_cost_usd'] = pct_delta(
        co.get('total_cost_usd', 0), po.get('total_cost_usd', 0)
    )
    deltas['avg_cost_per_session'] = pct_delta(
        co.get('avg_cost_per_session', 0), po.get('avg_cost_per_session', 0)
    )
    deltas['unique_users'] = pct_delta(
        co.get('unique_users', 0), po.get('unique_users', 0)
    )
    deltas['resolution_rate'] = pct_delta(
        current.get('resolution_rate', 0), previous.get('resolution_rate', 0)
    )

    # Friction delta (inversao: diminuicao = positivo)
    curr_friction = current.get('friction', {}).get('friction_score', 0)
    prev_friction = previous.get('friction', {}).get('friction_score', 0) if previous.get('friction') else 0
    if prev_friction > 0:
        # Delta invertido: friccao desceu = bom (delta negativo)
        deltas['friction_score'] = round(
            ((curr_friction - prev_friction) / prev_friction) * 100, 1
        )
    else:
        deltas['friction_score'] = None

    return deltas


def _null_deltas() -> Dict[str, None]:
    """Retorna deltas nulos quando nao ha periodo anterior."""
    return {
        'total_sessions': None,
        'total_cost_usd': None,
        'avg_cost_per_session': None,
        'unique_users': None,
        'resolution_rate': None,
        'friction_score': None,
    }


# =============================================================================
# METRICAS EXISTENTES (REFATORADAS)
# =============================================================================

def _empty_insights(days: int) -> Dict[str, Any]:
    """Retorna estrutura vazia quando nao ha dados."""
    return {
        'period_days': days,
        'generated_at': agora_utc_naive().isoformat(),
        'overview': {
            'total_sessions': 0,
            'total_messages': 0,
            'total_cost_usd': 0.0,
            'avg_messages_per_session': 0.0,
            'avg_cost_per_session': 0.0,
            'unique_users': 0,
            'sessions_with_summary': 0,
        },
        'costs': {'weekly': [], 'by_user': []},
        'tools': {'by_category': [], 'by_domain': [], 'most_used': []},
        'users': {'most_active': []},
        'sessions': {'all': []},
        'daily': {
            'dates': [], 'session_counts': [], 'message_counts': [],
            'cost_values': [], 'resolution_rates': [],
        },
        'resolution_rate': 0.0,
        'resolved_sessions': 0,
        'cost_per_resolution': 0.0,
        'model_distribution': {},
        'topics': [],
        'adoption_rate': 0.0,
        'health_score': 0.0,
        'friction': {
            'friction_score': 0,
            'total_sessions_analyzed': 0,
            'repeated_queries': [],
            'abandoned_sessions': [],
            'frustration_signals': [],
            'no_tool_sessions': [],
            'summary': 'Sem dados.',
        },
        'recommendations': [],
        'deltas': _null_deltas(),
    }


def _calc_overview(sessions: List, days: int) -> Dict[str, Any]:
    """Calcula metricas gerais."""
    total_sessions = len(sessions)
    total_messages = sum(s.message_count or 0 for s in sessions)
    total_cost = sum(float(s.total_cost_usd or 0) for s in sessions)
    unique_users = len(set(s.user_id for s in sessions if s.user_id))
    sessions_with_summary = sum(1 for s in sessions if s.summary)

    return {
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'total_cost_usd': round(total_cost, 4),
        'avg_messages_per_session': round(total_messages / total_sessions, 1) if total_sessions else 0,
        'avg_cost_per_session': round(total_cost / total_sessions, 4) if total_sessions else 0,
        'unique_users': unique_users,
        'sessions_with_summary': sessions_with_summary,
    }


def _calc_costs(sessions: List, days: int) -> Dict[str, Any]:
    """Calcula custos por semana e por usuario."""
    from app.auth.models import Usuario

    # Custo semanal
    weekly = {}
    for s in sessions:
        if s.created_at:
            week_key = s.created_at.strftime('%Y-W%V')
            weekly[week_key] = weekly.get(week_key, 0.0) + float(s.total_cost_usd or 0)

    weekly_list = [
        {'week': k, 'cost_usd': round(v, 4)}
        for k, v in sorted(weekly.items())
    ]

    # Custo por usuario
    user_costs = {}
    for s in sessions:
        uid = s.user_id
        if uid:
            if uid not in user_costs:
                user_costs[uid] = {'user_id': uid, 'cost_usd': 0.0, 'sessions': 0}
            user_costs[uid]['cost_usd'] += float(s.total_cost_usd or 0)
            user_costs[uid]['sessions'] += 1

    user_ids = list(user_costs.keys())
    if user_ids:
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        user_names = {u.id: u.nome for u in users}
        for uid, data in user_costs.items():
            data['name'] = user_names.get(uid, f'Usuario #{uid}')
            data['cost_usd'] = round(data['cost_usd'], 4)

    by_user = sorted(user_costs.values(), key=lambda x: x['cost_usd'], reverse=True)[:10]

    return {
        'weekly': weekly_list,
        'by_user': by_user,
    }


def _calc_tools(sessions: List) -> Dict[str, Any]:
    """
    Calcula tools mais usadas com mapeamento para categorias de negocio.

    Retorna:
        by_category: agregado por categoria (nomes legiveis)
        by_domain: agregado por dominio (6 dominios)
        most_used: raw (backward compat)
    """
    from .tool_skill_mapper import aggregate_by_category, aggregate_by_domain

    tool_counts: Dict[str, int] = {}

    for s in sessions:
        messages = s.get_messages() if s.data else []
        for msg in messages:
            tools = msg.get('tools_used', [])
            for tool in tools:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

    by_category = aggregate_by_category(tool_counts)
    by_domain = aggregate_by_domain(tool_counts)

    # Raw para backward compat
    most_used = sorted(
        [{'tool': k, 'count': v} for k, v in tool_counts.items()],
        key=lambda x: x['count'],
        reverse=True,
    )[:15]

    return {
        'by_category': by_category,
        'by_domain': by_domain,
        'most_used': most_used,
    }


def _calc_users(sessions: List) -> Dict[str, Any]:
    """Calcula usuarios mais ativos."""
    from app.auth.models import Usuario

    user_activity = {}
    for s in sessions:
        uid = s.user_id
        if uid:
            if uid not in user_activity:
                user_activity[uid] = {
                    'user_id': uid,
                    'sessions': 0,
                    'messages': 0,
                    'cost_usd': 0.0,
                }
            user_activity[uid]['sessions'] += 1
            user_activity[uid]['messages'] += (s.message_count or 0)
            user_activity[uid]['cost_usd'] += float(s.total_cost_usd or 0)

    user_ids = list(user_activity.keys())
    if user_ids:
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        user_names = {u.id: u.nome for u in users}
        for uid, data in user_activity.items():
            data['name'] = user_names.get(uid, f'Usuario #{uid}')
            data['cost_usd'] = round(data['cost_usd'], 4)

    most_active = sorted(
        user_activity.values(),
        key=lambda x: x['sessions'],
        reverse=True,
    )[:10]

    return {
        'most_active': most_active,
    }


def _calc_sessions(sessions: List) -> Dict[str, Any]:
    """
    Monta lista unificada de sessoes com status computado.

    Status:
        resolved  - >= 4 msgs E usou tools
        abandoned - <= 3 msgs
        no_tools  - >= 5 msgs sem tools
        normal    - demais
    """
    from app.auth.models import Usuario

    # Buscar nomes dos usuarios
    user_ids = list(set(s.user_id for s in sessions if s.user_id))
    user_names = {}
    if user_ids:
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        user_names = {u.id: u.nome for u in users}

    all_sessions = []
    for s in sorted(sessions, key=lambda x: x.created_at or agora_utc_naive(), reverse=True)[:50]:
        msg_count = s.message_count or 0
        cost = round(float(s.total_cost_usd or 0), 4)
        has_tools = False
        has_summary = bool(s.summary)

        messages = s.get_messages() if s.data else []
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('tools_used'):
                has_tools = True
                break

        # Determinar status
        if msg_count >= 4 and has_tools:
            status = 'resolved'
        elif msg_count <= 3 and msg_count > 0:
            status = 'abandoned'
        elif msg_count >= 5 and not has_tools:
            status = 'no_tools'
        else:
            status = 'normal'

        # Extrair topicos do summary
        topics = []
        if has_summary and isinstance(s.summary, dict):
            topics = s.summary.get('topicos_abordados', [])[:3]

        all_sessions.append({
            'session_id': s.session_id,
            'title': s.title or '(sem titulo)',
            'user_name': user_names.get(s.user_id, f'Usuario #{s.user_id}') if s.user_id else 'N/A',
            'message_count': msg_count,
            'cost_usd': cost,
            'status': status,
            'has_summary': has_summary,
            'topics': topics,
            'model': s.model or 'N/A',
            'created_at': s.created_at.isoformat() if s.created_at else None,
        })

    return {
        'all': all_sessions,
    }


def _calc_daily(sessions: List, days: int) -> Dict[str, Any]:
    """Calcula dados diarios para grafico de linha, incluindo taxa de resolucao."""
    daily = {}

    for s in sessions:
        if s.created_at:
            day_key = s.created_at.strftime('%Y-%m-%d')
            if day_key not in daily:
                daily[day_key] = {
                    'sessions': 0, 'messages': 0, 'cost': 0.0,
                    'resolved': 0, 'total': 0,
                }
            daily[day_key]['sessions'] += 1
            daily[day_key]['messages'] += (s.message_count or 0)
            daily[day_key]['cost'] += float(s.total_cost_usd or 0)
            daily[day_key]['total'] += 1

            # Check se resolvida
            msg_count = s.message_count or 0
            if msg_count >= 4:
                messages = s.get_messages() if s.data else []
                for msg in messages:
                    if msg.get('role') == 'assistant' and msg.get('tools_used'):
                        daily[day_key]['resolved'] += 1
                        break

    # Preencher dias sem atividade
    start_date = agora_utc_naive() - timedelta(days=days)
    dates = []
    session_counts = []
    message_counts = []
    cost_values = []
    resolution_rates = []

    for i in range(days + 1):
        day = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        data = daily.get(day, {
            'sessions': 0, 'messages': 0, 'cost': 0.0,
            'resolved': 0, 'total': 0,
        })
        dates.append(day)
        session_counts.append(data['sessions'])
        message_counts.append(data['messages'])
        cost_values.append(round(data['cost'], 4))
        rate = round((data['resolved'] / data['total']) * 100, 1) if data['total'] > 0 else 0
        resolution_rates.append(rate)

    return {
        'dates': dates,
        'session_counts': session_counts,
        'message_counts': message_counts,
        'cost_values': cost_values,
        'resolution_rates': resolution_rates,
    }
