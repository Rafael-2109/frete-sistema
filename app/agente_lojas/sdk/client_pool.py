"""
Pool enxuto do agente Lojas HORA — event loop persistente.

Versao MINIMAL do client_pool.py do agente Nacom (~600 LOC). Aqui mantemos
APENAS o event loop persistente em daemon thread, evitando o custo de
`asyncio.new_event_loop()` por request (~50-100ms).

NAO implementa (deliberado, escopo M2):
    - Reuso de ClaudeSDKClient instances (lifecycle + force-kill complexos)
    - Cleanup idle baseado em timestamp
    - Shutdown handler atexit
    - Force-kill de subprocess zombie

A cada request, criamos novo ClaudeSDKClient via `async with` (gerenciado
pelo SDK, encerra subprocess no __aexit__). O ganho aqui eh apenas evitar
spin-up/tear-down do event loop. Reuso de client e otimizacao M3+.

Feature flag:
    USE_PERSISTENT_LOJAS_LOOP (default true)
    Quando false, fallback para `asyncio.new_event_loop()` por request.

Uso:
    fut = submit_coroutine(some_async_func())
    result = fut.result(timeout=600)
"""
import asyncio
import logging
import os
import threading
from concurrent.futures import Future
from typing import Any, Coroutine, Optional

logger = logging.getLogger('sistema_fretes')


# Feature flag (env var). Default ON.
USE_PERSISTENT_LOJAS_LOOP: bool = os.getenv(
    'USE_PERSISTENT_LOJAS_LOOP', 'true'
).lower() in ('true', '1', 'yes', 'on')


# Loop persistente (lazy init, daemon thread)
_lojas_loop: Optional[asyncio.AbstractEventLoop] = None
_lojas_thread: Optional[threading.Thread] = None
_lojas_lock = threading.Lock()


def _ensure_loop_running() -> Optional[asyncio.AbstractEventLoop]:
    """Garante que o event loop persistente esta rodando.

    Returns:
        Loop ativo ou None se feature flag desligada.
    """
    if not USE_PERSISTENT_LOJAS_LOOP:
        return None

    global _lojas_loop, _lojas_thread
    with _lojas_lock:
        # Loop ja ativo e thread viva
        if (
            _lojas_loop is not None
            and not _lojas_loop.is_closed()
            and _lojas_thread is not None
            and _lojas_thread.is_alive()
        ):
            return _lojas_loop

        # Criar novo loop em daemon thread
        _lojas_loop = asyncio.new_event_loop()
        _lojas_thread = threading.Thread(
            target=_lojas_loop.run_forever,
            daemon=True,
            name='lojas-sdk-loop',
        )
        _lojas_thread.start()
        logger.info("[LOJAS_POOL] Event loop persistente iniciado (daemon thread)")
        return _lojas_loop


def submit_coroutine(coro: Coroutine[Any, Any, Any]) -> Optional[Future]:
    """Submete coroutine ao loop persistente.

    Args:
        coro: Coroutine a executar (deve eventualmente terminar).

    Returns:
        concurrent.futures.Future ou None se feature flag OFF.
        Caller deve usar fut.result(timeout=N) para aguardar.
    """
    loop = _ensure_loop_running()
    if loop is None:
        return None
    return asyncio.run_coroutine_threadsafe(coro, loop)


def shutdown_pool() -> None:
    """Encerra event loop persistente. Chamado em testes / shutdown."""
    global _lojas_loop, _lojas_thread
    with _lojas_lock:
        if _lojas_loop is None or _lojas_loop.is_closed():
            return
        try:
            _lojas_loop.call_soon_threadsafe(_lojas_loop.stop)
        except Exception:
            pass
        if _lojas_thread is not None and _lojas_thread.is_alive():
            try:
                _lojas_thread.join(timeout=2.0)
            except Exception:
                pass
        try:
            _lojas_loop.close()
        except Exception:
            pass
        _lojas_loop = None
        _lojas_thread = None
        logger.info("[LOJAS_POOL] Event loop persistente encerrado")


def is_running() -> bool:
    """Retorna True se loop persistente esta ativo."""
    with _lojas_lock:
        return (
            _lojas_loop is not None
            and not _lojas_loop.is_closed()
            and _lojas_thread is not None
            and _lojas_thread.is_alive()
        )
