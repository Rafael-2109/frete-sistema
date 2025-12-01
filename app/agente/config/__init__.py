"""
Configurações do Agente.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/permissions
"""

from .settings import AgentSettings, get_settings
from .permissions import can_use_tool

__all__ = [
    'AgentSettings',
    'get_settings',
    'can_use_tool',
]
