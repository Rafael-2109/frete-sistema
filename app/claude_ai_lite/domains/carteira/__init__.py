"""
Dominio: Carteira de Pedidos

Subloaders:
- PedidosLoader: consultas por pedido/cliente/CNPJ
- ProdutosLoader: consultas por produto
- DisponibilidadeLoader: analise de quando embarcar
- RotasLoader: consultas por rota/sub-rota/UF
- EstoqueLoader: analise de estoque e rupturas
- SaldoPedidoLoader: comparativo original vs separado
- GargalosLoader: identificacao de produtos gargalo
"""

from .. import registrar
from .loaders import (
    PedidosLoader,
    ProdutosLoader,
    DisponibilidadeLoader,
    RotasLoader,
    EstoqueLoader,
    SaldoPedidoLoader,
    GargalosLoader,
)

# Registra cada loader com intencao especifica
registrar("carteira", PedidosLoader)                       # Default para consultas gerais
registrar("carteira_produto", ProdutosLoader)              # Busca por produto
registrar("carteira_disponibilidade", DisponibilidadeLoader)  # Analise de embarque
registrar("carteira_rota", RotasLoader)                    # Consultas por rota/sub-rota/UF
registrar("estoque", EstoqueLoader)                        # Estoque e rupturas
registrar("carteira_saldo", SaldoPedidoLoader)             # Saldo de pedido
registrar("carteira_gargalo", GargalosLoader)              # Analise de gargalos

__all__ = [
    "PedidosLoader",
    "ProdutosLoader",
    "DisponibilidadeLoader",
    "RotasLoader",
    "EstoqueLoader",
    "SaldoPedidoLoader",
    "GargalosLoader",
]
