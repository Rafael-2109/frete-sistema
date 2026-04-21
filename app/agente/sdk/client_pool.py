"""
Pool de ClaudeSDKClient por sessão com daemon thread persistente.

Arquitetura:
- Daemon thread único com event loop persistente (_sdk_loop)
- Registry: session_id → PooledClient (1:1 — ClaudeSDKClient é stateful)
- submit_coroutine(): bridge Flask thread → daemon (run_coroutine_threadsafe)
- Cleanup automático de clients idle (PERSISTENT_CLIENT_IDLE_TIMEOUT)

CAVEAT SDK: "you cannot use a ClaudeSDKClient instance across different
async runtime contexts". Por isso TODAS as operações rodam no MESMO
event loop do daemon thread.

Feature flag: USE_PERSISTENT_SDK_CLIENT (default true)
Quando false: daemon thread NÃO inicia, funções retornam None/raise — rollback para query() standalone (spawn + destroy CLI por turno).

Ref: .claude/references/ROADMAP_SDK_CLIENT.md (Fase 0, Task 0.2)
"""

import asyncio
import logging
import os
import signal
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any, Coroutine, Dict, Optional

logger = logging.getLogger('sistema_fretes')


# =============================================================================
# Force Kill — bypass para subprocess zombie
# =============================================================================

async def _force_kill_subprocess(client) -> bool:
    """Mata o subprocess CLI quando disconnect() falha.

    disconnect() chama query.close() que falha com RuntimeError
    ("Attempted to exit cancel scope in a different task") quando
    chamado de task diferente do connect(). Nesse caso, transport.close()
    NUNCA é alcançado e o subprocess fica zombie.

    Este método acessa transport.close() diretamente. É SAFE porque:
    - _stderr_task_group.cancel_scope.cancel() + __aexit__() → suppress(Exception)
    - _write_lock é anyio.Lock (sem restrição cross-task)
    - _process.terminate() é OS-level (sem cancel scope)

    Ref: subprocess_cli.py:449-488 (transport.close)
    Ref: query.py:659-667 (query.close — onde falha)

    Args:
        client: ClaudeSDKClient com subprocess potencialmente zombie

    Returns:
        True se conseguiu matar, False se não encontrou subprocess
    """
    # Tentar via client._transport (acesso direto)
    transport = getattr(client, '_transport', None)

    # Fallback: via client._query.transport
    if not transport:
        query = getattr(client, '_query', None)
        if query:
            transport = getattr(query, 'transport', None)

    if not transport:
        logger.debug("[SDK_POOL] _force_kill_subprocess: nenhum transport encontrado")
        return False

    try:
        await transport.close()
        logger.info("[SDK_POOL] _force_kill_subprocess: transport.close() OK")
        return True
    except Exception as e:
        logger.warning(f"[SDK_POOL] _force_kill_subprocess: transport.close() falhou: {e}")
        # Fallback: terminate/kill direto no processo
        process = getattr(transport, '_process', None)
        if not process:
            logger.warning("[SDK_POOL] _force_kill_subprocess: nenhum _process no transport")
            return False

        pid = getattr(process, 'pid', None)

        # Nível 1: SIGTERM via process.terminate()
        if process.returncode is None:
            try:
                process.terminate()
                # Aguardar brevemente para terminate fazer efeito
                await asyncio.sleep(0.5)
                if process.returncode is not None:
                    logger.info("[SDK_POOL] _force_kill_subprocess: process.terminate() OK")
                    return True
            except Exception as e2:
                logger.warning(f"[SDK_POOL] _force_kill_subprocess: terminate() falhou: {e2}")

        # Nível 2: SIGKILL via os.kill (último recurso)
        if process.returncode is None and pid:
            try:
                os.kill(pid, signal.SIGKILL)
                logger.warning(f"[SDK_POOL] _force_kill_subprocess: SIGKILL enviado para PID {pid}")
                return True
            except ProcessLookupError:
                logger.debug(f"[SDK_POOL] _force_kill_subprocess: PID {pid} já não existe")
                return True  # Processo já morreu
            except Exception as e3:
                logger.error(
                    f"[SDK_POOL] _force_kill_subprocess: FALHA TOTAL "
                    f"(terminate + SIGKILL) PID={pid}: {e3}"
                )
                return False

        if process.returncode is not None:
            logger.debug(
                "[SDK_POOL] _force_kill_subprocess: processo já terminou "
                f"(returncode={process.returncode})"
            )
        return process.returncode is not None


# =============================================================================
# Tipos
# =============================================================================

