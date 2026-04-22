"""
Constantes do modulo Pessoal — categorias, regras semente e exclusoes.

Fonte unica para seed data. Usado pela migration e pelo service de categorizacao.
"""

# =============================================================================
# MEMBROS DA FAMILIA
# =============================================================================
MEMBROS_FAMILIA = [
    {"nome": "Rafael", "nome_completo": "RAFAEL C NASCIMENTO", "papel": "pai"},
    {"nome": "Renata", "nome_completo": "RENATA NASCIMENTO", "papel": "mae"},
    {"nome": "Arthur", "nome_completo": "ARTHUR NASCIMENTO", "papel": "filho"},
    {"nome": "Isabella", "nome_completo": "ISABELLA NASCIMENTO", "papel": "filha"},
    {"nome": "Felipe", "nome_completo": "FELIPE NASCIMENTO", "papel": "filho"},
    {"nome": "Leonardo", "nome_completo": "LEONARDO NASCIMENTO", "papel": "filho"},
]

# =============================================================================
# CONTAS BANCARIAS
# =============================================================================
CONTAS_BANCARIAS = [
    {
        "nome": "Bradesco CC 128948-9",
        "tipo": "conta_corrente",
        "banco": "bradesco",
        "agencia": "2878",
        "numero_conta": "128948-9",
        "ultimos_digitos_cartao": None,
        "membro_nome": "Rafael",
    },
    {
        "nome": "Bradesco Cartao 8918 (Rafael)",
        "tipo": "cartao_credito",
        "banco": "bradesco",
        "agencia": None,
        "numero_conta": None,
        "ultimos_digitos_cartao": "8918",
        "membro_nome": "Rafael",
    },
    {
        "nome": "Bradesco Cartao 38451 (Rafael)",
        "tipo": "cartao_credito",
        "banco": "bradesco",
        "agencia": None,
        "numero_conta": None,
        "ultimos_digitos_cartao": "38451",
        "membro_nome": "Rafael",
    },
    {
        "nome": "Bradesco Cartao 3918 (Renata)",
        "tipo": "cartao_credito",
        "banco": "bradesco",
        "agencia": None,
        "numero_conta": None,
        "ultimos_digitos_cartao": "3918",
        "membro_nome": "Renata",
    },
    {
        "nome": "Bradesco Cartao 82152 (Renata)",
        "tipo": "cartao_credito",
        "banco": "bradesco",
        "agencia": None,
        "numero_conta": None,
        "ultimos_digitos_cartao": "82152",
        "membro_nome": "Renata",
    },
]

