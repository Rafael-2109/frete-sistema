"""
Loaders do dominio Carteira.
Cada loader tem responsabilidade unica.
"""

from .pedidos import PedidosLoader
from .produtos import ProdutosLoader
from .disponibilidade import DisponibilidadeLoader
from .rotas import RotasLoader
from .estoque import EstoqueLoader
from .saldo_pedido import SaldoPedidoLoader
from .gargalos import GargalosLoader

__all__ = [
    "PedidosLoader",
    "ProdutosLoader",
    "DisponibilidadeLoader",
    "RotasLoader",
    "EstoqueLoader",
    "SaldoPedidoLoader",
    "GargalosLoader",
]
