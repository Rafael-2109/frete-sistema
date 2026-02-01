"""
SDK Core - Wrapper do Claude Agent SDK.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

Arquitetura: ClaudeSDKClient via SessionPool (canal bidirecional persistente).
Cost tracking é feito com deduplicação por message.id.
"""

from .client import AgentClient, get_client
from .cost_tracker import CostTracker, get_cost_tracker

# SessionPool — singleton para gerenciar ClaudeSDKClient instances
_session_pool = None

# Configuração do SessionPool (via env vars)
import os

_POOL_MAX_CLIENTS = int(os.getenv("AGENT_SDK_CLIENT_MAX_POOL", "5"))
_POOL_IDLE_TIMEOUT = int(os.getenv("AGENT_SDK_CLIENT_IDLE_TIMEOUT", "300"))
_POOL_CLEANUP_INTERVAL = int(os.getenv("AGENT_SDK_CLIENT_CLEANUP_INTERVAL", "60"))


def get_session_pool():
    """
    Retorna singleton do SessionPool.

    Criado sob demanda na primeira chamada.
    Configuração via env vars:
    - AGENT_SDK_CLIENT_MAX_POOL (default 5)
    - AGENT_SDK_CLIENT_IDLE_TIMEOUT (default 300s)
    - AGENT_SDK_CLIENT_CLEANUP_INTERVAL (default 60s)
    """
    global _session_pool

    if _session_pool is None:
        from .session_pool import SessionPool

        _session_pool = SessionPool(
            max_clients=_POOL_MAX_CLIENTS,
            idle_timeout=_POOL_IDLE_TIMEOUT,
            cleanup_interval=_POOL_CLEANUP_INTERVAL,
        )

    return _session_pool


__all__ = [
    'AgentClient',
    'get_client',
    'CostTracker',
    'get_cost_tracker',
    'get_session_pool',
]
