"""
CUTOVER E3.8b/C2+C3 — flag + drain do motor unico.

Quando AGENT_LOJAS_USA_MOTOR_UNICO=ON, a rota /agente-lojas usa
`_drain_via_motor`: seta os ContextVars do registry WEB (agente_id='lojas' +
loja_scope), chama get_client('lojas').stream_response(...) com o can_use_tool do
fork, e serializa cada StreamEvent no SSE que o frontend lojas espera. No finally
limpa os ContextVars. Estes testes usam um cliente FAKE (sem SDK real) para travar
o wiring, a serializacao integrada e o cleanup.
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


def test_flag_default_off():
    # Canary: o caminho do motor fica INERTE em producao ate ligarem a flag.
    assert chat_mod.AGENT_LOJAS_USA_MOTOR_UNICO is False


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


def test_streaming_worker_flag_on_despacha_para_motor(monkeypatch):
    import concurrent.futures as cf

    monkeypatch.setattr(chat_mod, 'AGENT_LOJAS_USA_MOTOR_UNICO', True)
    chamadas = {'motor': 0, 'fork': 0}

    async def _noop():
        return

    def _fake_drain_motor(**kwargs):
        chamadas['motor'] += 1
        return _noop()

    def _fake_drain_fork(**kwargs):
        chamadas['fork'] += 1
        return _noop()

    monkeypatch.setattr(chat_mod, '_drain_via_motor', _fake_drain_motor)
    monkeypatch.setattr(chat_mod, '_drain_async_gen', _fake_drain_fork)

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
    assert chamadas['fork'] == 0
