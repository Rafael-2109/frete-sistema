"""
Mapeadores de domínio - Mapeia campos específicos por domínio.
Responsabilidade: MAPEAR conceitos de domínio para campos de banco.
"""

from .base_mapper import BaseMapper
from .pedidos_mapper import PedidosMapper
from .embarques_mapper import EmbarquesMapper
from .faturamento_mapper import FaturamentoMapper
from .monitoramento_mapper import MonitoramentoMapper
from .transportadoras_mapper import TransportadorasMapper

# Função de conveniência
def get_domain_mapper(domain: str) -> BaseMapper:
    """
    Retorna mapeador específico para um domínio.
    
    Args:
        domain: Nome do domínio (pedidos, embarques, faturamento, etc.)
        
    Returns:
        Instância do mapeador apropriado
    """
    mappers = {
        'pedidos': PedidosMapper,
        'embarques': EmbarquesMapper,
        'faturamento': FaturamentoMapper,
        'monitoramento': MonitoramentoMapper,
        'transportadoras': TransportadorasMapper
    }
    
    mapper_class = mappers.get(domain.lower())
    if not mapper_class:
        raise ValueError(f"Domínio '{domain}' não suportado. Disponíveis: {list(mappers.keys())}")
    
    return mapper_class()

# Export explícito
__all__ = [
    'BaseMapper',
    'PedidosMapper',
    'EmbarquesMapper',
    'FaturamentoMapper',
    'MonitoramentoMapper',
    'TransportadorasMapper',
    'get_domain_mapper'
] 