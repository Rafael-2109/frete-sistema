"""Observabilidade de memoria (Nivel 1 — diagnostico de memory leak no app web).

Contexto: incidente OOM 2026-05-21 (web Pro Plus 8GB). Causa = memory leak no
processo web (cresce ~1.5-2 GB/h sob carga, nao libera, so reseta em restart).
Este modulo INSTRUMENTA para localizar a FONTE do leak — NAO mitiga.

Tres sondas, todas controladas por env var e DEFAULT OFF (deploy inocuo ate
ligar a flag no Render, sem novo deploy):

  MEMPROF_LIGHT=true   -> sondas leves (baixo overhead):
     1. RSS por request (after_request): loga endpoint que incha
     2. Monitor por worker (thread): RSS do worker + subprocess filhos (node/python3)
  MEMORY_PROFILING=true -> tracemalloc (overhead ~2-3x em alocacao):
     3. snapshot diff (top-N por arquivo:linha) quando RSS cruza limite

Logs com prefixo [MEMPROF] — consultar via Render list_logs text=["[MEMPROF]"].

Thresholds configuraveis por env (defaults entre parenteses):
  MEMPROF_REQ_DELTA_MB (25)   loga request se delta RSS >= isso
  MEMPROF_REQ_RSS_MB   (5000) ou se RSS absoluto >= isso
  MEMPROF_DUMP_RSS_MB  (6500) dispara dump tracemalloc acima disso
  MEMPROF_INTERVAL_S   (60)   intervalo do monitor
  MEMPROF_NFRAMES      (1)    profundidade de stack do tracemalloc (1=min overhead)
  MEMPROF_DUMP_COOLDOWN_S (300) intervalo minimo entre dumps
  MEMPROF_TOP_N        (25)   linhas no diff
"""
import os
import time
import logging
import threading

logger = logging.getLogger("sistema_fretes")

try:
    import psutil
except Exception as _e:  # pragma: no cover
    psutil = None
    logger.warning(f"[MEMPROF] psutil indisponivel — sondas de RSS desativadas: {_e}")


# --------------------------------------------------------------------- flags/env
def _flag(name: str) -> bool:
    return os.environ.get(name, "false").strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip())
    except (ValueError, TypeError):
        return default


def _light_enabled() -> bool:
    return _flag("MEMPROF_LIGHT")


def _trace_enabled() -> bool:
    return _flag("MEMORY_PROFILING")


# --------------------------------------------------------------------- psutil helpers
_proc_cache = {}


def _proc():
    """psutil.Process do PID atual (cache por-PID — robusto a fork de worker)."""
    if psutil is None:
        return None
    pid = os.getpid()
    p = _proc_cache.get(pid)
    if p is None:
        try:
            p = psutil.Process(pid)
            _proc_cache[pid] = p
        except Exception:
            return None
    return p


def _rss_mb() -> float:
    p = _proc()
    if p is None:
        return -1.0
    try:
        return p.memory_info().rss / (1024 * 1024)
    except Exception:
        return -1.0


def _children_summary() -> str:
    """Agrega subprocess filhos por nome: 'node=2(310MB) python3=1(231MB)'."""
    p = _proc()
    if p is None:
        return "psutil_off"
    try:
        agg = {}
        for c in p.children(recursive=True):
            try:
                name = c.name()
                rss = c.memory_info().rss / (1024 * 1024)
            except Exception:
                continue
            cnt, tot = agg.get(name, (0, 0.0))
            agg[name] = (cnt + 1, tot + rss)
        if not agg:
            return "sem_filhos"
        return " ".join(
            f"{n}={cnt}({tot:.0f}MB)"
            for n, (cnt, tot) in sorted(agg.items(), key=lambda kv: -kv[1][1])
        )
    except Exception as e:
        return f"erro:{e}"


# --------------------------------------------------------------------- tracemalloc
_tm_lock = threading.Lock()
_tm_started = False
_tm_baseline = None
_tm_last_dump = 0.0


def _maybe_start_tracemalloc():
    global _tm_started
    if _tm_started or not _trace_enabled():
        return
    with _tm_lock:
        if _tm_started:
            return
        try:
            import tracemalloc
            tracemalloc.start(max(1, _env_int("MEMPROF_NFRAMES", 1)))
            _tm_started = True
            logger.info(f"[MEMPROF] tracemalloc START nframes={_env_int('MEMPROF_NFRAMES', 1)} pid={os.getpid()}")
        except Exception as e:
            logger.warning(f"[MEMPROF] tracemalloc start falhou: {e}")


def _set_baseline():
    global _tm_baseline
    if _tm_baseline is not None:
        return
    try:
        import tracemalloc
        if not tracemalloc.is_tracing():
            return
        _tm_baseline = tracemalloc.take_snapshot()
        logger.info(f"[MEMPROF] tracemalloc BASELINE rss={_rss_mb():.0f}MB pid={os.getpid()}")
    except Exception as e:
        logger.warning(f"[MEMPROF] baseline falhou: {e}")


