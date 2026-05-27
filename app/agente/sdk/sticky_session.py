"""
Sticky session via Redis — força requests da mesma sessão para o mesmo worker.

Mitiga Anthropic Issue #61862 (Vj3 over-fires interrupted_turn). O bug:
quando o subprocess CLI Anthropic é recriado para uma sessão existente
(materialize_resume_session), ele inspeciona o JSONL e dispara
interrupted_turn em vários casos benignos (hook_success attachment como
leaf, tool_result de subagent paralelo tardio, hook_additional_context).
O resultado é injeção de "Continue from where you left off" que cria
branch paralela na chain de parentUuid, fazendo o modelo "esquecer"
turnos intermediários.

Cenário que amplifica em PROD:
4 workers Gunicorn sem session affinity → requests da mesma sessão
caem em workers diferentes → cada novo worker recria o subprocess CLI
→ materialize_resume_session → Vj3 over-fires → contexto quebrado.

Solução: registry em Redis com ownership por session_id. Quando uma
request HTTP chega num worker que NÃO é o dono atual, retorna 409 com
header X-Session-Owner-Hint. Frontend retry com backoff. Eventualmente
acerta no worker dono e reusa o subprocess CLI vivo.

Trade-offs aceitos:
- Latência extra em pico (até ~1.2s worst case com 4 workers + 6 retries).
- Worker que cresha sem cleanup deixa ownership "stuck" até TTL expirar.
- Em rolling deploy, sessões podem ficar ~30s sem dono até o owner novo
  reivindicar.

Rollback: AGENT_STICKY_SESSION_ENABLED=false desabilita (fail-open).

Ref:
- https://github.com/anthropics/claude-code/issues/61862
- docs/agente/STICKY_SESSION_FIX.md
"""

import logging
import os
import socket
from typing import Optional

logger = logging.getLogger(__name__)

# Worker identifier — calculado uma vez por processo
_worker_id_cache: Optional[str] = None


def get_worker_id() -> str:
    """Identificador único do worker = pid@hostname.

    Cacheado por processo. Em Render, hostname é o container ID.
    """
    global _worker_id_cache
    if _worker_id_cache is None:
        _worker_id_cache = f"{os.getpid()}@{socket.gethostname()}"
    return _worker_id_cache


def _get_redis_client():
    """Lazy import do RedisCache.client compartilhado. None se Redis off."""
    try:
        from app.utils.redis_cache import redis_cache
        if not redis_cache.disponivel:
            return None
        return redis_cache.client
    except Exception as e:
        logger.debug(f"[STICKY] Redis import falhou: {e}")
        return None


def _ownership_key(session_id: str) -> str:
    """Chave Redis para ownership da sessão."""
    return f"agent:session:owner:{session_id}"


def _is_enabled() -> bool:
    """Lazy check da flag (lida fresh do env para suportar toggle sem reboot)."""
    return os.getenv("AGENT_STICKY_SESSION_ENABLED", "false").lower() == "true"


def _ttl_seconds() -> int:
    """TTL do ownership em segundos. Default 30min."""
    try:
        return int(os.getenv("STICKY_SESSION_TTL_SEC", "1800"))
    except (ValueError, TypeError):
        return 1800


def claim_ownership(session_id: str) -> bool:
    """Reivindica ownership da sessão para este worker.

    Returns:
        True  → sou o dono (acabei de reivindicar OU já era meu).
        False → outro worker é o dono ativo. Caller deve retornar 409.

    Fail-open: se Redis estiver indisponível ou flag desligada, retorna
    True (comportamento atual, sem sticky).
    """
    if not _is_enabled():
        return True

    if not session_id:
        return True  # sem session_id, sem affinity

    rc = _get_redis_client()
    if rc is None:
        return True  # fail-open

    key = _ownership_key(session_id)
    me = get_worker_id()
    ttl = _ttl_seconds()

    try:
        # SET NX EX: atômico. Seta APENAS se key não existe.
        # Retorna True se setou, False/None se já existia.
        result = rc.set(key, me, nx=True, ex=ttl)
        if result:
            logger.info(
                f"[STICKY] Claimed: session={session_id[:8]}... worker={me} ttl={ttl}s"
            )
            return True

        # Já tem dono. Ver se sou eu mesmo.
        current = rc.get(key)
        if current is None:
            # Edge: expirou entre o SET NX e o GET. Reivindicar de novo.
            rc.set(key, me, ex=ttl)
            return True

        # decode_responses=True no nosso redis_cache, mas guard para bytes
        current_str = current if isinstance(current, str) else current.decode("utf-8")

        if current_str == me:
            # Sou eu — renovar TTL (heartbeat implícito por request).
            rc.expire(key, ttl)
            return True

        # Outro worker é o dono.
        logger.info(
            f"[STICKY] Owned by other: session={session_id[:8]}... "
            f"owner={current_str} me={me}"
        )
        return False
    except Exception as e:
        logger.warning(f"[STICKY] claim_ownership erro (fail-open): {e}")
        return True  # fail-open em qualquer erro


def get_owner(session_id: str) -> Optional[str]:
    """Retorna worker_id do dono atual, ou None se vazio/erro."""
    if not _is_enabled() or not session_id:
        return None

    rc = _get_redis_client()
    if rc is None:
        return None

    try:
        owner = rc.get(_ownership_key(session_id))
        if owner is None:
            return None
        return owner if isinstance(owner, str) else owner.decode("utf-8")
    except Exception:
        return None


def is_owned_by_me(session_id: str) -> bool:
    """True se sou o dono OU não há dono. False se outro worker tem ownership."""
    owner = get_owner(session_id)
    if owner is None:
        return True
    return owner == get_worker_id()


def release_ownership(session_id: str) -> None:
    """Libera ownership (chamado em disconnect_client ou atexit).

    Só deleta a chave se o dono atual SOU EU — evita race em rolling deploy.
    """
    if not _is_enabled() or not session_id:
        return

    rc = _get_redis_client()
    if rc is None:
        return

    me = get_worker_id()
    key = _ownership_key(session_id)
    try:
        # Lua script para CAS atômico (compare-and-delete)
        # Evita race: GET → outro worker reivindica → DELETE deletaria o errado.
        lua_cas_delete = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        deleted = rc.eval(lua_cas_delete, 1, key, me)
        if deleted:
            logger.info(f"[STICKY] Released: session={session_id[:8]}... worker={me}")
    except Exception as e:
        logger.debug(f"[STICKY] release_ownership erro (ignorado): {e}")


def cleanup_owned_sessions() -> int:
    """Libera todas ownerships deste worker. Chamado em atexit.

    Returns: número de sessions liberadas.
    """
    if not _is_enabled():
        return 0

    rc = _get_redis_client()
    if rc is None:
        return 0

    me = get_worker_id()
    count = 0
    try:
        # SCAN pelas keys de ownership
        cursor = 0
        while True:
            cursor, keys = rc.scan(cursor=cursor, match="agent:session:owner:*", count=100)
            for key in keys:
                key_str = key if isinstance(key, str) else key.decode("utf-8")
                owner = rc.get(key_str)
                if owner is None:
                    continue
                owner_str = owner if isinstance(owner, str) else owner.decode("utf-8")
                if owner_str == me:
                    rc.delete(key_str)
                    count += 1
            if cursor == 0:
                break
        if count:
            logger.info(f"[STICKY] atexit cleanup: {count} ownerships liberadas (worker={me})")
    except Exception as e:
        logger.debug(f"[STICKY] cleanup_owned_sessions erro: {e}")
    return count