@dataclass
class PooledClient:
    """Um ClaudeSDKClient no pool, com metadados de lifecycle.

    Atributos:
        client: Instância do ClaudeSDKClient (do SDK)
        session_id: Nosso UUID de sessão (não o sdk_session_id efêmero)
        user_id: ID do usuário dono da sessão
        created_at: Timestamp de criação (connect)
        last_used: Timestamp do último query()
        connected: Se o client está conectado (após connect(), antes de disconnect())
        lock: asyncio.Lock para serializar operações no mesmo client
        sdk_session_id: UUID do SDK (nome do JSONL) — setado apos init message
    """
    client: Any  # ClaudeSDKClient — tipado como Any para evitar import circular
    session_id: str
    user_id: int = 0
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    connected: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    sdk_session_id: Optional[str] = None


# =============================================================================
# Estado global do pool (module-level)
# =============================================================================

# Registry: session_id → PooledClient
_registry: Dict[str, PooledClient] = {}
_registry_lock = threading.Lock()

# Daemon thread e event loop persistente
_sdk_loop: Optional[asyncio.AbstractEventLoop] = None
_sdk_loop_thread: Optional[threading.Thread] = None
_cleanup_task: Optional[Future] = None  # Future da task _periodic_cleanup (rastreável)
_pool_initialized = False
_shutdown_requested = False


# =============================================================================
# Inicialização (lazy — só quando USE_PERSISTENT_SDK_CLIENT=true)
# =============================================================================

def _ensure_pool_initialized() -> bool:
    """Inicializa daemon thread e event loop se ainda não feito.

    Returns:
        True se o pool está pronto, False se flag desabilitada.
    """
    global _sdk_loop, _sdk_loop_thread, _cleanup_task, _pool_initialized

    if _pool_initialized:
        return True

    from ..config.feature_flags import USE_PERSISTENT_SDK_CLIENT
    if not USE_PERSISTENT_SDK_CLIENT:
        return False

    # Double-checked locking
    with _registry_lock:
        if _pool_initialized:
            return True

        _sdk_loop = asyncio.new_event_loop()

        _sdk_loop_thread = threading.Thread(
            target=_run_loop_forever,
            name="sdk-pool-daemon",
            daemon=True,
        )
        _sdk_loop_thread.start()

        # Agendar cleanup periódico — armazenar referência para cancelar no shutdown
        # (sem referência, a task é GC'd enquanto pendente → "Task was destroyed")
        _cleanup_task = asyncio.run_coroutine_threadsafe(
            _periodic_cleanup(), _sdk_loop
        )

        _pool_initialized = True
        logger.info(
            "[SDK_POOL] Daemon thread iniciado: "
            f"thread={_sdk_loop_thread.name}, "
            f"loop_id={id(_sdk_loop)}"
        )

    return True


def _run_loop_forever():
    """Target do daemon thread — roda event loop persistente."""
    global _sdk_loop
    assert _sdk_loop is not None

    try:
        _sdk_loop.run_forever()
    except Exception as e:
        logger.critical(f"[SDK_POOL] Daemon thread CRASHED: {e}", exc_info=True)
        # Auto-restart: marca como não-inicializado para que a próxima
        # chamada recrie o daemon
        global _pool_initialized
        _pool_initialized = False
    finally:
        # Cleanup: fechar o loop
        try:
            _sdk_loop.close()
        except Exception:
            pass
        logger.info("[SDK_POOL] Daemon thread encerrado")


# =============================================================================
# Bridge: Flask thread → daemon thread
# =============================================================================

def submit_coroutine(
    coro: Coroutine,
    timeout: float = 540.0,
) -> Future:
    """Submete coroutine ao daemon thread e retorna Future.

    Uso no Flask thread:
        future = submit_coroutine(some_async_func())
        result = future.result(timeout=540)

    Args:
        coro: Coroutine a executar no daemon thread
        timeout: Timeout em segundos (não usado aqui — aplicar via future.result())

    Returns:
        concurrent.futures.Future com resultado da coroutine

    Raises:
        RuntimeError: Se pool não está inicializado
    """
    if not _ensure_pool_initialized():
        raise RuntimeError(
            "[SDK_POOL] Pool não inicializado. "
            "Verifique AGENT_PERSISTENT_SDK_CLIENT=true"
        )

    if _sdk_loop is None or _sdk_loop.is_closed():
        raise RuntimeError("[SDK_POOL] Event loop do daemon está fechado")

    return asyncio.run_coroutine_threadsafe(coro, _sdk_loop)


# =============================================================================
# Gerenciamento de clients
# =============================================================================

