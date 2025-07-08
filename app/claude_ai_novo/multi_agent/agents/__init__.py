"""
🤖 AGENTS MODULE - Agentes Especializados Individuais

Este módulo contém todos os agentes especializados em arquivos separados:
- base_agent.py: Classe base para todos os agentes
- entregas_agent.py: Agente especialista em entregas  
- fretes_agent.py: Agente especialista em fretes
- pedidos_agent.py: Agente especialista em pedidos
- embarques_agent.py: Agente especialista em embarques
- financeiro_agent.py: Agente especialista em financeiro
"""

# Imports dos agentes especializados
from .base_agent import BaseSpecialistAgent
from .entregas_agent import EntregasAgent
from .fretes_agent import FretesAgent
from .pedidos_agent import PedidosAgent
from .embarques_agent import EmbarquesAgent
from .financeiro_agent import FinanceiroAgent

# Exportações principais
__all__ = [
    'BaseSpecialistAgent',
    'EntregasAgent',
    'FretesAgent', 
    'PedidosAgent',
    'EmbarquesAgent',
    'FinanceiroAgent'
] 