"""Testa emit_subagent_summary no client."""
from queue import Queue


def test_emit_subagent_summary_puts_stream_event_on_queue():
    from app.agente.sdk.client import _emit_subagent_summary
    from app.agente.sdk.stream_parser import StreamEvent

    q = Queue()
    summary_dict = {
        'agent_id': 'a1',
        'agent_type': 'analista-carteira',
        'status': 'done',
        'duration_ms': 8234,
        'tools_used': [],
        'cost_usd': 0.012,
    }

    _emit_subagent_summary(q, summary_dict)

    assert not q.empty()
    ev = q.get_nowait()
    assert isinstance(ev, StreamEvent)
    assert ev.type == 'subagent_summary'
    assert ev.content['agent_type'] == 'analista-carteira'


def test_emit_subagent_summary_safe_with_none_queue():
    from app.agente.sdk.client import _emit_subagent_summary
    _emit_subagent_summary(None, {'agent_type': 'x'})  # nao levanta
