"""
Módulo de leitura e processamento de pedidos em PDF
Suporta múltiplos formatos de clientes
"""

from .base import PDFExtractor
from .atacadao import AtacadaoExtractor
from .processor import PedidoProcessor

__all__ = ['PDFExtractor', 'AtacadaoExtractor', 'PedidoProcessor']