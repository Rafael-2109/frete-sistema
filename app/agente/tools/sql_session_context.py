"""SQL Session Context (T4): memoria curta de DMLs aprovados na sessao admin.

Motivacao: o evaluator Haiku e stateless — INSERT aprovado as 14:30, UPDATE as
14:31 sao tratados independentemente. Isso causou IMP-2026-05-13-004 (UPDATE
bloqueado mesmo com INSERT aprovado segundos antes na mesma sessao).

Solucao: apos DML aprovado + executado em modo admin, gravar no Redis com TTL
600s. Antes de chamar Haiku evaluator, ler contexto e injetar no prompt para
o LLM aplicar criterio uniforme entre verbos DML.

Best-effort: se Redis indisponivel, no-op (degrada para comportamento atual).
Feature flag: TEXT_TO_SQL_SESSION_CONTEXT=false → desativa.

API publica:
    record_dml_approved(session_id, dml_type, table) -> bool
    get_recent_dml_context(session_id) -> dict | None
"""
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Chave Redis: agent:sql_dml:{session_id}
KEY_PREFIX = "agent:sql_dml:"
TTL_SECONDS = 600  # 10 min — janela tipica de uma operacao multi-step admin
DML_VERBS = {"INSERT", "UPDATE", "DELETE"}


def _is_enabled() -> bool:
    return os.getenv("TEXT_TO_SQL_SESSION_CONTEXT", "true").lower() == "true"


def _get_redis_client():
    """Retorna client Redis ou None se indisponivel.

    Usa o singleton redis_cache.client (mesmo padrao de pending_questions.py
    e artifact_service.py).
    """
    try:
        from app.utils.redis_cache import redis_cache  # pyright: ignore[reportMissingImports]
        if not redis_cache.disponivel:
            return None
        return redis_cache.client
    except Exception:
        return None


def record_dml_approved(session_id: Optional[str], dml_type: str, table: str) -> bool:
    """Registra que um DML foi aprovado + executado nesta sessao.

    Args:
        session_id: UUID da sessao do agente (ContextVar). Se None, no-op.
        dml_type: 'INSERT', 'UPDATE' ou 'DELETE'.
        table: nome da tabela alvo.

    Returns:
        True se registrou, False caso contrario (Redis off, flag off, etc.).
    """
    if not session_id or not _is_enabled():
        return False
    if not dml_type or dml_type.upper() not in DML_VERBS:
        return False

    client = _get_redis_client()
    if client is None:
        return False

    key = f"{KEY_PREFIX}{session_id}"
    payload = {
        "last_dml_type": dml_type.upper(),
        "last_table": (table or "").lower(),
        "ts": time.time(),
    }
    try:
        client.setex(key, TTL_SECONDS, json.dumps(payload))
        logger.info(
            f"[SQL_SESSION_CTX] Gravado {dml_type} em '{table}' "
            f"para session={session_id[:8]}... (TTL {TTL_SECONDS}s)"
        )
        return True
    except Exception as e:
        logger.warning(f"[SQL_SESSION_CTX] Falha ao gravar: {e}")
        return False


def get_recent_dml_context(session_id: Optional[str]) -> Optional[dict]:
    """Recupera contexto DML recente da sessao.

    Args:
        session_id: UUID da sessao do agente.

    Returns:
        Dict com {last_dml_type, last_table, ts, age_seconds} ou None se ausente.
    """
    if not session_id or not _is_enabled():
        return None

    client = _get_redis_client()
    if client is None:
        return None

    key = f"{KEY_PREFIX}{session_id}"
    try:
        raw = client.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        data["age_seconds"] = int(time.time() - data.get("ts", 0))
        return data
    except Exception as e:
        logger.debug(f"[SQL_SESSION_CTX] Falha ao ler: {e}")
        return None


def clear_session_context(session_id: Optional[str]) -> bool:
    """Limpa contexto da sessao (admin tool, rollback de operacao).

    Returns: True se deletou, False caso contrario.
    """
    if not session_id:
        return False
    client = _get_redis_client()
    if client is None:
        return False
    try:
        client.delete(f"{KEY_PREFIX}{session_id}")
        return True
    except Exception:
        return False
