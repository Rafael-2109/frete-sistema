"""
Sistema MotoCHEFE - Importação centralizada de models
Facilita importação em outros módulos
"""

# Cadastros
from .cadastro import (
    VendedorMoto,
    EquipeVendasMoto,
    TabelaPrecoEquipe,
    TransportadoraMoto,
    ClienteMoto,
    EmpresaVendaMoto
)

# Produtos
from .produto import (
    ModeloMoto,
    Moto
)

# Vendas
from .vendas import (
    PedidoVendaMoto,
    PedidoVendaMotoItem
)

# Financeiro
from .financeiro import (
    TituloFinanceiro,
    ComissaoVendedor
)

# Logística
from .logistica import (
    EmbarqueMoto,
    EmbarquePedido
)

# Operacional
from .operacional import (
    CustosOperacionais,
    DespesaMensal
)

__all__ = [
    # Cadastros
    'VendedorMoto',
    'EquipeVendasMoto',
    'TabelaPrecoEquipe',
    'TransportadoraMoto',
    'ClienteMoto',
    'EmpresaVendaMoto',
    # Produtos
    'ModeloMoto',
    'Moto',
    # Vendas
    'PedidoVendaMoto',
    'PedidoVendaMotoItem',
    # Financeiro
    'TituloFinanceiro',
    'ComissaoVendedor',
    # Logística
    'EmbarqueMoto',
    'EmbarquePedido',
    # Operacional
    'CustosOperacionais',
    'DespesaMensal',
]
