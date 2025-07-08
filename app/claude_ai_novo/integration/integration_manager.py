#!/usr/bin/env python3
"""
🔗 INTEGRATION MANAGER - Gerenciador de Integrações
Orquestrador principal dos sistemas de integração
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

# Imports dos sistemas especializados
from .advanced.advanced_integration import AdvancedAIIntegration
from .claude.claude_integration import ClaudeRealIntegration
from .claude.claude_client import ClaudeClient
from ..data.providers.data_provider import SistemaRealData
from ..processors.query_processor import QueryProcessor
from .processing.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)

@dataclass
class IntegrationResult:
    """Resultado processado pelos sistemas de integração"""
    success: bool
    data: Dict[str, Any]
    response: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    errors: List[str] = field(default_factory=list)

class IntegrationManager:
    """
    Gerenciador principal das integrações.
    
    Orquestra todos os sistemas de integração disponíveis.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de integrações"""
        
        # Sistemas de integração
        self.claude_client = None
        self.claude_integration = None
        self.advanced_integration = None
        self.data_provider = None
        self.query_processor = None
        self.response_formatter = None
        
        # Inicializar sistemas
        self._inicializar_sistemas()
        
        logger.info("🔗 Integration Manager inicializado com sucesso!")
    
    def _inicializar_sistemas(self):
        """Inicializa todos os sistemas de integração"""
        
        # Inicializar Claude Client
        try:
            # Normalmente seria inicializado com API key
            # self.claude_client = ClaudeClient(api_key="...")
            logger.warning("⚠️ Cliente Claude não disponível: ClaudeClient.__init__() missing 1 required positional argument: 'api_key'")
        except Exception as e:
            logger.warning(f"⚠️ Cliente Claude não disponível: {e}")
        
        # Inicializar Claude Integration
        try:
            self.claude_integration = ClaudeRealIntegration()
            logger.info("🤖 Sistema de Integração Claude inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Claude Integration: {e}")
        
        # Inicializar Data Provider
        try:
            self.data_provider = SistemaRealData()
            logger.info("📊 Provedor de Dados inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Data Provider: {e}")
        
        # Inicializar Query Processor
        try:
            # Normalmente seria inicializado com dependências
            # self.query_processor = QueryProcessor(claude_client, context_manager, learning_system)
            logger.warning("⚠️ Processador de Consultas não disponível: QueryProcessor.__init__() missing 3 required positional arguments: 'claude_client', 'context_manager', and 'learning_system'")
        except Exception as e:
            logger.warning(f"⚠️ Processador de Consultas não disponível: {e}")
        
        # Inicializar Response Formatter
        try:
            self.response_formatter = ResponseFormatter()
            logger.info("📄 Formatador de Respostas inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Response Formatter: {e}")
    
    def get_available_integrations(self) -> Dict[str, bool]:
        """
        Retorna lista de integrações disponíveis.
        
        Returns:
            Dict com status das integrações
        """
        return {
            'claude_client': self.claude_client is not None,
            'claude_integration': self.claude_integration is not None,
            'advanced_integration': self.advanced_integration is not None,
            'data_provider': self.data_provider is not None,
            'query_processor': self.query_processor is not None,
            'response_formatter': self.response_formatter is not None
        }
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa consulta usando sistemas de integração.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            Resultado do processamento
        """
        try:
            # Usar Claude Integration se disponível
            if self.claude_integration:
                return self.claude_integration.processar_consulta_real(query, context or {})
            else:
                return {
                    'success': False,
                    'error': 'Nenhum sistema de integração disponível',
                    'response': 'Sistema de integração indisponível'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento da consulta: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': f'Erro no processamento: {str(e)}'
            }

# Instância global
integration_manager = None

def get_integration_manager() -> IntegrationManager:
    """Retorna instância do gerenciador de integrações"""
    global integration_manager
    
    if integration_manager is None:
        integration_manager = IntegrationManager()
    
    return integration_manager


# Exportações principais
__all__ = [
    'IntegrationManager',
    'IntegrationResult',
    'integration_manager',
    'get_integration_manager'
] 