# =============================================================================
# CATEGORIAS DE DESPESAS (~40 categorias em 18 grupos)
# =============================================================================
CATEGORIAS_DESPESAS = [
    # --- Moradia ---
    {"nome": "Aluguel", "grupo": "Moradia", "icone": "fa-home", "ordem": 1},
    {"nome": "Condominio", "grupo": "Moradia", "icone": "fa-building", "ordem": 2},
    {"nome": "IPTU", "grupo": "Moradia", "icone": "fa-file-invoice", "ordem": 3},
    {"nome": "Manutencao Casa", "grupo": "Moradia", "icone": "fa-tools", "ordem": 4},
    # --- Utilidades ---
    {"nome": "Energia Eletrica", "grupo": "Utilidades", "icone": "fa-bolt", "ordem": 10},
    {"nome": "Agua", "grupo": "Utilidades", "icone": "fa-tint", "ordem": 11},
    {"nome": "Gas", "grupo": "Utilidades", "icone": "fa-fire", "ordem": 12},
    {"nome": "Internet/Telefone", "grupo": "Utilidades", "icone": "fa-wifi", "ordem": 13},
    {"nome": "Celular", "grupo": "Utilidades", "icone": "fa-mobile-alt", "ordem": 14},
    # --- Alimentacao ---
    {"nome": "Supermercado", "grupo": "Alimentacao", "icone": "fa-shopping-cart", "ordem": 20},
    {"nome": "Restaurante", "grupo": "Alimentacao", "icone": "fa-utensils", "ordem": 21},
    {"nome": "Delivery", "grupo": "Alimentacao", "icone": "fa-motorcycle", "ordem": 22},
    {"nome": "Padaria/Lanchonete", "grupo": "Alimentacao", "icone": "fa-bread-slice", "ordem": 23},
    # --- Transporte ---
    {"nome": "Combustivel", "grupo": "Transporte", "icone": "fa-gas-pump", "ordem": 30},
    {"nome": "Estacionamento/Pedagio", "grupo": "Transporte", "icone": "fa-parking", "ordem": 31},
    {"nome": "Manutencao Veiculo", "grupo": "Transporte", "icone": "fa-car", "ordem": 32},
    {"nome": "Seguro Veiculo", "grupo": "Transporte", "icone": "fa-shield-alt", "ordem": 33},
    {"nome": "Transporte App", "grupo": "Transporte", "icone": "fa-taxi", "ordem": 34},
    # --- Saude ---
    {"nome": "Plano de Saude", "grupo": "Saude", "icone": "fa-hospital", "ordem": 40},
    {"nome": "Farmacia", "grupo": "Saude", "icone": "fa-pills", "ordem": 41},
    {"nome": "Consultas Medicas", "grupo": "Saude", "icone": "fa-stethoscope", "ordem": 42},
    {"nome": "Dentista", "grupo": "Saude", "icone": "fa-tooth", "ordem": 43},
    {"nome": "Academia/Esporte", "grupo": "Saude", "icone": "fa-dumbbell", "ordem": 44},
    # --- Educacao ---
    {"nome": "Escola/Faculdade", "grupo": "Educacao", "icone": "fa-graduation-cap", "ordem": 50},
    {"nome": "Material Escolar", "grupo": "Educacao", "icone": "fa-book", "ordem": 51},
    {"nome": "Cursos/Treinamentos", "grupo": "Educacao", "icone": "fa-chalkboard-teacher", "ordem": 52},
    # --- Lazer ---
    {"nome": "Entretenimento", "grupo": "Lazer", "icone": "fa-film", "ordem": 60},
    {"nome": "Viagem", "grupo": "Lazer", "icone": "fa-plane", "ordem": 61},
    {"nome": "Streaming/Assinaturas", "grupo": "Lazer", "icone": "fa-tv", "ordem": 62},
    {"nome": "Hobbies", "grupo": "Lazer", "icone": "fa-gamepad", "ordem": 63},
    # --- Vestuario ---
    {"nome": "Roupas/Calcados", "grupo": "Vestuario", "icone": "fa-tshirt", "ordem": 70},
    # --- Filhos ---
    {"nome": "Mesada/Filhos", "grupo": "Filhos", "icone": "fa-child", "ordem": 80},
    {"nome": "Brinquedos/Jogos", "grupo": "Filhos", "icone": "fa-puzzle-piece", "ordem": 81},
    # --- Pets ---
    {"nome": "Pet", "grupo": "Pets", "icone": "fa-paw", "ordem": 85},
    # --- Seguros ---
    {"nome": "Seguro Vida", "grupo": "Seguros", "icone": "fa-heart", "ordem": 90},
    {"nome": "Seguro Residencial", "grupo": "Seguros", "icone": "fa-home", "ordem": 91},
    # --- Impostos ---
    {"nome": "Imposto de Renda", "grupo": "Impostos", "icone": "fa-landmark", "ordem": 100},
    {"nome": "Outros Impostos", "grupo": "Impostos", "icone": "fa-file-invoice-dollar", "ordem": 101},
    # --- Financeiro ---
    {"nome": "Tarifa Bancaria", "grupo": "Financeiro", "icone": "fa-university", "ordem": 110},
    {"nome": "Juros/Multa", "grupo": "Financeiro", "icone": "fa-percentage", "ordem": 111},
    {"nome": "Emprestimo/Financiamento", "grupo": "Financeiro", "icone": "fa-hand-holding-usd", "ordem": 112},
    {"nome": "Investimento", "grupo": "Financeiro", "icone": "fa-chart-line", "ordem": 113},
    # Usada na vertente Fluxo de Caixa para agrupar pagamentos de fatura de cartao
    # (1 linha por fatura paga, com drilldown para compras originais).
    {"nome": "Cartao de Credito", "grupo": "Financeiro", "icone": "fa-credit-card", "ordem": 114},
    # --- Receitas ---
    {"nome": "Salario", "grupo": "Receitas", "icone": "fa-money-bill-wave", "ordem": 200},
    {"nome": "Pro-labore", "grupo": "Receitas", "icone": "fa-briefcase", "ordem": 201},
    {"nome": "Rendimentos", "grupo": "Receitas", "icone": "fa-piggy-bank", "ordem": 202},
    {"nome": "Outros Creditos", "grupo": "Receitas", "icone": "fa-plus-circle", "ordem": 203},
    # --- Outros ---
    {"nome": "Doacoes/Presentes", "grupo": "Outros", "icone": "fa-gift", "ordem": 300},
    {"nome": "Servicos Gerais", "grupo": "Outros", "icone": "fa-concierge-bell", "ordem": 301},
    {"nome": "Outros", "grupo": "Outros", "icone": "fa-question-circle", "ordem": 999},
]

