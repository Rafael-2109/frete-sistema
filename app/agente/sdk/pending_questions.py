"""
Mecanismo de espera para AskUserQuestion.

Permite que o callback can_use_tool() pause até o frontend
enviar a resposta do usuário via HTTP POST.

Usa threading.Event (thread-safe) pois:
- can_use_tool é chamado dentro de asyncio.run() em uma Thread
- A resposta vem via Flask route (outra thread)

Fluxo:
1. can_use_tool intercepta AskUserQuestion
2. register_question() → PendingQuestion com Event
3. SSE emitido para frontend (via event_queue no thread-local)
4. wait_for_answer() bloqueia (threading.Event.wait)
5. Frontend POST /api/user-answer → submit_answer() → Event.set()
6. wait_for_answer() retorna answers
7. can_use_tool retorna PermissionResultAllow(updated_input={answers: ...})
"""

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
            existing.event.set()  # Desbloqueia thread anterior
            logger.warning(
                f"[ASK_USER] Sobrescrevendo pergunta anterior: session={session_id[:8]}..."
            )

        pq = PendingQuestion(session_id=session_id, tool_input=tool_input)
        _pending[session_id] = pq
        logger.info(f"[ASK_USER] Pergunta registrada: session={session_id[:8]}...")
        return pq


def submit_answer(session_id: str, answers: Dict[str, str]) -> bool:
    """
    Submete resposta do usuário. Chamado pelo endpoint HTTP.

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
        pq.event.set()  # Desbloqueia o callback can_use_tool
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


def cancel_pending(session_id: str) -> None:
    """
    Cancela pergunta pendente (ex: stream interrompido, erro).

    Desbloqueia qualquer thread esperando em wait_for_answer(),
    que receberá None (pois answer não foi setado).

    Args:
        session_id: ID da sessão
    """
    with _lock:
        pq = _pending.pop(session_id, None)
        if pq:
            pq.event.set()  # Desbloqueia se alguém estiver esperando
            logger.info(f"[ASK_USER] Pergunta cancelada: session={session_id[:8]}...")
