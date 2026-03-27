"""
Unit Tests — Pending Questions Dual-Event Mechanism

Testa o mecanismo de espera para AskUserQuestion com dual events
(threading.Event + asyncio.Event).

Roda com: pytest tests/agente/sdk/test_pending_questions.py -v -m "unit and sdk_client"

Funcoes testadas:
    - register_question: criacao de PendingQuestion com threading.Event e asyncio.Event
    - submit_answer: sinalizacao de ambos events e armazenamento de resposta
    - wait_for_answer: espera sync (bloqueia thread) com timeout
    - async_wait_for_answer: espera async (suspende coroutine) com timeout
    - cancel_pending: cancelamento sem resposta (unblock waiters com None)
    - Overwrite: sobrescrita de pergunta existente desbloqueia waiters anteriores
"""

import asyncio
import threading
from unittest.mock import patch

import pytest

from app.agente.sdk.pending_questions import (
    _lock,
    _pending,
    async_wait_for_answer,
    cancel_pending,
    get_pending_tool_input,
    register_question,
    submit_answer,
    wait_for_answer,
)


@pytest.fixture(autouse=True)
def cleanup_pending_registry():
    """Limpa o registry global _pending antes e depois de cada teste."""
    with _lock:
        _pending.clear()
    yield
    with _lock:
        _pending.clear()


@pytest.mark.unit
@pytest.mark.sdk_client
class TestRegisterQuestion:
    """Testa register_question: criacao de PendingQuestion e dual events."""

    def test_register_creates_threading_event(self):
        """PendingQuestion tem threading.Event criado e nao sinalizado."""
        pq = register_question("sess-001", {"question": "Confirma?"})

        assert isinstance(pq.event, threading.Event)
        assert not pq.event.is_set()
        assert pq.session_id == "sess-001"
        assert pq.tool_input == {"question": "Confirma?"}
        assert pq.answer is None

    def test_register_in_async_context_creates_async_event(self):
        """Dentro de asyncio.run, PendingQuestion tem async_event criado."""

        async def _register_in_async():
            pq = register_question("sess-async-001", {"q": "ok?"})
            return pq

        pq = asyncio.run(_register_in_async())

        assert pq.async_event is not None
        assert isinstance(pq.async_event, asyncio.Event)

    def test_register_outside_async_no_async_event(self):
        """Fora de async context, async_event e None."""
        pq = register_question("sess-sync-001", {"q": "teste"})

        assert pq.async_event is None


@pytest.mark.unit
@pytest.mark.sdk_client
class TestSubmitAnswer:
    """Testa submit_answer: sinalizacao de events e armazenamento."""

    def test_submit_answer_signals_both_events(self):
        """Ambos threading.Event e asyncio.Event ficam set apos submit."""

        async def _test():
            pq = register_question("sess-both-001", {"q": "sim?"})
            # Em async context, async_event existe
            assert pq.async_event is not None
            assert not pq.event.is_set()
            assert not pq.async_event.is_set()

            result = submit_answer("sess-both-001", {"sim?": "Sim"})

            assert result is True
            assert pq.event.is_set()
            assert pq.async_event.is_set()

        asyncio.run(_test())

    def test_submit_answer_stores_answer(self):
        """pq.answer contem o dict submetido."""
        pq = register_question("sess-store-001", {"q": "nome?"})
        answers = {"nome?": "Rafael", "cargo?": "Dev"}

        submit_answer("sess-store-001", answers)

        assert pq.answer == {"nome?": "Rafael", "cargo?": "Dev"}

    def test_submit_answer_nonexistent_returns_false(self):
        """Retorna False para session_id inexistente."""
        result = submit_answer("sess-fantasma-999", {"q": "nada"})

        assert result is False


@pytest.mark.unit
@pytest.mark.sdk_client
class TestWaitForAnswer:
    """Testa wait_for_answer: espera sync com threading."""

    def test_wait_for_answer_returns_on_submit(self):
        """Thread espera, submit de outra thread desbloqueia e retorna answer."""
        pq = register_question("sess-wait-001", {"q": "confirma?"})
        expected_answer = {"confirma?": "Sim"}
        result_holder = {}

        def _waiter():
            result_holder["answer"] = wait_for_answer("sess-wait-001", timeout=2.0)

        def _submitter():
            submit_answer("sess-wait-001", expected_answer)

        waiter_thread = threading.Thread(target=_waiter)
        submitter_thread = threading.Thread(target=_submitter)

        waiter_thread.start()
        # Pequeno delay para garantir que waiter esta bloqueado antes do submit
        submitter_thread.start()

        waiter_thread.join(timeout=3.0)
        submitter_thread.join(timeout=3.0)

        assert not waiter_thread.is_alive()
        assert result_holder["answer"] == expected_answer

    def test_wait_for_answer_timeout_returns_none(self):
        """Sem submit dentro do timeout, retorna None."""
        register_question("sess-timeout-001", {"q": "vai?"})

        result = wait_for_answer("sess-timeout-001", timeout=0.1)

        assert result is None
        # Verifica cleanup: session removida do registry
        assert get_pending_tool_input("sess-timeout-001") is None


@pytest.mark.unit
@pytest.mark.sdk_client
class TestCancelPending:
    """Testa cancel_pending: desbloqueia waiters sem resposta."""

    def test_cancel_pending_unblocks_waiters(self):
        """cancel_pending seta events mas answer permanece None."""
        pq = register_question("sess-cancel-001", {"q": "cancela?"})

        cancel_pending("sess-cancel-001")

        assert pq.event.is_set()
        assert pq.answer is None
        # Session removida do registry pelo cancel
        assert get_pending_tool_input("sess-cancel-001") is None

    def test_cancel_pending_unblocks_async_event(self):
        """cancel_pending tambem seta async_event quando presente."""

        async def _test():
            pq = register_question("sess-cancel-async-001", {"q": "cancela async?"})
            assert pq.async_event is not None

            cancel_pending("sess-cancel-async-001")

            assert pq.event.is_set()
            assert pq.async_event.is_set()
            assert pq.answer is None

        asyncio.run(_test())


@pytest.mark.unit
@pytest.mark.sdk_client
class TestOverwriteExistingQuestion:
    """Testa sobrescrita: old PQ desbloqueado, new PQ criado."""

    def test_overwrite_existing_question(self):
        """Registrar mesma session_id seta events do PQ anterior e cria novo."""
        old_pq = register_question("sess-overwrite-001", {"q": "pergunta velha"})
        old_event = old_pq.event

        assert not old_event.is_set()

        new_pq = register_question("sess-overwrite-001", {"q": "pergunta nova"})

        # Old PQ desbloqueado
        assert old_event.is_set()
        # New PQ e diferente
        assert new_pq is not old_pq
        assert new_pq.tool_input == {"q": "pergunta nova"}
        assert not new_pq.event.is_set()
        # Registry aponta para o novo
        assert get_pending_tool_input("sess-overwrite-001") == {"q": "pergunta nova"}
