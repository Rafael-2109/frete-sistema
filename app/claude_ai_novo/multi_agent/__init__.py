"""
🤖 MULTI-AGENT MODULE - Sistema Multi-Agente Modularizado

Este módulo contém o sistema multi-agente completo modularizado em:
- agent_types.py: Tipos e enums básicos
- specialist_agents.py: Agentes especializados por domínio
- critic_agent.py: Agente crítico validador
- multi_agent_orchestrator.py: Orquestrador principal
- system.py: Wrapper unificado
"""

# Imports dos componentes modularizados
from .agent_types import AgentType, AgentResponse, ValidationResult, OperationRecord
from .specialist_agents import SpecialistAgent
from .critic_agent import CriticAgent
from .multi_agent_orchestrator import MultiAgentOrchestrator
from .system import MultiAgentSystem, get_multi_agent_system

# Exportações principais
__all__ = [
    # Sistema principal
    'MultiAgentSystem',
    'get_multi_agent_system',
    
    # Componentes modularizados
    'AgentType',
    'SpecialistAgent', 
    'CriticAgent',
    'MultiAgentOrchestrator',
    
    # Tipos e estruturas
    'AgentResponse',
    'ValidationResult',
    'OperationRecord',
] 