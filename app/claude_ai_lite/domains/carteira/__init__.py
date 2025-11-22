"""
Dominio: Carteira de Pedidos

Subloaders:
- PedidosLoader: consultas por pedido/cliente/CNPJ
- ProdutosLoader: consultas por produto
- DisponibilidadeLoader: analise de quando embarcar
"""

from .. import registrar
from .loaders import PedidosLoader, ProdutosLoader, DisponibilidadeLoader

# Registra cada loader com intencao especifica
registrar("carteira", PedidosLoader)              # Default para consultas gerais
registrar("carteira_produto", ProdutosLoader)     # Busca por produto
registrar("carteira_disponibilidade", DisponibilidadeLoader)  # Analise de embarque

__all__ = ["PedidosLoader", "ProdutosLoader", "DisponibilidadeLoader"]
