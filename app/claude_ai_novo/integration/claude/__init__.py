"""
🤖 CLAUDE MODULE - Integração Claude

Este módulo contém as integrações com Claude:
- Cliente Claude (API direto)
- Integração Claude (wrapper avançado)
- Configurações e utilitários
"""

from .claude_integration import ClaudeRealIntegration, get_claude_integration
from .claude_client import ClaudeClient

__all__ = [
    'ClaudeRealIntegration',
    'ClaudeClient',
    'get_claude_integration',
]