async def get_or_create_client(
    session_id: str,
    options: Any,  # ClaudeAgentOptions
    user_id: int = 0,
) -> PooledClient:
    """Obtém client existente ou cria novo para a sessão.

    DEVE ser chamada dentro do daemon thread (via submit_coroutine).

    Args:
        session_id: Nosso UUID de sessão
        options: ClaudeAgentOptions para connect()
        user_id: ID do usuário

    Returns:
        PooledClient conectado e pronto para query()

    Raises:
        Exception: Se connect() falhar
    """
    # Fast path: client já existe e está conectado
    with _registry_lock:
        pooled = _registry.get(session_id)

    if pooled and pooled.connected:
        pooled.last_used = time.time()
        logger.debug(
            f"[SDK_POOL] Reusing client: session={session_id[:8]}... "
            f"age={time.time() - pooled.created_at:.0f}s"
        )
        return pooled

    # Slow path: criar novo client
    from claude_agent_sdk import ClaudeSDKClient

    client = ClaudeSDKClient(options)

    # Connect com streaming mode (None = interactive, sem prompt inicial)
    await client.connect()

    pooled = PooledClient(
        client=client,
        session_id=session_id,
        user_id=user_id,
        connected=True,
    )

    with _registry_lock:
        # Se havia um client antigo desconectado, limpar
        old = _registry.get(session_id)
        _registry[session_id] = pooled

    # Limpar client antigo FORA do lock (I/O assíncrono)
    if old and old.connected:
        logger.warning(
            f"[SDK_POOL] Replacing connected client: session={session_id[:8]}... "
            "(possível race condition)"
        )
        try:
            await old.client.disconnect()
        except Exception as e:
            logger.warning(
                f"[SDK_POOL] Erro ao desconectar client antigo: {e}, "
                "tentando force kill"
            )
            await _force_kill_subprocess(old.client)

    logger.info(
        f"[SDK_POOL] Client criado e conectado: "
        f"session={session_id[:8]}... user_id={user_id} "
        f"total_clients={len(_registry)}"
    )

    return pooled


async def disconnect_client(session_id: str) -> bool:
    """Desconecta e remove client do pool.

    DEVE ser chamada dentro do daemon thread (via submit_coroutine).

    Args:
        session_id: Nosso UUID de sessão

    Returns:
        True se havia client para desconectar, False se não encontrado
    """
    with _registry_lock:
        pooled = _registry.pop(session_id, None)

    if not pooled:
        return False

    if pooled.connected:
        try:
            await pooled.client.disconnect()
            pooled.connected = False
            logger.info(
                f"[SDK_POOL] Client desconectado: session={session_id[:8]}... "
                f"duration={time.time() - pooled.created_at:.0f}s"
            )
        except Exception as e:
            logger.warning(
                f"[SDK_POOL] disconnect() falhou (esperado — cross-task cancel scope): "
                f"session={session_id[:8]}... error={e}"
            )
            # disconnect() falha com RuntimeError quando chamado de task
            # diferente do connect(). O subprocess fica zombie.
            # Force kill via transport.close() diretamente.
            killed = await _force_kill_subprocess(pooled.client)
            pooled.connected = False
            if killed:
                logger.info(
                    f"[SDK_POOL] Subprocess morto via force kill: "
                    f"session={session_id[:8]}... "
                    f"duration={time.time() - pooled.created_at:.0f}s"
                )
                # Cleanup JSONL potencialmente corrompido por SIGKILL.
                # SIGKILL mata mid-write → JSONL truncado → resume crash.
                _cleanup_stale_jsonl(pooled.sdk_session_id)
            else:
                logger.error(
                    f"[SDK_POOL] FALHA ao matar subprocess: "
                    f"session={session_id[:8]}... — POSSÍVEL ZOMBIE"
                )

    return True


def _cleanup_stale_jsonl(sdk_session_id: Optional[str]) -> None:
    """Remove JSONL potencialmente corrompido apos force kill.

    SIGKILL pode matar o CLI mid-write, deixando JSONL truncado.
    Se o arquivo existir quando o proximo resume tentar, _is_jsonl_valid()
    (com fix F1) detectaria a corrupcao — mas e melhor limpar proativamente.

    Args:
        sdk_session_id: UUID do SDK (nome do JSONL). None = noop.
    """
    if not sdk_session_id:
        return
    try:
        from .session_persistence import _get_session_path
        import os as _os
        path = _get_session_path(sdk_session_id)
        if _os.path.exists(path):
            _os.remove(path)
            logger.info(
                f"[SDK_POOL] Stale JSONL removido apos force kill: "
                f"{sdk_session_id[:8]}..."
            )
    except Exception as e:
        logger.debug(f"[SDK_POOL] JSONL cleanup ignorado: {e}")


def get_pooled_client(session_id: str) -> Optional[PooledClient]:
    """Obtém PooledClient do registry (sem criar).

    Thread-safe — pode ser chamado de qualquer thread.

    Args:
        session_id: Nosso UUID de sessão

    Returns:
        PooledClient ou None se não encontrado
    """
    with _registry_lock:
        return _registry.get(session_id)


# =============================================================================
# Cleanup periódico
# =============================================================================

