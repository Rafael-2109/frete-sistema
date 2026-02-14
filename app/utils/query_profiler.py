"""
Query Profiler — Detecta N+1 e conta queries por request.

Ativado via env var ENABLE_QUERY_PROFILING=true (default: false).
Custo quando desligado: 1 check booleano por query (overhead ~zero).

Output nos logs:
  GET /carteira/listar | Queries: 47 | DB time: 1.234s | Total: 2.100s
  N+1 SUSPECT: /carteira/listar | 47 queries | Repeated: {'SELECT separacao WHERE id = ?': 42}
"""

import re
import time

from flask import g, has_request_context
from sqlalchemy import event
from sqlalchemy.engine import Engine


# Threshold para considerar N+1 (mesma query normalizada repetida N+ vezes)
N_PLUS_ONE_THRESHOLD = 10

# Regex para normalizar queries (remove valores de parametros)
_PARAM_RE = re.compile(r"(%\([\w]+\)s|\$\d+|%s|\?)")
_WHITESPACE_RE = re.compile(r"\s+")
_IN_VALUES_RE = re.compile(r"IN\s*\([^)]+\)", re.IGNORECASE)

def _normalize_query(statement: str) -> str:
    """Normaliza query para agrupar similares (remove parametros e whitespace)."""
    normalized = _PARAM_RE.sub("?", statement)
    normalized = _IN_VALUES_RE.sub("IN (?)", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    # Trunca para evitar keys gigantes
    return normalized[:200]


@event.listens_for(Engine, "before_cursor_execute")
def _before_cursor_execute(_conn, _cursor, _statement, _parameters, context, _executemany):
    """Event listener: marca inicio da execucao."""
    if not has_request_context():
        return
    if not hasattr(g, "_query_profiler"):
        return
    context._query_start_time = time.monotonic()


@event.listens_for(Engine, "after_cursor_execute")
def _after_cursor_execute(_conn, _cursor, statement, _parameters, context, _executemany):
    """Event listener: registra query executada."""
    if not has_request_context():
        return
    if not hasattr(g, "_query_profiler"):
        return

    elapsed = time.monotonic() - getattr(context, "_query_start_time", time.monotonic())

    profiler = g._query_profiler
    profiler["count"] += 1
    profiler["db_time"] += elapsed

    normalized = _normalize_query(statement)
    profiler["queries"][normalized] = profiler["queries"].get(normalized, 0) + 1


def init_query_profiling(app):
    """Inicializa o query profiler.

    Listeners sao registrados via decorator no modulo (class-level, nao instance-level).
    Custo quando ENABLE_QUERY_PROFILING=false: 2 checks booleanos por query
    (has_request_context + hasattr).
    """
    if app.config.get("ENABLE_QUERY_PROFILING"):
        app.logger.info("Query Profiler ATIVO — monitorando queries por request")
    else:
        app.logger.info("Query Profiler desativado (ENABLE_QUERY_PROFILING=false)")


def start_profiling():
    """Inicia profiling para o request atual (chamado em before_request)."""
    g._query_profiler = {
        "count": 0,
        "db_time": 0.0,
        "queries": {},  # normalized_query -> count
    }


def get_profiling_summary() -> dict | None:
    """Retorna resumo do profiling do request atual.

    Returns:
        dict com count, db_time, n_plus_one (queries repetidas acima do threshold)
        ou None se profiling nao esta ativo.
    """
    if not hasattr(g, "_query_profiler"):
        return None

    profiler = g._query_profiler
    n_plus_one = {
        q: count for q, count in profiler["queries"].items() if count >= N_PLUS_ONE_THRESHOLD
    }

    return {
        "count": profiler["count"],
        "db_time": profiler["db_time"],
        "n_plus_one": n_plus_one,
    }
