"""
🔧 MICRO-LOADERS ESPECIALIZADOS
Módulos especializados para carregamento de dados por domínio
"""

# Import das classes
from .faturamento_loader import FaturamentoLoader, get_faturamento_loader
from .embarques_loader import EmbarquesLoader, get_embarques_loader
from .fretes_loader import FretesLoader, get_fretes_loader
from .entregas_loader import EntregasLoader, get_entregas_loader
from .pedidos_loader import PedidosLoader, get_pedidos_loader
from .agendamentos_loader import AgendamentosLoader, get_agendamentos_loader

__all__ = [
    # Classes
    'FaturamentoLoader',
    'EmbarquesLoader', 
    'FretesLoader',
    'EntregasLoader',
    'PedidosLoader',
    'AgendamentosLoader',
    # Funções de conveniência
    'get_faturamento_loader',
    'get_embarques_loader',
    'get_fretes_loader',
    'get_entregas_loader',
    'get_pedidos_loader',
    'get_agendamentos_loader'
] 