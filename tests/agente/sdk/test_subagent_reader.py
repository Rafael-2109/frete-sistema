"""Testes para subagent_reader — wrapper do SDK 0.1.60."""
from datetime import datetime
from unittest.mock import MagicMock, patch


def _make_message(role, content, timestamp=None):
    """Helper: cria mock de SessionMessage."""
    msg = MagicMock()
    msg.role = role
    msg.content = content
    msg.timestamp = timestamp or datetime(2026, 4, 16, 14, 22, 0)
    return msg


def test_list_session_subagents_returns_list_of_ids():
    """list_session_subagents wrapper chama SDK e retorna lista de agent_ids."""
    from app.agente.sdk.subagent_reader import list_session_subagents

    with patch('app.agente.sdk.subagent_reader.list_subagents') as mock:
        mock.return_value = ['agent-uuid-1', 'agent-uuid-2']
        result = list_session_subagents('session-uuid')

    assert result == ['agent-uuid-1', 'agent-uuid-2']
    # Chamada sem directory=None (SDK default honra CLAUDE_CONFIG_DIR / ~/.claude)
    mock.assert_called_with('session-uuid')


def test_list_session_subagents_empty_when_no_subagents():
    """Retorna lista vazia quando nao ha subagentes."""
    from app.agente.sdk.subagent_reader import list_session_subagents

    with patch('app.agente.sdk.subagent_reader.list_subagents', return_value=[]):
        assert list_session_subagents('session-uuid') == []


def test_get_subagent_summary_parses_tools_and_cost():
    """get_subagent_summary extrai tools, cost, tokens do transcript."""
    from app.agente.sdk.subagent_reader import get_subagent_summary

    messages = [
        _make_message('user', 'Analise a carteira do Atacadao'),
        _make_message('assistant', [
            {'type': 'tool_use', 'id': 't1', 'name': 'query_sql',
             'input': {'query': 'SELECT * FROM pedidos'}},
        ]),
        _make_message('user', [
            {'type': 'tool_result', 'tool_use_id': 't1',
             'content': '24 pedidos em aberto'},
        ]),
        _make_message('assistant', [
            {'type': 'text', 'text': 'Encontrei 24 pedidos em aberto.'}
        ]),
    ]

    with patch('app.agente.sdk.subagent_reader.get_subagent_messages',
               return_value=messages), \
         patch('app.agente.sdk.subagent_reader._read_result_metadata',
               return_value={'cost_usd': 0.012, 'duration_ms': 8234,
                             'num_turns': 4, 'input_tokens': 1200,
                             'output_tokens': 400, 'cache_read_tokens': 0,
                             'stop_reason': 'end_turn'}):
        summary = get_subagent_summary('session-uuid', 'agent-uuid-1',
                                        agent_type='analista-carteira')

    assert summary.agent_id == 'agent-uuid-1'
    assert summary.agent_type == 'analista-carteira'
    assert summary.status == 'done'
    assert len(summary.tools_used) == 1
    assert summary.tools_used[0]['name'] == 'query_sql'
    assert summary.cost_usd == 0.012
    assert summary.input_tokens == 1200
    assert summary.output_tokens == 400
    assert 'Encontrei 24 pedidos' in summary.findings_text


def test_get_subagent_summary_empty_when_agent_not_found():
    """Retorna SubagentSummary com status='error' quando SDK nao encontra."""
    from app.agente.sdk.subagent_reader import get_subagent_summary

    with patch('app.agente.sdk.subagent_reader.get_subagent_messages',
               return_value=[]):
        summary = get_subagent_summary('session-uuid', 'missing-id',
                                        agent_type='analista-carteira')

    assert summary.status == 'error'
    assert summary.tools_used == []
    assert summary.findings_text == ''


def test_get_subagent_summary_masks_pii_when_include_pii_false():
    """Quando include_pii=False, aplica pii_masker em tool args/results/findings."""
    from app.agente.sdk.subagent_reader import get_subagent_summary

    messages = [
        _make_message('assistant', [
            {'type': 'tool_use', 'id': 't1', 'name': 'query_sql',
             'input': {'cnpj': '12.345.678/0001-90'}},
        ]),
        _make_message('assistant', [
            {'type': 'text', 'text': 'Cliente 12.345.678/0001-90 tem 5 pedidos'}
        ]),
    ]

    with patch('app.agente.sdk.subagent_reader.get_subagent_messages',
               return_value=messages), \
         patch('app.agente.sdk.subagent_reader._read_result_metadata',
               return_value={'cost_usd': 0, 'duration_ms': 0, 'num_turns': 1,
                             'input_tokens': 0, 'output_tokens': 0,
                             'cache_read_tokens': 0, 'stop_reason': 'end_turn'}):
        summary = get_subagent_summary('s', 'a1', agent_type='test',
                                        include_pii=False)

    assert '12.345.678/0001-90' not in summary.findings_text
    assert '0001-90' in summary.findings_text  # preserva filial


def test_get_session_subagents_summary_batch():
    """get_session_subagents_summary combina list + get em batch."""
    from app.agente.sdk.subagent_reader import get_session_subagents_summary

    with patch('app.agente.sdk.subagent_reader.list_session_subagents',
               return_value=['a1', 'a2']), \
         patch('app.agente.sdk.subagent_reader.get_subagent_summary') as mock_get:
        mock_get.return_value = MagicMock(agent_id='mock')
        result = get_session_subagents_summary('session-uuid')

    assert len(result) == 2
    assert mock_get.call_count == 2
