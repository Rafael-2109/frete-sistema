"""Testa emit_subagent_summary via Redis pubsub."""
import json
from unittest.mock import MagicMock, patch


def test_emit_subagent_summary_publishes_to_redis_channel():
    from app.agente.sdk.client import _emit_subagent_summary

    summary_dict = {
        'agent_id': 'a1',
        'agent_type': 'analista-carteira',
        'status': 'done',
        'duration_ms': 8234,
        'tools_used': [],
        'cost_usd': 0.012,
    }

    fake_redis = MagicMock()
    with patch('redis.from_url', return_value=fake_redis):
        _emit_subagent_summary('sess-abc', summary_dict)

    # Verifica que publish foi chamado com canal correto + payload
    assert fake_redis.publish.called
    call = fake_redis.publish.call_args
    channel, payload_raw = call[0]
    assert channel == 'agent_sse:sess-abc'

    payload = json.loads(payload_raw)
    assert payload['type'] == 'subagent_summary'
    assert payload['data']['agent_type'] == 'analista-carteira'


def test_emit_subagent_summary_noop_when_session_id_empty():
    from app.agente.sdk.client import _emit_subagent_summary

    fake_redis = MagicMock()
    with patch('redis.from_url', return_value=fake_redis):
        _emit_subagent_summary('', {'agent_type': 'x'})
        _emit_subagent_summary(None, {'agent_type': 'x'})

    fake_redis.publish.assert_not_called()


def test_emit_subagent_summary_survives_redis_error():
    """R1 best-effort: Redis down nao levanta excecao."""
    from app.agente.sdk.client import _emit_subagent_summary

    with patch('redis.from_url', side_effect=Exception('redis down')):
        # Nao deve levantar
        _emit_subagent_summary('sess-x', {'agent_type': 'x'})
