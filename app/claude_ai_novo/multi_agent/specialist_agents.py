"""
🤖 SPECIALIST AGENTS - Wrapper para Agentes Especializados Individuais

Este wrapper mantém compatibilidade com o sistema anterior
while delegating to individual specialist agent files.

ESTRUTURA MODULAR:
- agents/base_agent.py: Classe base
- agents/entregas_agent.py: Agente de Entregas
- agents/fretes_agent.py: Agente de Fretes  
- agents/pedidos_agent.py: Agente de Pedidos
- agents/embarques_agent.py: Agente de Embarques
- agents/financeiro_agent.py: Agente Financeiro
"""

import logging
from typing import Dict, Any

# Imports dos agentes individuais
from .agents import (
    BaseSpecialistAgent,
    EntregasAgent,
    FretesAgent,
    PedidosAgent,
    EmbarquesAgent,
    FinanceiroAgent
)
from .agent_types import AgentType

logger = logging.getLogger(__name__)


class SpecialistAgent:
    """
    Wrapper de compatibilidade para agentes especializados individuais
    
    Mantém interface original while delegating to specialized agent classes
    """
    
    def __new__(cls, agent_type: AgentType, claude_client=None):
        """Factory method que retorna o agente especializado correto"""
        
        # Mapear tipos para classes específicas
        agent_classes = {
            AgentType.ENTREGAS: EntregasAgent,
            AgentType.FRETES: FretesAgent,
            AgentType.PEDIDOS: PedidosAgent,
            AgentType.EMBARQUES: EmbarquesAgent,
            AgentType.FINANCEIRO: FinanceiroAgent,
        }
        
        agent_class = agent_classes.get(agent_type)
        
        if agent_class:
            return agent_class(claude_client)
        else:
            logger.warning(f"Tipo de agente não reconhecido: {agent_type}")
            # Fallback para agente base
            return BaseSpecialistAgent(agent_type, claude_client)


# Factory functions para fácil criação
def create_entregas_agent(claude_client=None) -> EntregasAgent:
    """Cria agente especialista em entregas"""
    return EntregasAgent(claude_client)


def create_fretes_agent(claude_client=None) -> FretesAgent:
    """Cria agente especialista em fretes"""
    return FretesAgent(claude_client)


def create_pedidos_agent(claude_client=None) -> PedidosAgent:
    """Cria agente especialista em pedidos"""
    return PedidosAgent(claude_client)


def create_embarques_agent(claude_client=None) -> EmbarquesAgent:
    """Cria agente especialista em embarques"""
    return EmbarquesAgent(claude_client)


def create_financeiro_agent(claude_client=None) -> FinanceiroAgent:
    """Cria agente especialista em financeiro"""
    return FinanceiroAgent(claude_client)


def get_all_agent_types() -> Dict[str, type]:
    """Retorna mapeamento de todos os tipos de agentes"""
    return {
        'entregas': EntregasAgent,
        'fretes': FretesAgent,
        'pedidos': PedidosAgent,
        'embarques': EmbarquesAgent,
        'financeiro': FinanceiroAgent
    }


# Exportações principais
__all__ = [
    # Wrapper de compatibilidade
    'SpecialistAgent',
    
    # Agentes especializados individuais
    'EntregasAgent',
    'FretesAgent',
    'PedidosAgent', 
    'EmbarquesAgent',
    'FinanceiroAgent',
    
    # Classe base
    'BaseSpecialistAgent',
    
    # Factory functions
    'create_entregas_agent',
    'create_fretes_agent',
    'create_pedidos_agent',
    'create_embarques_agent',
    'create_financeiro_agent',
    'get_all_agent_types'
] 