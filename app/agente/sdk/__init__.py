"""
SDK Core - Wrapper do Claude Agent SDK.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

Arquitetura v2: query() + resume (self-contained, sem estado persistente).
Cost tracking é feito com deduplicação por message.id.
"""

from .client import AgentClient, get_client
from .cost_tracker import CostTracker, get_cost_tracker

__all__ = [
    'AgentClient',
    'get_client',
    'CostTracker',
    'get_cost_tracker',
]
