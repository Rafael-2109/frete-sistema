"""
🔗 INTEGRATION MODULE - Sistemas de Integração

Este módulo contém todos os sistemas de integração:
- Integration Manager (orquestrador principal)
- Advanced (integração avançada)
- Claude (integração Claude)
- Data (provedor de dados)
- Processing (processamento)
"""

# Imports do manager principal
from .integration_manager import (
    IntegrationManager,
    IntegrationResult,
    integration_manager,
    get_integration_manager
)

# Imports das subpastas especializadas
from .advanced.advanced_integration import AdvancedAIIntegration
from .claude.claude_integration import ClaudeRealIntegration
from .claude.claude_client import ClaudeClient
from ..data.providers.data_provider import SistemaRealData
from ..processors.query_processor import QueryProcessor
from .processing.response_formatter import ResponseFormatter

# Exportações principais
__all__ = [
    # Manager principal
    'IntegrationManager',
    'IntegrationResult',
    'integration_manager',
    'get_integration_manager',
    
    # Sistemas especializados
    'AdvancedAIIntegration',
    'ClaudeRealIntegration',
    'ClaudeClient',
    'SistemaRealData',
    'QueryProcessor',
    'ResponseFormatter',
] 