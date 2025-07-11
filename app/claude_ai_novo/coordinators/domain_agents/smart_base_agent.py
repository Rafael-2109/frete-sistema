#!/usr/bin/env python3
"""
🤖 SMART BASE AGENT - Agente Base Inteligente

Agente base especializado com foco em conhecimento de domínio específico.
Responsabilidades:
- Conhecimento específico do domínio
- Análise de relevância especializada  
- Resumo de dados especializados
- Integração com IntegrationManager para recursos pesados
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from ...utils.agent_types import AgentType
from app.claude_ai_novo.coordinators.domain_agents.base_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class SmartBaseAgent(BaseSpecialistAgent):
    """
    Agente base inteligente focado em especialização de domínio.
    
    RESPONSABILIDADES:
    ✅ Conhecimento específico do domínio
    ✅ Análise de relevância especializada
    ✅ Resumo de dados do domínio
    ✅ Integração com sistema central via IntegrationManager
    
    NÃO RESPONSÁVEL POR:
    ❌ Gerenciamento de recursos pesados (Claude, Cache, ML Models)
    ❌ Sistemas de intelligence (delegado ao IntelligenceManager)
    ❌ Orquestração geral (delegado ao IntegrationManager)
    """
    
    def __init__(self, agent_type: AgentType, claude_client=None):
        # Inicializar capacidades BÁSICAS
        self._inicializar_capacidades_basicas()
        
        # Chamar super() após inicialização básica
        super().__init__(agent_type, claude_client)
        
        # Configurar logging específico do agente
        self.logger_estruturado = logging.getLogger(f"agent.{self.agent_type.value}")
        
        logger.info(f"✅ {self.agent_type.value}: SmartBaseAgent inicializado (modo especialista)")

    def _inicializar_capacidades_basicas(self):
        """Inicializa apenas capacidades básicas para especialização"""
        
        # Flags básicas (sem recursos pesados)
        self.tem_integration_manager = False
        self.tem_dados_reais = False
        self.tem_claude_real = False
        
        # Tentar conectar ao IntegrationManager (recurso central)
        self._conectar_integration_manager()
    
    def _conectar_integration_manager(self):
        """Conecta ao IntegrationManager para delegar recursos pesados"""
        try:
            from app.claude_ai_novo.integration.integration_manager import get_integration_manager
            
            self.integration_manager = get_integration_manager()
            self.tem_integration_manager = self.integration_manager is not None
            
            if self.tem_integration_manager:
                # Verificar recursos disponíveis via IntegrationManager
                status = self.integration_manager.get_system_status()
                self.tem_dados_reais = status.get('data_provider_available', False)
                self.tem_claude_real = status.get('claude_integration_available', False)
                
                logger.info(f"✅ {self.agent_type.value}: Conectado ao IntegrationManager")
                logger.info(f"   📊 Dados reais: {self.tem_dados_reais}")
                logger.info(f"   🤖 Claude real: {self.tem_claude_real}")
            else:
                logger.warning(f"⚠️ {self.agent_type.value}: IntegrationManager não disponível")
                
        except Exception as e:
            self.integration_manager = None
            self.tem_integration_manager = False
            logger.warning(f"⚠️ {self.agent_type.value}: Erro ao conectar IntegrationManager: {e}")

    def _load_specialist_prompt(self) -> str:
        """System prompt genérico - cada agente especializado deve sobrescrever"""
        return f"""
Você é um agente especialista em {self.agent_type.value} do sistema de fretes.

RESPONSABILIDADES:
1. Analisar consultas específicas do seu domínio
2. Fornecer respostas especializadas e precisas
3. Aplicar conhecimento especializado no seu domínio
4. Ser direto e profissional
5. Cite números específicos quando possível

