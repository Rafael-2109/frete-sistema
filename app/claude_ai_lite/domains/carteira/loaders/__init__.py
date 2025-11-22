"""
Loaders do dominio Carteira.
Cada loader tem responsabilidade unica.
"""

from .pedidos import PedidosLoader
from .produtos import ProdutosLoader
from .disponibilidade import DisponibilidadeLoader

__all__ = ["PedidosLoader", "ProdutosLoader", "DisponibilidadeLoader"]
