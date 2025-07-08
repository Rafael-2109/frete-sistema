"""
🤖 MULTI-AGENT SYSTEM - Sistema Multi-Agente Modularizado

Este é o wrapper principal que integra todos os módulos do sistema multi-agente:
- AgentTypes: Tipos e enums
- SpecialistAgents: Agentes especializados por domínio
- CriticAgent: Validação cruzada
- MultiAgentOrchestrator: Orquestração principal
"""

import logging
from typing import Dict, List, Any, Optional

# Imports dos módulos modularizados
from .agent_types import AgentType, AgentResponse, ValidationResult, OperationRecord
from .specialist_agents import SpecialistAgent
from .critic_agent import CriticAgent
from .multi_agent_orchestrator import MultiAgentOrchestrator

logger = logging.getLogger(__name__)


class MultiAgentSystem:
    """
    Sistema Multi-Agente - Wrapper dos módulos modularizados
    
    Integra:
    - MultiAgentOrchestrator: Coordenação principal
    - SpecialistAgents: Agentes especializados
    - CriticAgent: Validação cruzada
    - AgentTypes: Tipos e estruturas
    """
    
    def __init__(self, claude_client=None, orchestrator=None, db_engine=None, db_session=None):
        """
        Inicializa o sistema multi-agente completo
        
        Args:
            claude_client: Cliente Claude (opcional)
            orchestrator: Orquestrador externo (opcional)
            db_engine: Engine do banco de dados (opcional)
            db_session: Sessão do banco de dados (opcional)
        """
        self.claude_client = claude_client
        self.db_engine = db_engine
        self.db_session = db_session
        
        # Usar orquestrador externo se fornecido, senão criar interno
        if orchestrator:
            self.orchestrator = orchestrator
        else:
            self.orchestrator = MultiAgentOrchestrator(claude_client)
        
        logger.info("🤖 Sistema Multi-Agente (modularizado) inicializado")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa consulta usando sistema multi-agente modularizado
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            Dict com resposta processada e metadados
        """
        try:
            # Delegar para o orquestrador modularizado
            return await self.orchestrator.process_query(query, context)
        except Exception as e:
            logger.error(f"❌ Erro no Sistema Multi-Agente: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': f"Erro no processamento multi-agente: {str(e)}"
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema usando orquestrador modularizado"""
        try:
            return self.orchestrator.get_system_stats()
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {"error": str(e)}
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza configurações usando orquestrador modularizado"""
        try:
            return self.orchestrator.update_config(new_config)
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar configuração: {e}")
            return {"error": str(e)}
    
    @property
    def agents(self):
        """Acesso aos agentes especializados"""
        return self.orchestrator.agents
    
    @property
    def critic(self):
        """Acesso ao agente crítico"""
        return self.orchestrator.critic
    
    @property
    def config(self):
        """Acesso às configurações"""
        return self.orchestrator.config
    
    @property
    def operation_history(self):
        """Acesso ao histórico de operações"""
        return self.orchestrator.operation_history


# Instância global para compatibilidade
multi_agent_system = None


def get_multi_agent_system(claude_client=None) -> MultiAgentSystem:
    """
    Função de conveniência para obter instância global do sistema
    
    Args:
        claude_client: Cliente Claude (opcional)
        
    Returns:
        MultiAgentSystem: Instância do sistema multi-agente
    """
    global multi_agent_system
    
    if multi_agent_system is None:
        multi_agent_system = MultiAgentSystem(claude_client)
        logger.info("🚀 Sistema Multi-Agente inicializado via factory function")
    
    return multi_agent_system


# Exportações principais para compatibilidade
__all__ = [
    # Classe principal
    'MultiAgentSystem',
    
    # Factory function
    'get_multi_agent_system',
    
    # Tipos importados para conveniência
    'AgentType',
    'AgentResponse',
    'ValidationResult', 
    'OperationRecord',
    
    # Componentes para uso avançado
    'SpecialistAgent',
    'CriticAgent',
    'MultiAgentOrchestrator'
] 