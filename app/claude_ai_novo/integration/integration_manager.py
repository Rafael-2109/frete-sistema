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
from ..intelligence.intelligence_manager import IntelligenceManager, get_intelligence_manager

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
    🔗 GERENCIADOR PRINCIPAL DAS INTEGRAÇÕES
    
    Orquestra todos os sistemas de integração disponíveis:
    - Claude Integration (IA principal)
    - Data Provider (dados reais)  
    - Intelligence Manager (sistemas de IA)
    - Advanced Integration (IA avançada)
    - Processamento e formatação
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
        
        # Sistema de inteligência (NOVO)
        self.intelligence_manager = None
        
        # Inicializar sistemas
        self._inicializar_sistemas()
        
        logger.info("🔗 Integration Manager inicializado com sucesso!")
    
    def _inicializar_sistemas(self):
        """Inicializa todos os sistemas de integração"""
        
        # 🧠 INTELLIGENCE MANAGER (PRIORIDADE MÁXIMA)
        try:
            self.intelligence_manager = get_intelligence_manager()
            logger.info("🧠 Intelligence Manager integrado")
        except Exception as e:
            logger.error(f"❌ Erro ao integrar Intelligence Manager: {e}")
        
        # 🤖 CLAUDE INTEGRATION
        try:
            self.claude_integration = ClaudeRealIntegration()
            logger.info("🤖 Sistema de Integração Claude inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Claude Integration: {e}")
        
        # 📊 DATA PROVIDER
        try:
            self.data_provider = SistemaRealData()
            logger.info("📊 Provedor de Dados inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Data Provider: {e}")
        
        # 🚀 ADVANCED INTEGRATION
        try:
            self.advanced_integration = AdvancedAIIntegration()
            logger.info("🚀 Sistema Avançado de IA inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Sistema Avançado de IA não disponível: {e}")
        
        # 📄 RESPONSE FORMATTER
        try:
            self.response_formatter = ResponseFormatter()
            logger.info("📄 Formatador de Respostas inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Response Formatter: {e}")
        
        # ⚙️ CLAUDE CLIENT (opcional)
        try:
            # Normalmente seria inicializado com API key
            logger.debug("⚙️ Claude Client: requer configuração de API key")
        except Exception as e:
            logger.debug(f"⚙️ Claude Client não configurado: {e}")
        
        # 🔍 QUERY PROCESSOR (opcional - requer dependências)
        try:
            # Normalmente seria inicializado com dependências completas
            logger.debug("🔍 Query Processor: requer configuração completa")
        except Exception as e:
            logger.debug(f"🔍 Query Processor não configurado: {e}")
    
    def get_system_status(self) -> Dict[str, bool]:
        """
        Retorna status de todos os sistemas integrados.
        
        Returns:
            Dict com status dos sistemas
        """
        return {
            # Sistemas principais
            'claude_integration_available': self.claude_integration is not None,
            'data_provider_available': self.data_provider is not None,
            'intelligence_manager_available': self.intelligence_manager is not None,
            
            # Sistemas avançados
            'advanced_integration_available': self.advanced_integration is not None,
            'response_formatter_available': self.response_formatter is not None,
            
            # Sistemas opcionais
            'claude_client_available': self.claude_client is not None,
            'query_processor_available': self.query_processor is not None,
            
            # Status consolidado
            'core_systems_ready': all([
                self.claude_integration is not None,
                self.data_provider is not None,
                self.intelligence_manager is not None
            ])
        }
    
    def get_available_integrations(self) -> Dict[str, bool]:
        """
        Retorna lista de integrações disponíveis.
        
        Returns:
            Dict com status das integrações
        """
        return self.get_system_status()
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa consulta usando sistemas de integração.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            Resultado do processamento
        """
        try:
            # 🧠 INTELLIGENCE PREPROCESSING
            intelligence_result = None
            if self.intelligence_manager:
                intelligence_result = self.intelligence_manager.process_intelligence(query, context)
                if intelligence_result.success:
                    # Enriquecer contexto com inteligência
                    context = {**(context or {}), 'intelligence': intelligence_result.data}
            
            # 🤖 CLAUDE PROCESSING
            if self.claude_integration:
                # Verificar se método é assíncrono e garantir tipo string
                if hasattr(self.claude_integration.processar_consulta_real, '__await__'):
                    response_result = await self.claude_integration.processar_consulta_real(query, context or {})
                else:
                    response_result = self.claude_integration.processar_consulta_real(query, context or {})
                
                # Garantir que response seja sempre string
                response: str = str(response_result) if response_result is not None else "Resposta não disponível"
                
                # 🧠 INTELLIGENCE POSTPROCESSING (feedback learning)
                if self.intelligence_manager and context and context.get('user_id'):
                    self.intelligence_manager.update_conversation_context(
                        str(context['user_id']), query, response
                    )
                
                return {
                    'success': True,
                    'response': response,
                    'metadata': {
                        'source': 'claude_integration',
                        'intelligence_used': intelligence_result is not None,
                        'systems_active': list(self.get_system_status().keys())
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Claude Integration não disponível',
                    'response': 'Sistema de IA principal indisponível'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento da consulta: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': f'Erro no processamento: {str(e)}'
            }
    
    async def process_unified_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa consulta unificada com todos os sistemas integrados.
        Método esperado pelo SmartBaseAgent.
        
        Args:
            query: Consulta do usuário
            context: Contexto especializado do agente
            
        Returns:
            Resultado unificado do processamento
        """
        try:
            # Extrair informações do especialista
            agent_type = context.get('agent_type', 'generic') if context else 'generic'
            specialist_prompt = context.get('specialist_prompt', '') if context else ''
            relevance_score = context.get('relevance_score', 0.5) if context else 0.5
            
            logger.info(f"🔗 Processando consulta unificada | Agente: {agent_type} | Relevância: {relevance_score:.2f}")
            
            # 🧠 INTELLIGENCE PREPROCESSING
            intelligence_result = None
            if self.intelligence_manager:
                intelligence_result = self.intelligence_manager.process_intelligence(query, context)
                if intelligence_result.success:
                    # Enriquecer contexto com inteligência
                    context = {**(context or {}), 'intelligence': intelligence_result.data}
            
            # 🤖 CLAUDE PROCESSING - DIRETO SEM RECURSÃO
            if self.claude_integration:
                # Verificar se método é assíncrono e garantir tipo string
                if hasattr(self.claude_integration.processar_consulta_real, '__await__'):
                    response_result = await self.claude_integration.processar_consulta_real(query, context or {})
                else:
                    response_result = self.claude_integration.processar_consulta_real(query, context or {})
                
                # Garantir que response seja sempre string
                response: str = str(response_result) if response_result is not None else "Resposta não disponível"
                
                # 🧠 INTELLIGENCE POSTPROCESSING (feedback learning)
                if self.intelligence_manager and context and context.get('user_id'):
                    self.intelligence_manager.update_conversation_context(
                        str(context['user_id']), query, response
                    )
                
                return {
                    'success': True,
                    'agent_response': {
                        'response': response,
                        'agent_type': agent_type,
                        'relevance': relevance_score,
                        'confidence': 0.85,  # Alta confiança com sistema completo
                        'specialist_analysis': True,
                        'processing_mode': 'unified_integration'
                    },
                    'metadata': {
                        'source': 'claude_integration',
                        'intelligence_used': intelligence_result is not None,
                        'systems_active': list(self.get_system_status().keys()),
                        'specialist_context': {
                            'agent_type': agent_type,
                            'relevance_score': relevance_score,
                            'has_specialist_prompt': bool(specialist_prompt)
                        }
                    }
                }
            else:
                return {
                    'success': False,
                    'agent_response': 'Claude Integration não disponível',
                    'error': 'Sistema de IA principal indisponível',
                    'fallback_response': f"Agente {agent_type}: Processamento indisponível"
                }
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento unificado: {e}")
            return {
                'success': False,
                'agent_response': f'Erro no sistema integrado: {str(e)}',
                'error': str(e),
                'fallback_response': 'Sistema de integração indisponível'
            }
    
    def get_module(self, module_name: str) -> Any:
        """
        Obtém acesso direto a um módulo específico.
        
        Args:
            module_name: Nome do módulo
            
        Returns:
            Instância do módulo ou None
        """
        modules = {
            'claude_integration': self.claude_integration,
            'data_provider': self.data_provider,
            'intelligence_manager': self.intelligence_manager,
            'advanced_integration': self.advanced_integration,
            'response_formatter': self.response_formatter,
            'claude_client': self.claude_client,
            'query_processor': self.query_processor
        }
        return modules.get(module_name)

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