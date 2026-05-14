# -*- coding: utf-8 -*-
"""
Constantes do SPED ECD Centralizado
====================================

Mapeamentos, signatarios padrao e configuracoes para gerar SPED ECD em
modalidade CENTRALIZADA (1 arquivo unico com matriz + filiais consolidadas).

Modalidade: Centralizada (IND_CENTRALIZADA=0)
Matriz: NACOM GOYA - FB (CNPJ 61.724.241/0001-78, company_id=1)
Filiais: NACOM GOYA - SC (company_id=3) + NACOM GOYA - CD (company_id=4)

Layout: SPED ECD Leiaute 9 (vigente desde 2021-12)
Manual: http://sped.rfb.gov.br/pasta/show/1569

Autor: Sistema de Fretes
Data: 2026-05-14
"""

# ============================================================
# MODALIDADE CENTRALIZADA — companies da consolidacao
# ============================================================

# IDs do Odoo (verificados em IDS_FIXOS.md)
COMPANY_MATRIZ_ID = 1                    # NACOM GOYA - FB
COMPANIES_FILIAIS = [3, 4]               # SC + CD
COMPANIES_ECD = [COMPANY_MATRIZ_ID] + COMPANIES_FILIAIS  # [1, 3, 4]
CNPJ_MATRIZ = '61724241000178'           # CNPJ FB (sem mascara)

# Companies que NAO entram na consolidacao (ECD propria por raiz CNPJ diferente)
COMPANY_LF_ID = 5                        # LA FAMIGLIA - LF (raiz 18.467.441) — gerar ECD propria

# ============================================================
# Layout SPED ECD versao
# ============================================================

LEIAUTE_VERSAO = '9.00'                  # Leiaute 9 vigente desde Dez/2021
COD_PLAN_REF = '1'                       # 1=PJ Lucro Real (decisao usuario)
IND_ESC = 'G'                            # G=Diario Completo (decisao usuario)
IND_CENTRALIZADA = '0'                   # 0=Centralizada (decisao critica do projeto)
IDENT_MF = 'M'                           # M=Matriz (FB e a matriz)
TIP_ECD = '0'                            # 0=ECD Regular (nao substituicao)
IND_FIN_ESC = '0'                        # 0=Original (nao substituicao)
IND_GRANDE_PORTE = '0'                   # 0=Nao (NACOM nao e grande porte)
IND_ESC_CONS = 'N'                       # N=Sem bloco K (consolidacao)
IND_MUDANC_PC = '0'                      # 0=Sem mudanca PC

# Limite Receita Federal: ECD a partir de 2010-01-01
DATA_LIMITE_INFERIOR = '2010-01-01'

# ============================================================
# Mapeamento account_type Odoo -> COD_NAT (Natureza da conta — I050 campo 3)
# ============================================================
# Tabela Manual ECD:
#   01 = Conta de Ativo
#   02 = Conta de Passivo
#   03 = Patrimonio Liquido
#   04 = Conta de Receita
#   05 = Conta de Custo
#   07 = Conta de Resultado
#   09 = Conta de Compensacao
#   99 = Outras

ACCOUNT_TYPE_TO_NAT = {
    # Ativo (01)
    'asset_receivable': '01', 'asset_cash': '01', 'asset_current': '01',
    'asset_non_current': '01', 'asset_prepayments': '01', 'asset_fixed': '01',
    # Passivo (02)
    'liability_payable': '02', 'liability_credit_card': '02',
    'liability_current': '02', 'liability_non_current': '02',
    # Patrimonio Liquido (03)
    'equity': '03', 'equity_unaffected': '03',
    # Receita (04)
    'income': '04', 'income_other': '04',
    # Custo/Despesa (05)
    'expense': '05', 'expense_depreciation': '05', 'expense_direct_cost': '05',
    # Compensacao (09)
    'off_balance': '09',
}

# Account types patrimoniais (Balanco Patrimonial — J100)
ACCOUNT_TYPES_PATRIMONIAIS = {
    'asset_receivable', 'asset_cash', 'asset_current',
    'asset_non_current', 'asset_prepayments', 'asset_fixed',
    'liability_payable', 'liability_credit_card',
    'liability_current', 'liability_non_current',
    'equity', 'equity_unaffected',
}

# Account types resultado (DRE — J150)
ACCOUNT_TYPES_RESULTADO = {
    'income', 'income_other',
    'expense', 'expense_depreciation', 'expense_direct_cost',
}

# ============================================================
# Mapeamento account_type Odoo -> Codigo Plano Referencial Receita (I051)
# ============================================================
# Plano Referencial PJ Lucro Real — codigos da Receita Federal
# Nivel 5 (analitica) - codigos representam grupos sem distinguir contas especificas

