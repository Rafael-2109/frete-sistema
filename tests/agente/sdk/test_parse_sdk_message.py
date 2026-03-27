"""
Unit Tests — _parse_sdk_message()

Tests the SDK message parsing method that converts raw SDK messages
into StreamEvent objects while mutating _StreamParseState.

Location under test: app/agente/sdk/client.py:1446
Run: pytest tests/agente/sdk/test_parse_sdk_message.py -v -m "unit and sdk_client"

Strategy: Since _parse_sdk_message uses isinstance() checks against SDK types,
we create lightweight stub classes that share the same identity as the ones
imported into the client module. We patch the module-level names so that
isinstance(stub_instance, PatchedClass) evaluates to True.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Stub classes for isinstance patching ────────────────────────────
# These are simple classes whose instances will pass isinstance() checks
# after we patch the corresponding names in app.agente.sdk.client.

class _StubSystemMessage:
    def __init__(self, data=None):
        self.data = data or {}


class _StubAssistantMessage:
    def __init__(self, content=None, usage=None, error=None, msg_id=None):
        self.content = content or []
        self.usage = usage
        self.error = error
        self.id = msg_id


class _StubUserMessage:
    def __init__(self, content=None):
        self.content = content or []


class _StubResultMessage:
    def __init__(self, subtype='end_turn', session_id=None, result=None,
                 is_error=False, usage=None, total_cost_usd=0.01,
                 num_turns=1, duration_ms=1000, stop_reason=None,
                 structured_output=None):
        self.subtype = subtype
        self.session_id = session_id
        self.result = result
        self.is_error = is_error
        self.usage = usage
        self.total_cost_usd = total_cost_usd
        self.num_turns = num_turns
        self.duration_ms = duration_ms
        self.stop_reason = stop_reason or subtype
        self.structured_output = structured_output


class _StubTextBlock:
    def __init__(self, text='Hello'):
        self.text = text


class _StubThinkingBlock:
    def __init__(self, thinking='Let me think...'):
        self.thinking = thinking


class _StubToolUseBlock:
    def __init__(self, name='consultar_sql', block_id='tool_123', block_input=None):
        self.name = name
        self.id = block_id
        self.input = block_input or {}


class _StubToolResultBlock:
    def __init__(self, tool_use_id='tool_123', content='result', is_error=False):
        self.tool_use_id = tool_use_id
        self.content = content
        self.is_error = is_error


class _StubTaskStartedMessage:
    def __init__(self, description='Analyzing...', task_id='task_abc', task_type='general'):
        self.description = description
        self.task_id = task_id
        self.task_type = task_type


class _StubTaskProgressMessage:
    def __init__(self, description='Processing...', task_id='task_abc', last_tool_name='Read'):
        self.description = description
        self.task_id = task_id
        self.last_tool_name = last_tool_name


class _StubTaskNotificationMessage:
    def __init__(self, summary='Done.', status='completed', task_id='task_abc', usage=None):
        self.summary = summary
        self.status = status
        self.task_id = task_id
        self.usage = usage


class _StubRateLimitEvent:
    def __init__(self, status='allowed_warning', utilization=0.85,
                 resets_at='2026-03-27T15:00:00Z', rate_limit_type='tokens'):
        self.rate_limit_info = MagicMock()
        self.rate_limit_info.status = status
        self.rate_limit_info.utilization = utilization
        self.rate_limit_info.resets_at = resets_at
        self.rate_limit_info.rate_limit_type = rate_limit_type


# ─── Patch map: module-level names to stub classes ───────────────────
_SDK_TYPE_PATCHES = {
    'app.agente.sdk.client.SystemMessage': _StubSystemMessage,
    'app.agente.sdk.client.AssistantMessage': _StubAssistantMessage,
    'app.agente.sdk.client.UserMessage': _StubUserMessage,
    'app.agente.sdk.client.ResultMessage': _StubResultMessage,
    'app.agente.sdk.client.TextBlock': _StubTextBlock,
    'app.agente.sdk.client.ThinkingBlock': _StubThinkingBlock,
    'app.agente.sdk.client.ToolUseBlock': _StubToolUseBlock,
    'app.agente.sdk.client.ToolResultBlock': _StubToolResultBlock,
    'app.agente.sdk.client.TaskStartedMessage': _StubTaskStartedMessage,
    'app.agente.sdk.client.TaskProgressMessage': _StubTaskProgressMessage,
    'app.agente.sdk.client.TaskNotificationMessage': _StubTaskNotificationMessage,
    'app.agente.sdk.client.RateLimitEvent': _StubRateLimitEvent,
}


# ─── Helpers ─────────────────────────────────────────────────────────

def _run_parse(client, message, state):
    """Run the async _parse_sdk_message in a new event loop."""
    return asyncio.run(client._parse_sdk_message(message, state))


def _make_state(**overrides):
    """Create a fresh _StreamParseState with optional overrides."""
    from app.agente.sdk.client import _StreamParseState
    state = _StreamParseState()
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def agent_client(app):
    """AgentClient instance inside app context with SDK types patched."""
    with app.app_context():
        from app.agente.sdk.client import AgentClient
        client = AgentClient()
        yield client


@pytest.fixture(autouse=True)
def patch_sdk_types():
    """Patch all SDK type references so isinstance checks pass with stubs."""
    with patch.multiple('app.agente.sdk.client', **{
        k.split('.')[-1]: v for k, v in _SDK_TYPE_PATCHES.items()
    }):
        yield


@pytest.fixture(autouse=True)
def patch_self_correct():
    """Disable _self_correct_response to avoid external API calls in tests."""
    with patch(
        'app.agente.sdk.client.AgentClient._self_correct_response',
        new_callable=AsyncMock,
        return_value=None,
    ):
        yield


# =====================================================================
# TESTS
# =====================================================================

@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseSystemMessage:
    """SystemMessage handling."""

    def test_system_message_extracts_session_id(self, agent_client):
        """SystemMessage with session_id in data sets state.result_session_id
        and returns no events."""
        state = _make_state()
        msg = _StubSystemMessage(data={'session_id': 'sdk-sess-abc123'})

        events = _run_parse(agent_client, msg, state)

        assert events == []
        assert state.result_session_id == 'sdk-sess-abc123'

    def test_system_message_without_session_id(self, agent_client):
        """SystemMessage without session_id does not set result_session_id."""
        state = _make_state()
        msg = _StubSystemMessage(data={'other_key': 'value'})

        events = _run_parse(agent_client, msg, state)

        assert events == []
        assert state.result_session_id is None


@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseAssistantMessage:
    """AssistantMessage handling (text, thinking, tool_use blocks)."""

    def test_assistant_text_block(self, agent_client):
        """AssistantMessage with a TextBlock produces StreamEvent(type='text')
        and appends text to state.full_text."""
        state = _make_state()
        text_block = _StubTextBlock(text='Olá, como posso ajudar?')
        msg = _StubAssistantMessage(content=[text_block])

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'text'
        assert events[0].content == 'Olá, como posso ajudar?'
        assert state.full_text == 'Olá, como posso ajudar?'

    def test_assistant_thinking_block(self, agent_client):
        """AssistantMessage with ThinkingBlock produces StreamEvent(type='thinking')."""
        state = _make_state()
        thinking_block = _StubThinkingBlock(thinking='Preciso analisar os dados...')
        msg = _StubAssistantMessage(content=[thinking_block])

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'thinking'
        assert events[0].content == 'Preciso analisar os dados...'

    def test_assistant_tool_use_block(self, agent_client):
        """AssistantMessage with ToolUseBlock produces StreamEvent(type='tool_call')
        and appends to state.tool_calls."""
        state = _make_state()
        tool_block = _StubToolUseBlock(
            name='mcp__sql__consultar_sql',
            block_id='toolu_001',
            block_input={'query': 'SELECT 1'}
        )
        msg = _StubAssistantMessage(content=[tool_block])

        events = _run_parse(agent_client, msg, state)

        # Should have tool_call event (possibly also a todos event, but not here)
        tool_events = [e for e in events if e.type == 'tool_call']
        assert len(tool_events) == 1
        assert tool_events[0].content == 'mcp__sql__consultar_sql'
        assert tool_events[0].metadata['tool_id'] == 'toolu_001'
        assert tool_events[0].metadata['input'] == {'query': 'SELECT 1'}

        # State mutation
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0].name == 'mcp__sql__consultar_sql'
        assert state.tool_calls[0].id == 'toolu_001'
        assert state.had_tool_between_texts is True

    def test_text_separator_after_tool(self, agent_client):
        """When state.had_tool_between_texts is True and full_text is non-empty,
        text is prefixed with newlines separator."""
        state = _make_state(
            full_text='Primeira parte.',
            had_tool_between_texts=True,
        )
        text_block = _StubTextBlock(text='Segunda parte.')
        msg = _StubAssistantMessage(content=[text_block])

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'text'
        assert events[0].content == '\n\nSegunda parte.'
        assert state.full_text == 'Primeira parte.\n\nSegunda parte.'
        assert state.had_tool_between_texts is False

    def test_token_accumulation_dict_usage(self, agent_client):
        """AssistantMessage with dict usage updates state token counts."""
        state = _make_state()
        msg = _StubAssistantMessage(
            content=[],
            usage={'input_tokens': 1500, 'output_tokens': 300},
        )

        _run_parse(agent_client, msg, state)

        assert state.input_tokens == 1500
        assert state.output_tokens == 300

    def test_token_accumulation_object_usage(self, agent_client):
        """AssistantMessage with object-style usage updates state token counts."""
        state = _make_state()
        usage_obj = MagicMock()
        usage_obj.input_tokens = 2000
        usage_obj.output_tokens = 450
        msg = _StubAssistantMessage(content=[], usage=usage_obj)

        _run_parse(agent_client, msg, state)

        assert state.input_tokens == 2000
        assert state.output_tokens == 450


@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseUserMessage:
    """UserMessage handling (tool results)."""

    def test_user_message_tool_result(self, agent_client):
        """UserMessage with ToolResultBlock produces StreamEvent(type='tool_result')."""
        state = _make_state()
        # Pre-populate tool_calls so tool_name lookup works
        from app.agente.sdk.client import ToolCall
        state.tool_calls.append(ToolCall(
            id='toolu_001',
            name='mcp__sql__consultar_sql',
            input={'query': 'SELECT 1'},
        ))
        state.current_tool_start_time = time.time() - 0.5
        state.current_tool_name = 'mcp__sql__consultar_sql'

        result_block = _StubToolResultBlock(
            tool_use_id='toolu_001',
            content='[{"count": 42}]',
            is_error=False,
        )
        msg = _StubUserMessage(content=[result_block])

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'tool_result'
        assert events[0].metadata['tool_name'] == 'mcp__sql__consultar_sql'
        assert events[0].metadata['is_error'] is False
        assert events[0].metadata['tool_use_id'] == 'toolu_001'
        assert events[0].metadata['duration_ms'] > 0
        # Tool timing reset
        assert state.current_tool_start_time is None

    def test_user_message_tool_result_error(self, agent_client):
        """UserMessage with is_error=True ToolResultBlock sets is_error in metadata."""
        state = _make_state()
        from app.agente.sdk.client import ToolCall
        state.tool_calls.append(ToolCall(
            id='toolu_err',
            name='Read',
            input={'file_path': '/nonexistent'},
        ))

        result_block = _StubToolResultBlock(
            tool_use_id='toolu_err',
            content='File does not exist: /nonexistent',
            is_error=True,
        )
        msg = _StubUserMessage(content=[result_block])

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'tool_result'
        assert events[0].metadata['is_error'] is True


@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseResultMessage:
    """ResultMessage handling (done, interrupt)."""

    def test_result_message_end_turn(self, agent_client):
        """ResultMessage with end_turn emits StreamEvent(type='done')
        and sets state.done_emitted=True."""
        state = _make_state(full_text='Resposta completa.')
        msg = _StubResultMessage(
            subtype='end_turn',
            session_id='final-sdk-session-id',
            result='Resposta completa.',
            usage={'input_tokens': 500, 'output_tokens': 200},
            total_cost_usd=0.005,
            stop_reason='end_turn',
        )

        events = _run_parse(agent_client, msg, state)

        done_events = [e for e in events if e.type == 'done']
        assert len(done_events) == 1
        done = done_events[0]
        assert done.content['text'] == 'Resposta completa.'
        assert done.content['session_id'] == 'final-sdk-session-id'
        assert done.content['input_tokens'] == 500
        assert done.content['output_tokens'] == 200
        assert done.content['interrupted'] is False
        assert done.content['stop_reason'] == 'end_turn'
        assert state.done_emitted is True
        assert state.result_session_id == 'final-sdk-session-id'

    def test_result_message_interrupted(self, agent_client):
        """ResultMessage with subtype='interrupted' emits StreamEvent(type='interrupt_ack')."""
        state = _make_state(full_text='Parcial...')
        msg = _StubResultMessage(
            subtype='interrupted',
            session_id='int-session-id',
            result=None,
            is_error=False,
            usage=None,
            stop_reason='interrupted',
        )

        events = _run_parse(agent_client, msg, state)

        interrupt_events = [e for e in events if e.type == 'interrupt_ack']
        assert len(interrupt_events) == 1
        assert interrupt_events[0].content == 'Operação interrompida pelo usuário'

        # Should also emit done
        done_events = [e for e in events if e.type == 'done']
        assert len(done_events) == 1
        assert done_events[0].content['interrupted'] is True
        assert state.done_emitted is True

    def test_done_not_duplicated(self, agent_client):
        """When state.done_emitted=True, a second ResultMessage does NOT
        emit another done event."""
        state = _make_state(done_emitted=True, full_text='Already done.')
        msg = _StubResultMessage(
            subtype='end_turn',
            session_id='dup-session',
            result='Already done.',
            usage=None,
        )

        events = _run_parse(agent_client, msg, state)

        done_events = [e for e in events if e.type == 'done']
        assert len(done_events) == 0
        interrupt_events = [e for e in events if e.type == 'interrupt_ack']
        assert len(interrupt_events) == 0


@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseTaskMessages:
    """Task messages for subagent observability."""

    def test_task_started_message(self, agent_client):
        """TaskStartedMessage produces StreamEvent(type='task_started')
        with task_id and task_type in metadata."""
        state = _make_state()
        msg = _StubTaskStartedMessage(
            description='Analisando pedido VCD123',
            task_id='task_xyz789',
            task_type='analista-carteira',
        )

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'task_started'
        assert events[0].content == 'Analisando pedido VCD123'
        assert events[0].metadata['task_id'] == 'task_xyz789'
        assert events[0].metadata['task_type'] == 'analista-carteira'

    def test_task_progress_message(self, agent_client):
        """TaskProgressMessage produces StreamEvent(type='task_progress')
        with task_id and last_tool_name in metadata."""
        state = _make_state()
        msg = _StubTaskProgressMessage(
            description='Consultando estoque...',
            task_id='task_xyz789',
            last_tool_name='mcp__sql__consultar_sql',
        )

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'task_progress'
        assert events[0].content == 'Consultando estoque...'
        assert events[0].metadata['task_id'] == 'task_xyz789'
        assert events[0].metadata['last_tool_name'] == 'mcp__sql__consultar_sql'

    def test_task_notification_message(self, agent_client):
        """TaskNotificationMessage produces StreamEvent(type='task_notification')
        with task_id, status, and usage in metadata."""
        state = _make_state()
        usage_data = {'input_tokens': 800, 'output_tokens': 150}
        msg = _StubTaskNotificationMessage(
            summary='Analise concluida: 3 pedidos P1.',
            status='completed',
            task_id='task_xyz789',
            usage=usage_data,
        )

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'task_notification'
        assert events[0].content == 'Analise concluida: 3 pedidos P1.'
        assert events[0].metadata['task_id'] == 'task_xyz789'
        assert events[0].metadata['status'] == 'completed'
        assert events[0].metadata['usage'] == usage_data


@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseRateLimitEvent:
    """RateLimitEvent handling."""

    def test_rate_limit_event(self, agent_client):
        """RateLimitEvent produces StreamEvent(type='rate_limit')
        with status, utilization, resets_at, and rate_limit_type."""
        state = _make_state()
        msg = _StubRateLimitEvent(
            status='allowed_warning',
            utilization=0.92,
            resets_at='2026-03-27T16:30:00Z',
            rate_limit_type='tokens',
        )

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].type == 'rate_limit'
        assert events[0].content == ''
        assert events[0].metadata['status'] == 'allowed_warning'
        assert events[0].metadata['utilization'] == 0.92
        assert events[0].metadata['resets_at'] == '2026-03-27T16:30:00Z'
        assert events[0].metadata['rate_limit_type'] == 'tokens'

    def test_rate_limit_rejected(self, agent_client):
        """RateLimitEvent with status='rejected' is correctly captured."""
        state = _make_state()
        msg = _StubRateLimitEvent(
            status='rejected',
            utilization=1.0,
            resets_at='2026-03-27T17:00:00Z',
            rate_limit_type='requests',
        )

        events = _run_parse(agent_client, msg, state)

        assert len(events) == 1
        assert events[0].metadata['status'] == 'rejected'
        assert events[0].metadata['rate_limit_type'] == 'requests'


@pytest.mark.unit
@pytest.mark.sdk_client
class TestParseDiagnostics:
    """Timing diagnostics and state tracking."""

    def test_first_message_updates_timing(self, agent_client):
        """First message sets first_message_logged flag."""
        state = _make_state()
        assert state.first_message_logged is False

        msg = _StubSystemMessage(data={})
        _run_parse(agent_client, msg, state)

        assert state.first_message_logged is True

    def test_unknown_message_returns_empty(self, agent_client):
        """An unrecognized message type returns empty list without errors."""
        state = _make_state()

        # A plain object that won't match any isinstance check
        class _UnknownMsg:
            pass

        msg = _UnknownMsg()
        events = _run_parse(agent_client, msg, state)

        assert events == []
