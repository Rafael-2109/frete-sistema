"""
Service de agregacoes para o Dashboard de Metricas de Subagents (A3).

Le exclusivamente da tabela `agent_invocation_metrics` (populada pelo
hook A1/A2 em `app/agente/sdk/hooks.py:_subagent_stop_hook`).

Padroes adotados:
- SQL via `text()` raw (queries agregadas — ORM ORM seria lento)
- Filtros uniformes via `_build_where_clause` (period, source, agent_types,
  user_ids) — DRY
- Todas as queries usam indices criados em
  scripts/migrations/2026_05_16_agent_invocation_metrics.sql
- Tempo de execucao alvo < 200ms ate ~1M rows
- Estado vazio (tabela sem dados) retorna estruturas vazias coerentes,
  nunca exceptions

Ref de uso: app/agente/routes/admin_metrics.py
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from app import db

logger = logging.getLogger('sistema_fretes')


# ---------------------------------------------------------------------------
# Filtros uniformes
# ---------------------------------------------------------------------------

PERIOD_HOURS = {
    '24h': 24,
    '7d': 24 * 7,
    '30d': 24 * 30,
}

VALID_SOURCES = {'production', 'dev', 'all'}


def _resolve_period_hours(period: str) -> int:
    """Converte period em horas. Default 7d se invalido."""
    return PERIOD_HOURS.get(period, PERIOD_HOURS['7d'])


def _build_where_clause(
    period: str = '7d',
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Constroi WHERE + params para queries agregadas.

    Retorna tuple (where_sql, params_dict). where_sql comeca com 'WHERE ...'.
    """
    hours = _resolve_period_hours(period)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    conds: List[str] = ['recorded_at >= :cutoff']
    params: Dict[str, Any] = {'cutoff': cutoff}

    if source in ('production', 'dev'):
        conds.append('source = :source')
        params['source'] = source

    if agent_types:
        clean = [a for a in agent_types if a]
        if clean:
            conds.append(
                'agent_type IN ('
                + ','.join(f':at_{i}' for i in range(len(clean)))
                + ')'
            )
            for i, at in enumerate(clean):
                params[f'at_{i}'] = at

    if user_ids:
        clean_ids = [int(u) for u in user_ids if u is not None]
        if clean_ids:
            conds.append(
                'user_id IN ('
                + ','.join(f':uid_{i}' for i in range(len(clean_ids)))
                + ')'
            )
            for i, uid in enumerate(clean_ids):
                params[f'uid_{i}'] = uid

    return 'WHERE ' + ' AND '.join(conds), params


# ---------------------------------------------------------------------------
# T1 — Overview (KPIs + stop reasons + top users)
# ---------------------------------------------------------------------------

