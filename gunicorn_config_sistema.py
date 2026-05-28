"""
Gunicorn config — instancia SISTEMA (tudo exceto /agente/*).

Mantem perfil atual de PROD: 4 workers gthread paralelizam picos de CPU
(2.5% das horas > 87% de 4CPU). Uso real observado (30d): p50 CPU 2%,
p95 77%, memoria 2.2 GB avg de 8 GB. HTTP pico 1.44 rps — 8 threads
simultaneas sao folga (~20 rps capacidade).

Nginx faz proxy / -> 127.0.0.1:5002.
"""

bind = "127.0.0.1:5002"

# 4 workers x 2 threads = 8 requests concorrentes
workers = 4
worker_class = "gthread"
threads = 2

# timeout=1800 (30min) — Render permite ate 100min per request.
timeout = 1800
# graceful_timeout=1740 alinha com MAX_STREAM_DURATION_SECONDS (29min).
graceful_timeout = 1740
keepalive = 10

# max_requests=5000 reduz frequencia de rotacao. Com 1.44 rps medio
# x 4 workers, rotacao a cada ~5h. Defesa contra memory leak.
max_requests = 5000
max_requests_jitter = 500

worker_connections = 1000
preload_app = False  # PG types per-worker


def on_starting(server):
    print("[SISTEMA] Gunicorn iniciando (workers=4 threads=2 timeout=1800)...")
    try:
        import register_pg_types  # noqa: F401
        print("[SISTEMA] Tipos PostgreSQL registrados")
    except Exception as e:
        print(f"[SISTEMA] WARN: Erro ao registrar tipos PG: {e}")


def post_fork(server, worker):
    print(f"[SISTEMA] Worker {worker.pid} iniciado")
    try:
        import register_pg_types  # noqa: F401
        print(f"[SISTEMA] Tipos PostgreSQL no worker {worker.pid}")
    except Exception as e:
        print(f"[SISTEMA] WARN: PG types worker {worker.pid}: {e}")
    try:
        import cysignals  # noqa: F401
    except ImportError:
        pass


def worker_exit(server, worker):
    """Marca tasks Teams running como timeout quando worker sai."""
    try:
        from app import create_app, db
        from app.teams.models import TeamsTask
        app = create_app()
        with app.app_context():
            count = TeamsTask.query.filter(
                TeamsTask.status.in_(['pending', 'processing']),
            ).update({'status': 'timeout'}, synchronize_session=False)
            if count > 0:
                db.session.commit()
                print(f"[SISTEMA] Worker {worker.pid} exit: {count} TeamsTask -> timeout")
            else:
                db.session.rollback()
    except Exception as e:
        print(f"[SISTEMA] Worker {worker.pid} exit cleanup: {e}")
