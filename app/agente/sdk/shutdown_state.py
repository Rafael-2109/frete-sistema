"""
Shutdown state — flag central para suprimir Sentry capture durante atexit.

Resolve PYTHON-FLASK-PP, PYTHON-FLASK-PN, PYTHON-FLASK-PM:
quando o interpretador Python comeca a finalizar (worker Teams recebe SIGTERM),
o ThreadPoolExecutor default do asyncio e fechado. Qualquer `loop.run_in_executor()`
ou `asyncio.to_thread()` posterior levanta:

    RuntimeError: cannot schedule new futures after shutdown
    RuntimeError: cannot schedule new futures after interpreter shutdown

Esses erros sao INERENTES a race de shutdown — nao indicam bug acionavel.
Antes desta solucao, eram capturados pelo Sentry como issues unresolved
(ruido permanente, ja que reincidem a cada deploy).

Fluxo:
1. `app/agente/__init__.py` chama `register_shutdown_handler()` no init_app
2. Python inicia shutdown -> atexit dispara nosso handler
3. Handler seta `_INTERPRETER_SHUTTING_DOWN = True`
4. Callsites criticos (client.py mirror_error, file_storage.py S3 save) checam
   `is_interpreter_shutting_down()` antes de capturar Sentry
5. Erro continua sendo logado em WARNING (visibilidade local) mas NAO vai pro Sentry

Importante:
- Flag e thread-safe (assignment atomico em CPython, sem necessidade de Lock)
- Nao previne o erro — apenas suprime captura redundante
- Pre-shutdown (operacao normal): comportamento inalterado
- Post-shutdown: log warning + skip Sentry
"""
from __future__ import annotations

import atexit
import logging

logger = logging.getLogger('sistema_fretes')

# Flag global. Assignment booleano e atomico em CPython — sem Lock.
_INTERPRETER_SHUTTING_DOWN: bool = False
_HANDLER_REGISTERED: bool = False


def is_interpreter_shutting_down() -> bool:
    """Retorna True se o interpretador Python iniciou shutdown (atexit disparou)."""
    return _INTERPRETER_SHUTTING_DOWN


def _mark_shutting_down() -> None:
    """Atexit handler — marca flag global. Idempotente."""
    global _INTERPRETER_SHUTTING_DOWN
    _INTERPRETER_SHUTTING_DOWN = True
    logger.info("[shutdown_state] interpretador finalizando — Sentry capture suprimida")


def register_shutdown_handler() -> None:
    """Registra atexit handler. Idempotente — chamadas extras sao no-op.

    Chamado por `app/agente/__init__.py:init_app()` na inicializacao.
    Roda uma vez por processo (worker gunicorn, worker RQ, worker Teams).
    """
    global _HANDLER_REGISTERED
    if _HANDLER_REGISTERED:
        return
    atexit.register(_mark_shutting_down)
    _HANDLER_REGISTERED = True
    logger.debug("[shutdown_state] atexit handler registrado")


def is_shutdown_error(exc: BaseException | str) -> bool:
    """Heuristica: True se a exception/mensagem indica race de shutdown.

    Usado como fallback nos callsites onde `is_interpreter_shutting_down()`
    pode ainda retornar False (atexit ainda nao disparou) mas a exception
    ja revela o estado real (ex: ThreadPoolExecutor fechado por outro motivo).

    Padroes reconhecidos (case-insensitive):
    - "cannot schedule new futures after shutdown"
    - "cannot schedule new futures after interpreter shutdown"
    - "Event loop is closed"
    """
    msg = str(exc).lower() if exc else ""
    return (
        "cannot schedule new futures" in msg
        or "event loop is closed" in msg
    )
