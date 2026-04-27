"""
SDK Core - Wrapper do Claude Agent SDK.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

Arquitetura v3: ClaudeSDKClient persistente via client_pool.py.
Cost tracking é feito com deduplicação por message.id.
"""

from .client import AgentClient, get_client
from .cost_tracker import CostTracker, get_cost_tracker
from .client_pool import (
    submit_coroutine,
    get_or_create_client,
    disconnect_client,
    get_pooled_client,
    get_pool_status,
    shutdown_pool,
    PooledClient,
)
from .shutdown_state import (
    is_interpreter_shutting_down,
    is_shutdown_error,
    register_shutdown_handler,
)

__all__ = [
    'AgentClient',
    'get_client',
    'CostTracker',
    'get_cost_tracker',
    # Pool (ativo por default — flag USE_PERSISTENT_SDK_CLIENT)
    'submit_coroutine',
    'get_or_create_client',
    'disconnect_client',
    'get_pooled_client',
    'get_pool_status',
    'shutdown_pool',
    'PooledClient',
    # Shutdown state — suprime Sentry capture durante atexit (PP/PN/PM)
    'is_interpreter_shutting_down',
    'is_shutdown_error',
    'register_shutdown_handler',
]
