"""
Configuracoes do Claude AI Lite
"""

# Campos de busca aceitos
CAMPOS_BUSCA = {
    'raz_social_red': 'razao social',
    'cnpj_cpf': 'cnpj',
    'pedido_cliente': 'pedido cliente',
    'num_pedido': 'numero pedido'
}

# Sinonimos para identificar criterio de busca
SINONIMOS = {
    'raz_social_red': ['cliente', 'razao', 'razao social', 'nome', 'empresa'],
    'cnpj_cpf': ['cnpj', 'cpf', 'documento'],
    'pedido_cliente': ['pedido cliente', 'pedido de compra', 'pc', 'ordem de compra', 'oc'],
    'num_pedido': ['pedido', 'numero', 'num', 'nro', 'numero pedido']
}

# Status possiveis da Separacao
STATUS_SEPARACAO = ['PREVISAO', 'ABERTO', 'COTADO', 'EMBARCADO', 'FATURADO', 'NF no CD']
