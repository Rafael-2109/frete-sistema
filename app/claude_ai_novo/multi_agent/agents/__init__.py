"""
🧠 MULTI-AGENT SYSTEM - Agentes Especializados COM TODAS AS CAPACIDADES

Sistema de agentes especializados em diferentes domínios do sistema de fretes.
TODOS os agentes agora herdam de SmartBaseAgent e possuem:

✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet real (não simulado)
✅ Cache Redis para performance
✅ Sistema de contexto conversacional
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Sistema de logs estruturados
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos
"""

from .smart_base_agent import SmartBaseAgent
from .entregas_agent import EntregasAgent
from .embarques_agent import EmbarquesAgent
from .financeiro_agent import FinanceiroAgent
from .pedidos_agent import PedidosAgent
from .fretes_agent import FretesAgent

# Exportações principais
__all__ = [
    'SmartBaseAgent',
    'EntregasAgent',
    'EmbarquesAgent', 
    'FinanceiroAgent',
    'PedidosAgent',
    'FretesAgent'
]