def get_overview(
    period: str = '7d',
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """KPIs agregados + stop reason breakdown + top users.

    Retorno:
    {
        'kpis': {
            'total_invocations': N,
            'total_cost_usd': float,
            'avg_duration_ms': int,
            'p95_duration_ms': int,
            'error_rate_pct': float,  # stop_reason in ('error', 'max_turns')
            'total_tokens_in': N,
            'total_tokens_out': N,
            'total_cache_read': N,
            'total_cache_create': N,
            'distinct_users': N,
            'distinct_sessions': N,
        },
        'stop_reasons': [{'reason': str, 'count': N, 'pct': float}, ...],
        'top_users': [{'user_id': N, 'name': str, 'invocations': N,
                       'cost_usd': float}, ...]
    }
    """
    where, params = _build_where_clause(period, source, agent_types, user_ids)

    # KPIs principais — 1 query so com agregados
    kpis_sql = text(f"""
        SELECT
            COUNT(*)::bigint AS total_invocations,
            COALESCE(SUM(cost_usd), 0)::numeric AS total_cost_usd,
            COALESCE(AVG(duration_ms), 0)::bigint AS avg_duration_ms,
            COALESCE(
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms),
                0
            )::bigint AS p95_duration_ms,
            COUNT(*) FILTER (
                WHERE stop_reason IN ('error', 'max_turns')
            )::bigint AS errors,
            COALESCE(SUM(input_tokens), 0)::bigint AS total_tokens_in,
            COALESCE(SUM(output_tokens), 0)::bigint AS total_tokens_out,
            COALESCE(SUM(cache_read_tokens), 0)::bigint AS total_cache_read,
            COALESCE(SUM(cache_creation_tokens), 0)::bigint AS total_cache_create,
            COUNT(DISTINCT user_id)::bigint AS distinct_users,
            COUNT(DISTINCT session_id)::bigint AS distinct_sessions
        FROM agent_invocation_metrics
        {where}
    """)
    row = db.session.execute(kpis_sql, params).mappings().one()
    total = int(row['total_invocations']) or 0
    errors = int(row['errors'])
    kpis = {
        'total_invocations': total,
        'total_cost_usd': float(row['total_cost_usd'] or 0),
        'avg_duration_ms': int(row['avg_duration_ms'] or 0),
        'p95_duration_ms': int(row['p95_duration_ms'] or 0),
        'error_rate_pct': round((errors / total * 100) if total else 0.0, 2),
        'total_tokens_in': int(row['total_tokens_in'] or 0),
        'total_tokens_out': int(row['total_tokens_out'] or 0),
        'total_cache_read': int(row['total_cache_read'] or 0),
        'total_cache_create': int(row['total_cache_create'] or 0),
        'distinct_users': int(row['distinct_users'] or 0),
        'distinct_sessions': int(row['distinct_sessions'] or 0),
    }

    # Stop reasons breakdown
    sr_sql = text(f"""
        SELECT
            COALESCE(stop_reason, 'unknown') AS reason,
            COUNT(*)::bigint AS count
        FROM agent_invocation_metrics
        {where}
        GROUP BY 1
        ORDER BY count DESC
    """)
    sr_rows = db.session.execute(sr_sql, params).mappings().all()
    stop_reasons = [
        {
            'reason': r['reason'],
            'count': int(r['count']),
            'pct': round(int(r['count']) / total * 100, 2) if total else 0.0,
        }
        for r in sr_rows
    ]

    # Top users (JOIN com usuarios para nome).
    # Nota: colunas do WHERE (recorded_at, source, agent_type, user_id) existem
    # apenas na tabela agent_invocation_metrics — nao ha ambiguidade no JOIN,
    # entao usamos WHERE sem prefixar.
    tu_sql = text(f"""
        SELECT
            m.user_id,
            COALESCE(u.nome, 'user_' || m.user_id) AS name,
            COUNT(*)::bigint AS invocations,
            COALESCE(SUM(m.cost_usd), 0)::numeric AS cost_usd
        FROM agent_invocation_metrics m
        LEFT JOIN usuarios u ON u.id = m.user_id
        {where}
              AND m.user_id IS NOT NULL
        GROUP BY m.user_id, u.nome
        ORDER BY invocations DESC
        LIMIT 10
    """)
    tu_rows = db.session.execute(tu_sql, params).mappings().all()
    top_users = [
        {
            'user_id': int(r['user_id']),
            'name': r['name'] or f"user_{r['user_id']}",
            'invocations': int(r['invocations']),
            'cost_usd': float(r['cost_usd'] or 0),
        }
        for r in tu_rows
    ]

    return {
        'kpis': kpis,
        'stop_reasons': stop_reasons,
        'top_users': top_users,
    }


# ---------------------------------------------------------------------------
# T1+T2+T3 — Por agent_type (tabela enriquecida)
# ---------------------------------------------------------------------------

# Heuristica para flag de downgrade-candidate (T2):
# - Custo medio > $0.05 por invocacao E
# - num_turns medio < 5 (subagent simples) E
# - cache_hit_ratio > 0.6 (ja bem cacheavel)
# Se bate os 3: candidato a Opus->Sonnet (similar ao G5 do roadmap)

def get_by_agent_type(
    period: str = '7d',
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """Tabela enriquecida por agent_type.

    Retorno: lista ordenada por invocations DESC com:
    - count, avg/p50/p95 duration_ms
    - avg num_turns
    - sum cost_usd, avg cost_usd
    - sum tokens (in/out/cache), cache_hit_ratio
    - error_count, error_rate_pct
    - downgrade_candidate (bool) — flag T2
    """
    where, params = _build_where_clause(period, source, agent_types, user_ids)

    sql = text(f"""
        SELECT
            agent_type,
            COUNT(*)::bigint AS invocations,
            COALESCE(AVG(duration_ms), 0)::bigint AS avg_duration_ms,
            COALESCE(
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms), 0
            )::bigint AS p50_duration_ms,
            COALESCE(
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 0
            )::bigint AS p95_duration_ms,
            COALESCE(AVG(num_turns), 0)::numeric(10,2) AS avg_num_turns,
            COALESCE(SUM(cost_usd), 0)::numeric AS sum_cost_usd,
            COALESCE(AVG(cost_usd), 0)::numeric(12,6) AS avg_cost_usd,
            COALESCE(SUM(input_tokens), 0)::bigint AS sum_input_tokens,
            COALESCE(SUM(output_tokens), 0)::bigint AS sum_output_tokens,
            COALESCE(SUM(cache_read_tokens), 0)::bigint AS sum_cache_read,
            COALESCE(SUM(cache_creation_tokens), 0)::bigint AS sum_cache_create,
            COUNT(*) FILTER (
                WHERE stop_reason IN ('error', 'max_turns')
            )::bigint AS errors,
            MAX(recorded_at) AS last_seen
        FROM agent_invocation_metrics
        {where}
        GROUP BY agent_type
        ORDER BY invocations DESC
    """)
    rows = db.session.execute(sql, params).mappings().all()

    result: List[Dict[str, Any]] = []
    for r in rows:
        invocations = int(r['invocations'])
        errors = int(r['errors'])
        input_t = int(r['sum_input_tokens'])
        cache_read = int(r['sum_cache_read'])
        total_read_in = input_t + cache_read

        cache_hit_ratio = (
            round(cache_read / total_read_in, 4) if total_read_in > 0 else 0.0
        )
        avg_cost = float(r['avg_cost_usd'] or 0)
        avg_turns = float(r['avg_num_turns'] or 0)
        # Downgrade candidate (T2): custo alto + turns baixos + cache OK
        downgrade_candidate = (
            avg_cost > 0.05
            and avg_turns < 5.0
            and cache_hit_ratio > 0.6
            and invocations >= 5  # amostra minima
        )

        result.append({
            'agent_type': r['agent_type'],
            'invocations': invocations,
            'avg_duration_ms': int(r['avg_duration_ms']),
            'p50_duration_ms': int(r['p50_duration_ms']),
            'p95_duration_ms': int(r['p95_duration_ms']),
            'avg_num_turns': avg_turns,
            'sum_cost_usd': float(r['sum_cost_usd'] or 0),
            'avg_cost_usd': avg_cost,
            'sum_input_tokens': input_t,
            'sum_output_tokens': int(r['sum_output_tokens']),
            'sum_cache_read': cache_read,
            'sum_cache_create': int(r['sum_cache_create']),
            'cache_hit_ratio': cache_hit_ratio,
            'errors': errors,
            'error_rate_pct': round(errors / invocations * 100, 2) if invocations else 0.0,
            'last_seen': r['last_seen'].isoformat() if r['last_seen'] else None,
            'downgrade_candidate': downgrade_candidate,
        })

    return result


# ---------------------------------------------------------------------------
# T1 — Time series (invocacoes por dia, stacked por agent_type)
# ---------------------------------------------------------------------------

def get_timeseries(
    period: str = '30d',
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Time series diaria de invocacoes, agrupada por agent_type.

    Retorno:
    {
        'labels': ['2026-04-16', ...],  # dias
        'series': [{'agent_type': str, 'data': [N, N, ...]}, ...]
    }
    """
    where, params = _build_where_clause(period, source, agent_types, user_ids)

    sql = text(f"""
        SELECT
            to_char(date_trunc('day', recorded_at), 'YYYY-MM-DD') AS day,
            agent_type,
            COUNT(*)::bigint AS count
        FROM agent_invocation_metrics
        {where}
        GROUP BY 1, agent_type
        ORDER BY 1
    """)
    rows = db.session.execute(sql, params).mappings().all()

    # Pivot: linhas (day, agent_type, count) -> dict per agent
    days_set = sorted({r['day'] for r in rows})
    agents_set = sorted({r['agent_type'] for r in rows})

    matrix: Dict[str, Dict[str, int]] = {a: {d: 0 for d in days_set} for a in agents_set}
    for r in rows:
        matrix[r['agent_type']][r['day']] = int(r['count'])

    series = [
        {
            'agent_type': agent_type,
            'data': [matrix[agent_type][day] for day in days_set],
        }
        for agent_type in agents_set
    ]

    return {'labels': days_set, 'series': series}


# ---------------------------------------------------------------------------
# T2 — Anomalies (P95 x 2 outliers last 24h)
# ---------------------------------------------------------------------------

def get_anomalies(
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """Invocacoes com duration > P95(7d) * 2 nas ultimas 24h.

    Sinal precoce de regressao por agent — Anthropic doc Stage 4 LLMOps #1
    (Robust monitoring and observability).
    """
    # Baseline: P95 dos 7 dias anteriores por agent_type
    baseline_where, baseline_params = _build_where_clause(
        '7d', source, agent_types, user_ids
    )
    baseline_sql = text(f"""
        SELECT
            agent_type,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95
        FROM agent_invocation_metrics
        {baseline_where}
          AND duration_ms IS NOT NULL
        GROUP BY agent_type
        HAVING COUNT(*) >= 5
    """)
    baseline = {
        r['agent_type']: float(r['p95'] or 0)
        for r in db.session.execute(baseline_sql, baseline_params).mappings().all()
    }

    if not baseline:
        return []

    # Anomalias: duration > 2 * baseline
    recent_where, recent_params = _build_where_clause(
        '24h', source, agent_types, user_ids
    )
    # Anexar filtro de baseline per agent
    in_clause = ','.join(f':a_{i}' for i in range(len(baseline)))
    or_clauses = ' OR '.join(
        f"(agent_type = :a_{i} AND duration_ms > :p_{i})"
        for i in range(len(baseline))
    )
    extra_params: Dict[str, Any] = {}
    for i, (agent, p95) in enumerate(baseline.items()):
        extra_params[f'a_{i}'] = agent
        extra_params[f'p_{i}'] = int(p95 * 2)

    recent_params.update(extra_params)

    anomaly_sql = text(f"""
        SELECT
            agent_id, agent_type, session_id, user_id,
            duration_ms, num_turns, stop_reason, cost_usd,
            recorded_at
        FROM agent_invocation_metrics
        {recent_where}
          AND duration_ms IS NOT NULL
          AND agent_type IN ({in_clause})
          AND ({or_clauses})
        ORDER BY duration_ms DESC
        LIMIT 50
    """)
    rows = db.session.execute(anomaly_sql, recent_params).mappings().all()

    result = []
    for r in rows:
        agent = r['agent_type']
        p95 = baseline.get(agent, 0)
        result.append({
            'agent_id': r['agent_id'],
            'agent_type': agent,
            'session_id': r['session_id'],
            'user_id': r['user_id'],
            'duration_ms': int(r['duration_ms']),
            'baseline_p95_ms': int(p95),
            'multiplier': round(r['duration_ms'] / p95, 2) if p95 else 0,
            'num_turns': r['num_turns'],
            'stop_reason': r['stop_reason'],
            'cost_usd': float(r['cost_usd'] or 0),
            'recorded_at': r['recorded_at'].isoformat() if r['recorded_at'] else None,
        })
    return result


# ---------------------------------------------------------------------------
# T3 — Co-occurrence matrix (agents invocados na mesma session_id)
# ---------------------------------------------------------------------------

def get_cooccurrence(
    period: str = '7d',
    source: str = 'all',
) -> Dict[str, Any]:
    """Matriz de co-ocorrencia: para cada par (A, B), quantas sessoes
    invocaram AMBOS A e B.

    Retorno:
    {
        'agent_types': [str, ...],  # eixos
        'matrix': [[int, int, ...], ...],  # qtd sessoes onde ambos presentes
    }
    """
    where, params = _build_where_clause(period, source)

    sql = text(f"""
        WITH session_agents AS (
            SELECT DISTINCT session_id, agent_type
            FROM agent_invocation_metrics
            {where}
              AND session_id IS NOT NULL
        )
        SELECT
            sa1.agent_type AS agent_a,
            sa2.agent_type AS agent_b,
            COUNT(DISTINCT sa1.session_id)::bigint AS cnt
        FROM session_agents sa1
        JOIN session_agents sa2 ON sa1.session_id = sa2.session_id
        GROUP BY sa1.agent_type, sa2.agent_type
    """)
    rows = db.session.execute(sql, params).mappings().all()

    agents = sorted({r['agent_a'] for r in rows} | {r['agent_b'] for r in rows})
    idx = {a: i for i, a in enumerate(agents)}
    matrix = [[0] * len(agents) for _ in agents]

    for r in rows:
        i = idx[r['agent_a']]
        j = idx[r['agent_b']]
        matrix[i][j] = int(r['cnt'])

    return {'agent_types': agents, 'matrix': matrix}


# ---------------------------------------------------------------------------
# T3 — Hourly heatmap (capacity planning)
# ---------------------------------------------------------------------------

def get_hourly_heatmap(
    period: str = '30d',
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Heatmap dia da semana (0-6) x hora do dia (0-23).

    Retorno:
    {
        'matrix': [[N, ...23], ...7],  # [dow][hour] = invocations
        'max_value': N
    }
    """
    where, params = _build_where_clause(period, source, agent_types, user_ids)

    sql = text(f"""
        SELECT
            EXTRACT(DOW FROM recorded_at)::int AS dow,
            EXTRACT(HOUR FROM recorded_at)::int AS hour,
            COUNT(*)::bigint AS cnt
        FROM agent_invocation_metrics
        {where}
        GROUP BY 1, 2
    """)
    rows = db.session.execute(sql, params).mappings().all()

    matrix = [[0] * 24 for _ in range(7)]
    max_value = 0
    for r in rows:
        dow = int(r['dow'])
        hour = int(r['hour'])
        cnt = int(r['cnt'])
        matrix[dow][hour] = cnt
        if cnt > max_value:
            max_value = cnt

    return {'matrix': matrix, 'max_value': max_value}


# ---------------------------------------------------------------------------
# T3 — Sparkline per agent (30d daily count)
# ---------------------------------------------------------------------------

def get_sparklines(
    period: str = '30d',
    source: str = 'all',
    agent_types: Optional[List[str]] = None,
    user_ids: Optional[List[int]] = None,
) -> Dict[str, List[int]]:
    """Sparkline: para cada agent_type, lista de counts diarios.

    Retorno: {agent_type: [N, N, ...]}  # ordem cronologica
    """
    ts = get_timeseries(period, source, agent_types, user_ids)
    return {s['agent_type']: s['data'] for s in ts['series']}


# ---------------------------------------------------------------------------
# T3 — Drilldown (last N invocations of an agent)
# ---------------------------------------------------------------------------

def get_drilldown(
    agent_type: str,
    period: str = '7d',
    source: str = 'all',
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Ultimas N invocacoes de um agent — para investigacao detalhada."""
    where, params = _build_where_clause(period, source, [agent_type], None)
    params['lim'] = max(1, min(int(limit), 100))

    sql = text(f"""
        SELECT
            agent_id, agent_type, session_id, user_id,
            started_at, finished_at, duration_ms, num_turns,
            stop_reason, cost_usd,
            input_tokens, output_tokens,
            cache_read_tokens, cache_creation_tokens,
            source, recorded_at
        FROM agent_invocation_metrics
        {where}
        ORDER BY recorded_at DESC
        LIMIT :lim
    """)
    rows = db.session.execute(sql, params).mappings().all()

    return [
        {
            'agent_id': r['agent_id'],
            'agent_type': r['agent_type'],
            'session_id': r['session_id'],
            'user_id': r['user_id'],
            'started_at': r['started_at'].isoformat() if r['started_at'] else None,
            'finished_at': r['finished_at'].isoformat() if r['finished_at'] else None,
            'duration_ms': r['duration_ms'],
            'num_turns': r['num_turns'],
            'stop_reason': r['stop_reason'],
            'cost_usd': float(r['cost_usd'] or 0),
            'input_tokens': int(r['input_tokens'] or 0),
            'output_tokens': int(r['output_tokens'] or 0),
            'cache_read_tokens': int(r['cache_read_tokens'] or 0),
            'cache_creation_tokens': int(r['cache_creation_tokens'] or 0),
            'source': r['source'],
            'recorded_at': r['recorded_at'].isoformat() if r['recorded_at'] else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Util: lista de agent_types e users disponiveis (para popular filtros)
# ---------------------------------------------------------------------------

def get_filter_options(period: str = '30d') -> Dict[str, Any]:
    """Retorna agent_types e users que tem invocacao no periodo (popula UI)."""
    where, params = _build_where_clause(period, 'all')

    at_sql = text(f"""
        SELECT DISTINCT agent_type
        FROM agent_invocation_metrics
        {where}
        ORDER BY agent_type
    """)
    agent_types = [r['agent_type'] for r in db.session.execute(at_sql, params).mappings().all()]

    u_sql = text(f"""
        SELECT
            m.user_id,
            COALESCE(u.nome, 'user_' || m.user_id) AS name,
            COUNT(*)::bigint AS invocations
        FROM agent_invocation_metrics m
        LEFT JOIN usuarios u ON u.id = m.user_id
        {where}
          AND m.user_id IS NOT NULL
        GROUP BY m.user_id, u.nome
        ORDER BY invocations DESC
        LIMIT 50
    """)
    users = [
        {
            'user_id': int(r['user_id']),
            'name': r['name'],
            'invocations': int(r['invocations']),
        }
        for r in db.session.execute(u_sql, params).mappings().all()
    ]

    return {'agent_types': agent_types, 'users': users}


# ---------------------------------------------------------------------------
# Util: total de linhas (para detectar estado vazio)
# ---------------------------------------------------------------------------

def get_table_status() -> Dict[str, Any]:
    """Status da tabela — usado para mostrar estado vazio na UI."""
    try:
        total = db.session.execute(
            text("SELECT COUNT(*)::bigint AS n FROM agent_invocation_metrics")
        ).scalar()
        most_recent = db.session.execute(
            text(
                "SELECT MAX(recorded_at) AS last "
                "FROM agent_invocation_metrics"
            )
        ).scalar()
        return {
            'total_rows': int(total or 0),
            'last_recorded_at': most_recent.isoformat() if most_recent else None,
            'table_exists': True,
        }
    except Exception as e:
        logger.warning(f"[metrics_dashboard] get_table_status falhou: {e}")
        return {'total_rows': 0, 'last_recorded_at': None, 'table_exists': False}