# =============================================================================
# REGRAS DE CATEGORIZACAO SEMENTE
# tipo_regra: PADRAO = sempre mesma categoria, RELATIVO = depende do contexto
# =============================================================================
REGRAS_CATEGORIZACAO_SEMENTE = [
    # --- PADRAO: Moradia ---
    {"padrao": "ALUGUEL", "tipo": "PADRAO", "categoria": "Aluguel"},
    {"padrao": "CONDOMINIO", "tipo": "PADRAO", "categoria": "Condominio"},
    {"padrao": "IPTU", "tipo": "PADRAO", "categoria": "IPTU"},
    # --- PADRAO: Utilidades ---
    {"padrao": "CPFL", "tipo": "PADRAO", "categoria": "Energia Eletrica"},
    {"padrao": "ENERGISA", "tipo": "PADRAO", "categoria": "Energia Eletrica"},
    {"padrao": "ENEL", "tipo": "PADRAO", "categoria": "Energia Eletrica"},
    {"padrao": "SABESP", "tipo": "PADRAO", "categoria": "Agua"},
    {"padrao": "SANEPAR", "tipo": "PADRAO", "categoria": "Agua"},
    {"padrao": "COMGAS", "tipo": "PADRAO", "categoria": "Gas"},
    {"padrao": "ULTRAGAZ", "tipo": "PADRAO", "categoria": "Gas"},
    {"padrao": "VIVO", "tipo": "PADRAO", "categoria": "Internet/Telefone"},
    {"padrao": "CLARO", "tipo": "PADRAO", "categoria": "Internet/Telefone"},
    {"padrao": "TIM", "tipo": "PADRAO", "categoria": "Celular"},
    # --- PADRAO: Supermercado ---
    {"padrao": "ATACADAO", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "ASSAI", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "CARREFOUR", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "PAO DE ACUCAR", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "EXTRA HIPER", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "SONDA", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "TENDA ATACADO", "tipo": "PADRAO", "categoria": "Supermercado"},
    {"padrao": "HIROTA", "tipo": "PADRAO", "categoria": "Supermercado"},
    # --- PADRAO: Delivery ---
    {"padrao": "IFOOD", "tipo": "PADRAO", "categoria": "Delivery"},
    {"padrao": "RAPPI", "tipo": "PADRAO", "categoria": "Delivery"},
    {"padrao": "UBER EATS", "tipo": "PADRAO", "categoria": "Delivery"},
    # --- PADRAO: Transporte ---
    {"padrao": "SHELL", "tipo": "PADRAO", "categoria": "Combustivel"},
    {"padrao": "IPIRANGA", "tipo": "PADRAO", "categoria": "Combustivel"},
    {"padrao": "BR DISTRIBUIDORA", "tipo": "PADRAO", "categoria": "Combustivel"},
    {"padrao": "POSTO", "tipo": "PADRAO", "categoria": "Combustivel"},
    {"padrao": "UBER TRIP", "tipo": "PADRAO", "categoria": "Transporte App"},
    {"padrao": "99 TECNOL", "tipo": "PADRAO", "categoria": "Transporte App"},
    {"padrao": "CONECTCAR", "tipo": "PADRAO", "categoria": "Estacionamento/Pedagio"},
    {"padrao": "VELOE", "tipo": "PADRAO", "categoria": "Estacionamento/Pedagio"},
    {"padrao": "SEM PARAR", "tipo": "PADRAO", "categoria": "Estacionamento/Pedagio"},
    {"padrao": "ESTAPAR", "tipo": "PADRAO", "categoria": "Estacionamento/Pedagio"},
    # --- PADRAO: Saude ---
    {"padrao": "DROGASIL", "tipo": "PADRAO", "categoria": "Farmacia"},
    {"padrao": "DROGA RAIA", "tipo": "PADRAO", "categoria": "Farmacia"},
    {"padrao": "DROGARIA", "tipo": "PADRAO", "categoria": "Farmacia"},
    {"padrao": "FARMACIA", "tipo": "PADRAO", "categoria": "Farmacia"},
    {"padrao": "UNIMED", "tipo": "PADRAO", "categoria": "Plano de Saude"},
    {"padrao": "AMIL", "tipo": "PADRAO", "categoria": "Plano de Saude"},
    {"padrao": "SULAMERICA", "tipo": "PADRAO", "categoria": "Plano de Saude"},
    {"padrao": "SMART FIT", "tipo": "PADRAO", "categoria": "Academia/Esporte"},
    {"padrao": "ACADEMIA", "tipo": "PADRAO", "categoria": "Academia/Esporte"},
    # --- PADRAO: Educacao ---
    {"padrao": "SOCIEDADE EDUCA", "tipo": "PADRAO", "categoria": "Escola/Faculdade"},
    {"padrao": "ESCOLA", "tipo": "PADRAO", "categoria": "Escola/Faculdade"},
    {"padrao": "COLEGIO", "tipo": "PADRAO", "categoria": "Escola/Faculdade"},
    {"padrao": "UDEMY", "tipo": "PADRAO", "categoria": "Cursos/Treinamentos"},
    {"padrao": "ALURA", "tipo": "PADRAO", "categoria": "Cursos/Treinamentos"},
    # --- PADRAO: Streaming ---
    {"padrao": "NETFLIX", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "SPOTIFY", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "DISNEY", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "AMAZON PRIME", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "HBO", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "APPLE.COM/BILL", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "GOOGLE PLAY", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    {"padrao": "YOUTUBE PREMIUM", "tipo": "PADRAO", "categoria": "Streaming/Assinaturas"},
    # --- PADRAO: Financeiro ---
    {"padrao": "TARIFA", "tipo": "PADRAO", "categoria": "Tarifa Bancaria"},
    {"padrao": "TAR PACOTE", "tipo": "PADRAO", "categoria": "Tarifa Bancaria"},
    {"padrao": "ANUIDADE", "tipo": "PADRAO", "categoria": "Tarifa Bancaria"},
    {"padrao": "IOF", "tipo": "PADRAO", "categoria": "Juros/Multa"},
    {"padrao": "JUROS", "tipo": "PADRAO", "categoria": "Juros/Multa"},
    {"padrao": "APL.INVEST", "tipo": "PADRAO", "categoria": "Investimento"},
    {"padrao": "APLICACAO", "tipo": "PADRAO", "categoria": "Investimento"},
    {"padrao": "RESGATE", "tipo": "PADRAO", "categoria": "Investimento"},
    {"padrao": "CDB", "tipo": "PADRAO", "categoria": "Investimento"},
    # --- PADRAO: Pet ---
    {"padrao": "PETZ", "tipo": "PADRAO", "categoria": "Pet"},
    {"padrao": "COBASI", "tipo": "PADRAO", "categoria": "Pet"},
    {"padrao": "PET SHOP", "tipo": "PADRAO", "categoria": "Pet"},
    # --- RELATIVO: depende do contexto para categorizar ---
    {
        "padrao": "PIX ENVIADO",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Aluguel", "Servicos Gerais", "Mesada/Filhos",
            "Doacoes/Presentes", "Outros",
        ],
    },
    {
        "padrao": "PIX RECEBIDO",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Salario", "Pro-labore", "Rendimentos", "Outros Creditos",
        ],
    },
    {
        "padrao": "TED ENVIADO",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Aluguel", "Servicos Gerais", "Emprestimo/Financiamento", "Outros",
        ],
    },
    {
        "padrao": "TED RECEBIDO",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Salario", "Pro-labore", "Rendimentos", "Outros Creditos",
        ],
    },
    {
        "padrao": "TRANSF",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Salario", "Pro-labore", "Outros Creditos", "Servicos Gerais", "Outros",
        ],
    },
    {
        "padrao": "BOLETO",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Escola/Faculdade", "Plano de Saude", "Condominio",
            "Energia Eletrica", "Agua", "Internet/Telefone",
            "Seguro Veiculo", "Emprestimo/Financiamento", "Outros Impostos", "Outros",
        ],
    },
    {
        "padrao": "DEBITO AUTOMATICO",
        "tipo": "RELATIVO",
        "categoria": None,
        "categorias_restritas": [
            "Energia Eletrica", "Agua", "Gas", "Internet/Telefone",
            "Celular", "Plano de Saude", "Outros",
        ],
    },
]

