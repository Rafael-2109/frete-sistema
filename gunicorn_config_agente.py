"""
Gunicorn config — instancia AGENTE (rotas /agente/*).

Filosofia: Claude Agent SDK e per-process. 1 worker = 1 ClaudeSDKClient
persistente por sessao = sem cross-worker contention. Threads atendem
multiplos usuarios concorrentes em sessoes diferentes (e dentro da
mesma sessao serializam via lock interno no client_pool).

Nginx faz proxy /agente/* -> 127.0.0.1:5001.
"""

# Bind interno — nginx faz proxy
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
# Defesa contra memory leak: monitorar via /admin/render-metrics; se vazar,
# reduzir para 10000 (vs 5000 do sistema porque ja temos so 1 worker).
max_requests = 0  # 0 = desabilitado
max_requests_jitter = 0

worker_connections = 1000
preload_app = False  # mesma razao do sistema (PG types per-worker)


def on_starting(server):
    print("[AGENTE] Gunicorn iniciando (workers=1 threads=8 timeout=1800)...")
    try:
        import register_pg_types  # noqa: F401
        print("[AGENTE] Tipos PostgreSQL registrados")
    except Exception as e:
        print(f"[AGENTE] WARN: Erro ao registrar tipos PG: {e}")


def post_fork(server, worker):
    print(f"[AGENTE] Worker {worker.pid} iniciado")
    try:
        import register_pg_types  # noqa: F401
        print(f"[AGENTE] Tipos PostgreSQL no worker {worker.pid}")
    except Exception as e:
        print(f"[AGENTE] WARN: PG types worker {worker.pid}: {e}")
    # Pre-importar cysignals na main thread (gthread + tesserocr requirement)
    try:
        import cysignals  # noqa: F401
    except ImportError:
        pass


def worker_exit(server, worker):
    """Cleanup ownerships sticky em rolling deploy (mesmo com sticky off — defesa)."""
    try:
        from app.agente.sdk.sticky_session import cleanup_owned_sessions
        n = cleanup_owned_sessions()
        if n:
            print(f"[AGENTE] Worker {worker.pid} exit: {n} sticky ownerships liberadas")
    except Exception as e:
        print(f"[AGENTE] Worker {worker.pid} exit cleanup: {e}")
