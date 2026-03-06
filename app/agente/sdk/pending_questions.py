"""
Mecanismo de espera para AskUserQuestion.

Permite que o callback can_use_tool() pause até o frontend
enviar a resposta do usuário via HTTP POST.

Modelo Dual Event (Fase 2 Async Migration):
- threading.Event: sync path (legado/Teams, bloqueia thread)
- asyncio.Event: async path (can_use_tool em asyncio.run(), suspende coroutine)

Fluxo:
1. can_use_tool intercepta AskUserQuestion
2. register_question() → PendingQuestion com Event + async_event (se em async context)
3. SSE emitido para frontend (via event_queue)
4. async_wait_for_answer() suspende coroutine OU wait_for_answer() bloqueia thread
5. Frontend POST /api/user-answer → submit_answer() → ambos Events sinalizados
6. Resposta coletada
7. can_use_tool retorna PermissionResultAllow(updated_input={answers: ...})
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Timeout para o usuário responder (segundos)
# SDK tem timeout de 60s no can_use_tool, usamos 55s para ter margem
USER_RESPONSE_TIMEOUT = 55


@dataclass
class PendingQuestion:
    """Pergunta pendente aguardando resposta do usuário."""
    session_id: str
    tool_input: Dict[str, Any]
    event: threading.Event = field(default_factory=threading.Event)
    async_event: Optional[asyncio.Event] = field(default=None)  # Fase 2: para async context
    answer: Optional[Dict[str, str]] = None


# Registry global: session_id → PendingQuestion
_pending: Dict[str, PendingQuestion] = {}
_lock = threading.Lock()


def register_question(session_id: str, tool_input: Dict[str, Any]) -> PendingQuestion:
    """
    Registra pergunta pendente para uma sessão.

    Args:
        session_id: ID da sessão (nosso, não do SDK)
        tool_input: Input completo da tool AskUserQuestion

    Returns:
        PendingQuestion com Event para sincronização
    """
    with _lock:
        # Se já existe pergunta pendente para esta sessão, cancela a anterior
        # para evitar deadlock (thread anterior ficaria bloqueada até timeout)
        existing = _pending.get(session_id)
        if existing:
            existing.event.set()  # Desbloqueia thread anterior (sync)
            if existing.async_event:
                existing.async_event.set()  # Desbloqueia coroutine anterior (async)
            logger.warning(
                f"[ASK_USER] Sobrescrevendo pergunta anterior: session={session_id[:8]}..."
            )

        pq = PendingQuestion(session_id=session_id, tool_input=tool_input)
        # Fase 2: Cria asyncio.Event se estamos em async context
        try:
            asyncio.get_running_loop()
            pq.async_event = asyncio.Event()
        except RuntimeError:
            pass  # Não estamos em async context — sem async_event
        _pending[session_id] = pq
        logger.info(f"[ASK_USER] Pergunta registrada: session={session_id[:8]}...")
        return pq


def submit_answer(session_id: str, answers: Dict[str, str]) -> bool:
    """
    Submete resposta do usuário. Chamado pelo endpoint HTTP.

    NOTA thread-safety do async_event.set():
    Chamado pela Flask route (thread do Gunicorn worker) enquanto async_wait_for_answer
    espera no event loop da thread daemon. No CPython, asyncio.Event.set() é protegido
    pelo GIL, mas não é oficialmente thread-safe. Se causar problemas, substituir por
    loop.call_soon_threadsafe(). Mantido simples até evidência de race condition.

    Args:
        session_id: ID da sessão
        answers: Dict mapeando question text → label selecionado

    Returns:
        True se havia pergunta pendente e foi respondida.
    """
    with _lock:
        pq = _pending.get(session_id)
        if not pq:
            logger.warning(f"[ASK_USER] Nenhuma pergunta pendente: session={session_id[:8]}...")
            return False

        pq.answer = answers
        pq.event.set()  # Desbloqueia threading.Event (sync path)
        if pq.async_event:
            pq.async_event.set()  # Desbloqueia asyncio.Event (async path)
        logger.info(
            f"[ASK_USER] Resposta recebida: session={session_id[:8]}... "
            f"answers={list(answers.keys())}"
        )
        return True


def wait_for_answer(
    session_id: str,
    timeout: float = USER_RESPONSE_TIMEOUT,
) -> Optional[Dict[str, str]]:
    """
    Bloqueia até o usuário responder ou timeout.
    Chamado dentro do can_use_tool callback (que roda em Thread daemon).

    IMPORTANTE: Usa threading.Event.wait() que é thread-safe.
    O can_use_tool roda em asyncio.run() dentro de uma Thread,
    e a resposta vem via Flask route (outra thread).

    Args:
        session_id: ID da sessão
        timeout: Segundos máximos para esperar (default 55s)

    Returns:
        Dict de respostas ou None se timeout
    """
    with _lock:
        pq = _pending.get(session_id)

    if not pq:
        logger.warning(f"[ASK_USER] wait_for_answer: nenhum PQ encontrado para session={session_id[:8]}...")
        return None

    # Espera (thread-safe, funciona entre threads diferentes)
    answered = pq.event.wait(timeout=timeout)

    # Cleanup: remove do registry independente do resultado
    with _lock:
        _pending.pop(session_id, None)

    if answered and pq.answer is not None:
        logger.info(f"[ASK_USER] Resposta coletada: session={session_id[:8]}...")
        return pq.answer

    logger.warning(f"[ASK_USER] Timeout ({timeout}s) sem resposta: session={session_id[:8]}...")
    return None


async def async_wait_for_answer(
    session_id: str,
    timeout: float = USER_RESPONSE_TIMEOUT,
) -> Optional[Dict[str, str]]:
    """
    Versão async — suspende coroutine sem bloquear thread.

    Usada quando can_use_tool roda em async context nativo
    (Fase 2: can_use_tool já roda dentro de asyncio.run() na thread daemon,
     Fase 3 futura: streaming sem Thread intermediária).

    Args:
        session_id: ID da sessão
        timeout: Segundos máximos para esperar (default 55s)

    Returns:
        Dict de respostas ou None se timeout
    """
    with _lock:
        pq = _pending.get(session_id)

    if not pq or not pq.async_event:
        logger.warning(
            f"[ASK_USER] async_wait: sem PQ ou sem async_event: session={session_id[:8]}..."
        )
        return None

    try:
        await asyncio.wait_for(pq.async_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"[ASK_USER] Async timeout ({timeout}s): session={session_id[:8]}...")

    # Cleanup: remove do registry independente do resultado
    with _lock:
        _pending.pop(session_id, None)

    if pq.answer is not None:
        logger.info(f"[ASK_USER] Async resposta coletada: session={session_id[:8]}...")
        return pq.answer

    return None


def cancel_pending(session_id: str) -> None:
    """
    Cancela pergunta pendente (ex: stream interrompido, erro).

    Desbloqueia qualquer thread/coroutine esperando em wait_for_answer()
    ou async_wait_for_answer(), que receberá None (pois answer não foi setado).

    Args:
        session_id: ID da sessão
    """
    with _lock:
        pq = _pending.pop(session_id, None)
        if pq:
            pq.event.set()  # Desbloqueia sync path
            if pq.async_event:
                pq.async_event.set()  # Desbloqueia async path
            logger.info(f"[ASK_USER] Pergunta cancelada: session={session_id[:8]}...")
