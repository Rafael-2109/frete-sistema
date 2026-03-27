"""
Fixtures compartilhadas para testes do SDK client.

Fornece mocks de mensagens SDK, setup/teardown do pool,
e utilitarios para coleta de StreamEvents.
"""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ['TESTING'] = 'true'


# ─── pytest markers ────────────────────────────────────────────────
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Pure unit tests, no API, no DB")
    config.addinivalue_line("markers", "integration: Integration tests, may use Flask, no external API")
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring real Claude API")
    config.addinivalue_line("markers", "sdk_client: Tests related to SDK client migration")


# ─── App fixture ────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Flask app para testes que precisam de app_context."""
    from app import create_app
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    return app


# ─── Mock SDK Messages ──────────────────────────────────────────────

@pytest.fixture
def mock_sdk_messages():
    """Factory de mensagens SDK mockadas.

    Retorna dict com funcoes que criam cada tipo de mensagem
    sem depender de imports reais do claude_agent_sdk.
    """
    def _make_system_message(session_id='test-sdk-session-123', **kwargs):
        msg = MagicMock()
        msg.__class__.__name__ = 'SystemMessage'
        msg.data = {'session_id': session_id, **kwargs}
        # Para isinstance checks no _parse_sdk_message
        return msg

    def _make_assistant_message(content_blocks=None, usage=None, error=None, msg_id=None):
        msg = MagicMock()
        msg.__class__.__name__ = 'AssistantMessage'
        msg.content = content_blocks or []
        msg.usage = usage
        msg.error = error
        msg.id = msg_id
        return msg

    def _make_text_block(text='Hello'):
        block = MagicMock()
        block.__class__.__name__ = 'TextBlock'
        block.text = text
        return block

    def _make_thinking_block(thinking='Let me think...'):
        block = MagicMock()
        block.__class__.__name__ = 'ThinkingBlock'
        block.thinking = thinking
        return block

    def _make_tool_use_block(name='consultar_sql', tool_id='tool_123', tool_input=None):
        block = MagicMock()
        block.__class__.__name__ = 'ToolUseBlock'
        block.name = name
        block.id = tool_id
        block.input = tool_input or {}
        return block

    def _make_user_message(content_blocks=None):
        msg = MagicMock()
        msg.__class__.__name__ = 'UserMessage'
        msg.content = content_blocks or []
        return msg

    def _make_tool_result_block(tool_use_id='tool_123', content='result', is_error=False):
        block = MagicMock()
        block.__class__.__name__ = 'ToolResultBlock'
        block.tool_use_id = tool_use_id
        block.content = content
        block.is_error = is_error
        return block

    def _make_result_message(subtype='end_turn', session_id=None, duration_ms=1000,
                             input_tokens=100, output_tokens=50, num_turns=1,
                             total_cost_usd=0.01, stop_reason=None):
        msg = MagicMock()
        msg.__class__.__name__ = 'ResultMessage'
        msg.subtype = subtype
        msg.session_id = session_id
        msg.duration_ms = duration_ms
        msg.input_tokens = input_tokens
        msg.output_tokens = output_tokens
        msg.num_turns = num_turns
        msg.total_cost_usd = total_cost_usd
        msg.stop_reason = stop_reason or 'end_turn'
        return msg

    def _make_task_started_message(description='Analyzing...', task_id='task_abc', task_type='general'):
        msg = MagicMock()
        msg.__class__.__name__ = 'TaskStartedMessage'
        msg.description = description
        msg.task_id = task_id
        msg.task_type = task_type
        return msg

    def _make_task_progress_message(description='Processing...', task_id='task_abc', last_tool_name='Read'):
        msg = MagicMock()
        msg.__class__.__name__ = 'TaskProgressMessage'
        msg.description = description
        msg.task_id = task_id
        msg.last_tool_name = last_tool_name
        return msg

    def _make_task_notification_message(summary='Done.', status='completed', task_id='task_abc', usage=None):
        msg = MagicMock()
        msg.__class__.__name__ = 'TaskNotificationMessage'
        msg.summary = summary
        msg.status = status
        msg.task_id = task_id
        msg.usage = usage
        return msg

    def _make_rate_limit_event(status='allowed_warning', utilization=0.85, resets_at='2026-03-27T15:00:00Z',
                                rate_limit_type='tokens'):
        msg = MagicMock()
        msg.__class__.__name__ = 'RateLimitEvent'
        msg.rate_limit_info = MagicMock()
        msg.rate_limit_info.status = status
        msg.rate_limit_info.utilization = utilization
        msg.rate_limit_info.resets_at = resets_at
        msg.rate_limit_info.rate_limit_type = rate_limit_type
        return msg

    return {
        'system': _make_system_message,
        'assistant': _make_assistant_message,
        'text_block': _make_text_block,
        'thinking_block': _make_thinking_block,
        'tool_use_block': _make_tool_use_block,
        'user': _make_user_message,
        'tool_result_block': _make_tool_result_block,
        'result': _make_result_message,
        'task_started': _make_task_started_message,
        'task_progress': _make_task_progress_message,
        'task_notification': _make_task_notification_message,
        'rate_limit': _make_rate_limit_event,
    }


# ─── Pool setup/teardown ────────────────────────────────────────────

@pytest.fixture
def pool_reset():
    """Reset do estado global do pool entre testes.

    DEVE ser usado por qualquer teste que interage com client_pool.
    """
    import app.agente.sdk.client_pool as cp

    yield

    # Restaurar estado — shutdown se necessario
    if cp._pool_initialized and cp._sdk_loop and not cp._sdk_loop.is_closed():
        try:
            cp.shutdown_pool()
        except Exception:
            pass

    cp._registry.clear()
    cp._pool_initialized = False
    cp._shutdown_requested = False
    cp._sdk_loop = None
    cp._sdk_loop_thread = None


@pytest.fixture
def mock_claude_sdk_client():
    """Mock do ClaudeSDKClient com metodos async."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.query = AsyncMock()
    client.interrupt = AsyncMock()
    client.set_model = AsyncMock()
    client.set_permission_mode = AsyncMock()

    # Mock receive_response como async generator vazio
    async def _empty_receive():
        return
        yield  # noqa: unreachable - necessario para async generator protocol

    client.receive_response = _empty_receive

    # Mock transport para force_kill tests
    client._transport = MagicMock()
    client._transport.close = AsyncMock()
    client._transport._process = MagicMock()
    client._transport._process.returncode = None

    return client


# ─── Utilitarios ─────────────────────────────────────────────────────

def collect_events_by_type(events):
    """Agrupa lista de StreamEvent por tipo.

    Returns:
        Dict[str, List[StreamEvent]]
    """
    result = {}
    for event in events:
        event_type = event.type
        if event_type not in result:
            result[event_type] = []
        result[event_type].append(event)
    return result
