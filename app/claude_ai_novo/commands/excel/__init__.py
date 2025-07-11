#!/usr/bin/env python3
"""
Módulos Excel - Mini esqueletos especializados
Cada módulo é especializado em um tipo específico de relatório Excel
"""

# Exports organizados dos mini esqueletos
try:
    from .fretes import ExcelFretes, get_excel_fretes
    FRETES_AVAILABLE = True
except ImportError:
    FRETES_AVAILABLE = False

try:
    from .pedidos import ExcelPedidos, get_excel_pedidos
    PEDIDOS_AVAILABLE = True
except ImportError:
    PEDIDOS_AVAILABLE = False

try:
    from .entregas import ExcelEntregas, get_excel_entregas
    ENTREGAS_AVAILABLE = True
except ImportError:
    ENTREGAS_AVAILABLE = False

try:
    from .faturamento import ExcelFaturamento, get_excel_faturamento
    FATURAMENTO_AVAILABLE = True
except ImportError:
    FATURAMENTO_AVAILABLE = False

# Exports principais
__all__ = [
    'ExcelFretes', 'get_excel_fretes',
    'ExcelPedidos', 'get_excel_pedidos', 
    'ExcelEntregas', 'get_excel_entregas',
    'ExcelFaturamento', 'get_excel_faturamento',
    'FRETES_AVAILABLE', 'PEDIDOS_AVAILABLE', 'ENTREGAS_AVAILABLE', 'FATURAMENTO_AVAILABLE'
]

def get_available_modules():
    """Retorna módulos Excel disponíveis"""
    return {
        'fretes': FRETES_AVAILABLE,
        'pedidos': PEDIDOS_AVAILABLE,
        'entregas': ENTREGAS_AVAILABLE,
        'faturamento': FATURAMENTO_AVAILABLE
    } 