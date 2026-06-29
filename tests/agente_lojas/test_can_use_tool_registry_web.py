"""
CUTOVER E3.8b/C4 — convergencia do registry de contexto.

Sob o motor unico, a rota /agente-lojas seta session_id/event_queue no registry
do modulo WEB (app/agente/config/permissions). O can_use_tool do fork precisa LER
desse mesmo registry para o AskUserQuestion funcionar (emitir SSE + aguardar
resposta). Estes testes travam que as funcoes de contexto do modulo lojas SAO as
do registry web (registro unico), e que o can_use_tool acha um event_queue setado
exclusivamente pelo registry web.
"""
import asyncio
import queue as _queue

from claude_agent_sdk import PermissionResultAllow

from app.agente_lojas.config import permissions as lp
from app.agente.config import permissions as wp


def test_funcoes_de_contexto_sao_as_do_registry_web():
    # Registro unico: as funcoes de contexto do modulo lojas sao identicas as
    # do modulo web (re-export), garantindo um unico _stream_context/ContextVar.
    assert lp.get_current_session_id is wp.get_current_session_id
    assert lp.set_current_session_id is wp.set_current_session_id
    assert lp.get_event_queue is wp.get_event_queue
    assert lp.set_event_queue is wp.set_event_queue
    assert lp.cleanup_session_context is wp.cleanup_session_context


def test_ask_user_question_acha_event_queue_do_registry_web(monkeypatch):
    import app.agente.sdk.pending_questions as pq

    sid = 'cutover-c4-web-registry'
    q = _queue.Queue()
    # Seta SOMENTE no registry WEB (como a rota fara sob o motor).
    wp.set_current_session_id(sid)
    wp.set_event_queue(sid, q)

    # Evita bloqueio real do AskUserQuestion: stub das funcoes de pending.
    monkeypatch.setattr(pq, 'register_question', lambda *a, **k: None)

    async def _fake_async_wait(*a, **k):
        return {'q1': 'resposta'}

    monkeypatch.setattr(pq, 'async_wait_for_answer', _fake_async_wait)
    monkeypatch.setattr(pq, 'wait_for_answer', lambda *a, **k: {'q1': 'resposta'})

    try:
        result = asyncio.new_event_loop().run_until_complete(
            lp.can_use_tool(
                'AskUserQuestion',
                {'questions': [{'question': 'q1', 'options': []}]},
                None,
            )
        )
        # Achou o event_queue (setado so no web) -> emitiu SSE + retornou Allow.
        assert isinstance(result, PermissionResultAllow)
        emitted = q.get_nowait()
        assert 'ask_user_question' in emitted
    finally:
        wp.cleanup_session_context(sid)
        # reseta o ContextVar p/ nao contaminar testes que esperam session None
        wp._current_session_id.set(None)