def _dump_tracemalloc(reason: str):
    """Loga top-N alocacoes que cresceram desde o baseline (arquivo:linha)."""
    global _tm_last_dump
    if _tm_baseline is None:
        return
    now = time.time()
    if now - _tm_last_dump < _env_int("MEMPROF_DUMP_COOLDOWN_S", 300):
        return
    try:
        import tracemalloc
        snap = tracemalloc.take_snapshot().filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
            tracemalloc.Filter(False, __file__),
        ))
        _tm_last_dump = now
        stats = snap.compare_to(_tm_baseline, "lineno")
        top_n = _env_int("MEMPROF_TOP_N", 25)
        logger.warning(f"[MEMPROF] tracemalloc DIFF ({reason}) rss={_rss_mb():.0f}MB pid={os.getpid()} — top {top_n}:")
        for i, st in enumerate(stats[:top_n], 1):
            frame = st.traceback[0] if st.traceback else "?"
            logger.warning(
                f"[MEMPROF]   #{i} +{st.size_diff/1024/1024:.1f}MB "
                f"(blocks {st.count_diff:+d}) {frame}"
            )
    except Exception as e:
        logger.warning(f"[MEMPROF] tracemalloc dump falhou: {e}")


# --------------------------------------------------------------------- malloc_trim (glibc)
# Distingue fragmentacao (liberavel via trim) de retencao real (objetos vivos).
# Cai muito apos trim -> era fragmentacao glibc (fix sem mudar comportamento:
# MALLOC_ARENA_MAX=2). Nao cai -> retencao real (precisa tracemalloc).
_libc_cache = None


def _libc():
    """Carrega libc.so.6 (glibc) lazy. None se indisponivel (nao-Linux/musl)."""
    global _libc_cache
    if _libc_cache is False:
        return None
    if _libc_cache is None:
        try:
            import ctypes
            _libc_cache = ctypes.CDLL("libc.so.6")
        except Exception:
            _libc_cache = False
            return None
    return _libc_cache


def _maybe_malloc_trim():
    """Devolve paginas LIVRES das arenas glibc ao SO. Loga RSS antes/depois.

    SEGURO: NAO toca em objetos vivos — so devolve memoria que o glibc ja tinha
    liberado mas reteve em arenas para reuso. Custo: ~ms a centenas de ms, em
    thread separada (monitor). Pior caso (retencao em pymalloc, nao glibc): no-op.
    Atras de flag MEMPROF_TRIM (default OFF) — liga/desliga via env var.
    """
    if not _flag("MEMPROF_TRIM"):
        return
    libc = _libc()
    if libc is None:
        return
    try:
        rss_before = _rss_mb()
        ret = libc.malloc_trim(0)  # 0 = sem padding, devolve tudo possivel
        rss_after = _rss_mb()
        delta = rss_after - rss_before
        logger.info(
            f"[MEMPROF] trim pid={os.getpid()} ret={ret} "
            f"rss_before={rss_before:.0f}MB rss_after={rss_after:.0f}MB delta={delta:+.0f}MB"
        )
    except Exception as e:
        logger.warning(f"[MEMPROF] malloc_trim falhou: {e}")


# --------------------------------------------------------------------- monitor thread
_monitor_started = False


def _monitor_loop():
    interval = max(5, _env_int("MEMPROF_INTERVAL_S", 60))
    # warmup: deixa o app terminar de carregar antes do baseline do tracemalloc
    time.sleep(min(interval, 30))
    if _trace_enabled():
        _set_baseline()
    while True:
        try:
            _maybe_malloc_trim()  # se MEMPROF_TRIM=true: trim + log antes/depois
            rss = _rss_mb()
            logger.info(
                f"[MEMPROF] worker pid={os.getpid()} rss={rss:.0f}MB | filhos: {_children_summary()}"
            )
            if _trace_enabled() and rss >= _env_int("MEMPROF_DUMP_RSS_MB", 6500):
                _dump_tracemalloc(f"rss>={_env_int('MEMPROF_DUMP_RSS_MB', 6500)}MB")
        except Exception as e:
            logger.warning(f"[MEMPROF] monitor erro: {e}")
        time.sleep(interval)


def _start_monitor_once():
    global _monitor_started
    if _monitor_started:
        return
    _monitor_started = True
    t = threading.Thread(target=_monitor_loop, name="memprof-monitor", daemon=True)
    t.start()
    logger.info(f"[MEMPROF] monitor thread iniciada pid={os.getpid()} interval={max(5, _env_int('MEMPROF_INTERVAL_S', 60))}s")


# --------------------------------------------------------------------- request probe
def _register_request_probe(app):
    from flask import g, request

    @app.before_request
    def _memprof_before():  # pyright: ignore[reportUnusedFunction]
        try:
            g._memprof_rss0 = _rss_mb()
        except Exception:
            pass

    @app.after_request
    def _memprof_after(response):  # pyright: ignore[reportUnusedFunction]
        try:
            rss0 = getattr(g, "_memprof_rss0", None)
            rss1 = _rss_mb()
            if rss0 is not None and rss0 >= 0 and rss1 >= 0:
                delta = rss1 - rss0
                if delta >= _env_int("MEMPROF_REQ_DELTA_MB", 25) or rss1 >= _env_int("MEMPROF_REQ_RSS_MB", 5000):
                    logger.warning(
                        f"[MEMPROF] req {request.method} {request.path} "
                        f"rss={rss1:.0f}MB delta={delta:+.0f}MB status={response.status_code}"
                    )
        except Exception:
            pass
        return response


# --------------------------------------------------------------------- entrypoint
def init_memory_profiling(app):
    """Chamado em create_app. No-op total se nenhuma flag ativa."""
    if not (_light_enabled() or _trace_enabled()):
        return
    _maybe_start_tracemalloc()
    if _light_enabled():
        _register_request_probe(app)
    _start_monitor_once()
    logger.info(
        f"[MEMPROF] init light={_light_enabled()} trace={_trace_enabled()} pid={os.getpid()}"
    )
