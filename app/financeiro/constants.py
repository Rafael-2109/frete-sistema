# -*- coding: utf-8 -*-
"""
Constantes do Modulo Financeiro
===============================

Centraliza IDs de contas contabeis, journals e mapeamentos Odoo
para evitar duplicacao entre services.

IMPORTANTE: Alterar valores aqui afeta TODOS os services financeiros.
Confirmar IDs no Odoo antes de modificar.

Autor: Sistema de Fretes
Data: 2026-02-14
"""

# =============================================================================
# CONTAS CONTABEIS - IDs no Odoo (account.account)
# =============================================================================

# Conta ponte para pagamentos/recebimentos pendentes de conciliacao
CONTA_PAGAMENTOS_PENDENTES = 26868  # 1110100004 PAGAMENTOS/RECEBIMENTOS PENDENTES

# Conta transitoria usada pelo Odoo em extratos bancarios
CONTA_TRANSITORIA = 22199  # 1110100003 TRANSITORIA DE VALORES

# Conta de clientes nacionais (asset_receivable)
CONTA_CLIENTES_NACIONAIS = 24801  # 1120100001 CLIENTES NACIONAIS


# =============================================================================
# CONTAS DE JUROS POR EMPRESA (para Write-Off)
# =============================================================================

# Conta 3702010003 JUROS DE RECEBIMENTOS EM ATRASO (income_other)
# Quando cliente paga valor > saldo do titulo, a diferenca vai como RECEITA
CONTA_JUROS_RECEBIMENTOS_POR_COMPANY = {
    1: 22778,  # NACOM GOYA - FB
    3: 24061,  # NACOM GOYA - SC
    4: 25345,  # NACOM GOYA - CD
    5: 26629,  # LA FAMIGLIA - LF
}

# Conta 3701010003 JUROS DE PAGAMENTOS EM ATRASO (expense)
# Quando pagamento a fornecedor tem juros (valor_pago > saldo do titulo),
# a diferenca vai como DESPESA
CONTA_JUROS_PAGAMENTOS_POR_COMPANY = {
    1: 22769,  # NACOM GOYA - FB
    3: 24051,  # NACOM GOYA - SC
    4: 25335,  # NACOM GOYA - CD
    5: 26619,  # LA FAMIGLIA - LF
}


# =============================================================================
# JOURNALS ESPECIAIS - IDs no Odoo (account.journal)
# =============================================================================

# Journals de abatimento
JOURNAL_DESCONTO_CONCEDIDO_ID = 886
JOURNAL_DESCONTO_CONCEDIDO_CODE = 'DESCO'
JOURNAL_DESCONTO_CONCEDIDO_NAME = 'DESCONTO CONCEDIDO'

JOURNAL_ACORDO_COMERCIAL_ID = 885
JOURNAL_ACORDO_COMERCIAL_CODE = 'ACORD'
JOURNAL_ACORDO_COMERCIAL_NAME = 'ACORDO COMERCIAL'

JOURNAL_DEVOLUCAO_ID = 879
JOURNAL_DEVOLUCAO_CODE = 'DEVOL'
JOURNAL_DEVOLUCAO_NAME = 'DEVOLUCAO'

# Journal padrao Grafeno (banco principal)
JOURNAL_GRAFENO_ID = 883
JOURNAL_GRAFENO_CODE = 'GRAFENO'


# =============================================================================
# MAPEAMENTO DE BANCOS CNAB PARA JOURNALS ODOO
# =============================================================================
# Chave: codigo do banco no arquivo CNAB (posicao 77-79 do header)
# Valor: dict com journal_id, code e nome
#
# FLUXO TESTADO (22/01/2026): Banco Grafeno (274) com journal GRAFENO (883)
CNAB_BANCO_PARA_JOURNAL = {
    '274': {  # BMP Money Plus / Banco Grafeno
        'journal_id': 883,
        'journal_code': 'GRAFENO',
        'journal_name': 'Banco Grafeno',
    },
    # Adicionar outros bancos conforme configurados:
    # '001': {'journal_id': ???, 'journal_code': 'BB', 'journal_name': 'Banco do Brasil'},
    # '341': {'journal_id': ???, 'journal_code': 'ITAU', 'journal_name': 'Itau'},
    # '237': {'journal_id': ???, 'journal_code': 'BRAD', 'journal_name': 'Bradesco'},
}


# =============================================================================
# MAPEAMENTO DE EMPRESA ODOO -> CODIGO INTERNO
# =============================================================================
# 1 = FB (Fabrica), 2 = SC (Santa Catarina), 3 = CD (Centro de Distribuicao)
EMPRESA_MAP = {
    'NACOM GOYA - FB': 1,
    'NACOM GOYA - SC': 2,
    'NACOM GOYA - CD': 3,
}