async def _periodic_cleanup():
    """Task periódica que desconecta clients idle.

    Roda no daemon thread. Executa a cada PERSISTENT_CLIENT_CLEANUP_INTERVAL.
    """
    from ..config.feature_flags import (
        PERSISTENT_CLIENT_IDLE_TIMEOUT,
        PERSISTENT_CLIENT_CLEANUP_INTERVAL,
    )

    while not _shutdown_requested:
        try:
            await asyncio.sleep(PERSISTENT_CLIENT_CLEANUP_INTERVAL)
            await _cleanup_idle_clients(PERSISTENT_CLIENT_IDLE_TIMEOUT)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[SDK_POOL] Cleanup error: {e}", exc_info=True)
            await asyncio.sleep(30)  # Backoff após erro


async def _cleanup_idle_clients(idle_timeout: float):
    """Desconecta clients que ultrapassaram o idle timeout.

    Args:
        idle_timeout: Segundos de inatividade antes de desconectar
    """
    now = time.time()
    to_disconnect = []

    with _registry_lock:
        for session_id, pooled in _registry.items():
            idle_seconds = now - pooled.last_used
            if idle_seconds > idle_timeout and pooled.connected:
                to_disconnect.append(session_id)

    if not to_disconnect:
        return

    for session_id in to_disconnect:
        try:
            await disconnect_client(session_id)
            logger.info(
                f"[SDK_POOL] Idle cleanup: session={session_id[:8]}... "
                f"(idle > {idle_timeout}s)"
            )
        except Exception as e:
            logger.warning(
                f"[SDK_POOL] Cleanup failed: session={session_id[:8]}... error={e}"
            )

    logger.info(
        f"[SDK_POOL] Cleanup concluído: {len(to_disconnect)} clients desconectados, "
        f"{len(_registry)} restantes"
    )


# =============================================================================
# Diagnóstico (para health check)
# =============================================================================

def get_pool_status() -> Dict[str, Any]:
    """Retorna status do pool para health check / diagnóstico.

    Thread-safe — pode ser chamado de qualquer thread.

    Returns:
        Dict com métricas do pool
    """
    from ..config.feature_flags import USE_PERSISTENT_SDK_CLIENT

    if not USE_PERSISTENT_SDK_CLIENT:
        return {
            'enabled': False,
            'status': 'disabled',
        }

    with _registry_lock:
        clients_info = []
        for session_id, pooled in _registry.items():
            clients_info.append({
                'session_id': session_id[:8] + '...',
                'user_id': pooled.user_id,
                'connected': pooled.connected,
                'idle_seconds': round(time.time() - pooled.last_used, 1),
                'age_seconds': round(time.time() - pooled.created_at, 1),
            })

    thread_alive = _sdk_loop_thread.is_alive() if _sdk_loop_thread else False
    loop_running = _sdk_loop.is_running() if _sdk_loop else False

    return {
        'enabled': True,
        'status': 'healthy' if (thread_alive and loop_running) else 'degraded',
        'daemon_thread_alive': thread_alive,
        'event_loop_running': loop_running,
        'total_clients': len(clients_info),
        'clients': clients_info,
    }


# =============================================================================
# Shutdown (para worker exit / gunicorn hooks)
# =============================================================================

def shutdown_pool():
    """Desconecta todos os clients e para o daemon thread.

    Chamado no worker_exit hook do Gunicorn ou em testes.
    Thread-safe — pode ser chamado de qualquer thread.
    """
    global _shutdown_requested, _pool_initialized, _cleanup_task

    if not _pool_initialized:
        return

    _shutdown_requested = True
    logger.info("[SDK_POOL] Shutdown iniciado...")

    # Cancelar cleanup task periódica ANTES de desconectar clients
    # (evita "Task was destroyed but it is pending" no GC)
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.debug("[SDK_POOL] Cleanup task cancelada")
    _cleanup_task = None

    # Desconectar todos os clients
    with _registry_lock:
        session_ids = list(_registry.keys())

    for session_id in session_ids:
        try:
            future = asyncio.run_coroutine_threadsafe(
                disconnect_client(session_id),
                _sdk_loop,
            )
            future.result(timeout=10)
        except Exception as e:
            logger.warning(
                f"[SDK_POOL] Shutdown disconnect failed: "
                f"session={session_id[:8]}... error={e}"
            )

    # Parar event loop
    if _sdk_loop and _sdk_loop.is_running():
        _sdk_loop.call_soon_threadsafe(_sdk_loop.stop)

    # Aguardar daemon thread encerrar
    if _sdk_loop_thread and _sdk_loop_thread.is_alive():
        _sdk_loop_thread.join(timeout=5)

    _pool_initialized = False
    logger.info(
        f"[SDK_POOL] Shutdown concluído: "
        f"{len(session_ids)} clients desconectados"
    )