PLANO_REFERENCIAL = {
    # Ativo Circulante
    'asset_cash': '1.01.01.01.01.01',
    'asset_receivable': '1.01.02.01.01.01',
    'asset_current': '1.01.99.99.99.99',
    'asset_prepayments': '1.01.05.01.01.01',
    # Ativo Nao Circulante
    'asset_non_current': '1.02.99.99.99.99',
    'asset_fixed': '1.02.03.01.01.01',
    # Passivo Circulante
    'liability_payable': '2.01.02.01.01.01',
    'liability_credit_card': '2.01.04.01.01.01',
    'liability_current': '2.01.99.99.99.99',
    # Passivo Nao Circulante
    'liability_non_current': '2.02.99.99.99.99',
    # PL
    'equity': '2.03.01.01.01.01',
    'equity_unaffected': '2.03.07.01.01.01',
    # Resultado
    'income': '3.01.01.01.01.01',
    'income_other': '3.05.01.01.01.01',
    'expense': '3.02.01.01.01.01',
    'expense_direct_cost': '3.02.01.01.01.01',
    'expense_depreciation': '3.04.01.01.01.01',
    'off_balance': '',
}

# ============================================================
# Indicador Debito/Credito (D/C) por natureza da conta
# ============================================================
# Regra contabil:
#   Ativo: saldo natural DEVEDOR (D)
#   Passivo + PL: saldo natural CREDOR (C)
#   Receita: saldo natural CREDOR (C)
#   Despesa/Custo: saldo natural DEVEDOR (D)

def saldo_natural_dc(account_type: str) -> str:
    """Retorna 'D' ou 'C' do saldo natural por account_type."""
    if account_type in {'income', 'income_other'}:
        return 'C'
    if account_type.startswith('expense'):
        return 'D'
    if account_type.startswith('asset'):
        return 'D'
    if account_type.startswith('liability') or account_type.startswith('equity'):
        return 'C'
    return 'D'  # default

# ============================================================
# Signatarios padrao J930 (decisao usuario)
# ============================================================

CONTADOR_NOME = 'TAMIRIS SALLES CORDEIRO'
CONTADOR_CPF = '41832597890'                     # CPF do contador (sem mascara)
CONTADOR_EMAIL = 'tamiris.cordeiro@conservascampobelo.com.br'  # Email contato ECD
CONTADOR_CRC = '1SP041472'                       # IND_CRC: numero inscricao formato XSP123456
CONTADOR_NUM_SEQ_CRC = 'SP/2026/041472'          # NUM_SEQ_CRC: formato UF/AAAA/seq
CONTADOR_UF_CRC = 'SP'

# Sequencial extraido do CRC original 'SP-1303041/O-9' fornecido pelo usuario
# IND_CRC formato: <classe><UF><numero> -> '1SP041472' (1=titular, SP=UF, 041472=seq)

SOCIO_NOME = 'AIRTON ALVES NASCIMENTO'
SOCIO_CPF = '27428710804'

# Codigos de qualificacao do signatario (campo COD_ASSIN do J930) — Manual ECD Tabela
# Ordem: codigo, descricao
QUALIFICACOES_J930 = [
    ('001', 'Empresario'),
    ('203', 'Acionista Controlador (Pessoa Fisica)'),
    ('205', 'Administrador (Pessoa Fisica)'),
    ('206', 'Conselheiro de Administracao'),
    ('207', 'Diretor'),
    ('220', 'Procurador'),
    ('309', 'Inventariante (do Espolio)'),
    ('312', 'Liquidante (de Massa Falida)'),
    ('801', 'Empresario Individual'),
    ('900', 'Contabilista'),  # Reservado para contador
    ('999', 'Outros'),
]

QUALIFICACAO_CONTADOR = '900'           # COD_ASSIN para contabilista (sempre)

# ============================================================
# Indicadores J100 (Balanco) e J150 (DRE)
# ============================================================

# IND_GRP_BAL do J100: A=Ativo, P=Passivo+PL
IND_GRP_BAL_ATIVO = 'A'
IND_GRP_BAL_PASSIVO = 'P'

# IND_COD_AGL do J100 e J150: T=Totalizador, D=Detalhe
IND_COD_AGL_TOTAL = 'T'
IND_COD_AGL_DETALHE = 'D'

# ============================================================
# Performance — batch sizes
# ============================================================

# Batch para search_read paginado (lances de account.move.line)
BATCH_SIZE_LANCAMENTOS = 1000           # 1000 lines por round-trip XML-RPC
BATCH_SIZE_PLANO = 5000                 # plano de contas: cabe tudo num batch

# Timeout XML-RPC (seg)
TIMEOUT_QUERY_SIMPLES = 60
TIMEOUT_QUERY_PESADA = 180              # read_group multi-company

# Job RQ
JOB_TIMEOUT = '60m'                     # 60 minutos para ano inteiro
JOB_RESULT_TTL = 86400                  # 24h
PROGRESSO_TTL = 7200                    # 2h

# ============================================================
# S3 — paths para historico de geracoes
# ============================================================

S3_PREFIX_ECD = 'sped_ecd'              # bucket/sped_ecd/{user_id}/{ano}/sped_ecd_*.txt
S3_RETENCAO_DIAS = 90                   # historico de geracoes

# ============================================================
# Filas RQ
# ============================================================

QUEUE_NAME = 'sped_ecd'                 # Adicionar a worker_atacadao.py
