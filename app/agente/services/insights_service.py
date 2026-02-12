"""
P2-2: Dashboard de Insights do Agente.

Gera métricas analíticas sobre uso do agente: sessões, custos, tools, erros.
Acesso restrito a administradores.

Queries sobre AgentSession:
- Total de sessões e mensagens por período
- Custo por usuário/semana
- Tools/skills mais usadas
- Duração média de sessão
- Top queries por categoria
- Erros identificados

Uso:
    Chamado pelas rotas /agente/insights e /agente/api/insights/data.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from app.utils.timezone import agora_utc_naive
logger = logging.getLogger(__name__)


def get_insights_data(
    days: int = 30,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Gera dados completos de insights do agente.

    Args:
        days: Período de análise em dias (default 30)
        user_id: Filtrar por usuário específico (None = todos)

    Returns:
        Dict com seções: overview, costs, tools, sessions, users
    """
    try:
        from ..models import AgentSession
        since = agora_utc_naive() - timedelta(days=days)

        # Query base
        base_query = AgentSession.query.filter(
            AgentSession.created_at >= since
        )
        if user_id:
            base_query = base_query.filter(AgentSession.user_id == user_id)

        sessions = base_query.all()

        if not sessions:
            return _empty_insights(days)

        # Gera cada seção
        overview = _calc_overview(sessions, days)
        cost_data = _calc_costs(sessions, days)
        tool_data = _calc_tools(sessions)
        user_data = _calc_users(sessions)
        session_data = _calc_sessions(sessions)
        daily_data = _calc_daily(sessions, days)

        return {
            'period_days': days,
            'generated_at': agora_utc_naive().isoformat(),
            'overview': overview,
            'costs': cost_data,
            'tools': tool_data,
            'users': user_data,
            'sessions': session_data,
            'daily': daily_data,
        }

    except Exception as e:
        logger.error(f"[INSIGHTS] Erro ao gerar insights: {e}")
        return _empty_insights(days)


def _empty_insights(days: int) -> Dict[str, Any]:
    """Retorna estrutura vazia quando não há dados."""
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
        'tools': {'most_used': [], 'by_session': []},
        'users': {'most_active': [], 'by_cost': []},
        'sessions': {'longest': [], 'most_expensive': [], 'recent': []},
        'daily': {'dates': [], 'session_counts': [], 'message_counts': [], 'cost_values': []},
    }


def _calc_overview(sessions: List, days: int) -> Dict[str, Any]:
    """Calcula métricas gerais."""
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
    """Calcula custos por semana e por usuário."""
    from app.auth.models import Usuario

    # Custo semanal
    weekly = {}
    for s in sessions:
        if s.created_at:
            # Semana ISO (YYYY-WNN)
            week_key = s.created_at.strftime('%Y-W%V')
            weekly[week_key] = weekly.get(week_key, 0.0) + float(s.total_cost_usd or 0)

    weekly_list = [
        {'week': k, 'cost_usd': round(v, 4)}
        for k, v in sorted(weekly.items())
    ]

    # Custo por usuário
    user_costs = {}
    for s in sessions:
        uid = s.user_id
        if uid:
            if uid not in user_costs:
                user_costs[uid] = {'user_id': uid, 'cost_usd': 0.0, 'sessions': 0}
            user_costs[uid]['cost_usd'] += float(s.total_cost_usd or 0)
            user_costs[uid]['sessions'] += 1

    # Enriquecer com nomes de usuários
    user_ids = list(user_costs.keys())
    if user_ids:
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        user_names = {u.id: u.nome for u in users}
        for uid, data in user_costs.items():
            data['name'] = user_names.get(uid, f'Usuário #{uid}')
            data['cost_usd'] = round(data['cost_usd'], 4)

    by_user = sorted(user_costs.values(), key=lambda x: x['cost_usd'], reverse=True)[:10]

    return {
        'weekly': weekly_list,
        'by_user': by_user,
    }


def _calc_tools(sessions: List) -> Dict[str, Any]:
    """Calcula tools mais usadas."""
    tool_counts = {}

    for s in sessions:
        messages = s.get_messages() if s.data else []
        for msg in messages:
            tools = msg.get('tools_used', [])
            for tool in tools:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

    most_used = sorted(
        [{'tool': k, 'count': v} for k, v in tool_counts.items()],
        key=lambda x: x['count'],
        reverse=True,
    )[:15]

    return {
        'most_used': most_used,
    }


def _calc_users(sessions: List) -> Dict[str, Any]:
    """Calcula usuários mais ativos."""
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

    # Enriquecer com nomes
    user_ids = list(user_activity.keys())
    if user_ids:
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        user_names = {u.id: u.nome for u in users}
        for uid, data in user_activity.items():
            data['name'] = user_names.get(uid, f'Usuário #{uid}')
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
    """Calcula sessões mais longas, caras e recentes."""
    # Mais longas (por mensagens)
    longest = sorted(sessions, key=lambda s: s.message_count or 0, reverse=True)[:5]
    longest_list = [
        {
            'session_id': s.session_id,
            'title': s.title or '(sem título)',
            'message_count': s.message_count or 0,
            'cost_usd': round(float(s.total_cost_usd or 0), 4),
            'created_at': s.created_at.isoformat() if s.created_at else None,
        }
        for s in longest
    ]

    # Mais caras
    most_expensive = sorted(sessions, key=lambda s: float(s.total_cost_usd or 0), reverse=True)[:5]
    expensive_list = [
        {
            'session_id': s.session_id,
            'title': s.title or '(sem título)',
            'message_count': s.message_count or 0,
            'cost_usd': round(float(s.total_cost_usd or 0), 4),
            'created_at': s.created_at.isoformat() if s.created_at else None,
        }
        for s in most_expensive
    ]

    # Mais recentes
    recent = sorted(sessions, key=lambda s: s.created_at or datetime.min, reverse=True)[:10]
    recent_list = [
        {
            'session_id': s.session_id,
            'title': s.title or '(sem título)',
            'message_count': s.message_count or 0,
            'cost_usd': round(float(s.total_cost_usd or 0), 4),
            'created_at': s.created_at.isoformat() if s.created_at else None,
            'has_summary': bool(s.summary),
        }
        for s in recent
    ]

    return {
        'longest': longest_list,
        'most_expensive': expensive_list,
        'recent': recent_list,
    }


def _calc_daily(sessions: List, days: int) -> Dict[str, Any]:
    """Calcula dados diários para gráfico de linha."""
    daily = {}

    for s in sessions:
        if s.created_at:
            day_key = s.created_at.strftime('%Y-%m-%d')
            if day_key not in daily:
                daily[day_key] = {'sessions': 0, 'messages': 0, 'cost': 0.0}
            daily[day_key]['sessions'] += 1
            daily[day_key]['messages'] += (s.message_count or 0)
            daily[day_key]['cost'] += float(s.total_cost_usd or 0)

    # Preencher dias sem atividade
    start_date = agora_utc_naive() - timedelta(days=days)
    dates = []
    session_counts = []
    message_counts = []
    cost_values = []

    for i in range(days + 1):
        day = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        data = daily.get(day, {'sessions': 0, 'messages': 0, 'cost': 0.0})
        dates.append(day)
        session_counts.append(data['sessions'])
        message_counts.append(data['messages'])
        cost_values.append(round(data['cost'], 4))

    return {
        'dates': dates,
        'session_counts': session_counts,
        'message_counts': message_counts,
        'cost_values': cost_values,
    }