RESPONDA SEMPRE EM PORTUGUÊS.
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento básico - cada agente especializado deve sobrescrever com seu conhecimento específico"""
        
        # Conhecimento básico genérico apenas para fallback
        # Cada agente especializado deve sobrescrever este método
        return {
            'tipo_agente': self.agent_type.value,
            'sistema': 'frete_sistema',
            'capacidades': 'especialista_dominio',
            'nota': 'Conhecimento específico deve ser implementado no agente especializado'
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave básicas - cada agente especializado deve sobrescrever com suas palavras específicas"""
        
        # Keywords básicas apenas para fallback
        # Cada agente especializado deve sobrescrever este método
        return [
            'sistema', 'dados', 'informação', 'relatório', 'análise', 'consulta'
        ]

    async def analyze(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Análise especializada focada no domínio específico
        
        Fluxo:
        1. Log da consulta
        2. Delegar para IntegrationManager se disponível
        3. Fallback para análise básica
        """
        try:
            # 📊 LOG ESTRUTURADO DA CONSULTA
            self._log_consulta_estruturada(query, context)
            
            # 🎯 DELEGAR PARA INTEGRATION MANAGER (se disponível)
            if self.tem_integration_manager:
                return await self._delegar_para_integration_manager(query, context)
            
            # 🔄 FALLBACK PARA ANÁLISE BÁSICA
            else:
                return await self._analise_basica_especializada(query, context)
            
        except Exception as e:
            logger.error(f"❌ Erro no SmartBaseAgent {self.agent_type.value}: {e}")
            # Fallback seguro
            return await super().analyze(query, context)

    async def _delegar_para_integration_manager(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Delega processamento para IntegrationManager com contexto especializado"""
        try:
            # Enriquecer contexto com informações do especialista
            context_especializado = {
                **context,
                'agent_type': self.agent_type.value,
                'domain_knowledge': self._load_domain_knowledge(),
                'domain_keywords': self._get_domain_keywords(),
                'specialist_prompt': self._load_specialist_prompt(),
                'relevance_score': self._calculate_relevance(query)
            }
            
            # Processar via IntegrationManager (MÉTODO ASSÍNCRONO)
            resultado = await self.integration_manager.process_unified_query(query, context_especializado)
            
            # Extrair resposta do agente se estiver no formato correto
            if isinstance(resultado, dict) and 'agent_response' in resultado:
                return resultado['agent_response']
            elif isinstance(resultado, dict):
                resultado.update({
                    'agent_type': self.agent_type.value,
                    'specialist_analysis': True,
                    'relevance': self._calculate_relevance(query),
                    'timestamp': datetime.now().isoformat()
                })
                return resultado
            else:
                return {
                    'response': str(resultado),
                    'agent_type': self.agent_type.value,
                    'specialist_analysis': True,
                    'relevance': self._calculate_relevance(query),
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"❌ Erro ao delegar para IntegrationManager: {e}")
            return await self._analise_basica_especializada(query, context)

    async def _analise_basica_especializada(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Análise básica quando IntegrationManager não está disponível"""
        
        # Análise de relevância especializada
        relevance = self._calculate_relevance(query)
        
        # Resposta básica baseada no conhecimento do domínio
        domain_knowledge = self._load_domain_knowledge()
        
        resposta_basica = f"""
🤖 **Agente Especialista {self.agent_type.value.title()}**

Consulta analisada com relevância: {relevance:.2f}

**Domínio de Especialização:**
{domain_knowledge.get('nota', 'Especialista em análise de dados')}

**Para análises mais avançadas:**
- Sistema IntegrationManager não disponível
- Funcionalidades limitadas ao conhecimento básico
- Recomenda-se verificar conectividade dos sistemas

---
🔧 **Modo Básico** | {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        return {
            'response': resposta_basica,
            'relevance': relevance,
            'confidence': 0.6,  # Confiança média para modo básico
            'agent_type': self.agent_type.value,
            'mode': 'basic_specialist',
            'timestamp': datetime.now().isoformat(),
            'capabilities': ['domain_analysis', 'relevance_calculation']
        }

    def _log_consulta_estruturada(self, query: str, context: Dict[str, Any]):
        """Log estruturado da consulta"""
        self.logger_estruturado.info(
            f"📋 CONSULTA | Agente: {self.agent_type.value} | "
            f"Query: {query[:100]}... | "
            f"User: {context.get('username', 'N/A')} | "
            f"Relevância: {self._calculate_relevance(query):.2f}"
        )

    def get_agent_status(self) -> Dict[str, Any]:
        """Retorna status do agente especialista"""
        return {
            'agent_type': self.agent_type.value,
            'mode': 'specialist',
            'integration_manager_available': self.tem_integration_manager,
            'data_available': self.tem_dados_reais,
            'claude_available': self.tem_claude_real,
            'domain_knowledge': self._load_domain_knowledge(),
            'domain_keywords': self._get_domain_keywords(),
            'specialist_capabilities': [
                'domain_analysis',
                'relevance_calculation', 
                'specialized_knowledge',
                'integration_delegation'
            ],
            'timestamp': datetime.now().isoformat()
        }


# Exportações principais
__all__ = [
    'SmartBaseAgent'
] 