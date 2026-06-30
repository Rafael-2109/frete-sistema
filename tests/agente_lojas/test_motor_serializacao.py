"""
CUTOVER E3.8b — serializacao StreamEvent (motor web) -> SSE (formato fork).

O frontend do agente lojas (templates/agente_lojas/chat.html) consome o SSE no
SHAPE que o fork `_drain_async_gen` produzia (tool_call -> tool_name+tool_input,
tool_result -> content+is_error), que DIFERE do shape do agente web. Estes testes
travam o contrato: `_motor_event_to_sse` converte um StreamEvent do motor no SSE
que o frontend lojas espera, e acumula assistant_text/sdk_session_id/final_metadata
no `state` (para a persistencia pos-stream).
"""
import json

import pytest

from app.agente.sdk.stream_parser import StreamEvent
from app.agente_lojas.routes.chat import _motor_event_to_sse


def _parse_sse(s):
    """Quebra 'event: X\\ndata: {json}\\n\\n' em (event_type, data_dict)."""
    assert s is not None, "esperava string SSE, veio None"
    event_type = None
    data = None
    for ln in s.strip().split('\n'):
        if ln.startswith('event: '):
            event_type = ln[len('event: '):]
        elif ln.startswith('data: '):
            data = json.loads(ln[len('data: '):])
    return event_type, data


def test_init_captura_sdk_session_id_no_state():
    state = {}
    ev = StreamEvent(type='init', content={'session_id': 'abc-123'})
    et, data = _parse_sse(_motor_event_to_sse(ev, state))
    assert et == 'init'
    assert data['sdk_session_id'] == 'abc-123'
    assert state['sdk_session_id'] == 'abc-123'


def test_init_pending_nao_grava_no_state():
    state = {}
    ev = StreamEvent(type='init', content={'session_id': 'pending'})
    _motor_event_to_sse(ev, state)
    assert state.get('sdk_session_id') is None


def test_text_emite_content_e_acumula_assistant_text():
    state = {}
    sse1 = _motor_event_to_sse(StreamEvent(type='text', content='Ola '), state)
    sse2 = _motor_event_to_sse(StreamEvent(type='text', content='mundo'), state)
    et1, data1 = _parse_sse(sse1)
    assert et1 == 'text'
    assert data1['content'] == 'Ola '
    et2, _ = _parse_sse(sse2)
    assert et2 == 'text'
    assert state['assistant_text'] == 'Ola mundo'


def test_thinking_emite_content():
    et, data = _parse_sse(_motor_event_to_sse(StreamEvent(type='thinking', content='pensando'), {}))
    assert et == 'thinking'
    assert data['content'] == 'pensando'


def test_tool_call_mapeia_tool_name_e_tool_input():
    # Motor: content=tool_name, metadata['input']=tool_input. Frontend lojas le
    # payload.tool_name + payload.tool_input (appendToolCall).
    ev = StreamEvent(
        type='tool_call',
        content='Bash',
        metadata={'input': {'command': 'ls'}, 'tool_id': 'tu_1', 'description': 'lista'},
    )
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'tool_call'
    assert data['tool_name'] == 'Bash'
    assert data['tool_input'] == {'command': 'ls'}


def test_tool_result_mapeia_content_e_is_error():
    # Motor: content=result, metadata['is_error']. Frontend lojas le
    # payload.content + payload.is_error (appendToolResult).
    ev = StreamEvent(type='tool_result', content='saida do comando', metadata={'is_error': True, 'tool_name': 'Bash'})
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'tool_result'
    assert data['content'] == 'saida do comando'
    assert data['is_error'] is True


def test_tool_result_is_error_default_false():
    ev = StreamEvent(type='tool_result', content='ok', metadata={})
    _et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert data['is_error'] is False


@pytest.mark.parametrize('tname', ['TaskCreate', 'TaskUpdate', 'TaskList'])
def test_tool_result_de_task_star_suprimido_quando_sucesso(tname):
    # O motor emite tool_result E task_event para Task* (client.py:1239 + :1280).
    # O fork suprimia o tool_result generico (continue apos task_event). Replicamos:
    # so o task_event renderiza no UI — evita duplicata visual para o operador.
    ev = StreamEvent(type='tool_result', content='Task #1 created successfully: X',
                     metadata={'tool_name': tname, 'is_error': False})
    assert _motor_event_to_sse(ev, {}) is None


def test_tool_result_de_task_star_com_erro_e_emitido():
    # Task* com erro: o motor NAO emite task_event (client.py:1253 `and not is_error`),
    # entao o tool_result (carregando o erro) DEVE aparecer para o operador.
    ev = StreamEvent(type='tool_result', content='boom', metadata={'tool_name': 'TaskCreate', 'is_error': True})
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'tool_result'
    assert data['is_error'] is True


def test_tool_result_de_tool_normal_nao_e_suprimido():
    ev = StreamEvent(type='tool_result', content='saida', metadata={'tool_name': 'Bash', 'is_error': False})
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'tool_result'
    assert data['content'] == 'saida'


def test_task_event_com_action_emite_payload_direto():
    ev = StreamEvent(type='task_event', content={'action': 'created', 'task_id': '1', 'subject': 'X'})
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'task_event'
    assert data['action'] == 'created'
    assert data['task_id'] == '1'


def test_task_event_sem_action_ignora():
    assert _motor_event_to_sse(StreamEvent(type='task_event', content={}), {}) is None


def test_todos_emite_lista():
    ev = StreamEvent(type='todos', content={'todos': [{'content': 'a', 'status': 'pending'}]})
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'todos'
    assert data['todos'] == [{'content': 'a', 'status': 'pending'}]


def test_todos_vazio_ignora():
    assert _motor_event_to_sse(StreamEvent(type='todos', content={'todos': []}), {}) is None


def test_done_captura_custo_e_sdk_session_no_state():
    state = {}
    ev = StreamEvent(type='done', content={
        'session_id': 'sdk-9', 'total_cost_usd': 0.05,
        'input_tokens': 10, 'output_tokens': 20,
    })
    et, data = _parse_sse(_motor_event_to_sse(ev, state))
    assert et == 'done'
    assert data['total_cost_usd'] == 0.05
    assert data['input_tokens'] == 10
    assert state['final_metadata']['total_cost_usd'] == 0.05
    assert state['sdk_session_id'] == 'sdk-9'


def test_done_pending_session_nao_sobrescreve():
    state = {'sdk_session_id': 'ja-tenho'}
    ev = StreamEvent(type='done', content={'session_id': 'pending', 'total_cost_usd': 0})
    _motor_event_to_sse(ev, state)
    assert state['sdk_session_id'] == 'ja-tenho'


def test_error_emite_content_e_error_type():
    ev = StreamEvent(type='error', content='deu ruim', metadata={'error_type': 'process_error'})
    et, data = _parse_sse(_motor_event_to_sse(ev, {}))
    assert et == 'error'
    assert data['content'] == 'deu ruim'
    assert data['error_type'] == 'process_error'


@pytest.mark.parametrize('tipo', [
    'warning', 'queued', 'task_started', 'task_progress', 'task_notification',
    'rate_limit', 'stderr', 'subagent_summary', 'interrupt_ack',
])
def test_tipos_nao_consumidos_pelo_frontend_lojas_sao_ignorados(tipo):
    # O frontend lojas (chat.html) so trata text/thinking/tool_call/tool_result/
    # todos/task_event/error/ask_user_question/init/start/heartbeat/done. Outros
    # tipos do motor web NAO devem virar SSE (evita ruido/eventos mortos).
    assert _motor_event_to_sse(StreamEvent(type=tipo, content='x'), {}) is None
