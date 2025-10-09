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
    EmpresaVendaMoto,
    CrossDocking,
    TabelaPrecoCrossDocking
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
    ComissaoVendedor,
    MovimentacaoFinanceira,
    TituloAPagar
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
    'CrossDocking',
    'TabelaPrecoCrossDocking',
    # Produtos
    'ModeloMoto',
    'Moto',
    # Vendas
    'PedidoVendaMoto',
    'PedidoVendaMotoItem',
    # Financeiro
    'TituloFinanceiro',
    'ComissaoVendedor',
    'MovimentacaoFinanceira',
    'TituloAPagar',
    # Logística
    'EmbarqueMoto',
    'EmbarquePedido',
    # Operacional
    'CustosOperacionais',
    'DespesaMensal',
]
