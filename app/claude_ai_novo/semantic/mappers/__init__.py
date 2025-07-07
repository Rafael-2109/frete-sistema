"""
📋 MAPPERS - Mapeamentos Semânticos por Modelo
==============================================

Módulo contendo mapeadores específicos para cada modelo de dados.
Cada mapper é responsável por mapear termos naturais para campos
de um modelo específico.

Mappers Disponíveis:
- PedidosMapper         - Mapeamentos para modelo Pedido
- EmbarquesMapper       - Mapeamentos para Embarque/EmbarqueItem  
- MonitoramentoMapper   - Mapeamentos para EntregaMonitorada
- FaturamentoMapper     - Mapeamentos para RelatorioFaturamentoImportado
- TransportadorasMapper - Mapeamentos para Transportadora
"""

from .base_mapper import BaseMapper
from .pedidos_mapper import PedidosMapper
from .embarques_mapper import EmbarquesMapper
from .monitoramento_mapper import MonitoramentoMapper
from .faturamento_mapper import FaturamentoMapper
from .transportadoras_mapper import TransportadorasMapper

__all__ = [
    'BaseMapper',
    'PedidosMapper',
    'EmbarquesMapper', 
    'MonitoramentoMapper',
    'FaturamentoMapper',
    'TransportadorasMapper'
] 