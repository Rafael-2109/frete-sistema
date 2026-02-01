"""
SDK Core - Wrapper do Claude Agent SDK.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

Suporta dois modos (controlado por feature flag USE_SDK_CLIENT):
- query(): Chamada isolada por mensagem (padrão, comportamento legado)
- ClaudeSDKClient: Canal bidirecional persistente via SessionPool

Cost tracking é feito com deduplicação por message.id.
"""

from .client import AgentClient, get_client
from .cost_tracker import CostTracker, get_cost_tracker

# SessionPool — singleton para gerenciar ClaudeSDKClient instances
# Importado condicionalmente para evitar overhead quando USE_SDK_CLIENT=false
_session_pool = None


def get_session_pool():
    """
    Retorna singleton do SessionPool.

    Criado sob demanda na primeira chamada.
    Configurado via feature flags:
    - SDK_CLIENT_MAX_POOL (default 5)
    - SDK_CLIENT_IDLE_TIMEOUT (default 300s)
    - SDK_CLIENT_CLEANUP_INTERVAL (default 60s)
    """
    global _session_pool

    if _session_pool is None:
        from ..config.feature_flags import (
            SDK_CLIENT_MAX_POOL,
            SDK_CLIENT_IDLE_TIMEOUT,
            SDK_CLIENT_CLEANUP_INTERVAL,
        )
        from .session_pool import SessionPool

        _session_pool = SessionPool(
            max_clients=SDK_CLIENT_MAX_POOL,
            idle_timeout=SDK_CLIENT_IDLE_TIMEOUT,
            cleanup_interval=SDK_CLIENT_CLEANUP_INTERVAL,
        )

    return _session_pool


__all__ = [
    'AgentClient',
    'get_client',
    'CostTracker',
    'get_cost_tracker',
    'get_session_pool',
]