# =============================================================================
# EXCLUSOES EMPRESARIAIS — transacoes que NAO sao pessoais
# =============================================================================
EXCLUSOES_EMPRESA = [
    {"padrao": "LA FAMIGLIA", "descricao": "Restaurante La Famiglia (empresa)"},
    {"padrao": "NG PROMO", "descricao": "NG Promocoes (empresa)"},
    {"padrao": "SOGIMA", "descricao": "Sogima (empresa)"},
    {"padrao": "AANP", "descricao": "AANP (empresa)"},
    {"padrao": "NACOM GOYA", "descricao": "Nacom Goya (empresa)"},
    {"padrao": "PARNAPLAST", "descricao": "Parnaplast (empresa)"},
    {"padrao": "SALDO ANTERIOR", "descricao": "Saldo inicial do extrato (nao e transacao)"},
    {"padrao": "PAGTO POR DEB EM C/C", "descricao": "Pagamento cartao via CC (double-count)"},
]

# =============================================================================
# HEURISTICAS (Layer 4)
# =============================================================================

# Padroes que indicam pagamento de fatura de cartao (double-count)
PADROES_PAGAMENTO_CARTAO = [
    "GASTO C CREDITO",
    "PAG CARTAO CREDITO",
    "PAGAMENTO DE CARTAO",
    "PGTO CARTAO",
    "PAGTO POR DEB EM C/C",
    "PAGTO. POR DEB EM C/C",
]

# Padroes que indicam transferencia propria (entre contas)
PADROES_TRANSFERENCIA_PROPRIA = [
    "TRANSF.AUT. NG PROMO",
    "TRANSF.AUT. LA FAMIGLIA",
    "TRANSF.AUT. SOGIMA",
    "TRANSF ENTRE CONTAS",
    "TED-T ELET DISP",
]

# Padroes que indicam investimento/aplicacao (excluir de relatorio)
PADROES_INVESTIMENTO = [
    "APL.INVEST",
    "APLICACAO",
    "RESGATE",
    "CDB",
    "TESOURO DIRETO",
    "FUNDO",
]
