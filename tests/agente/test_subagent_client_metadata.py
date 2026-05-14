"""Testes para metadata enriquecido em task_started/task_progress.

P0.3: TaskProgressMessage.usage propagado em metadata.
P1.1: TaskStartedMessage.tool_use_id propagado como parent_tool_use_id.

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (5.1)
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock
import pytest

from claude_agent_sdk import (
    TaskStartedMessage,
    TaskProgressMessage,
)

from app.agente.sdk.client import AgentClient, _StreamParseState


@dataclass
class FakeUsage:
    """Simula TaskUsage TypedDict do SDK."""
    total_tokens: int = 3400
    tool_uses: int = 5
    duration_ms: int = 12000


def _new_state():
    """_StreamParseState com defaults preenchidos para teste isolado."""
    now = time.time()
    return _StreamParseState(
        tool_calls=[],
        stream_start_time=now,
        last_message_time=now,
    )


@pytest.fixture
def client():
    """AgentClient sem __init__ — para testes unitarios do parser."""
    return AgentClient.__new__(AgentClient)


def _run(coro):
    """Helper para rodar coroutine sincrono no teste."""
    return asyncio.run(coro)


def _make_task_started(tool_use_id=None, task_id='t-abc', description='desc', task_type='local_agent'):
    """Cria mock que passa isinstance(msg, TaskStartedMessage)."""
    m = MagicMock(spec=TaskStartedMessage)
    m.task_id = task_id
    m.description = description
    m.task_type = task_type
    m.tool_use_id = tool_use_id
    m.uuid = 'u-1'
    m.session_id = 's-1'
    return m


def _make_task_progress(usage=None, parent_tool_use_id=None,
                        task_id='t-abc', description='Usando Grep',
                        last_tool_name='Grep'):
    """Cria mock que passa isinstance(msg, TaskProgressMessage)."""
    m = MagicMock(spec=TaskProgressMessage)
    m.task_id = task_id
    m.description = description
    m.last_tool_name = last_tool_name
    m.usage = usage
    m.parent_tool_use_id = parent_tool_use_id
    m.uuid = 'u-2'
    m.session_id = 's-1'
    return m


# ─── TaskStartedMessage (P1.1) ───

def test_task_started_propaga_parent_tool_use_id(client):
    """P1.1: tool_use_id do TaskStartedMessage vira parent_tool_use_id no metadata."""
    msg = _make_task_started(tool_use_id='tu_xyz789')
    events = _run(client._parse_sdk_message(msg, _new_state()))
    assert len(events) == 1
    assert events[0].type == 'task_started'
    assert events[0].metadata['parent_tool_use_id'] == 'tu_xyz789'


def test_task_started_sem_tool_use_id_nao_quebra(client):
    """SDK pode nao emitir tool_use_id (forward-compat). Deve resultar em None."""
    msg = _make_task_started(tool_use_id=None)
    events = _run(client._parse_sdk_message(msg, _new_state()))
    assert events[0].metadata['parent_tool_use_id'] is None
    # Campos antigos preservados
    assert events[0].metadata['task_id'] == 't-abc'
    assert events[0].metadata['task_type'] == 'local_agent'


# ─── TaskProgressMessage (P0.3 + P1.1) ───

def test_task_progress_propaga_usage_completo(client):
    """P0.3: TaskUsage no metadata do task_progress."""
    msg = _make_task_progress(usage=FakeUsage(total_tokens=4200, duration_ms=8500))
    events = _run(client._parse_sdk_message(msg, _new_state()))
    assert len(events) == 1
    assert events[0].type == 'task_progress'
    usage = events[0].metadata['usage']
    assert usage is not None
    # Pode ser dict, dataclass, ou TypedDict — checar via getattr ou get
    tt = getattr(usage, 'total_tokens', None)
    if tt is None and isinstance(usage, dict):
        tt = usage.get('total_tokens')
    assert tt == 4200


def test_task_progress_usage_ausente_nao_quebra(client):
    """SDK pode nao popular usage (forward-compat). metadata.usage = None aceitavel."""
    msg = _make_task_progress(usage=None)
    events = _run(client._parse_sdk_message(msg, _new_state()))
    # Sem crash
    assert len(events) == 1
    assert events[0].metadata.get('usage') is None
    # Campo antigo preservado
    assert events[0].metadata['last_tool_name'] == 'Grep'


def test_task_progress_parent_tool_use_id_propagado(client):
    """P1.1: parent_tool_use_id tambem no task_progress (correlacao)."""
    msg = _make_task_progress(parent_tool_use_id='tu_xyz789')
    events = _run(client._parse_sdk_message(msg, _new_state()))
    assert events[0].metadata['parent_tool_use_id'] == 'tu_xyz789'
