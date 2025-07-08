"""
🤖 BASE SPECIALIST AGENT - Classe Base para Agentes Especializados

Classe base que define a interface comum e funcionalidades básicas
para todos os agentes especializados do sistema multi-agente.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from ..agent_types import AgentType

logger = logging.getLogger(__name__)


class BaseSpecialistAgent(ABC):
    """
    Classe base abstrata para agentes especializados
    
    Define interface comum e funcionalidades compartilhadas
    """
    
    def __init__(self, agent_type: AgentType, claude_client=None):
        self.agent_type = agent_type
        self.claude_client = claude_client
        self.specialist_prompt = self._load_specialist_prompt()
        self.knowledge_base = self._load_domain_knowledge()
        
        logger.debug(f"🤖 {self.agent_type.value.title()} Agent inicializado")
    
    @abstractmethod
    def _load_specialist_prompt(self) -> str:
        """Carrega system prompt especializado para o domínio (deve ser implementado)"""
        pass
    
    @abstractmethod
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Carrega conhecimento específico do domínio (deve ser implementado)"""
        pass
    
    @abstractmethod
    def _get_domain_keywords(self) -> List[str]:
        """Retorna palavras-chave específicas do domínio (deve ser implementado)"""
        pass
    
    async def analyze(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa consulta específica do domínio
        
        Args:
            query: Consulta do usuário
            context: Contexto da consulta
            
        Returns:
            Dict com resposta do agente
        """
        
        try:
            # Verificar se a consulta é relevante para este domínio
            relevance_score = self._calculate_relevance(query)
            
            if relevance_score < 0.3:
                return {
                    'agent': self.agent_type.value,
                    'relevance': relevance_score,
                    'response': None,
                    'reasoning': f'Consulta não relevante para domínio {self.agent_type.value}'
                }
            
            # Processar consulta com especialização
            response = await self._process_specialized_query(query, context)
            
            return {
                'agent': self.agent_type.value,
                'relevance': relevance_score,
                'response': response,
                'confidence': self._calculate_confidence(response),
                'timestamp': datetime.now().isoformat(),
                'reasoning': f'Análise especializada em {self.agent_type.value}'
            }
            
        except Exception as e:
            logger.error(f"Erro no agente {self.agent_type.value}: {e}")
            return {
                'agent': self.agent_type.value,
                'error': str(e),
                'response': None
            }
    
    def _calculate_relevance(self, query: str) -> float:
        """Calcula relevância da consulta para este domínio"""
        
        query_lower = query.lower()
        keywords = self._get_domain_keywords()
        
        if not keywords:
            return 0.5  # Score neutro se não há keywords
        
        # Contar matches de keywords
        matches = sum(1 for keyword in keywords if keyword in query_lower)
        
        if matches == 0:
            return 0.0
        
        # Lógica corrigida: dar peso adequado aos matches
        # 1 match = relevância 0.4, 2+ matches = relevância alta
        if matches == 1:
            return 0.4  # Acima do threshold de 0.3
        elif matches == 2:
            return 0.7
        elif matches >= 3:
            return 0.9
        else:
            return min(matches * 0.3, 1.0)  # Fallback scaling
    
    async def _process_specialized_query(self, query: str, context: Dict[str, Any]) -> str:
        """Processa consulta com especialização de domínio"""
        
        if not self.claude_client:
            return f"Análise simulada do agente {self.agent_type.value} para: {query}"
        
        # Construir mensagem especializada
        specialized_message = f"""
CONSULTA ESPECIALIZADA EM {self.agent_type.value.upper()}:

Consulta do usuário: {query}

Contexto disponível:
{json.dumps(context, indent=2, ensure_ascii=False)}

Conhecimento específico do domínio:
{json.dumps(self.knowledge_base, indent=2, ensure_ascii=False)}

Por favor, forneça análise especializada focada exclusivamente no seu domínio de expertise.
"""
        
        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.1,
                system=self.specialist_prompt,
                messages=[{"role": "user", "content": specialized_message}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erro no Claude para agente {self.agent_type.value}: {e}")
            return f"Erro na análise especializada: {str(e)}"
    
    def _calculate_confidence(self, response: str) -> float:
        """Calcula score de confiança da resposta"""
        
        if not response or 'erro' in response.lower():
            return 0.0
        
        # Fatores que aumentam confiança
        confidence_factors = [
            len(response) > 100,  # Resposta substancial
            'dados' in response.lower(),  # Menciona dados
            any(field in response.lower() for field in self.knowledge_base.get('key_fields', [])),
            'análise' in response.lower(),  # Faz análise
            not ('não encontrado' in response.lower())  # Encontrou dados
        ]
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o agente"""
        return {
            'type': self.agent_type.value,
            'models': self.knowledge_base.get('main_models', []),
            'kpis': self.knowledge_base.get('kpis', []),
            'keywords': self._get_domain_keywords(),
            'has_claude_client': self.claude_client is not None
        }


# Exportações principais
__all__ = [
    'BaseSpecialistAgent'
] 