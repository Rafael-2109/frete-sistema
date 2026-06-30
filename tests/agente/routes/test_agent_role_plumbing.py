"""8b passo 2: plumbing de agent_role pela cadeia de streaming.

api_chat -> _stream_chat_response -> run_async_stream -> _async_stream_sdk_client
        -> AgentClient.stream_response -> _stream_response_persistent

Cada elo aceita `agent_role` (default 'principal'). Sem isto, o papel decidido
em _resolve_agent_role morre no log e nunca chega ao pool/resume/profile. O
default 'principal' garante caminho principal byte-equivalente (callers que nao
passam agent_role permanecem identicos).
"""
import inspect

from app.agente.routes import chat as chat_mod
from app.agente.sdk.client import AgentClient


def _param(func, name):
    return inspect.signature(func).parameters.get(name)


def test_stream_chat_response_aceita_agent_role_default_principal():
    p = _param(chat_mod._stream_chat_response, 'agent_role')
    assert p is not None, "_stream_chat_response sem agent_role"
    assert p.default == 'principal'


def test_async_stream_sdk_client_aceita_agent_role_default_principal():
    p = _param(chat_mod._async_stream_sdk_client, 'agent_role')
    assert p is not None, "_async_stream_sdk_client sem agent_role"
    assert p.default == 'principal'


def test_stream_response_aceita_agent_role_default_principal():
    p = _param(AgentClient.stream_response, 'agent_role')
    assert p is not None, "stream_response sem agent_role"
    assert p.default == 'principal'


def test_stream_response_persistent_aceita_agent_role_default_principal():
    p = _param(AgentClient._stream_response_persistent, 'agent_role')
    assert p is not None, "_stream_response_persistent sem agent_role"
    assert p.default == 'principal'
