"""
Gunicorn config — instancia AGENTE (rotas /agente/*).

Filosofia: Claude Agent SDK e per-process. 1 worker = 1 ClaudeSDKClient
persistente por sessao = sem cross-worker contention. Threads atendem
multiplos usuarios concorrentes em sessoes diferentes (e dentro da
mesma sessao serializam via lock interno no client_pool).

Nginx faz proxy /agente/* -> 127.0.0.1:5001.

IMPORTANTE: o start_render.sh DEVE fazer `unset GUNICORN_CMD_ARGS`
ANTES de chamar este config — o Render injeta
`GUNICORN_CMD_ARGS=--bind=0.0.0.0:$PORT` que sobrescreve o bind abaixo.
"""

# Bind interno — nginx faz proxy externo em 0.0.0.0:10000
bind = "127.0.0.1:5001"

# 1 worker (Pattern 2 da doc oficial /hosting)
workers = 1
worker_class = "gthread"
# 8 threads: atendem sessoes diferentes em paralelo (I/O bound — Sonnet API)
# A serializacao por session_id e feita no client_pool (lock por session)
threads = 8

# Timeouts identicos ao gunicorn-sistema para consistencia
timeout = 1800
graceful_timeout = 1740
keepalive = 10

# Worker rotation: agente acumula state (ClaudeSDKClient, JSONLs em disco).
# Rotacao mata subprocess CLI e quebra sessoes ativas — desligamos.
# Defesa contra memory leak: monitorar via /admin/render-metrics.
max_requests = 0  # 0 = desabilitado
max_requests_jitter = 0

worker_connections = 1000
preload_app = False  # PG types per-worker


def on_starting(server):
    print("[AGENTE] Gunicorn iniciando (workers=1 threads=8 timeout=1800)...")
    try:
        import register_pg_types  # noqa: F401
        print("[AGENTE] Tipos PostgreSQL registrados")
    except Exception as e:
        print(f"[AGENTE] WARN: Erro ao registrar tipos PG: {e}")


def post_fork(server, worker):
    print(f"[AGENTE] Worker {worker.pid} iniciado")
    # Watchdog de deadlock-de-fork no boot (2026-06-18): o worker do agente as
    # vezes trava em futex durante o load do app (1 thread, app nao carrega) —
    # deadlock de fork intermitente que deixava /agente 502. dump_traceback_later
    # dispara uma thread interna do faulthandler que, se o worker NAO terminar de
    # carregar em 80s, dumpa o stack de TODAS as threads nos logs (pina o ponto
    # exato do deadlock; funciona mesmo com a main thread travada e sem ptrace).
    # Cancelado em post_worker_init quando o load completa (sem ruido no boot OK).
    try:
        import faulthandler, threading  # noqa: E401
        faulthandler.dump_traceback_later(80, exit=False)
        _threads = [t.name for t in threading.enumerate()]
        print(f"[AGENTE] post_fork pid={worker.pid} threads_apos_fork={_threads} (faulthandler armado 80s)")
    except Exception as _e:
        print(f"[AGENTE] post_fork instrumentacao falhou: {_e}")
    try:
        import register_pg_types  # noqa: F401
        print(f"[AGENTE] Tipos PostgreSQL no worker {worker.pid}")
    except Exception as e:
        print(f"[AGENTE] WARN: PG types worker {worker.pid}: {e}")
    try:
        import cysignals  # noqa: F401
    except ImportError:
        pass


def post_worker_init(worker):
    """App carregou com sucesso — cancela o watchdog de deadlock do faulthandler."""
    try:
        import faulthandler
        faulthandler.cancel_dump_traceback_later()
        print(f"[AGENTE] Worker {worker.pid} app carregado — faulthandler watchdog cancelado")
    except Exception:
        pass


def worker_exit(server, worker):
    """Cleanup ownerships sticky em rolling deploy."""
    try:
        from app.agente.sdk.sticky_session import cleanup_owned_sessions
        n = cleanup_owned_sessions()
        if n:
            print(f"[AGENTE] Worker {worker.pid} exit: {n} sticky ownerships liberadas")
    except Exception as e:
        print(f"[AGENTE] Worker {worker.pid} exit cleanup: {e}")
