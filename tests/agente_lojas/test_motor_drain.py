"""
CUTOVER (FASE B) — drain do motor unico na rota /agente-lojas.

A rota usa SEMPRE `_drain_via_motor` (fork aposentado): seta os ContextVars do
registry WEB (agente_id='lojas' + loja_scope), chama get_client('lojas').
stream_response(...) com o can_use_tool do agente_lojas (config/permissions), e
serializa cada StreamEvent no SSE que o frontend lojas espera. No finally limpa os
ContextVars. Estes testes usam um cliente FAKE (sem SDK real) para travar o wiring,
a serializacao integrada e o cleanup.
"""
import asyncio
import queue

import app.agente_lojas.routes.chat as chat_mod
from app.agente.sdk.stream_parser import StreamEvent
from app.agente.config.permissions import get_current_agent_id, get_loja_scope


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _drain_queue(q):
    out = []
    while True:
        item = q.get_nowait()
        if item is None:
            break
        out.append(item)
    return out


class _FakeClient:
    """Captura o estado de ContextVar visto DURANTE o stream + os kwargs."""

    def __init__(self, events, capture):
        self._events = events
        self._capture = capture

    async def stream_response(self, **kwargs):
        self._capture['agente'] = get_current_agent_id()
        self._capture['loja_scope'] = get_loja_scope()
        self._capture['kwargs'] = kwargs
        for ev in self._events:
            yield ev


def test_drain_via_motor_wiring_serializacao_e_persistencia(monkeypatch):
    events = [
        StreamEvent(type='init', content={'session_id': 'sdk-xyz'}),
        StreamEvent(type='text', content='Oi '),
        StreamEvent(type='tool_call', content='Bash',
                    metadata={'input': {'command': 'ls'}, 'tool_id': 't1'}),
        StreamEvent(type='tool_result', content='arquivos', metadata={'is_error': False}),
        StreamEvent(type='text', content='pronto'),
        StreamEvent(type='done', content={
            'session_id': 'sdk-xyz', 'total_cost_usd': 0.02,
            'input_tokens': 10, 'output_tokens': 5,
        }),
    ]
    capture = {}
    fake = _FakeClient(events, capture)
    monkeypatch.setattr('app.agente.sdk.client.get_client', lambda agente_id='web': fake)

    q = queue.Queue()
    state = {}
    _run(chat_mod._drain_via_motor(
        user_message='oi', user_id=7, user_name='Operador', perfil='vendedor',
        loja_hora_id=3, sdk_session_id=None, our_session_id='our-sid-1',
        event_queue=q, state=state,
    ))

    # 1) Wiring: durante o stream, o perfil 'lojas' + loja_scope estavam setados
    assert capture['agente'] == 'lojas'
    assert capture['loja_scope'] == ('vendedor', 3)
    # 2) can_use_tool do fork foi passado ao motor + nosso UUID
    assert capture['kwargs'].get('can_use_tool') is not None
    assert capture['kwargs'].get('our_session_id') == 'our-sid-1'

    sse = _drain_queue(q)
    blob = '\n'.join(sse)
    # 3) Serializacao no formato do frontend lojas
    assert 'event: text' in blob
    assert '"tool_name": "Bash"' in blob and '"tool_input"' in blob
    assert 'event: tool_result' in blob and 'arquivos' in blob
    assert 'event: done' in blob
    # 4) state acumulado p/ a persistencia pos-stream
    assert state['assistant_text'] == 'Oi pronto'
    assert state['sdk_session_id'] == 'sdk-xyz'
    assert state['final_metadata']['total_cost_usd'] == 0.02
    # 5) sentinel None encerrou o drain
    # (drenado por _drain_queue ao ver None)

    # 6) Cleanup: ContextVars voltaram ao default apos o finally
    assert get_current_agent_id() == 'web'
    assert get_loja_scope() is None


def test_drain_via_motor_erro_emite_error_e_done(monkeypatch):
    class _BoomClient:
        async def stream_response(self, **kwargs):
            raise RuntimeError("falha no motor")
            yield  # pragma: no cover (torna async generator)

    monkeypatch.setattr('app.agente.sdk.client.get_client', lambda agente_id='web': _BoomClient())

    q = queue.Queue()
    _run(chat_mod._drain_via_motor(
        user_message='oi', user_id=7, user_name='Op', perfil='admin',
        loja_hora_id=None, sdk_session_id=None, our_session_id='our-err',
        event_queue=q, state={},
    ))
    blob = '\n'.join(_drain_queue(q))
    # frontend lojas: error reseta o modal; done destrava o stream
    assert 'event: error' in blob
    assert 'event: done' in blob
    # cleanup mesmo no erro
    assert get_current_agent_id() == 'web'
    assert get_loja_scope() is None


def test_streaming_worker_despacha_para_o_motor(monkeypatch):
    # FASE B: o fork foi aposentado — o worker SEMPRE roda _drain_via_motor no
    # loop do client_pool do motor (sem mais a flag AGENT_LOJAS_USA_MOTOR_UNICO).
    import concurrent.futures as cf

    chamadas = {'motor': 0}

    async def _noop():
        return

    def _fake_drain_motor(**kwargs):
        chamadas['motor'] += 1
        return _noop()

    monkeypatch.setattr(chat_mod, '_drain_via_motor', _fake_drain_motor)

    def _fake_submit_motor(coro):
        coro.close()  # evita 'coroutine never awaited'
        f = cf.Future()
        f.set_result(None)
        return f

    monkeypatch.setattr('app.agente.sdk.client_pool.submit_coroutine', _fake_submit_motor)

    chat_mod._streaming_worker(
        user_message='x', user_id=1, user_name='u', perfil='p', loja_hora_id=1,
        sdk_session_id=None, our_session_id='s', event_queue=queue.Queue(), state={},
    )
    assert chamadas['motor'] == 1


def test_streaming_worker_motor_submit_falha_emite_error_e_sentinel(monkeypatch):
    # Robustez: submit_coroutine do MOTOR LEVANTA RuntimeError se o pool web estiver
    # off (USE_PERSISTENT_SDK_CLIENT=false) ou o loop fechado — diferente do fork,
    # que retorna None. Sem tratamento, a thread daemon morre ANTES do sentinel None
    # -> o SSE generator trava ate o timeout de inatividade (~300s). O worker deve
    # capturar e emitir error + None para destravar o frontend.
    async def _noop():
        return

    def _make_drain(**kwargs):
        return _noop()

    monkeypatch.setattr(chat_mod, '_drain_via_motor', _make_drain)

    def _submit_boom(coro):
        coro.close()  # evita 'coroutine never awaited'
        raise RuntimeError("[SDK_POOL] Pool não inicializado")

    monkeypatch.setattr('app.agente.sdk.client_pool.submit_coroutine', _submit_boom)

    q = queue.Queue()
    # NAO deve propagar a excecao (senao a thread daemon morreria sem sentinel)
    chat_mod._streaming_worker(
        user_message='x', user_id=1, user_name='u', perfil='p', loja_hora_id=1,
        sdk_session_id=None, our_session_id='s', event_queue=q, state={},
    )

    items = []
    while True:
        it = q.get_nowait()
        items.append(it)
        if it is None:
            break
    blob = '\n'.join(str(i) for i in items if i is not None)
    assert 'event: error' in blob, "deve emitir error ao falhar o submit"
    assert items[-1] is None, "deve emitir sentinel None para destravar o SSE"
