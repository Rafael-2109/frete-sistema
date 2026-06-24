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

# Conta 3701010002 ENCARGOS DE EMPRESTIMOS E FINANCIAMENTOS (expense)
# Usada na baixa de ANTECIPACAO (ex.: Sendas/Assai): o titulo entra liquido no banco
# (journal Sicoob) e a diferenca saldo-liquido e' o encargo financeiro da antecipacao,
# lancado como DESPESA via write-off do wizard account.payment.register.
# IMPORTANTE: a conta segue a company do JOURNAL do pagamento (Sicoob), NAO a do titulo
# — espelha o padrao validado em prod (titulo CD baixado via Sicoob FB usa encargos FB 22768).
# Confirmado no Odoo 2026-06-23 (code 3701010002 por company).
CONTA_ENCARGOS_POR_COMPANY = {
    1: 22768,  # NACOM GOYA - FB
    3: 24050,  # NACOM GOYA - SC
    4: 25334,  # NACOM GOYA - CD
    5: 26618,  # LA FAMIGLIA - LF
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

# Journal SICOOB por empresa (conta bancaria operacional). Fonte canonica aqui;
# `comprovante_lancamento_service.SICOOB_JOURNAL_POR_COMPANY` duplica este mapa
# (consolidar via import como follow-up). Validado em PROD via Odoo (2026-06-18):
# SO existe em FB(1)->10 e LF(5)->386. SC(3)/CD(4) NAO tem journal bancario proprio
# (zero journals type bank/cash) — por isso o par SICOOB+DESAGIO e estruturalmente FB/LF-only.
JOURNAL_SICOOB_POR_COMPANY = {1: 10, 5: 386}

# Journal DESAGIO (type cash) — usado no par de baixa de credores (SICOOB + DESAGIO).
# SO existe na FB (company 1). Nao existia em constants ate 2026-06-18 (era hardcoded ao vivo).
JOURNAL_DESAGIO_ID = 1025
JOURNAL_DESAGIO_CODE = 'DESAG'
JOURNAL_DESAGIO_NAME = 'DESAGIO'

# IDs reais de company no Odoo (NAO usar EMPRESA_MAP abaixo, que esta divergente:
# diz SC=2/CD=3, mas o Odoo real e SC=3/CD=4 — consistente com CONTA_JUROS_*_POR_COMPANY).
COMPANY_IDS_ODOO = {'FB': 1, 'SC': 3, 'CD': 4, 'LF': 5}
# Empresas SEM journal bancario proprio -> pagamento por banco e cross-company (conta-ponte 26868).
COMPANIES_SEM_JOURNAL_BANCARIO = {3, 4}  # SC, CD


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
