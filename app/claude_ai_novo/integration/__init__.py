"""
🔗 INTEGRATION SYSTEM
Sistema de integração e processamento avançado
"""

from .advanced import get_advanced_ai_integration, AdvancedAIIntegration
from .claude import get_claude_integration, ClaudeRealIntegration
from .data_provider import get_sistema_real_data, SistemaRealData

# Classes diretas (sem funções get_*)
from .claude_client import ClaudeClient
from .query_processor import QueryProcessor
from .response_formatter import ResponseFormatter

__all__ = [
    'get_advanced_ai_integration',
    'AdvancedAIIntegration',
    'get_claude_integration',
    'ClaudeRealIntegration',
    'get_sistema_real_data',
    'SistemaRealData',
    'ClaudeClient',
    'QueryProcessor',
    'ResponseFormatter'
] 