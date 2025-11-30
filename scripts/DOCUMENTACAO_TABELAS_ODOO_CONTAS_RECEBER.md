# DOCUMENTAÇÃO COMPLETA: TABELAS DO ODOO - CONTAS A RECEBER

**Data de geração:** 2025-11-28 17:09:11

## Objetivo
Documentar TODAS as tabelas do Odoo relacionadas ao Contas a Receber,
com TODOS os campos, tipos, descrições e valores de exemplo.

## Tabelas Documentadas

1. **account.move.line** - Linhas de movimento contábil - onde estão as parcelas/títulos a receber
1. **account.move** - Documentos fiscais - faturas, notas de crédito, lançamentos
1. **account.payment** - Pagamentos e recebimentos registrados no sistema
1. **account.partial.reconcile** - Reconciliações parciais - vincula débito com crédito
1. **account.full.reconcile** - Reconciliações completas - quando saldo = 0

---


================================================================================
## account.move.line
**Descrição:** Linhas de movimento contábil - onde estão as parcelas/títulos a receber
================================================================================

**Total de campos:** 315

**Exemplo encontrado:** ID = 2636115

### CAMPOS:

| # | Campo | Tipo | Label | Armazenado | Obrigatório | Valor Exemplo |
|---|-------|------|-------|------------|-------------|---------------|
| 1 | `account_id` | many2one → account.account | Account | ✅ | ❌ | [24801, '1120100001 CLIENTES NACIONAIS'] |
| 2 | `account_internal_group` | selection [equity=Equity, asset=Asset, liability=Liability, income=Income, expense=Expense... (+1)] | Internal Group | ❌ | ❌ | '-' |
| 3 | `account_root_id` | many2one → account.root | Account Root | ✅ | ❌ | '-' |
| 4 | `account_type` | selection [asset_receivable=Receivable, asset_cash=Bank and Cash, asset_current=Current Assets, asset_non_current=Non-current Assets, asset_prepayments=Prepayments... (+13)] | Internal Type | ❌ | ❌ | '-' |
| 5 | `activity_calendar_event_id` | many2one → calendar.event | Next Activity Calendar Event | ❌ | ❌ | False |
| 6 | `activity_date_deadline` | date | Next Activity Deadline | ❌ | ❌ | False |
| 7 | `activity_exception_decoration` | selection [warning=Alert, danger=Error] | Activity Exception Decoration | ❌ | ❌ | False |
| 8 | `activity_exception_icon` | char | Icon | ❌ | ❌ | False |
| 9 | `activity_ids` | one2many → mail.activity | Activities | ✅ | ❌ | [] |
| 10 | `activity_state` | selection [overdue=Overdue, today=Today, planned=Planned] | Activity State | ❌ | ❌ | False |
| 11 | `activity_summary` | char | Next Activity Summary | ❌ | ❌ | False |
| 12 | `activity_type_icon` | char | Activity Type Icon | ❌ | ❌ | False |
| 13 | `activity_type_id` | many2one → mail.activity.type | Next Activity Type | ❌ | ❌ | False |
| 14 | `activity_user_id` | many2one → res.users | Responsible User | ❌ | ❌ | False |
| 15 | `amount_currency` | monetary | Amount in Currency | ✅ | ❌ | 840.76 |
| 16 | `amount_residual` | monetary | Residual Amount | ✅ | ❌ | '-' |
| 17 | `amount_residual_currency` | monetary | Residual Amount in Currency | ✅ | ❌ | '-' |
| 18 | `analytic_distribution` | json | Analytic Distribution | ✅ | ❌ | False |
| 19 | `analytic_distribution_search` | json | Analytic Distribution Search | ❌ | ❌ | False |
| 20 | `analytic_line_ids` | one2many → account.analytic.line | Analytic lines | ✅ | ❌ | '-' |
| 21 | `analytic_precision` | integer | Analytic Precision | ❌ | ❌ | 2 |
| 22 | `asset_ids` | many2many → account.asset | Related Assets | ✅ | ❌ | '-' |
| 23 | `balance` | monetary | Balance | ✅ | ❌ | 840.76 |
| 24 | `blocked` | boolean | No Follow-up | ✅ | ❌ | '-' |
| 25 | `can_be_paid` | selection [yes=Yes, no=No, exception=Exception] | Release to Pay | ✅ | ❌ | '-' |
| 26 | `cogs_origin_id` | many2one → account.move.line | Cogs Origin | ✅ | ❌ | '-' |
| 27 | `company_currency_id` | many2one → res.currency | Company Currency | ✅ | ❌ | [6, 'BRL'] |
| 28 | `company_id` | many2one → res.company | Company | ✅ | ❌ | [4, 'NACOM GOYA - CD'] |
| 29 | `compute_all_tax` | binary | Compute All Tax | ❌ | ❌ | '-' |
| 30 | `compute_all_tax_dirty` | boolean | Compute All Tax Dirty | ❌ | ❌ | '-' |
| 31 | `create_date` | datetime | Created on | ✅ | ❌ | '-' |
| 32 | `create_uid` | many2one → res.users | Created by | ✅ | ❌ | '-' |
| 33 | `credit` | monetary | Credit | ✅ | ❌ | 0.0 |
| 34 | `cumulated_balance` | monetary | Cumulated Balance | ❌ | ❌ | 19125816.63 |
| 35 | `currency_id` | many2one → res.currency | Currency | ✅ | ✅ | [6, 'BRL'] |
| 36 | `currency_rate` | float | Currency Rate | ❌ | ❌ | 1.0 |
| 37 | `date` | date | Date | ✅ | ❌ | '2025-11-13' |
| 38 | `date_maturity` | date | Due Date | ✅ | ❌ | '-' |
| 39 | `debit` | monetary | Debit | ✅ | ❌ | 840.76 |
| 40 | `deferred_end_date` | date | End Date | ✅ | ❌ | '-' |
| 41 | `deferred_start_date` | date | Start Date | ✅ | ❌ | '-' |
| 42 | `desconto_concedido` | float | Desconto Concedido | ✅ | ❌ | '-' |
| 43 | `desconto_concedido_percentual` | float | Desconto Concedido (%) | ❌ | ❌ | '-' |
| 44 | `dfe_line_id` | many2one → l10n_br_ciel_it_account.dfe.line | Item Documento Fiscal | ✅ | ❌ | '-' |
| 45 | `discount` | float | Discount (%) | ✅ | ❌ | '-' |
| 46 | `discount_allocation_dirty` | boolean | Discount Allocation Dirty | ❌ | ❌ | '-' |
| 47 | `discount_allocation_key` | binary | Discount Allocation Key | ❌ | ❌ | '-' |
| 48 | `discount_allocation_needed` | binary | Discount Allocation Needed | ❌ | ❌ | '-' |
| 49 | `discount_amount_currency` | monetary | Discount amount in Currency | ✅ | ❌ | '-' |
| 50 | `discount_balance` | monetary | Discount Balance | ✅ | ❌ | '-' |
| 51 | `discount_date` | date | Discount Date | ✅ | ❌ | '-' |
| 52 | `display_name` | char | Display Name | ❌ | ❌ | '-' |
| 53 | `display_type` | selection [product=Product, cogs=Cost of Goods Sold, tax=Tax, discount=Discount, rounding=Rounding... (+4)] | Display Type | ✅ | ✅ | '-' |
| 54 | `distribution_analytic_account_ids` | many2many → account.analytic.account | Distribution Analytic Account | ❌ | ❌ | [] |
| 55 | `epd_dirty` | boolean | Epd Dirty | ❌ | ❌ | '-' |
| 56 | `epd_key` | binary | Epd Key | ❌ | ❌ | '-' |
| 57 | `epd_needed` | binary | Epd Needed | ❌ | ❌ | '-' |
| 58 | `expected_pay_date` | date | Expected Date | ✅ | ❌ | '-' |
| 59 | `followup_line_id` | many2one → account_followup.followup.line | Follow-up Level | ✅ | ❌ | '-' |
| 60 | `full_reconcile_id` | many2one → account.full.reconcile | Matching | ✅ | ❌ | '-' |
| 61 | `group_tax_id` | many2one → account.tax | Originator Group of Taxes | ✅ | ❌ | '-' |
| 62 | `has_abnormal_deferred_dates` | boolean | Has Abnormal Deferred Dates | ❌ | ❌ | '-' |
| 63 | `has_deferred_moves` | boolean | Has Deferred Moves | ❌ | ❌ | '-' |
| 64 | `has_message` | boolean | Has Message | ❌ | ❌ | True |
| 65 | `id` | integer | ID | ✅ | ❌ | 2636115 |
| 66 | `indice_comissao` | float | Índice de Comissão | ❌ | ❌ | '-' |
| 67 | `invoice_date` | date | Invoice/Bill Date | ✅ | ❌ | '2025-11-13' |
| 68 | `invoice_origin` | char | Origin | ❌ | ❌ | '-' |
| 69 | `is_account_reconcile` | boolean | Account Reconcile | ❌ | ❌ | '-' |
| 70 | `is_downpayment` | boolean | Is Downpayment | ✅ | ❌ | '-' |
| 71 | `is_landed_costs_line` | boolean | Is Landed Costs Line | ✅ | ❌ | '-' |
| 72 | `is_refund` | boolean | Is Refund | ❌ | ❌ | '-' |
| 73 | `is_same_currency` | boolean | Is Same Currency | ❌ | ❌ | True |
| 74 | `is_storno` | boolean | Company Storno Accounting | ❌ | ❌ | False |
| 75 | `journal_id` | many2one → account.journal | Journal | ✅ | ❌ | [826, 'VENDA DE PRODUÇÃO'] |
| 76 | `l10n_br_arquivo_cobranca_escritural_id` | many2one → l10n_br_ciel_it_account.arquivo.cobranca.escritural | Arquivo Remessa Manual | ✅ | ❌ | '-' |
| 77 | `l10n_br_calcular_imposto` | boolean | Calcular Impostos | ❌ | ❌ | '-' |
| 78 | `l10n_br_cbs_aliquota` | float | Aliquota do CBS (%) | ✅ | ❌ | '-' |
| 79 | `l10n_br_cbs_valor` | float | Valor do CBS (Tributável) | ✅ | ❌ | '-' |
| 80 | `l10n_br_cfop_codigo` | char | Código CFOP | ❌ | ❌ | '-' |
| 81 | `l10n_br_cfop_id` | many2one → l10n_br_ciel_it_account.cfop | CFOP | ✅ | ❌ | '-' |
| 82 | `l10n_br_chave_nfe_exportacao` | char | Chave NF-e Recebida p/ Exportação | ✅ | ❌ | '-' |
| 83 | `l10n_br_cobranca_arquivo_remessa` | char | Arquivo Remessa Automática | ✅ | ❌ | '-' |
| 84 | `l10n_br_cobranca_autorizacao_cartao` | char | Autorização | ❌ | ❌ | '-' |
| 85 | `l10n_br_cobranca_data_desconto` | date | Data Limite p/ Desconto | ✅ | ❌ | '-' |
| 86 | `l10n_br_cobranca_idintegracao` | char | Id Integração | ✅ | ❌ | '-' |
| 87 | `l10n_br_cobranca_nossonumero` | char | Nosso Numero | ✅ | ❌ | '-' |
| 88 | `l10n_br_cobranca_nsu_cartao` | char | NSU | ❌ | ❌ | '-' |
| 89 | `l10n_br_cobranca_numero_cartao` | char | Número do Cartão | ❌ | ❌ | '-' |
| 90 | `l10n_br_cobranca_parcela` | integer | Parcela | ✅ | ❌ | '-' |
| 91 | `l10n_br_cobranca_parcela_manual_linha_id` | many2one → l10n_br_ciel_it_account.payment.parcela.manual.linhas | Parcela Personalizada | ✅ | ❌ | '-' |
| 92 | `l10n_br_cobranca_protocolo` | char | Protocolo | ✅ | ❌ | '-' |
| 93 | `l10n_br_cobranca_situacao` | selection [SALVO=Salvo, PENDENTE_RETENTATIVA=Pendente, FALHA=Falha, EMITIDO=Emitido, REJEITADO=Rejeitado... (+3)] | Situação | ✅ | ❌ | '-' |
| 94 | `l10n_br_cobranca_situacao_mensagem` | char | Mensagem | ✅ | ❌ | '-' |
| 95 | `l10n_br_cobranca_tipo_desconto` | selection [0=0 - Sem instrução de desconto., 1=1 - Valor Fixo Até a Data Informada., 2=2 - Percentual Até a Data Informada., 3=3 - Valor por Antecipação Dia Corrido.., 4=4 - Valor por Antecipação Dia Útil.... (+2)] | Tipo Desconto | ✅ | ❌ | '-' |
| 96 | `l10n_br_cobranca_transmissao` | selection [webservice=Webservice / Ecommerce, automatico=Remessa Automática (VAN), manual=Remessa Manual (Internet Bank)] | Tipo Transmissão | ✅ | ❌ | '-' |
| 97 | `l10n_br_cobranca_valor_desconto` | float | Valor Desconto | ✅ | ❌ | '-' |
| 98 | `l10n_br_codigo_beneficio` | char | Código do Benefício Fiscal | ✅ | ❌ | '-' |
| 99 | `l10n_br_codigo_servico` | char | Código Serviço | ❌ | ❌ | '-' |
| 100 | `l10n_br_codigo_tributacao_servico` | char | Código Tributação Serviço | ❌ | ❌ | '-' |
| 101 | `l10n_br_cofins_aliquota` | float | Aliquota do Cofins (%) | ✅ | ❌ | '-' |
| 102 | `l10n_br_cofins_base` | float | Valor da Base de Cálculo do Cofins | ✅ | ❌ | '-' |
| 103 | `l10n_br_cofins_cst` | selection [01=01 - Operação Tributável com Alíquota Básica, 02=02 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 03=03 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 04=04 - Operação Tributável Monofásica - Revenda a Alíquota Zero, 05=05 - Operação Tributável por Substituição Tributária... (+28)] | Código de Situação Tributária do Cofins | ✅ | ❌ | '-' |
| 104 | `l10n_br_cofins_ret_aliquota` | float | Aliquota do Cofins (%) Retido | ✅ | ❌ | '-' |
| 105 | `l10n_br_cofins_ret_base` | float | Valor da Base de Cálculo do Cofins Retido | ✅ | ❌ | '-' |
| 106 | `l10n_br_cofins_ret_valor` | float | Valor do Cofins Retido | ✅ | ❌ | '-' |
| 107 | `l10n_br_cofins_valor` | float | Valor do Cofins (Tributável) | ✅ | ❌ | '-' |
| 108 | `l10n_br_cofins_valor_isento` | float | Valor do Cofins (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 109 | `l10n_br_cofins_valor_outros` | float | Valor do Cofins (Outros) | ✅ | ❌ | '-' |
| 110 | `l10n_br_compra_indcom` | selection [uso=Uso e Consumo, uso-prestacao=Uso na Prestação de Serviço, ind=Industrialização, com=Comercialização, ativo=Ativo... (+2)] | Destinação de Uso | ✅ | ❌ | '-' |
| 111 | `l10n_br_csll_aliquota` | float | Aliquota do CSLL (%) | ✅ | ❌ | '-' |
| 112 | `l10n_br_csll_base` | float | Valor da Base de Cálculo do CSLL | ✅ | ❌ | '-' |
| 113 | `l10n_br_csll_ret_aliquota` | float | Aliquota do CSLL (%) Retido | ✅ | ❌ | '-' |
| 114 | `l10n_br_csll_ret_base` | float | Valor da Base de Cálculo do CSLL Retido | ✅ | ❌ | '-' |
| 115 | `l10n_br_csll_ret_valor` | float | Valor do CSLL Retido | ✅ | ❌ | '-' |
| 116 | `l10n_br_csll_valor` | float | Valor do CSLL | ✅ | ❌ | '-' |
| 117 | `l10n_br_dados_pagamento_id` | one2many → l10n_br_ciel_it_account.dados.pagamento | Dados de Pagamento (CNAB) | ✅ | ❌ | '-' |
| 118 | `l10n_br_desc_valor` | float | Valor do Desconto | ✅ | ❌ | '-' |
| 119 | `l10n_br_despesas_acessorias` | float | Despesas Acessórias | ✅ | ❌ | '-' |
| 120 | `l10n_br_di_adicao_id` | many2one → l10n_br_ciel_it_account.di.adicao | DI/Adição | ✅ | ❌ | '-' |
| 121 | `l10n_br_drawback` | char | Número Drawback | ✅ | ❌ | '-' |
| 122 | `l10n_br_fcp_base` | float | Valor da Base do Fundo de Combate a Pobreza | ✅ | ❌ | '-' |
| 123 | `l10n_br_fcp_dest_aliquota` | float | Aliquota do Fundo de Combate a Pobreza (%) | ✅ | ❌ | '-' |
| 124 | `l10n_br_fcp_dest_valor` | float | Valor do Fundo de Combate a Pobreza | ✅ | ❌ | '-' |
| 125 | `l10n_br_fcp_st_aliquota` | float | Aliquota do Fundo de Combate a Pobreza (%) retido por ST | ✅ | ❌ | '-' |
| 126 | `l10n_br_fcp_st_ant_aliquota` | float | Aliquota do Fundo de Combate a Pobreza (%) retido anteriormente por ST | ✅ | ❌ | '-' |
| 127 | `l10n_br_fcp_st_ant_base` | float | Valor da Base do Fundo de Combate a Pobreza retido anteriormente por ST | ✅ | ❌ | '-' |
| 128 | `l10n_br_fcp_st_ant_valor` | float | Valor do Fundo de Combate a Pobreza retido anteriormente por ST | ✅ | ❌ | '-' |
| 129 | `l10n_br_fcp_st_base` | float | Valor da Base do Fundo de Combate a Pobreza retido por ST | ✅ | ❌ | '-' |
| 130 | `l10n_br_fcp_st_valor` | float | Valor do Fundo de Combate a Pobreza retido por ST | ✅ | ❌ | '-' |
| 131 | `l10n_br_frete` | float | Frete | ✅ | ❌ | '-' |
| 132 | `l10n_br_ibs_mun_aliquota` | float | Aliquota do IBS Município (%) | ✅ | ❌ | '-' |
| 133 | `l10n_br_ibs_mun_valor` | float | Valor do IBS Município (Tributável) | ✅ | ❌ | '-' |
| 134 | `l10n_br_ibs_uf_aliquota` | float | Aliquota do IBS UF (%) | ✅ | ❌ | '-' |
| 135 | `l10n_br_ibs_uf_valor` | float | Valor do IBS UF (Tributável) | ✅ | ❌ | '-' |
| 136 | `l10n_br_ibs_valor` | float | Valor do IBS (Tributável) | ✅ | ❌ | '-' |
| 137 | `l10n_br_ibscbs_base` | float | Valor da Base de Cálculo do IBS/CBS | ✅ | ❌ | '-' |
| 138 | `l10n_br_ibscbs_classtrib_id` | many2one → l10n_br_ciel_it_account.classificacao.tributaria.ibscbs | Classificação Tributária do IBS/CBS | ✅ | ❌ | '-' |
| 139 | `l10n_br_ibscbs_cst` | selection [000=000 - Tributação integral, 010=010 - Tributação com alíquotas uniformes, 011=011 - Tributação com alíquotas uniformes reduzidas, 200=200 - Alíquota reduzida, 210=210 - Redução de alíquota com redutor de base de cálculo... (+14)] | Código de Situação Tributária do IBS/CBS | ✅ | ❌ | '-' |
| 140 | `l10n_br_icms_ajuste_ids` | one2many → l10n_br_ciel_it_account.icms.ajuste.line | Ajuste de ICMS | ✅ | ❌ | '-' |
| 141 | `l10n_br_icms_aliquota` | float | Aliquota do ICMS (%) | ✅ | ❌ | '-' |
| 142 | `l10n_br_icms_base` | float | Valor da Base de Cálculo do ICMS | ✅ | ❌ | '-' |
| 143 | `l10n_br_icms_credito_aliquota` | float | Alíquota aplicável de cálculo do crédito (Simples Nacional) | ✅ | ❌ | '-' |
| 144 | `l10n_br_icms_credito_valor` | float | Valor crédito do ICMS que pode ser aproveitado | ✅ | ❌ | '-' |
| 145 | `l10n_br_icms_cst` | selection [00=00 - Tributada integralmente, 10=10 - Tributada e com cobrança do ICMS-ST, 20=20 - Com redução de base de cálculo, 30=30 - Isenta ou não tributada e com cobrança do ICMS-ST, 40=40 - Isenta... (+16)] | Código de Situação Tributária do ICMS | ✅ | ❌ | '-' |
| 146 | `l10n_br_icms_dest_aliquota` | float | Aliquota do ICMS UF Destino (%) | ✅ | ❌ | '-' |
| 147 | `l10n_br_icms_dest_base` | float | Valor da Base de Cálculo do ICMS UF Destino | ✅ | ❌ | '-' |
| 148 | `l10n_br_icms_dest_valor` | float | Valor do ICMS UF Destino | ✅ | ❌ | '-' |
| 149 | `l10n_br_icms_diferido_aliquota` | float | Aliquota do ICMS Diferido (%) | ✅ | ❌ | '-' |
| 150 | `l10n_br_icms_diferido_valor` | float | Valor do ICMS Diferido | ✅ | ❌ | '-' |
| 151 | `l10n_br_icms_diferido_valor_operacao` | float | Valor do ICMS da Operação | ✅ | ❌ | '-' |
| 152 | `l10n_br_icms_inter_aliquota` | float | Aliquota do ICMS Interestadual (%) | ✅ | ❌ | '-' |
| 153 | `l10n_br_icms_inter_participacao` | float | Participação da Aliquota do ICMS Interestadual (%) | ✅ | ❌ | '-' |
| 154 | `l10n_br_icms_modalidade_base` | selection [0=0 - Margem Valor Agregado (%), 1=1 - Pauta (Valor), 2=2 - Preço Tabelado Máx. (valor), 3=3 - Valor da operação] | Modalidade de Determinação da BC do ICMS | ✅ | ❌ | '-' |
| 155 | `l10n_br_icms_motivo_desonerado` | selection [1=1 - Táxi;, 2=2 - Deficiente Físico (Revogado);, 3=3 - Produtor Agropecuário;, 4=4 - Frotista/Locadora;, 5=5 - Diplomático/Consular;... (+9)] | Motivo Desoneração do ICMS | ✅ | ❌ | '-' |
| 156 | `l10n_br_icms_reducao_base` | float | Aliquota de Redução da BC do ICMS (%) | ✅ | ❌ | '-' |
| 157 | `l10n_br_icms_remet_valor` | float | Valor do ICMS UF Remetente | ✅ | ❌ | '-' |
| 158 | `l10n_br_icms_valor` | float | Valor do ICMS (Tributável) | ✅ | ❌ | '-' |
| 159 | `l10n_br_icms_valor_credito_presumido` | float | Valor do ICMS (Crédito Presumido) | ✅ | ❌ | '-' |
| 160 | `l10n_br_icms_valor_desonerado` | float | Valor do ICMS (Desonerado) | ✅ | ❌ | '-' |
| 161 | `l10n_br_icms_valor_efetivo` | float | Valor do ICMS (Efetivo) | ✅ | ❌ | '-' |
| 162 | `l10n_br_icms_valor_isento` | float | Valor do ICMS (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 163 | `l10n_br_icms_valor_outros` | float | Valor do ICMS (Outros) | ✅ | ❌ | '-' |
| 164 | `l10n_br_icmsst_aliquota` | float | Aliquota do ICMSST (%) | ✅ | ❌ | '-' |
| 165 | `l10n_br_icmsst_base` | float | Valor da Base de Cálculo do ICMSST | ✅ | ❌ | '-' |
| 166 | `l10n_br_icmsst_base_propria_aliquota` | float | Alíquota da Base de Cálculo da Operação Própria | ✅ | ❌ | '-' |
| 167 | `l10n_br_icmsst_modalidade_base` | selection [0=0 - Preço tabelado ou máximo sugerido, 1=1 - Lista Negativa (valor), 2=2 - Lista Positiva (valor), 3=3 - Lista Neutra (valor), 4=4 - Margem Valor Agregado (%)... (+2)] | Modalidade de Determinação da BC do ICMSST | ✅ | ❌ | '-' |
| 168 | `l10n_br_icmsst_mva` | float | Aliquota da Margem de Valor Adicionado do ICMSST (%) | ✅ | ❌ | '-' |
| 169 | `l10n_br_icmsst_reducao_base` | float | Aliquota de Redução da BC do ICMSST (%) | ✅ | ❌ | '-' |
| 170 | `l10n_br_icmsst_retido_aliquota` | float | Alíquota suportada pelo Consumidor Final (%) | ✅ | ❌ | '-' |
| 171 | `l10n_br_icmsst_retido_base` | float | Valor da Base de Cálculo do ICMSST Retido | ✅ | ❌ | '-' |
| 172 | `l10n_br_icmsst_retido_valor` | float | Valor do ICMSST Retido | ✅ | ❌ | '-' |
| 173 | `l10n_br_icmsst_retido_valor_outros` | float | Valor do ICMSST Retido (Outros) | ✅ | ❌ | '-' |
| 174 | `l10n_br_icmsst_substituto_valor` | float | Valor do ICMS próprio do Substituto | ✅ | ❌ | '-' |
| 175 | `l10n_br_icmsst_substituto_valor_outros` | float | Valor do ICMS próprio do Substituto (Outros) | ✅ | ❌ | '-' |
| 176 | `l10n_br_icmsst_uf` | char | UF para qual é devido o ICMSST | ✅ | ❌ | '-' |
| 177 | `l10n_br_icmsst_valor` | float | Valor do ICMSST | ✅ | ❌ | '-' |
| 178 | `l10n_br_icmsst_valor_outros` | float | Valor do ICMSST (Outros) | ✅ | ❌ | '-' |
| 179 | `l10n_br_icmsst_valor_proprio` | float | Valor do ICMSST (Próprio) | ✅ | ❌ | '-' |
| 180 | `l10n_br_ii_aliquota` | float | Aliquota do II (%) | ✅ | ❌ | '-' |
| 181 | `l10n_br_ii_base` | float | Valor da Base de Cálculo do II | ✅ | ❌ | '-' |
| 182 | `l10n_br_ii_valor` | float | Valor do II (Tributável) | ✅ | ❌ | '-' |
| 183 | `l10n_br_ii_valor_aduaneira` | float | Valor do II (Aduaneira) | ✅ | ❌ | '-' |
| 184 | `l10n_br_ii_valor_afrmm` | float | Valor do II (AFRMM) | ✅ | ❌ | '-' |
| 185 | `l10n_br_imposto_auto` | boolean | Calcular Impostos Automaticamente | ✅ | ❌ | '-' |
| 186 | `l10n_br_informacao_adicional` | text | Informações Adicionais | ✅ | ❌ | '-' |
| 187 | `l10n_br_informacao_adicional_produto_ids` | many2many → l10n_br_ciel_it_account.mensagem.fiscal | Informação Adicional do Produto | ✅ | ❌ | '-' |
| 188 | `l10n_br_inss_ret_aliquota` | float | Aliquota do INSS Retido (%) | ✅ | ❌ | '-' |
| 189 | `l10n_br_inss_ret_base` | float | Valor da Base de Cálculo do INSS Retido | ✅ | ❌ | '-' |
| 190 | `l10n_br_inss_ret_valor` | float | Valor do INSS Retido | ✅ | ❌ | '-' |
| 191 | `l10n_br_iof_valor` | float | Valor do IOF | ✅ | ❌ | '-' |
| 192 | `l10n_br_ipi_aliquota` | float | Aliquota do IPI (%) | ✅ | ❌ | '-' |
| 193 | `l10n_br_ipi_base` | float | Valor da Base de Cálculo do IPI | ✅ | ❌ | '-' |
| 194 | `l10n_br_ipi_cnpj` | char | CNPJ do produtor da mercadoria | ✅ | ❌ | '-' |
| 195 | `l10n_br_ipi_cst` | selection [00=00 - Entrada com Recuperação de Crédito, 01=01 - Entrada Tributável com Alíquota Zero, 02=02 - Entrada Isenta, 03=03 - Entrada Não-Tributada, 04=04 - Entrada Imune... (+9)] | Código de Situação Tributária do IPI | ✅ | ❌ | '-' |
| 196 | `l10n_br_ipi_enq` | char | Código Enquadramento | ✅ | ❌ | '-' |
| 197 | `l10n_br_ipi_selo_codigo` | char | Código do selo de controle IPI | ✅ | ❌ | '-' |
| 198 | `l10n_br_ipi_selo_quantidade` | integer | Quantidade de selo de controle | ✅ | ❌ | '-' |
| 199 | `l10n_br_ipi_valor` | float | Valor do IPI (Tributável) | ✅ | ❌ | '-' |
| 200 | `l10n_br_ipi_valor_isento` | float | Valor do IPI (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 201 | `l10n_br_ipi_valor_outros` | float | Valor do IPI (Outros) | ✅ | ❌ | '-' |
| 202 | `l10n_br_irpj_aliquota` | float | Aliquota do IRPJ (%) | ✅ | ❌ | '-' |
| 203 | `l10n_br_irpj_base` | float | Valor da Base de Cálculo do IRPJ | ✅ | ❌ | '-' |
| 204 | `l10n_br_irpj_ret_aliquota` | float | Aliquota do IRPJ Retido (%) | ✅ | ❌ | '-' |
| 205 | `l10n_br_irpj_ret_base` | float | Valor da Base de Cálculo do IRPJ Retido | ✅ | ❌ | '-' |
| 206 | `l10n_br_irpj_ret_valor` | float | Valor do IRPJ Retido | ✅ | ❌ | '-' |
| 207 | `l10n_br_irpj_valor` | float | Valor do IRPJ | ✅ | ❌ | '-' |
| 208 | `l10n_br_is_aliquota` | float | Aliquota do IS (%) | ✅ | ❌ | '-' |
| 209 | `l10n_br_is_base` | float | Valor da Base de Cálculo do IS | ✅ | ❌ | '-' |
| 210 | `l10n_br_is_classtrib_id` | many2one → l10n_br_ciel_it_account.classificacao.tributaria.is | Classificação Tributária do IS | ✅ | ❌ | '-' |
| 211 | `l10n_br_is_cst` | selection [00=00 - Tabela não divulgada] | Código de Situação Tributária do IS | ✅ | ❌ | '-' |
| 212 | `l10n_br_is_valor` | float | Valor do IS (Tributável) | ✅ | ❌ | '-' |
| 213 | `l10n_br_iss_aliquota` | float | Aliquota do ISS (%) | ✅ | ❌ | '-' |
| 214 | `l10n_br_iss_base` | float | Valor da Base de Cálculo do ISS | ✅ | ❌ | '-' |
| 215 | `l10n_br_iss_deducao` | float | Valor da Dedução para efeito de Base de Cálculo do ISS | ✅ | ❌ | '-' |
| 216 | `l10n_br_iss_ret_aliquota` | float | Aliquota do ISS Retido (%) | ✅ | ❌ | '-' |
| 217 | `l10n_br_iss_ret_base` | float | Valor da Base de Cálculo do ISS Retido | ✅ | ❌ | '-' |
| 218 | `l10n_br_iss_ret_valor` | float | Valor do ISS Retido | ✅ | ❌ | '-' |
| 219 | `l10n_br_iss_valor` | float | Valor do ISS | ✅ | ❌ | '-' |
| 220 | `l10n_br_item_pedido_compra` | char | Item Pedido de Compra do Cliente | ✅ | ❌ | '-' |
| 221 | `l10n_br_meio` | selection [01=Dinheiro, 02=Cheque, 03=Cartão de Crédito, 04=Cartão de Débito, 05=Crédito Loja... (+15)] | Meio de Pagamento | ❌ | ❌ | '-' |
| 222 | `l10n_br_mensagem_fiscal_ids` | many2many → l10n_br_ciel_it_account.mensagem.fiscal | Observação Fiscal | ✅ | ❌ | '-' |
| 223 | `l10n_br_nat_bc_cred` | selection [01=Aquisição de bens para revenda, 02=Aquisição de bens utilizados como insumo, 03=Aquisição de serviços utilizados como insumo, 04=Energia elétrica e térmica, inclusive sob a forma de vapor, 05=Aluguéis de prédios... (+13)] | Natureza da Base de Cálculo dos Créditos | ✅ | ❌ | '-' |
| 224 | `l10n_br_nat_rec` | char | Natureza da Receita | ✅ | ❌ | '-' |
| 225 | `l10n_br_ncm_id` | many2one → l10n_br_ciel_it_account.ncm | NCM | ❌ | ❌ | '-' |
| 226 | `l10n_br_operacao_id` | many2one → l10n_br_ciel_it_account.operacao | Operação | ✅ | ❌ | '-' |
| 227 | `l10n_br_operacao_manual` | boolean | Definir Operação Manual | ✅ | ❌ | '-' |
| 228 | `l10n_br_origem` | selection [0=0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8;, 1=1 - Estrangeira - Importação direta, exceto a indicada no código 6;, 2=2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7;, 3=3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70%;, 4=4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de quetratam as legislações citadas nos Ajustes;... (+4)] | Origem do Produto | ✅ | ❌ | '-' |
| 229 | `l10n_br_paga` | boolean | Parcela Paga? | ✅ | ❌ | '-' |
| 230 | `l10n_br_pdf_boleto` | binary | Boleto | ✅ | ❌ | '-' |
| 231 | `l10n_br_pdf_boleto_fname` | char | Arquivo Boleto | ❌ | ❌ | '-' |
| 232 | `l10n_br_pedido_compra` | char | Pedido de Compra do Cliente | ✅ | ❌ | '-' |
| 233 | `l10n_br_pis_aliquota` | float | Aliquota do PIS (%) | ✅ | ❌ | '-' |
| 234 | `l10n_br_pis_base` | float | Valor da Base de Cálculo do PIS | ✅ | ❌ | '-' |
| 235 | `l10n_br_pis_cst` | selection [01=01 - Operação Tributável com Alíquota Básica, 02=02 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 03=03 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 04=04 - Operação Tributável Monofásica - Revenda a Alíquota Zero, 05=05 - Operação Tributável por Substituição Tributária... (+28)] | Código de Situação Tributária do PIS | ✅ | ❌ | '-' |
| 236 | `l10n_br_pis_ret_aliquota` | float | Aliquota do PIS (%) Retido | ✅ | ❌ | '-' |
| 237 | `l10n_br_pis_ret_base` | float | Valor da Base de Cálculo do PIS Retido | ✅ | ❌ | '-' |
| 238 | `l10n_br_pis_ret_valor` | float | Valor do PIS Retido | ✅ | ❌ | '-' |
| 239 | `l10n_br_pis_valor` | float | Valor do PIS (Tributável) | ✅ | ❌ | '-' |
| 240 | `l10n_br_pis_valor_isento` | float | Valor do PIS (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 241 | `l10n_br_pis_valor_outros` | float | Valor do PIS (Outros) | ✅ | ❌ | '-' |
| 242 | `l10n_br_prod_valor` | float | Valor do Produto | ✅ | ❌ | '-' |
| 243 | `l10n_br_registro_exportacao` | char | Registro de Exportação | ✅ | ❌ | '-' |
| 244 | `l10n_br_seguro` | float | Seguro | ✅ | ❌ | '-' |
| 245 | `l10n_br_tipo_pedido` | selection [baixa-estoque=Saída: Baixa de Estoque, complemento-valor=Saída: Complemento de Preço, dev-comodato=Saída: Devolução de Comodato, compra=Saída: Devolução de Compra, dev-conserto=Saída: Devolução de Conserto... (+42)] | Tipo de Pedido (saída) | ✅ | ❌ | '-' |
| 246 | `l10n_br_tipo_pedido_entrada` | selection [ent-amostra=Entrada: Amostra Grátis, ent-bonificacao=Entrada: Bonificação, ent-comodato=Entrada: Comodato, comp-importacao=Entrada: Complementar de Importação, compra=Entrada: Compra... (+33)] | Tipo de Pedido (entrada) | ✅ | ❌ | '-' |
| 247 | `l10n_br_tipo_pedido_str` | char | Tipo de Pedido | ✅ | ❌ | '-' |
| 248 | `l10n_br_total_nfe` | float | Valor Total do Item da NF | ✅ | ❌ | '-' |
| 249 | `l10n_br_total_tributos` | float | Valor dos Tributos | ✅ | ❌ | '-' |
| 250 | `l10n_br_unit_nfe` | float | Valor Unitário do Item da NF | ✅ | ❌ | '-' |
| 251 | `l10n_br_unit_tax` | float | Valor Unitário com Imposto | ✅ | ❌ | '-' |
| 252 | `l10n_br_unit_tax_recompute` | boolean | Recompute Unit Tax | ✅ | ❌ | '-' |
| 253 | `last_followup_date` | date | Latest Follow-up | ✅ | ❌ | '-' |
| 254 | `matched_credit_ids` | one2many → account.partial.reconcile | Matched Credits | ✅ | ❌ | '-' |
| 255 | `matched_debit_ids` | one2many → account.partial.reconcile | Matched Debits | ✅ | ❌ | '-' |
| 256 | `matching_number` | char | Matching # | ✅ | ❌ | '-' |
| 257 | `message_attachment_count` | integer | Attachment Count | ❌ | ❌ | 0 |
| 258 | `message_follower_ids` | one2many → mail.followers | Followers | ✅ | ❌ | [] |
| 259 | `message_has_error` | boolean | Message Delivery error | ❌ | ❌ | False |
| 260 | `message_has_error_counter` | integer | Number of errors | ❌ | ❌ | 0 |
| 261 | `message_has_sms_error` | boolean | SMS Delivery error | ❌ | ❌ | False |
| 262 | `message_ids` | one2many → mail.message | Messages | ✅ | ❌ | [7 itens: [12279208, 12095931, 12075319]...] |
| 263 | `message_is_follower` | boolean | Is Follower | ❌ | ❌ | False |
| 264 | `message_needaction` | boolean | Action Needed | ❌ | ❌ | False |
| 265 | `message_needaction_counter` | integer | Number of Actions | ❌ | ❌ | 0 |
| 266 | `message_partner_ids` | many2many → res.partner | Followers (Partners) | ❌ | ❌ | [] |
| 267 | `move_attachment_ids` | one2many → ir.attachment | Move Attachment | ❌ | ❌ | '-' |
| 268 | `move_id` | many2one → account.move | Journal Entry | ✅ | ✅ | [404387, 'NF-e: 141787 Série: 1 - VND/2025/05103'] |
| 269 | `move_name` | char | Number | ✅ | ❌ | 'VND/2025/05103' |
| 270 | `move_type` | selection [entry=Journal Entry, out_invoice=Customer Invoice, out_refund=Customer Credit Note, in_invoice=Vendor Bill, in_refund=Vendor Credit Note... (+2)] | Type | ❌ | ❌ | 'out_invoice' |
| 271 | `my_activity_date_deadline` | date | My Activity Deadline | ❌ | ❌ | False |
| 272 | `name` | char | Label | ✅ | ❌ | 'VND/2025/05103 parcela nº1' |
| 273 | `next_action_date` | date | Next Action Date | ✅ | ❌ | '-' |
| 274 | `non_deductible_tax_value` | monetary | Non Deductible Tax Value | ❌ | ❌ | '-' |
| 275 | `parent_state` | selection [draft=Draft, posted=Posted, cancel=Cancelled] | Status | ✅ | ❌ | 'posted' |
| 276 | `partner_id` | many2one → res.partner | Partner | ✅ | ❌ | '-' |
| 277 | `payment_date` | date | Payment Date | ❌ | ❌ | '-' |
| 278 | `payment_id` | many2one → account.payment | Originator Payment | ✅ | ❌ | '-' |
| 279 | `payment_provider_id` | many2one → payment.provider | Forma de Pagamento | ✅ | ❌ | '-' |
| 280 | `price_subtotal` | monetary | Subtotal | ✅ | ❌ | '-' |
| 281 | `price_total` | monetary | Total | ✅ | ❌ | '-' |
| 282 | `price_unit` | float | Unit Price | ✅ | ❌ | '-' |
| 283 | `product_id` | many2one → product.product | Product | ✅ | ❌ | '-' |
| 284 | `product_type` | selection [consu=Consumable, service=Service, product=Storable Product] | Product Type | ❌ | ❌ | '-' |
| 285 | `product_uom_category_id` | many2one → uom.category | Category | ❌ | ❌ | '-' |
| 286 | `product_uom_id` | many2one → uom.uom | Unit of Measure | ✅ | ❌ | '-' |
| 287 | `purchase_line_id` | many2one → purchase.order.line | Purchase Order Line | ✅ | ❌ | '-' |
| 288 | `purchase_order_id` | many2one → purchase.order | Purchase Order | ❌ | ❌ | '-' |
| 289 | `quantity` | float | Quantity | ✅ | ❌ | '-' |
| 290 | `rating_ids` | one2many → rating.rating | Ratings | ✅ | ❌ | [] |
| 291 | `reconcile_model_id` | many2one → account.reconcile.model | Reconciliation Model | ✅ | ❌ | '-' |
| 292 | `reconciled` | boolean | Reconciled | ✅ | ❌ | '-' |
| 293 | `ref` | char | Reference | ✅ | ❌ | '' |
| 294 | `sale_line_id` | many2one → sale.order.line | Sale Line | ✅ | ❌ | '-' |
| 295 | `sale_line_ids` | many2many → sale.order.line | Sales Order Lines | ✅ | ❌ | '-' |
| 296 | `sequence` | integer | Sequence | ✅ | ❌ | 12000 |
| 297 | `statement_id` | many2one → account.bank.statement | Statement | ✅ | ❌ | '-' |
| 298 | `statement_line_id` | many2one → account.bank.statement.line | Originator Statement Line | ✅ | ❌ | '-' |
| 299 | `stock_valuation_layer_ids` | one2many → stock.valuation.layer | Stock Valuation Layer | ✅ | ❌ | '-' |
| 300 | `tax_base_amount` | monetary | Base Amount | ✅ | ❌ | '-' |
| 301 | `tax_calculation_rounding_method` | selection [round_per_line=Round per Line, round_globally=Round Globally] | Tax calculation rounding method | ❌ | ❌ | '-' |
| 302 | `tax_group_id` | many2one → account.tax.group | Originator tax group | ✅ | ❌ | '-' |
| 303 | `tax_ids` | many2many → account.tax | Taxes | ✅ | ❌ | '-' |
| 304 | `tax_key` | binary | Tax Key | ❌ | ❌ | '-' |
| 305 | `tax_line_id` | many2one → account.tax | Originator Tax | ✅ | ❌ | '-' |
| 306 | `tax_repartition_line_id` | many2one → account.tax.repartition.line | Originator Tax Distribution Line | ✅ | ❌ | '-' |
| 307 | `tax_tag_ids` | many2many → account.account.tag | Tags | ✅ | ❌ | '-' |
| 308 | `tax_tag_invert` | boolean | Invert Tags | ✅ | ❌ | '-' |
| 309 | `term_key` | binary | Term Key | ❌ | ❌ | '-' |
| 310 | `website_message_ids` | one2many → mail.message | Website Messages | ✅ | ❌ | [] |
| 311 | `write_date` | datetime | Last Updated on | ✅ | ❌ | '-' |
| 312 | `write_uid` | many2one → res.users | Last Updated by | ✅ | ❌ | '-' |
| 313 | `x_studio_nf_e` | char | NF-e | ✅ | ❌ | '-' |
| 314 | `x_studio_status_de_pagamento` | selection [not_paid=Not Paid, in_payment=In Payment, paid=Paid, partial=Partially Paid, reversed=Reversed... (+1)] | Status de Pagamento | ✅ | ❌ | '-' |
| 315 | `x_studio_tipo_de_documento_fiscal` | selection [NFS=Nota Fiscal de Serviços Instituída por Municípios, NFSE=Nota Fiscal de Serviços Eletrônica - NFS-e, NDS=Nota de Débito de Serviços, FAT=Fatura, ND=Nota de Débito... (+32)] | Tipo de Documento Fiscal | ✅ | ❌ | '-' |


### DETALHAMENTO DOS CAMPOS:

#### `account_id`
- **Label:** Account
- **Tipo:** many2one → account.account
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.account`
- **Valor Exemplo:** `[24801, '1120100001 CLIENTES NACIONAIS']`

#### `account_internal_group`
- **Label:** Internal Group
- **Tipo:** selection [equity=Equity, asset=Asset, liability=Liability, income=Income, expense=Expense... (+1)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['equity', 'Equity'], ['asset', 'Asset'], ['liability', 'Liability'], ['income', 'Income'], ['expense', 'Expense'], ['off_balance', 'Off Balance']]

#### `account_root_id`
- **Label:** Account Root
- **Tipo:** many2one → account.root
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.root`

#### `account_type`
- **Label:** Internal Type
- **Tipo:** selection [asset_receivable=Receivable, asset_cash=Bank and Cash, asset_current=Current Assets, asset_non_current=Non-current Assets, asset_prepayments=Prepayments... (+13)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['asset_receivable', 'Receivable'], ['asset_cash', 'Bank and Cash'], ['asset_current', 'Current Assets'], ['asset_non_current', 'Non-current Assets'], ['asset_prepayments', 'Prepayments'], ['asset_fixed', 'Fixed Assets'], ['liability_payable', 'Payable'], ['liability_credit_card', 'Credit Card'], ['liability_current', 'Current Liabilities'], ['liability_non_current', 'Non-current Liabilities'], ['equity', 'Equity'], ['equity_unaffected', 'Current Year Earnings'], ['income', 'Income'], ['income_other', 'Other Income'], ['expense', 'Expenses'], ['expense_depreciation', 'Depreciation'], ['expense_direct_cost', 'Cost of Revenue'], ['off_balance', 'Off-Balance Sheet']]
- **Descrição:** Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.

#### `activity_calendar_event_id`
- **Label:** Next Activity Calendar Event
- **Tipo:** many2one → calendar.event
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `calendar.event`
- **Valor Exemplo:** `False`

#### `activity_date_deadline`
- **Label:** Next Activity Deadline
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `activity_exception_decoration`
- **Label:** Activity Exception Decoration
- **Tipo:** selection [warning=Alert, danger=Error]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['warning', 'Alert'], ['danger', 'Error']]
- **Descrição:** Type of the exception activity on record.
- **Valor Exemplo:** `False`

#### `activity_exception_icon`
- **Label:** Icon
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Icon to indicate an exception activity.
- **Valor Exemplo:** `False`

#### `activity_ids`
- **Label:** Activities
- **Tipo:** one2many → mail.activity
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.activity`
- **Valor Exemplo:** `[]`

#### `activity_state`
- **Label:** Activity State
- **Tipo:** selection [overdue=Overdue, today=Today, planned=Planned]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']]
- **Descrição:** Status based on activities
Overdue: Due date is already passed
Today: Activity date is today
Planned: Future activities.
- **Valor Exemplo:** `False`

#### `activity_summary`
- **Label:** Next Activity Summary
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `activity_type_icon`
- **Label:** Activity Type Icon
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Font awesome icon e.g. fa-tasks
- **Valor Exemplo:** `False`

#### `activity_type_id`
- **Label:** Next Activity Type
- **Tipo:** many2one → mail.activity.type
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.activity.type`
- **Valor Exemplo:** `False`

#### `activity_user_id`
- **Label:** Responsible User
- **Tipo:** many2one → res.users
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `False`

#### `amount_currency`
- **Label:** Amount in Currency
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** The amount expressed in an optional other currency if it is a multi-currency entry.
- **Valor Exemplo:** `840.76`

#### `amount_residual`
- **Label:** Residual Amount
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The residual amount on a journal item expressed in the company currency.

#### `amount_residual_currency`
- **Label:** Residual Amount in Currency
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The residual amount on a journal item expressed in its currency (possibly not the company currency).

#### `analytic_distribution`
- **Label:** Analytic Distribution
- **Tipo:** json
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `analytic_distribution_search`
- **Label:** Analytic Distribution Search
- **Tipo:** json
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `analytic_line_ids`
- **Label:** Analytic lines
- **Tipo:** one2many → account.analytic.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.analytic.line`

#### `analytic_precision`
- **Label:** Analytic Precision
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `2`

#### `asset_ids`
- **Label:** Related Assets
- **Tipo:** many2many → account.asset
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.asset`

#### `balance`
- **Label:** Balance
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `840.76`

#### `blocked`
- **Label:** No Follow-up
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** You can check this box to mark this journal item as a litigation with the associated partner

#### `can_be_paid`
- **Label:** Release to Pay
- **Tipo:** selection [yes=Yes, no=No, exception=Exception]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['yes', 'Yes'], ['no', 'No'], ['exception', 'Exception']]

#### `cogs_origin_id`
- **Label:** Cogs Origin
- **Tipo:** many2one → account.move.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`

#### `company_currency_id`
- **Label:** Company Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.currency`
- **Valor Exemplo:** `[6, 'BRL']`

#### `company_id`
- **Label:** Company
- **Tipo:** many2one → res.company
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.company`
- **Valor Exemplo:** `[4, 'NACOM GOYA - CD']`

#### `compute_all_tax`
- **Label:** Compute All Tax
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `compute_all_tax_dirty`
- **Label:** Compute All Tax Dirty
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `create_date`
- **Label:** Created on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `create_uid`
- **Label:** Created by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `credit`
- **Label:** Credit
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `0.0`

#### `cumulated_balance`
- **Label:** Cumulated Balance
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Cumulated balance depending on the domain and the order chosen in the view.
- **Valor Exemplo:** `19125816.63`

#### `currency_id`
- **Label:** Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Relacionamento:** `res.currency`
- **Valor Exemplo:** `[6, 'BRL']`

#### `currency_rate`
- **Label:** Currency Rate
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Currency rate from company currency to document currency.
- **Valor Exemplo:** `1.0`

#### `date`
- **Label:** Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2025-11-13'`

#### `date_maturity`
- **Label:** Due Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.

#### `debit`
- **Label:** Debit
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `840.76`

#### `deferred_end_date`
- **Label:** End Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Date at which the deferred expense/revenue ends

#### `deferred_start_date`
- **Label:** Start Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Date at which the deferred expense/revenue starts

#### `desconto_concedido`
- **Label:** Desconto Concedido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `desconto_concedido_percentual`
- **Label:** Desconto Concedido (%)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `dfe_line_id`
- **Label:** Item Documento Fiscal
- **Tipo:** many2one → l10n_br_ciel_it_account.dfe.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.dfe.line`

#### `discount`
- **Label:** Discount (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `discount_allocation_dirty`
- **Label:** Discount Allocation Dirty
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `discount_allocation_key`
- **Label:** Discount Allocation Key
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `discount_allocation_needed`
- **Label:** Discount Allocation Needed
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `discount_amount_currency`
- **Label:** Discount amount in Currency
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `discount_balance`
- **Label:** Discount Balance
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `discount_date`
- **Label:** Discount Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Last date at which the discounted amount must be paid in order for the Early Payment Discount to be granted

#### `display_name`
- **Label:** Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `display_type`
- **Label:** Display Type
- **Tipo:** selection [product=Product, cogs=Cost of Goods Sold, tax=Tax, discount=Discount, rounding=Rounding... (+4)]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['product', 'Product'], ['cogs', 'Cost of Goods Sold'], ['tax', 'Tax'], ['discount', 'Discount'], ['rounding', 'Rounding'], ['payment_term', 'Payment Term'], ['line_section', 'Section'], ['line_note', 'Note'], ['epd', 'Early Payment Discount']]

#### `distribution_analytic_account_ids`
- **Label:** Distribution Analytic Account
- **Tipo:** many2many → account.analytic.account
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.analytic.account`
- **Valor Exemplo:** `[]`

#### `epd_dirty`
- **Label:** Epd Dirty
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `epd_key`
- **Label:** Epd Key
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `epd_needed`
- **Label:** Epd Needed
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `expected_pay_date`
- **Label:** Expected Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Expected payment date as manually set through the customer statement(e.g: if you had the customer on the phone and want to remember the date he promised he would pay)

#### `followup_line_id`
- **Label:** Follow-up Level
- **Tipo:** many2one → account_followup.followup.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account_followup.followup.line`

#### `full_reconcile_id`
- **Label:** Matching
- **Tipo:** many2one → account.full.reconcile
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.full.reconcile`

#### `group_tax_id`
- **Label:** Originator Group of Taxes
- **Tipo:** many2one → account.tax
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.tax`

#### `has_abnormal_deferred_dates`
- **Label:** Has Abnormal Deferred Dates
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `has_deferred_moves`
- **Label:** Has Deferred Moves
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `has_message`
- **Label:** Has Message
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `True`

#### `id`
- **Label:** ID
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `2636115`

#### `indice_comissao`
- **Label:** Índice de Comissão
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_date`
- **Label:** Invoice/Bill Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2025-11-13'`

#### `invoice_origin`
- **Label:** Origin
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The document(s) that generated the invoice.

#### `is_account_reconcile`
- **Label:** Account Reconcile
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Check this box if this account allows invoices & payments matching of journal items.

#### `is_downpayment`
- **Label:** Is Downpayment
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `is_landed_costs_line`
- **Label:** Is Landed Costs Line
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `is_refund`
- **Label:** Is Refund
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `is_same_currency`
- **Label:** Is Same Currency
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `True`

#### `is_storno`
- **Label:** Company Storno Accounting
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Utility field to express whether the journal item is subject to storno accounting
- **Valor Exemplo:** `False`

#### `journal_id`
- **Label:** Journal
- **Tipo:** many2one → account.journal
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.journal`
- **Valor Exemplo:** `[826, 'VENDA DE PRODUÇÃO']`

#### `l10n_br_arquivo_cobranca_escritural_id`
- **Label:** Arquivo Remessa Manual
- **Tipo:** many2one → l10n_br_ciel_it_account.arquivo.cobranca.escritural
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.arquivo.cobranca.escritural`

#### `l10n_br_calcular_imposto`
- **Label:** Calcular Impostos
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cbs_aliquota`
- **Label:** Aliquota do CBS (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cbs_valor`
- **Label:** Valor do CBS (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cfop_codigo`
- **Label:** Código CFOP
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cfop_id`
- **Label:** CFOP
- **Tipo:** many2one → l10n_br_ciel_it_account.cfop
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.cfop`

#### `l10n_br_chave_nfe_exportacao`
- **Label:** Chave NF-e Recebida p/ Exportação
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_arquivo_remessa`
- **Label:** Arquivo Remessa Automática
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_autorizacao_cartao`
- **Label:** Autorização
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_data_desconto`
- **Label:** Data Limite p/ Desconto
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_idintegracao`
- **Label:** Id Integração
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_nossonumero`
- **Label:** Nosso Numero
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_nsu_cartao`
- **Label:** NSU
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_numero_cartao`
- **Label:** Número do Cartão
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_parcela`
- **Label:** Parcela
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_parcela_manual_linha_id`
- **Label:** Parcela Personalizada
- **Tipo:** many2one → l10n_br_ciel_it_account.payment.parcela.manual.linhas
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.payment.parcela.manual.linhas`

#### `l10n_br_cobranca_protocolo`
- **Label:** Protocolo
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_situacao`
- **Label:** Situação
- **Tipo:** selection [SALVO=Salvo, PENDENTE_RETENTATIVA=Pendente, FALHA=Falha, EMITIDO=Emitido, REJEITADO=Rejeitado... (+3)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['SALVO', 'Salvo'], ['PENDENTE_RETENTATIVA', 'Pendente'], ['FALHA', 'Falha'], ['EMITIDO', 'Emitido'], ['REJEITADO', 'Rejeitado'], ['REGISTRADO', 'Registrado'], ['LIQUIDADO', 'Liquidado'], ['BAIXADO', 'Baixado']]

#### `l10n_br_cobranca_situacao_mensagem`
- **Label:** Mensagem
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_tipo_desconto`
- **Label:** Tipo Desconto
- **Tipo:** selection [0=0 - Sem instrução de desconto., 1=1 - Valor Fixo Até a Data Informada., 2=2 - Percentual Até a Data Informada., 3=3 - Valor por Antecipação Dia Corrido.., 4=4 - Valor por Antecipação Dia Útil.... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['0', '0 - Sem instrução de desconto.'], ['1', '1 - Valor Fixo Até a Data Informada.'], ['2', '2 - Percentual Até a Data Informada.'], ['3', '3 - Valor por Antecipação Dia Corrido..'], ['4', '4 - Valor por Antecipação Dia Útil.'], ['5', '5 - Percentual Sobre o Valor Nominal Dia Corrido.'], ['6', '6 - Percentual Sobre o Valor Nominal Dia Útil.']]

#### `l10n_br_cobranca_transmissao`
- **Label:** Tipo Transmissão
- **Tipo:** selection [webservice=Webservice / Ecommerce, automatico=Remessa Automática (VAN), manual=Remessa Manual (Internet Bank)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['webservice', 'Webservice / Ecommerce'], ['automatico', 'Remessa Automática (VAN)'], ['manual', 'Remessa Manual (Internet Bank)']]

#### `l10n_br_cobranca_valor_desconto`
- **Label:** Valor Desconto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_codigo_beneficio`
- **Label:** Código do Benefício Fiscal
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_codigo_servico`
- **Label:** Código Serviço
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_codigo_tributacao_servico`
- **Label:** Código Tributação Serviço
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_aliquota`
- **Label:** Aliquota do Cofins (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_base`
- **Label:** Valor da Base de Cálculo do Cofins
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_cst`
- **Label:** Código de Situação Tributária do Cofins
- **Tipo:** selection [01=01 - Operação Tributável com Alíquota Básica, 02=02 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 03=03 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 04=04 - Operação Tributável Monofásica - Revenda a Alíquota Zero, 05=05 - Operação Tributável por Substituição Tributária... (+28)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['01', '01 - Operação Tributável com Alíquota Básica'], ['02', '02 - Operação Tributável com Alíquota por Unidade de Medida de Produto'], ['03', '03 - Operação Tributável com Alíquota por Unidade de Medida de Produto'], ['04', '04 - Operação Tributável Monofásica - Revenda a Alíquota Zero'], ['05', '05 - Operação Tributável por Substituição Tributária'], ['06', '06 - Operação Tributável a Alíquota Zero'], ['07', '07 - Operação Isenta da Contribuição'], ['08', '08 - Operação sem Incidência da Contribuição'], ['09', '09 - Operação com Suspensão da Contribuição'], ['49', '49 - Outras Operações de Saída'], ['50', '50 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Tributada no Mercado Interno'], ['51', '51 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Não-Tributada no Mercado Interno'], ['52', '52 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita de Exportação'], ['53', '53 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno'], ['54', '54 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas no Mercado Interno e de Exportação'], ['55', '55 - Operação com Direito a Crédito - Vinculada a Receitas Não Tributadas Mercado Interno e de Exportação'], ['56', '56 - Oper. c/ Direito a Créd. Vinculada a Rec. Tributadas e Não-Tributadas Mercado Interno e de Exportação'], ['60', '60 - Crédito Presumido - Oper. de Aquisição Vinculada Exclusivamente a Rec. Tributada no Mercado Interno'], ['61', '61 - Créd. Presumido - Oper. de Aquisição Vinculada Exclusivamente a Rec. Não-Tributada Mercado Interno'], ['62', '62 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita de Exportação'], ['63', '63 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec.Tributadas e Não-Tributadas no Mercado Interno'], ['64', '64 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec. Tributadas no Mercado Interno e de Exportação'], ['65', '65 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec. Não-Tributadas Mercado Interno e Exportação'], ['66', '66 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec. Trib. e Não-Trib. Mercado Interno e Exportação'], ['67', '67 - Crédito Presumido - Outras Operações'], ['70', '70 - Operação de Aquisição sem Direito a Crédito'], ['71', '71 - Operação de Aquisição com Isenção'], ['72', '72 - Operação de Aquisição com Suspensão'], ['73', '73 - Operação de Aquisição a Alíquota Zero'], ['74', '74 - Operação de Aquisição sem Incidência da Contribuição'], ['75', '75 - Operação de Aquisição por Substituição Tributária'], ['98', '98 - Outras Operações de Entrada'], ['99', '99 - Outras Operações']]

#### `l10n_br_cofins_ret_aliquota`
- **Label:** Aliquota do Cofins (%) Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_ret_base`
- **Label:** Valor da Base de Cálculo do Cofins Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_ret_valor`
- **Label:** Valor do Cofins Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_valor`
- **Label:** Valor do Cofins (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_valor_isento`
- **Label:** Valor do Cofins (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_valor_outros`
- **Label:** Valor do Cofins (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_compra_indcom`
- **Label:** Destinação de Uso
- **Tipo:** selection [uso=Uso e Consumo, uso-prestacao=Uso na Prestação de Serviço, ind=Industrialização, com=Comercialização, ativo=Ativo... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['uso', 'Uso e Consumo'], ['uso-prestacao', 'Uso na Prestação de Serviço'], ['ind', 'Industrialização'], ['com', 'Comercialização'], ['ativo', 'Ativo'], ['garantia', 'Garantia'], ['out', 'Outros']]

#### `l10n_br_csll_aliquota`
- **Label:** Aliquota do CSLL (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_base`
- **Label:** Valor da Base de Cálculo do CSLL
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_ret_aliquota`
- **Label:** Aliquota do CSLL (%) Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_ret_base`
- **Label:** Valor da Base de Cálculo do CSLL Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_ret_valor`
- **Label:** Valor do CSLL Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_valor`
- **Label:** Valor do CSLL
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_dados_pagamento_id`
- **Label:** Dados de Pagamento (CNAB)
- **Tipo:** one2many → l10n_br_ciel_it_account.dados.pagamento
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.dados.pagamento`

#### `l10n_br_desc_valor`
- **Label:** Valor do Desconto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_despesas_acessorias`
- **Label:** Despesas Acessórias
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_di_adicao_id`
- **Label:** DI/Adição
- **Tipo:** many2one → l10n_br_ciel_it_account.di.adicao
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.di.adicao`

#### `l10n_br_drawback`
- **Label:** Número Drawback
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_base`
- **Label:** Valor da Base do Fundo de Combate a Pobreza
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_dest_aliquota`
- **Label:** Aliquota do Fundo de Combate a Pobreza (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_dest_valor`
- **Label:** Valor do Fundo de Combate a Pobreza
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_st_aliquota`
- **Label:** Aliquota do Fundo de Combate a Pobreza (%) retido por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_st_ant_aliquota`
- **Label:** Aliquota do Fundo de Combate a Pobreza (%) retido anteriormente por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_st_ant_base`
- **Label:** Valor da Base do Fundo de Combate a Pobreza retido anteriormente por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_st_ant_valor`
- **Label:** Valor do Fundo de Combate a Pobreza retido anteriormente por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_st_base`
- **Label:** Valor da Base do Fundo de Combate a Pobreza retido por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_fcp_st_valor`
- **Label:** Valor do Fundo de Combate a Pobreza retido por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_frete`
- **Label:** Frete
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_mun_aliquota`
- **Label:** Aliquota do IBS Município (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_mun_valor`
- **Label:** Valor do IBS Município (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_uf_aliquota`
- **Label:** Aliquota do IBS UF (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_uf_valor`
- **Label:** Valor do IBS UF (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_valor`
- **Label:** Valor do IBS (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibscbs_base`
- **Label:** Valor da Base de Cálculo do IBS/CBS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibscbs_classtrib_id`
- **Label:** Classificação Tributária do IBS/CBS
- **Tipo:** many2one → l10n_br_ciel_it_account.classificacao.tributaria.ibscbs
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.classificacao.tributaria.ibscbs`

#### `l10n_br_ibscbs_cst`
- **Label:** Código de Situação Tributária do IBS/CBS
- **Tipo:** selection [000=000 - Tributação integral, 010=010 - Tributação com alíquotas uniformes, 011=011 - Tributação com alíquotas uniformes reduzidas, 200=200 - Alíquota reduzida, 210=210 - Redução de alíquota com redutor de base de cálculo... (+14)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['000', '000 - Tributação integral'], ['010', '010 - Tributação com alíquotas uniformes'], ['011', '011 - Tributação com alíquotas uniformes reduzidas'], ['200', '200 - Alíquota reduzida'], ['210', '210 - Redução de alíquota com redutor de base de cálculo'], ['220', '220 - Alíquota fixa'], ['221', '221 - Alíquota fixa proporcional'], ['222', '222 - Redução de base de cálculo'], ['400', '400 - Isenção'], ['410', '410 - Imunidade e não incidência'], ['510', '510 - Diferimento'], ['515', '515 - Diferimento com redução de alíquota'], ['550', '550 - Suspensão'], ['620', '620 - Tributação monofásica'], ['800', '800 - Transferência de crédito'], ['810', '810 - Ajuste de IBS na ZFM'], ['811', '811 - Ajustes'], ['820', '820 - Tributação em declaração de regime específico'], ['830', '830 - Exclusão de base de cálculo']]

#### `l10n_br_icms_ajuste_ids`
- **Label:** Ajuste de ICMS
- **Tipo:** one2many → l10n_br_ciel_it_account.icms.ajuste.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.icms.ajuste.line`

#### `l10n_br_icms_aliquota`
- **Label:** Aliquota do ICMS (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_base`
- **Label:** Valor da Base de Cálculo do ICMS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_credito_aliquota`
- **Label:** Alíquota aplicável de cálculo do crédito (Simples Nacional)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_credito_valor`
- **Label:** Valor crédito do ICMS que pode ser aproveitado
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_cst`
- **Label:** Código de Situação Tributária do ICMS
- **Tipo:** selection [00=00 - Tributada integralmente, 10=10 - Tributada e com cobrança do ICMS-ST, 20=20 - Com redução de base de cálculo, 30=30 - Isenta ou não tributada e com cobrança do ICMS-ST, 40=40 - Isenta... (+16)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['00', '00 - Tributada integralmente'], ['10', '10 - Tributada e com cobrança do ICMS-ST'], ['20', '20 - Com redução de base de cálculo'], ['30', '30 - Isenta ou não tributada e com cobrança do ICMS-ST'], ['40', '40 - Isenta'], ['41', '41 - Não tributada'], ['50', '50 - Suspensão'], ['51', '51 - Diferimento'], ['60', '60 - ICMS cobrado anteriormente por ST'], ['70', '70 - Com redução de base de cálculo e cobrança do ICMS-ST'], ['90', '90 - Outras'], ['101', '101 - Tributada pelo Simples Nacional com permissão de crédito'], ['102', '102 - Tributada pelo Simples Nacional sem permissão de crédito'], ['103', '103 - Isenção do ICMS no Simples Nacional para faixa de receita bruta'], ['201', '201 - Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por substituição tributária'], ['202', '202 - Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por substituição tributária'], ['203', '203 - Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por substituição tributária'], ['300', '300 - Imune'], ['400', '400 - Não tributada pelo Simples Nacional'], ['500', '500 - ICMS cobrado anteriormente por substituição tributária (substituído) ou por antecipação'], ['900', '900 - Outros']]

#### `l10n_br_icms_dest_aliquota`
- **Label:** Aliquota do ICMS UF Destino (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_dest_base`
- **Label:** Valor da Base de Cálculo do ICMS UF Destino
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_dest_valor`
- **Label:** Valor do ICMS UF Destino
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_diferido_aliquota`
- **Label:** Aliquota do ICMS Diferido (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_diferido_valor`
- **Label:** Valor do ICMS Diferido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_diferido_valor_operacao`
- **Label:** Valor do ICMS da Operação
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_inter_aliquota`
- **Label:** Aliquota do ICMS Interestadual (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_inter_participacao`
- **Label:** Participação da Aliquota do ICMS Interestadual (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_modalidade_base`
- **Label:** Modalidade de Determinação da BC do ICMS
- **Tipo:** selection [0=0 - Margem Valor Agregado (%), 1=1 - Pauta (Valor), 2=2 - Preço Tabelado Máx. (valor), 3=3 - Valor da operação]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['0', '0 - Margem Valor Agregado (%)'], ['1', '1 - Pauta (Valor)'], ['2', '2 - Preço Tabelado Máx. (valor)'], ['3', '3 - Valor da operação']]

#### `l10n_br_icms_motivo_desonerado`
- **Label:** Motivo Desoneração do ICMS
- **Tipo:** selection [1=1 - Táxi;, 2=2 - Deficiente Físico (Revogado);, 3=3 - Produtor Agropecuário;, 4=4 - Frotista/Locadora;, 5=5 - Diplomático/Consular;... (+9)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['1', '1 - Táxi;'], ['2', '2 - Deficiente Físico (Revogado);'], ['3', '3 - Produtor Agropecuário;'], ['4', '4 - Frotista/Locadora;'], ['5', '5 - Diplomático/Consular;'], ['6', '6 - Utilitários e Motocicletas da Amazônia Ocidental e Áreas de Livre Comércio (Resolução 714/88 e 790/94 - CONTRAN e suas alterações);'], ['7', '7 - SUFRAMA;'], ['8', '8 - Venda a Órgãos Públicos'], ['9', '9 - outros.'], ['10', '10 - Deficiente Condutor (Convênio ICMS 38/12);'], ['11', '11 - Deficiente Não Condutor (Convênio ICMS 38/12)'], ['12', '12 - Órgão de fomento e desenvolvimento agropecuário'], ['16', '16 - Olimpíadas Rio 2016;'], ['90', '90 - Solicitado pelo Fisco']]

#### `l10n_br_icms_reducao_base`
- **Label:** Aliquota de Redução da BC do ICMS (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_remet_valor`
- **Label:** Valor do ICMS UF Remetente
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_valor`
- **Label:** Valor do ICMS (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_valor_credito_presumido`
- **Label:** Valor do ICMS (Crédito Presumido)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_desonerado`
- **Label:** Valor do ICMS (Desonerado)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_valor_efetivo`
- **Label:** Valor do ICMS (Efetivo)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_isento`
- **Label:** Valor do ICMS (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icms_valor_outros`
- **Label:** Valor do ICMS (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_aliquota`
- **Label:** Aliquota do ICMSST (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_base`
- **Label:** Valor da Base de Cálculo do ICMSST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_base_propria_aliquota`
- **Label:** Alíquota da Base de Cálculo da Operação Própria
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_modalidade_base`
- **Label:** Modalidade de Determinação da BC do ICMSST
- **Tipo:** selection [0=0 - Preço tabelado ou máximo sugerido, 1=1 - Lista Negativa (valor), 2=2 - Lista Positiva (valor), 3=3 - Lista Neutra (valor), 4=4 - Margem Valor Agregado (%)... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['0', '0 - Preço tabelado ou máximo sugerido'], ['1', '1 - Lista Negativa (valor)'], ['2', '2 - Lista Positiva (valor)'], ['3', '3 - Lista Neutra (valor)'], ['4', '4 - Margem Valor Agregado (%)'], ['5', '5 - Pauta (valor)'], ['6', '6 - Valor da Operação (NT 2019.001)']]

#### `l10n_br_icmsst_mva`
- **Label:** Aliquota da Margem de Valor Adicionado do ICMSST (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_reducao_base`
- **Label:** Aliquota de Redução da BC do ICMSST (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_retido_aliquota`
- **Label:** Alíquota suportada pelo Consumidor Final (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_retido_base`
- **Label:** Valor da Base de Cálculo do ICMSST Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_retido_valor`
- **Label:** Valor do ICMSST Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_retido_valor_outros`
- **Label:** Valor do ICMSST Retido (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_substituto_valor`
- **Label:** Valor do ICMS próprio do Substituto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_substituto_valor_outros`
- **Label:** Valor do ICMS próprio do Substituto (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_uf`
- **Label:** UF para qual é devido o ICMSST
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_valor`
- **Label:** Valor do ICMSST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_valor_outros`
- **Label:** Valor do ICMSST (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_icmsst_valor_proprio`
- **Label:** Valor do ICMSST (Próprio)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ii_aliquota`
- **Label:** Aliquota do II (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ii_base`
- **Label:** Valor da Base de Cálculo do II
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ii_valor`
- **Label:** Valor do II (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ii_valor_aduaneira`
- **Label:** Valor do II (Aduaneira)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ii_valor_afrmm`
- **Label:** Valor do II (AFRMM)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_imposto_auto`
- **Label:** Calcular Impostos Automaticamente
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_informacao_adicional`
- **Label:** Informações Adicionais
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_informacao_adicional_produto_ids`
- **Label:** Informação Adicional do Produto
- **Tipo:** many2many → l10n_br_ciel_it_account.mensagem.fiscal
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.mensagem.fiscal`

#### `l10n_br_inss_ret_aliquota`
- **Label:** Aliquota do INSS Retido (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_inss_ret_base`
- **Label:** Valor da Base de Cálculo do INSS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_inss_ret_valor`
- **Label:** Valor do INSS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iof_valor`
- **Label:** Valor do IOF
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_aliquota`
- **Label:** Aliquota do IPI (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_base`
- **Label:** Valor da Base de Cálculo do IPI
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_cnpj`
- **Label:** CNPJ do produtor da mercadoria
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_cst`
- **Label:** Código de Situação Tributária do IPI
- **Tipo:** selection [00=00 - Entrada com Recuperação de Crédito, 01=01 - Entrada Tributável com Alíquota Zero, 02=02 - Entrada Isenta, 03=03 - Entrada Não-Tributada, 04=04 - Entrada Imune... (+9)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['00', '00 - Entrada com Recuperação de Crédito'], ['01', '01 - Entrada Tributável com Alíquota Zero'], ['02', '02 - Entrada Isenta'], ['03', '03 - Entrada Não-Tributada'], ['04', '04 - Entrada Imune'], ['05', '05 - Entrada com Suspensão'], ['49', '49 - Outras Entradas'], ['50', '50 - Saída Tributada'], ['51', '51 - Saída Tributável com Alíquota Zero'], ['52', '52 - Saída Isenta'], ['53', '53 - Saída Não-Tributada'], ['54', '54 - Saída Imune'], ['55', '55 - Saída com Suspensão'], ['99', '99 - Outras Saídas']]

#### `l10n_br_ipi_enq`
- **Label:** Código Enquadramento
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_selo_codigo`
- **Label:** Código do selo de controle IPI
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_selo_quantidade`
- **Label:** Quantidade de selo de controle
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_valor`
- **Label:** Valor do IPI (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_valor_isento`
- **Label:** Valor do IPI (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ipi_valor_outros`
- **Label:** Valor do IPI (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_irpj_aliquota`
- **Label:** Aliquota do IRPJ (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_irpj_base`
- **Label:** Valor da Base de Cálculo do IRPJ
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_irpj_ret_aliquota`
- **Label:** Aliquota do IRPJ Retido (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_irpj_ret_base`
- **Label:** Valor da Base de Cálculo do IRPJ Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_irpj_ret_valor`
- **Label:** Valor do IRPJ Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_irpj_valor`
- **Label:** Valor do IRPJ
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_is_aliquota`
- **Label:** Aliquota do IS (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_is_base`
- **Label:** Valor da Base de Cálculo do IS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_is_classtrib_id`
- **Label:** Classificação Tributária do IS
- **Tipo:** many2one → l10n_br_ciel_it_account.classificacao.tributaria.is
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.classificacao.tributaria.is`

#### `l10n_br_is_cst`
- **Label:** Código de Situação Tributária do IS
- **Tipo:** selection [00=00 - Tabela não divulgada]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['00', '00 - Tabela não divulgada']]

#### `l10n_br_is_valor`
- **Label:** Valor do IS (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_aliquota`
- **Label:** Aliquota do ISS (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_base`
- **Label:** Valor da Base de Cálculo do ISS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_deducao`
- **Label:** Valor da Dedução para efeito de Base de Cálculo do ISS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_ret_aliquota`
- **Label:** Aliquota do ISS Retido (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_ret_base`
- **Label:** Valor da Base de Cálculo do ISS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_ret_valor`
- **Label:** Valor do ISS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_iss_valor`
- **Label:** Valor do ISS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_item_pedido_compra`
- **Label:** Item Pedido de Compra do Cliente
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_meio`
- **Label:** Meio de Pagamento
- **Tipo:** selection [01=Dinheiro, 02=Cheque, 03=Cartão de Crédito, 04=Cartão de Débito, 05=Crédito Loja... (+15)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['01', 'Dinheiro'], ['02', 'Cheque'], ['03', 'Cartão de Crédito'], ['04', 'Cartão de Débito'], ['05', 'Crédito Loja'], ['10', 'Vale Alimentação'], ['11', 'Vale Refeição'], ['12', 'Vale Presente'], ['13', 'Vale Combustível'], ['14', 'Duplicata Mercantil'], ['15', 'Boleto Bancário'], ['16', 'Depósito Bancário'], ['17', 'Pagamento Instantâneo (PIX)'], ['18', 'Transferência bancária, Carteira Digital'], ['19', 'Programa de fidelidade, Cashback, Crédito Virtual'], ['20', 'Pagamento Instantâneo (PIX) – Estático'], ['21', 'Crédito em Loja'], ['22', 'Pagamento Eletrônico não Informado'], ['90', 'Sem pagamento'], ['99', 'Outros']]

#### `l10n_br_mensagem_fiscal_ids`
- **Label:** Observação Fiscal
- **Tipo:** many2many → l10n_br_ciel_it_account.mensagem.fiscal
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.mensagem.fiscal`

#### `l10n_br_nat_bc_cred`
- **Label:** Natureza da Base de Cálculo dos Créditos
- **Tipo:** selection [01=Aquisição de bens para revenda, 02=Aquisição de bens utilizados como insumo, 03=Aquisição de serviços utilizados como insumo, 04=Energia elétrica e térmica, inclusive sob a forma de vapor, 05=Aluguéis de prédios... (+13)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['01', 'Aquisição de bens para revenda'], ['02', 'Aquisição de bens utilizados como insumo'], ['03', 'Aquisição de serviços utilizados como insumo'], ['04', 'Energia elétrica e térmica, inclusive sob a forma de vapor'], ['05', 'Aluguéis de prédios'], ['06', 'Aluguéis de máquinas e equipamentos'], ['07', 'Armazenagem de mercadoria e frete na operação de venda'], ['08', 'Contraprestações de arrendamento mercantil'], ['09', 'Máquinas, equipamentos e outros bens incorporados ao ativo imobilizado (crédito sobre encargos de depreciação)'], ['10', 'Máquinas, equipamentos e outros bens incorporados ao ativo imobilizado (crédito com base no valor de aquisição)'], ['11', 'Amortização e Depreciação de edificações e benfeitorias em imóveis'], ['12', 'Devolução de Vendas Sujeitas à Incidência Não-Cumulativa'], ['13', 'Outras Operações com Direito a Crédito'], ['14', 'Atividade de Transporte de Cargas – Subcontratação'], ['15', 'Atividade Imobiliária – Custo Incorrido de Unidade Imobiliária'], ['16', 'Atividade Imobiliária – Custo Orçado de unidade não concluída'], ['17', 'Atividade de Prestação de Serviços de Limpeza, Conservação e Manutenção – vale-transporte, vale-refeição ou vale-alimentação, fardamento ou uniforme'], ['18', 'Estoque de abertura de bens']]

#### `l10n_br_nat_rec`
- **Label:** Natureza da Receita
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ncm_id`
- **Label:** NCM
- **Tipo:** many2one → l10n_br_ciel_it_account.ncm
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.ncm`

#### `l10n_br_operacao_id`
- **Label:** Operação
- **Tipo:** many2one → l10n_br_ciel_it_account.operacao
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.operacao`

#### `l10n_br_operacao_manual`
- **Label:** Definir Operação Manual
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_origem`
- **Label:** Origem do Produto
- **Tipo:** selection [0=0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8;, 1=1 - Estrangeira - Importação direta, exceto a indicada no código 6;, 2=2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7;, 3=3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70%;, 4=4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de quetratam as legislações citadas nos Ajustes;... (+4)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['0', '0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8;'], ['1', '1 - Estrangeira - Importação direta, exceto a indicada no código 6;'], ['2', '2 - Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7;'], ['3', '3 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% e inferior ou igual a 70%;'], ['4', '4 - Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de quetratam as legislações citadas nos Ajustes;'], ['5', '5 - Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40%;'], ['6', '6 - Estrangeira - Importação direta, sem similar nacional, constante em lista da CAMEX e gás natural;'], ['7', '7 - Estrangeira - Adquirida no mercado interno, sem similar nacional, constante lista CAMEX e gás natural.'], ['8', '8 - Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70%;']]

#### `l10n_br_paga`
- **Label:** Parcela Paga?
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_boleto`
- **Label:** Boleto
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_boleto_fname`
- **Label:** Arquivo Boleto
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pedido_compra`
- **Label:** Pedido de Compra do Cliente
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_aliquota`
- **Label:** Aliquota do PIS (%)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_base`
- **Label:** Valor da Base de Cálculo do PIS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_cst`
- **Label:** Código de Situação Tributária do PIS
- **Tipo:** selection [01=01 - Operação Tributável com Alíquota Básica, 02=02 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 03=03 - Operação Tributável com Alíquota por Unidade de Medida de Produto, 04=04 - Operação Tributável Monofásica - Revenda a Alíquota Zero, 05=05 - Operação Tributável por Substituição Tributária... (+28)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['01', '01 - Operação Tributável com Alíquota Básica'], ['02', '02 - Operação Tributável com Alíquota por Unidade de Medida de Produto'], ['03', '03 - Operação Tributável com Alíquota por Unidade de Medida de Produto'], ['04', '04 - Operação Tributável Monofásica - Revenda a Alíquota Zero'], ['05', '05 - Operação Tributável por Substituição Tributária'], ['06', '06 - Operação Tributável a Alíquota Zero'], ['07', '07 - Operação Isenta da Contribuição'], ['08', '08 - Operação sem Incidência da Contribuição'], ['09', '09 - Operação com Suspensão da Contribuição'], ['49', '49 - Outras Operações de Saída'], ['50', '50 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Tributada no Mercado Interno'], ['51', '51 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Não-Tributada no Mercado Interno'], ['52', '52 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita de Exportação'], ['53', '53 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno'], ['54', '54 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas no Mercado Interno e de Exportação'], ['55', '55 - Operação com Direito a Crédito - Vinculada a Receitas Não Tributadas Mercado Interno e de Exportação'], ['56', '56 - Oper. c/ Direito a Créd. Vinculada a Rec. Tributadas e Não-Tributadas Mercado Interno e de Exportação'], ['60', '60 - Crédito Presumido - Oper. de Aquisição Vinculada Exclusivamente a Rec. Tributada no Mercado Interno'], ['61', '61 - Créd. Presumido - Oper. de Aquisição Vinculada Exclusivamente a Rec. Não-Tributada Mercado Interno'], ['62', '62 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita de Exportação'], ['63', '63 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec.Tributadas e Não-Tributadas no Mercado Interno'], ['64', '64 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec. Tributadas no Mercado Interno e de Exportação'], ['65', '65 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec. Não-Tributadas Mercado Interno e Exportação'], ['66', '66 - Créd. Presumido - Oper. de Aquisição Vinculada a Rec. Trib. e Não-Trib. Mercado Interno e Exportação'], ['67', '67 - Crédito Presumido - Outras Operações'], ['70', '70 - Operação de Aquisição sem Direito a Crédito'], ['71', '71 - Operação de Aquisição com Isenção'], ['72', '72 - Operação de Aquisição com Suspensão'], ['73', '73 - Operação de Aquisição a Alíquota Zero'], ['74', '74 - Operação de Aquisição sem Incidência da Contribuição'], ['75', '75 - Operação de Aquisição por Substituição Tributária'], ['98', '98 - Outras Operações de Entrada'], ['99', '99 - Outras Operações']]

#### `l10n_br_pis_ret_aliquota`
- **Label:** Aliquota do PIS (%) Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_ret_base`
- **Label:** Valor da Base de Cálculo do PIS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_ret_valor`
- **Label:** Valor do PIS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_valor`
- **Label:** Valor do PIS (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_valor_isento`
- **Label:** Valor do PIS (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pis_valor_outros`
- **Label:** Valor do PIS (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_prod_valor`
- **Label:** Valor do Produto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_registro_exportacao`
- **Label:** Registro de Exportação
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_seguro`
- **Label:** Seguro
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_tipo_pedido`
- **Label:** Tipo de Pedido (saída)
- **Tipo:** selection [baixa-estoque=Saída: Baixa de Estoque, complemento-valor=Saída: Complemento de Preço, dev-comodato=Saída: Devolução de Comodato, compra=Saída: Devolução de Compra, dev-conserto=Saída: Devolução de Conserto... (+42)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['baixa-estoque', 'Saída: Baixa de Estoque'], ['complemento-valor', 'Saída: Complemento de Preço'], ['dev-comodato', 'Saída: Devolução de Comodato'], ['compra', 'Saída: Devolução de Compra'], ['dev-conserto', 'Saída: Devolução de Conserto'], ['dev-consignacao', 'Saída: Devolução de Consignação'], ['dev-demonstracao', 'Saída: Devolução de Demonstração'], ['dev-industrializacao', 'Saída: Devolução de Industrialização'], ['dev-locacao', 'Saída: Devolução de Locação'], ['dev-mostruario', 'Saída: Devolução de Mostruário'], ['dev-teste', 'Saída: Devolução de Teste'], ['dev-vasilhame', 'Saída: Devolução de Vasilhame'], ['venda-locacao', 'Saída: Locação'], ['outro', 'Saída: Outros'], ['perda', 'Saída: Perda'], ['mostruario', 'Saída: Remessa de Mostruário'], ['vasilhame', 'Saída: Remessa de Vasilhame'], ['rem-venda-futura', 'Saída: Remessa de Venda p/ Entrega Futura'], ['ativo-fora', 'Saída: Remessa de bem do ativo imobilizado p/ uso Fora do Estabelecimento'], ['comodato', 'Saída: Remessa em Comodato'], ['consignacao', 'Saída: Remessa em Consignação'], ['garantia', 'Saída: Remessa em Garantia'], ['amostra', 'Saída: Remessa p/ Amostra Grátis'], ['bonificacao', 'Saída: Remessa p/ Bonificação'], ['conserto', 'Saída: Remessa p/ Conserto'], ['demonstracao', 'Saída: Remessa p/ Demonstração'], ['deposito', 'Saída: Remessa p/ Depósito'], ['exportacao', 'Saída: Remessa p/ Exportação'], ['feira', 'Saída: Remessa p/ Feira'], ['fora', 'Saída: Remessa p/ Fora do Estabelecimento'], ['industrializacao', 'Saída: Remessa p/ Industrialização'], ['rem-obra', 'Saída: Remessa p/ Obra'], ['teste', 'Saída: Remessa p/ Teste'], ['troca', 'Saída: Remessa p/ Troca'], ['uso-prestacao', 'Saída: Remessa p/ Uso na Prestação de Serviço'], ['locacao', 'Saída: Remessa para Locação'], ['rem-conta-ordem', 'Saída: Remessa por Conta e Ordem'], ['transf-filial', 'Saída: Transferencia entre Filiais'], ['venda', 'Saída: Venda'], ['venda-nfce', 'Saída: Venda Cupom Fiscal'], ['venda-armazem', 'Saída: Venda de Armazém Externo'], ['venda-industrializacao', 'Saída: Venda de Industrialização'], ['servico', 'Saída: Venda de Serviço'], ['venda-consignacao', 'Saída: Venda em Consignação'], ['venda_futura', 'Saída: Venda p/ Entrega Futura'], ['venda-conta-ordem', 'Saída: Venda por Conta e Ordem'], ['venda-conta-ordem-vendedor', 'Saída: Venda por Conta e Ordem por Vendedor']]

#### `l10n_br_tipo_pedido_entrada`
- **Label:** Tipo de Pedido (entrada)
- **Tipo:** selection [ent-amostra=Entrada: Amostra Grátis, ent-bonificacao=Entrada: Bonificação, ent-comodato=Entrada: Comodato, comp-importacao=Entrada: Complementar de Importação, compra=Entrada: Compra... (+33)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['ent-amostra', 'Entrada: Amostra Grátis'], ['ent-bonificacao', 'Entrada: Bonificação'], ['ent-comodato', 'Entrada: Comodato'], ['comp-importacao', 'Entrada: Complementar de Importação'], ['compra', 'Entrada: Compra'], ['compra-venda-ordem', 'Entrada: Compra Venda à Ordem'], ['compra-ent-futura', 'Entrada: Compra p/ Entrega Futura'], ['ent-conserto', 'Entrada: Conserto'], ['credito-imposto', 'Entrada: Crédito de Imposto'], ['ent-demonstracao', 'Entrada: Demonstração'], ['devolucao', 'Entrada: Devolução Emissão Própria'], ['devolucao_compra', 'Entrada: Devolução de Venda'], ['importacao', 'Entrada: Importação'], ['locacao', 'Entrada: Locação'], ['ent-mostruario', 'Entrada: Mostruário'], ['outro', 'Entrada: Outros'], ['retorno', 'Entrada: Outros Retorno'], ['compra-rec-venda-ordem', 'Entrada: Recebimento de Compra Venda à Ordem'], ['compra-rec-ent-futura', 'Entrada: Recebimento de Compra p/ Entrega Futura'], ['rem-industrializacao', 'Entrada: Remessa p/ Industrialização'], ['rem-conta-ordem', 'Entrada: Remessa por Conta e Ordem'], ['comodato', 'Entrada: Retorno de Comodato'], ['conserto', 'Entrada: Retorno de Conserto'], ['consignacao', 'Entrada: Retorno de Consignação'], ['demonstracao', 'Entrada: Retorno de Demonstração'], ['deposito', 'Entrada: Retorno de Depósito'], ['feira', 'Entrada: Retorno de Feira'], ['industrializacao', 'Entrada: Retorno de Industrialização'], ['ret-locacao', 'Entrada: Retorno de Locação'], ['mostruario', 'Entrada: Retorno de Mostruário'], ['troca', 'Entrada: Retorno de Troca'], ['vasilhame', 'Entrada: Retorno de Vasilhame'], ['ativo-fora', 'Entrada: Retorno de bem do ativo imobilizado p/ uso Fora do Estabelecimento'], ['servico', 'Entrada: Serviço'], ['serv-industrializacao', 'Entrada: Serviço de Industrialização'], ['transf-filial', 'Entrada: Transferencia entre Filiais'], ['importacao-transporte', 'Entrada: Transporte de Importação'], ['ent-vasilhame', 'Entrada: Vasilhame']]

#### `l10n_br_tipo_pedido_str`
- **Label:** Tipo de Pedido
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_total_nfe`
- **Label:** Valor Total do Item da NF
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_total_tributos`
- **Label:** Valor dos Tributos
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_unit_nfe`
- **Label:** Valor Unitário do Item da NF
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_unit_tax`
- **Label:** Valor Unitário com Imposto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_unit_tax_recompute`
- **Label:** Recompute Unit Tax
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `last_followup_date`
- **Label:** Latest Follow-up
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `matched_credit_ids`
- **Label:** Matched Credits
- **Tipo:** one2many → account.partial.reconcile
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.partial.reconcile`
- **Descrição:** Credit journal items that are matched with this journal item.

#### `matched_debit_ids`
- **Label:** Matched Debits
- **Tipo:** one2many → account.partial.reconcile
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.partial.reconcile`
- **Descrição:** Debit journal items that are matched with this journal item.

#### `matching_number`
- **Label:** Matching #
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Matching number for this line, 'P' if it is only partially reconcile, or the name of the full reconcile if it exists.

#### `message_attachment_count`
- **Label:** Attachment Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `0`

#### `message_follower_ids`
- **Label:** Followers
- **Tipo:** one2many → mail.followers
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.followers`
- **Valor Exemplo:** `[]`

#### `message_has_error`
- **Label:** Message Delivery error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, some messages have a delivery error.
- **Valor Exemplo:** `False`

#### `message_has_error_counter`
- **Label:** Number of errors
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Number of messages with delivery error
- **Valor Exemplo:** `0`

#### `message_has_sms_error`
- **Label:** SMS Delivery error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, some messages have a delivery error.
- **Valor Exemplo:** `False`

#### `message_ids`
- **Label:** Messages
- **Tipo:** one2many → mail.message
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.message`
- **Valor Exemplo:** `[7 itens: [12279208, 12095931, 12075319]...]`

#### `message_is_follower`
- **Label:** Is Follower
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `message_needaction`
- **Label:** Action Needed
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, new messages require your attention.
- **Valor Exemplo:** `False`

#### `message_needaction_counter`
- **Label:** Number of Actions
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Number of messages requiring action
- **Valor Exemplo:** `0`

#### `message_partner_ids`
- **Label:** Followers (Partners)
- **Tipo:** many2many → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`
- **Valor Exemplo:** `[]`

#### `move_attachment_ids`
- **Label:** Move Attachment
- **Tipo:** one2many → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `move_id`
- **Label:** Journal Entry
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`
- **Valor Exemplo:** `[404387, 'NF-e: 141787 Série: 1 - VND/2025/05103']`

#### `move_name`
- **Label:** Number
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'VND/2025/05103'`

#### `move_type`
- **Label:** Type
- **Tipo:** selection [entry=Journal Entry, out_invoice=Customer Invoice, out_refund=Customer Credit Note, in_invoice=Vendor Bill, in_refund=Vendor Credit Note... (+2)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['entry', 'Journal Entry'], ['out_invoice', 'Customer Invoice'], ['out_refund', 'Customer Credit Note'], ['in_invoice', 'Vendor Bill'], ['in_refund', 'Vendor Credit Note'], ['out_receipt', 'Sales Receipt'], ['in_receipt', 'Purchase Receipt']]
- **Valor Exemplo:** `'out_invoice'`

#### `my_activity_date_deadline`
- **Label:** My Activity Deadline
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `name`
- **Label:** Label
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `'VND/2025/05103 parcela nº1'`

#### `next_action_date`
- **Label:** Next Action Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Date where the next action should be taken for a receivable item. Usually, automatically set when sending reminders through the customer statement.

#### `non_deductible_tax_value`
- **Label:** Non Deductible Tax Value
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `parent_state`
- **Label:** Status
- **Tipo:** selection [draft=Draft, posted=Posted, cancel=Cancelled]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['draft', 'Draft'], ['posted', 'Posted'], ['cancel', 'Cancelled']]
- **Valor Exemplo:** `'posted'`

#### `partner_id`
- **Label:** Partner
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`

#### `payment_date`
- **Label:** Payment Date
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `payment_id`
- **Label:** Originator Payment
- **Tipo:** many2one → account.payment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.payment`
- **Descrição:** The payment that created this entry

#### `payment_provider_id`
- **Label:** Forma de Pagamento
- **Tipo:** many2one → payment.provider
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `payment.provider`

#### `price_subtotal`
- **Label:** Subtotal
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `price_total`
- **Label:** Total
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `price_unit`
- **Label:** Unit Price
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `product_id`
- **Label:** Product
- **Tipo:** many2one → product.product
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `product.product`

#### `product_type`
- **Label:** Product Type
- **Tipo:** selection [consu=Consumable, service=Service, product=Storable Product]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['consu', 'Consumable'], ['service', 'Service'], ['product', 'Storable Product']]
- **Descrição:** A storable product is a product for which you manage stock. The Inventory app has to be installed.
A consumable product is a product for which stock is not managed.
A service is a non-material product you provide.

#### `product_uom_category_id`
- **Label:** Category
- **Tipo:** many2one → uom.category
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `uom.category`
- **Descrição:** Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios.

#### `product_uom_id`
- **Label:** Unit of Measure
- **Tipo:** many2one → uom.uom
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `uom.uom`

#### `purchase_line_id`
- **Label:** Purchase Order Line
- **Tipo:** many2one → purchase.order.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `purchase.order.line`

#### `purchase_order_id`
- **Label:** Purchase Order
- **Tipo:** many2one → purchase.order
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `purchase.order`

#### `quantity`
- **Label:** Quantity
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports.

#### `rating_ids`
- **Label:** Ratings
- **Tipo:** one2many → rating.rating
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `rating.rating`
- **Valor Exemplo:** `[]`

#### `reconcile_model_id`
- **Label:** Reconciliation Model
- **Tipo:** many2one → account.reconcile.model
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.reconcile.model`

#### `reconciled`
- **Label:** Reconciled
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `ref`
- **Label:** Reference
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `''`

#### `sale_line_id`
- **Label:** Sale Line
- **Tipo:** many2one → sale.order.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `sale.order.line`

#### `sale_line_ids`
- **Label:** Sales Order Lines
- **Tipo:** many2many → sale.order.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `sale.order.line`

#### `sequence`
- **Label:** Sequence
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `12000`

#### `statement_id`
- **Label:** Statement
- **Tipo:** many2one → account.bank.statement
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.bank.statement`
- **Descrição:** The bank statement used for bank reconciliation

#### `statement_line_id`
- **Label:** Originator Statement Line
- **Tipo:** many2one → account.bank.statement.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.bank.statement.line`
- **Descrição:** The statement line that created this entry

#### `stock_valuation_layer_ids`
- **Label:** Stock Valuation Layer
- **Tipo:** one2many → stock.valuation.layer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.valuation.layer`

#### `tax_base_amount`
- **Label:** Base Amount
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_calculation_rounding_method`
- **Label:** Tax calculation rounding method
- **Tipo:** selection [round_per_line=Round per Line, round_globally=Round Globally]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['round_per_line', 'Round per Line'], ['round_globally', 'Round Globally']]

#### `tax_group_id`
- **Label:** Originator tax group
- **Tipo:** many2one → account.tax.group
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.tax.group`

#### `tax_ids`
- **Label:** Taxes
- **Tipo:** many2many → account.tax
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.tax`

#### `tax_key`
- **Label:** Tax Key
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_line_id`
- **Label:** Originator Tax
- **Tipo:** many2one → account.tax
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.tax`
- **Descrição:** Indicates that this journal item is a tax line

#### `tax_repartition_line_id`
- **Label:** Originator Tax Distribution Line
- **Tipo:** many2one → account.tax.repartition.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.tax.repartition.line`
- **Descrição:** Tax distribution line that caused the creation of this move line, if any

#### `tax_tag_ids`
- **Label:** Tags
- **Tipo:** many2many → account.account.tag
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.account.tag`
- **Descrição:** Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.

#### `tax_tag_invert`
- **Label:** Invert Tags
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `term_key`
- **Label:** Term Key
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `website_message_ids`
- **Label:** Website Messages
- **Tipo:** one2many → mail.message
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.message`
- **Descrição:** Website communication history
- **Valor Exemplo:** `[]`

#### `write_date`
- **Label:** Last Updated on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `write_uid`
- **Label:** Last Updated by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `x_studio_nf_e`
- **Label:** NF-e
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `x_studio_status_de_pagamento`
- **Label:** Status de Pagamento
- **Tipo:** selection [not_paid=Not Paid, in_payment=In Payment, paid=Paid, partial=Partially Paid, reversed=Reversed... (+1)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['not_paid', 'Not Paid'], ['in_payment', 'In Payment'], ['paid', 'Paid'], ['partial', 'Partially Paid'], ['reversed', 'Reversed'], ['invoicing_legacy', 'Invoicing App Legacy']]

#### `x_studio_tipo_de_documento_fiscal`
- **Label:** Tipo de Documento Fiscal
- **Tipo:** selection [NFS=Nota Fiscal de Serviços Instituída por Municípios, NFSE=Nota Fiscal de Serviços Eletrônica - NFS-e, NDS=Nota de Débito de Serviços, FAT=Fatura, ND=Nota de Débito... (+32)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['NFS', 'Nota Fiscal de Serviços Instituída por Municípios'], ['NFSE', 'Nota Fiscal de Serviços Eletrônica - NFS-e'], ['NDS', 'Nota de Débito de Serviços'], ['FAT', 'Fatura'], ['ND', 'Nota de Débito'], ['01', 'Nota Fiscal'], ['1B', 'Nota Fiscal Avulsa'], ['02', 'Nota Fiscal de Venda a Consumidor'], ['2D', 'Cupom Fiscal'], ['2E', 'Cupom Fiscal Bilhete de Passagem'], ['04', 'Nota Fiscal de Produtor'], ['06', 'Nota Fiscal/Conta de Energia Elétrica'], ['07', 'Nota Fiscal de Serviço de Transporte'], ['08', 'Conhecimento de Transporte Rodoviário de Cargas'], ['8B', 'Conhecimento de Transporte de Cargas Avulso'], ['09', 'Conhecimento de Transporte Aquaviário de Cargas'], ['10', 'Conhecimento Aéreo'], ['11', 'Conhecimento de Transporte Ferroviário de Cargas'], ['13', 'Bilhete de Passagem Rodoviário'], ['14', 'Bilhete de Passagem Aquaviário'], ['15', 'Bilhete de Passagem e Nota de Bagagem'], ['16', 'Bilhete de Passagem Ferroviário'], ['18', 'Resumo de Movimento Diário'], ['21', 'Nota Fiscal de Serviço de Comunicação'], ['22', 'Nota Fiscal de Serviço de Telecomunicação'], ['26', 'Conhecimento de Transporte Multimodal de Cargas'], ['27', 'Nota Fiscal De Transporte Ferroviário De Carga'], ['28', 'Nota Fiscal/Conta de Fornecimento de Gás Canalizado'], ['29', 'Nota Fiscal/Conta de Fornecimento de Água Canalizada'], ['55', 'Nota Fiscal Eletrônica (NF-e)'], ['57', 'Conhecimento de Transporte Eletrônico (CT-e)'], ['59', 'Cupom Fiscal Eletrônico (CF-e-SAT)'], ['60', 'Cupom Fiscal Eletrônico (CF-e-ECF)'], ['63', 'Bilhete de Passagem Eletrônico (BP-e)'], ['65', 'Nota Fiscal Eletrônica ao Consumidor Final (NFC-e)'], ['66', 'Nota Fiscal de Energia Elétrica Eletrônica - NF3e'], ['67', 'Conhecimento de Transporte Eletrônico (CT-e OS)']]



================================================================================
## account.move
**Descrição:** Documentos fiscais - faturas, notas de crédito, lançamentos
================================================================================

**Total de campos:** 376

**Exemplo encontrado:** ID = 416177

### CAMPOS:

| # | Campo | Tipo | Label | Armazenado | Obrigatório | Valor Exemplo |
|---|-------|------|-------|------------|-------------|---------------|
| 1 | `access_token` | char | Security Token | ✅ | ❌ | 'f9ab66d4-a0ae-4774-b982-03d8b2ae27f5' |
| 2 | `access_url` | char | Portal Access URL | ❌ | ❌ | '/my/invoices/416177' |
| 3 | `access_warning` | text | Access warning | ❌ | ❌ | '' |
| 4 | `activity_calendar_event_id` | many2one → calendar.event | Next Activity Calendar Event | ❌ | ❌ | False |
| 5 | `activity_date_deadline` | date | Next Activity Deadline | ❌ | ❌ | False |
| 6 | `activity_exception_decoration` | selection [warning=Alert, danger=Error] | Activity Exception Decoration | ❌ | ❌ | False |
| 7 | `activity_exception_icon` | char | Icon | ❌ | ❌ | False |
| 8 | `activity_ids` | one2many → mail.activity | Activities | ✅ | ❌ | [] |
| 9 | `activity_state` | selection [overdue=Overdue, today=Today, planned=Planned] | Activity State | ❌ | ❌ | False |
| 10 | `activity_summary` | char | Next Activity Summary | ❌ | ❌ | False |
| 11 | `activity_type_icon` | char | Activity Type Icon | ❌ | ❌ | False |
| 12 | `activity_type_id` | many2one → mail.activity.type | Next Activity Type | ❌ | ❌ | False |
| 13 | `activity_user_id` | many2one → res.users | Responsible User | ❌ | ❌ | False |
| 14 | `adiantamento_id` | boolean | Adiantamento | ❌ | ❌ | '-' |
| 15 | `agendamento_id` | selection [sim=Sim, nao=Não] | Agendamento | ❌ | ❌ | '-' |
| 16 | `always_tax_exigible` | boolean | Always Tax Exigible | ✅ | ❌ | False |
| 17 | `amount_paid` | monetary | Amount paid | ❌ | ❌ | '-' |
| 18 | `amount_residual` | monetary | Amount Due | ✅ | ❌ | '-' |
| 19 | `amount_residual_signed` | monetary | Amount Due Signed | ✅ | ❌ | '-' |
| 20 | `amount_tax` | monetary | Tax | ✅ | ❌ | '-' |
| 21 | `amount_tax_signed` | monetary | Tax Signed | ✅ | ❌ | '-' |
| 22 | `amount_total` | monetary | Total | ✅ | ❌ | '-' |
| 23 | `amount_total_in_currency_signed` | monetary | Total in Currency Signed | ✅ | ❌ | '-' |
| 24 | `amount_total_signed` | monetary | Total Signed | ✅ | ❌ | '-' |
| 25 | `amount_total_words` | char | Amount total in words | ❌ | ❌ | '-' |
| 26 | `amount_untaxed` | monetary | Untaxed Amount | ✅ | ❌ | '-' |
| 27 | `amount_untaxed_signed` | monetary | Untaxed Amount Signed | ✅ | ❌ | '-' |
| 28 | `asset_depreciated_value` | monetary | Cumulative Depreciation | ❌ | ❌ | '-' |
| 29 | `asset_depreciation_beginning_date` | date | Date of the beginning of the depreciation | ✅ | ❌ | '-' |
| 30 | `asset_id` | many2one → account.asset | Asset | ✅ | ❌ | '-' |
| 31 | `asset_id_display_name` | char | Asset Id Display Name | ❌ | ❌ | '-' |
| 32 | `asset_ids` | one2many → account.asset | Assets | ❌ | ❌ | '-' |
| 33 | `asset_number_days` | integer | Number of days | ✅ | ❌ | '-' |
| 34 | `asset_remaining_value` | monetary | Depreciable Value | ❌ | ❌ | '-' |
| 35 | `asset_value_change` | boolean | Asset Value Change | ✅ | ❌ | '-' |
| 36 | `attachment_ids` | one2many → ir.attachment | Attachments | ✅ | ❌ | '-' |
| 37 | `authorized_transaction_ids` | many2many → payment.transaction | Authorized Transactions | ❌ | ❌ | '-' |
| 38 | `auto_generated` | boolean | Auto Generated Document | ✅ | ❌ | '-' |
| 39 | `auto_invoice_id` | many2one → account.move | Source Invoice | ✅ | ❌ | '-' |
| 40 | `auto_post` | selection [no=No, at_date=At Date, monthly=Monthly, quarterly=Quarterly, yearly=Yearly] | Auto-post | ✅ | ✅ | 'no' |
| 41 | `auto_post_origin_id` | many2one → account.move | First recurring entry | ✅ | ❌ | '-' |
| 42 | `auto_post_until` | date | Auto-post until | ✅ | ❌ | '-' |
| 43 | `bank_partner_id` | many2one → res.partner | Bank Partner | ❌ | ❌ | '-' |
| 44 | `campaign_id` | many2one → utm.campaign | Campaign | ✅ | ❌ | False |
| 45 | `commercial_partner_id` | many2one → res.partner | Commercial Entity | ✅ | ❌ | '-' |
| 46 | `company_currency_id` | many2one → res.currency | Company Currency | ❌ | ❌ | '-' |
| 47 | `company_id` | many2one → res.company | Company | ✅ | ❌ | [4, 'NACOM GOYA - CD'] |
| 48 | `count_asset` | integer | Count Asset | ❌ | ❌ | '-' |
| 49 | `country_code` | char | Country Code | ❌ | ❌ | '-' |
| 50 | `create_date` | datetime | Created on | ✅ | ❌ | '-' |
| 51 | `create_uid` | many2one → res.users | Created by | ✅ | ❌ | '-' |
| 52 | `currency_id` | many2one → res.currency | Currency | ✅ | ✅ | '-' |
| 53 | `date` | date | Date | ✅ | ✅ | '2025-11-28' |
| 54 | `deferred_entry_type` | selection [expense=Deferred Expense, revenue=Deferred Revenue] | Deferred Entry Type | ❌ | ❌ | '-' |
| 55 | `deferred_move_ids` | many2many → account.move | Deferred Entries | ✅ | ❌ | '-' |
| 56 | `deferred_original_move_ids` | many2many → account.move | Original Invoices | ✅ | ❌ | '-' |
| 57 | `delivery_date` | date | Delivery Date | ✅ | ❌ | '-' |
| 58 | `depreciation_value` | monetary | Depreciation | ✅ | ❌ | '-' |
| 59 | `dfe_id` | many2one → l10n_br_ciel_it_account.dfe | Documento | ✅ | ❌ | '-' |
| 60 | `direction_sign` | integer | Direction Sign | ❌ | ❌ | '-' |
| 61 | `display_inactive_currency_warning` | boolean | Display Inactive Currency Warning | ❌ | ❌ | '-' |
| 62 | `display_name` | char | Display Name | ❌ | ❌ | '-' |
| 63 | `display_qr_code` | boolean | Display QR-code | ❌ | ❌ | '-' |
| 64 | `draft_asset_exists` | boolean | Draft Asset Exists | ❌ | ❌ | '-' |
| 65 | `duplicated_ref_ids` | many2many → account.move | Duplicated Ref | ❌ | ❌ | '-' |
| 66 | `edi_blocking_level` | selection [info=Info, warning=Warning, error=Error] | Edi Blocking Level | ❌ | ❌ | '-' |
| 67 | `edi_document_ids` | one2many → account.edi.document | Edi Document | ✅ | ❌ | '-' |
| 68 | `edi_error_count` | integer | Edi Error Count | ❌ | ❌ | '-' |
| 69 | `edi_error_message` | html | Edi Error Message | ❌ | ❌ | '-' |
| 70 | `edi_show_abandon_cancel_button` | boolean | Edi Show Abandon Cancel Button | ❌ | ❌ | '-' |
| 71 | `edi_show_cancel_button` | boolean | Edi Show Cancel Button | ❌ | ❌ | '-' |
| 72 | `edi_show_force_cancel_button` | boolean | Edi Show Force Cancel Button | ❌ | ❌ | '-' |
| 73 | `edi_state` | selection [to_send=To Send, sent=Sent, to_cancel=To Cancel, cancelled=Cancelled] | Electronic invoicing | ✅ | ❌ | '-' |
| 74 | `edi_web_services_to_process` | text | Edi Web Services To Process | ❌ | ❌ | '-' |
| 75 | `extract_attachment_id` | many2one → ir.attachment | Extract Attachment | ✅ | ❌ | '-' |
| 76 | `extract_can_show_banners` | boolean | Can show the ocr banners | ❌ | ❌ | '-' |
| 77 | `extract_can_show_send_button` | boolean | Can show the ocr send button | ❌ | ❌ | '-' |
| 78 | `extract_detected_layout` | integer | Extract Detected Layout Id | ✅ | ❌ | '-' |
| 79 | `extract_document_uuid` | char | ID of the request to IAP-OCR | ✅ | ❌ | '-' |
| 80 | `extract_error_message` | text | Error message | ❌ | ❌ | '-' |
| 81 | `extract_partner_name` | char | Extract Detected Partner Name | ✅ | ❌ | '-' |
| 82 | `extract_state` | selection [no_extract_requested=No extract requested, not_enough_credit=Not enough credits, error_status=An error occurred, waiting_extraction=Waiting extraction, extract_not_ready=waiting extraction, but it is not ready... (+3)] | Extract state | ✅ | ✅ | '-' |
| 83 | `extract_state_processed` | boolean | Extract State Processed | ✅ | ❌ | '-' |
| 84 | `extract_status` | char | Extract status | ✅ | ❌ | '-' |
| 85 | `extract_word_ids` | one2many → account.invoice_extract.words | Extract Word | ✅ | ❌ | '-' |
| 86 | `fiscal_position_id` | many2one → account.fiscal.position | Fiscal Position | ✅ | ❌ | '-' |
| 87 | `force_release_to_pay` | boolean | Force Status | ✅ | ❌ | '-' |
| 88 | `has_message` | boolean | Has Message | ❌ | ❌ | True |
| 89 | `has_reconciled_entries` | boolean | Has Reconciled Entries | ❌ | ❌ | '-' |
| 90 | `hide_post_button` | boolean | Hide Post Button | ❌ | ❌ | '-' |
| 91 | `highest_name` | char | Highest Name | ❌ | ❌ | '-' |
| 92 | `id` | integer | ID | ✅ | ❌ | 416177 |
| 93 | `inalterable_hash` | char | Inalterability Hash | ✅ | ❌ | '-' |
| 94 | `incoterm_location` | char | Incoterm Location | ✅ | ❌ | '-' |
| 95 | `invoice_cash_rounding_id` | many2one → account.cash.rounding | Cash Rounding Method | ✅ | ❌ | '-' |
| 96 | `invoice_date` | date | Invoice/Bill Date | ✅ | ❌ | '-' |
| 97 | `invoice_date_due` | date | Due Date | ✅ | ❌ | '-' |
| 98 | `invoice_filter_type_domain` | char | Invoice Filter Type Domain | ❌ | ❌ | '-' |
| 99 | `invoice_has_outstanding` | boolean | Invoice Has Outstanding | ❌ | ❌ | '-' |
| 100 | `invoice_incoterm_id` | many2one → account.incoterms | Tipo de Frete | ✅ | ❌ | '-' |
| 101 | `invoice_line_ids` | one2many → account.move.line | Invoice lines | ✅ | ❌ | '-' |
| 102 | `invoice_origin` | char | Origin | ✅ | ❌ | '-' |
| 103 | `invoice_outstanding_credits_debits_widget` | binary | Invoice Outstanding Credits Debits Widget | ❌ | ❌ | '-' |
| 104 | `invoice_partner_display_name` | char | Invoice Partner Display Name | ✅ | ❌ | '-' |
| 105 | `invoice_payment_term_id` | many2one → account.payment.term | Payment Terms | ✅ | ❌ | '-' |
| 106 | `invoice_payments_widget` | binary | Invoice Payments Widget | ❌ | ❌ | '-' |
| 107 | `invoice_pdf_report_file` | binary | PDF File | ✅ | ❌ | '-' |
| 108 | `invoice_pdf_report_id` | many2one → ir.attachment | PDF Attachment | ❌ | ❌ | '-' |
| 109 | `invoice_source_email` | char | Source Email | ✅ | ❌ | '-' |
| 110 | `invoice_user_id` | many2one → res.users | Salesperson | ✅ | ❌ | '-' |
| 111 | `invoice_vendor_bill_id` | many2one → account.move | Vendor Bill | ❌ | ❌ | '-' |
| 112 | `is_being_sent` | boolean | Is Being Sent | ❌ | ❌ | '-' |
| 113 | `is_encerramento` | boolean | Lançamento de Encerramento | ✅ | ❌ | '-' |
| 114 | `is_in_extractable_state` | boolean | Is In Extractable State | ✅ | ❌ | '-' |
| 115 | `is_move_sent` | boolean | Is Move Sent | ✅ | ❌ | '-' |
| 116 | `is_storno` | boolean | Is Storno | ✅ | ❌ | False |
| 117 | `journal_id` | many2one → account.journal | Journal | ✅ | ✅ | [826, 'VENDA DE PRODUÇÃO'] |
| 118 | `l10n_br_calcular_imposto` | boolean | Calcular Impostos | ✅ | ❌ | '-' |
| 119 | `l10n_br_carrier_id` | many2one → delivery.carrier | Carrier | ✅ | ❌ | '-' |
| 120 | `l10n_br_cbs_valor` | float | Total do CBS | ✅ | ❌ | '-' |
| 121 | `l10n_br_cfop_id` | many2one → l10n_br_ciel_it_account.cfop | CFOP | ✅ | ❌ | '-' |
| 122 | `l10n_br_chave_nf` | char | Chave da Nota Fiscal | ✅ | ❌ | '-' |
| 123 | `l10n_br_cnpj` | char | CNPJ | ✅ | ❌ | '-' |
| 124 | `l10n_br_cofins_ret_base` | float | Base do Cofins Retido | ✅ | ❌ | '-' |
| 125 | `l10n_br_cofins_ret_valor` | float | Valor do Cofins Retido | ✅ | ❌ | '-' |
| 126 | `l10n_br_cofins_valor` | float | Total do Cofins | ✅ | ❌ | '-' |
| 127 | `l10n_br_cofins_valor_isento` | float | Total do Cofins (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 128 | `l10n_br_cofins_valor_outros` | float | Total do Cofins (Outros) | ✅ | ❌ | '-' |
| 129 | `l10n_br_compra_indcom` | selection [uso=Uso e Consumo, uso-prestacao=Uso na Prestação de Serviço, ind=Industrialização, com=Comercialização, ativo=Ativo... (+2)] | Destinação de Uso | ✅ | ❌ | '-' |
| 130 | `l10n_br_correcao` | text | Correção | ✅ | ❌ | '-' |
| 131 | `l10n_br_csll_ret_base` | float | Base do CSLL Retido | ✅ | ❌ | '-' |
| 132 | `l10n_br_csll_ret_valor` | float | Valor do CSLL Retido | ✅ | ❌ | '-' |
| 133 | `l10n_br_csll_valor` | float | Total do CSLL | ✅ | ❌ | '-' |
| 134 | `l10n_br_cstat_nf` | char | Status da Nota Fiscal | ✅ | ❌ | '-' |
| 135 | `l10n_br_data_nfse_substituida` | date | Data de Emissão da NFS-e Substituida | ✅ | ❌ | '-' |
| 136 | `l10n_br_data_saida` | datetime | Data/Hora de Saída | ✅ | ❌ | '-' |
| 137 | `l10n_br_dctf_imposto_codigo` | char | Código do Imposto DCTF | ✅ | ❌ | '-' |
| 138 | `l10n_br_desc_valor` | float | Total do Desconto | ✅ | ❌ | '-' |
| 139 | `l10n_br_descricao_servico` | text | Descrição do Serviço | ✅ | ❌ | '-' |
| 140 | `l10n_br_descricao_servico_show` | boolean | Mostrar Descrição do Serviço | ❌ | ❌ | '-' |
| 141 | `l10n_br_despesas_acessorias` | float | Total da Despesas Acessórias | ✅ | ❌ | '-' |
| 142 | `l10n_br_especie` | char | Espécie | ✅ | ❌ | '-' |
| 143 | `l10n_br_fcp_dest_valor` | float | Total do Fundo de Combate a Pobreza | ✅ | ❌ | '-' |
| 144 | `l10n_br_fcp_st_ant_valor` | float | Total do Fundo de Combate a Pobreza Retido Anteriormente por ST | ✅ | ❌ | '-' |
| 145 | `l10n_br_fcp_st_valor` | float | Total do Fundo de Combate a Pobreza Retido por ST | ✅ | ❌ | '-' |
| 146 | `l10n_br_frete` | float | Total do Frete | ✅ | ❌ | '-' |
| 147 | `l10n_br_gnre_disponivel` | boolean | GNRE Disponível | ❌ | ❌ | '-' |
| 148 | `l10n_br_gnre_numero_recibo` | char | GNRE - Número do Recibo | ✅ | ❌ | '-' |
| 149 | `l10n_br_gnre_ok` | boolean | GNRE OK | ✅ | ❌ | '-' |
| 150 | `l10n_br_handle_nfce` | integer | Handle da Nota Fiscal Eletrônica ao Consumidor | ✅ | ❌ | '-' |
| 151 | `l10n_br_handle_nfse` | integer | Handle da Nota Fiscal de Serviço | ✅ | ❌ | '-' |
| 152 | `l10n_br_ibs_mun_valor` | float | Total do IBS Município | ✅ | ❌ | '-' |
| 153 | `l10n_br_ibs_uf_valor` | float | Total do IBS UF | ✅ | ❌ | '-' |
| 154 | `l10n_br_ibs_valor` | float | Total do IBS | ✅ | ❌ | '-' |
| 155 | `l10n_br_ibscbs_base` | float | Total da Base de Cálculo do IBS/CBS | ✅ | ❌ | '-' |
| 156 | `l10n_br_icms_base` | float | Total da Base de Cálculo do ICMS | ✅ | ❌ | '-' |
| 157 | `l10n_br_icms_dest_valor` | float | Total do ICMS UF Destino | ✅ | ❌ | '-' |
| 158 | `l10n_br_icms_remet_valor` | float | Total do ICMS UF Remetente | ✅ | ❌ | '-' |
| 159 | `l10n_br_icms_valor` | float | Total do ICMS (Tributável) | ✅ | ❌ | '-' |
| 160 | `l10n_br_icms_valor_credito_presumido` | float | Total do ICMS (Crédito Presumido) | ✅ | ❌ | '-' |
| 161 | `l10n_br_icms_valor_desonerado` | float | Total do ICMS (Desonerado) | ✅ | ❌ | '-' |
| 162 | `l10n_br_icms_valor_efetivo` | float | Total do ICMS (Efetivo) | ✅ | ❌ | '-' |
| 163 | `l10n_br_icms_valor_isento` | float | Total do ICMS (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 164 | `l10n_br_icms_valor_outros` | float | Total do ICMS (Outros) | ✅ | ❌ | '-' |
| 165 | `l10n_br_icmsst_base` | float | Total da Base de Cálculo do ICMSST | ✅ | ❌ | '-' |
| 166 | `l10n_br_icmsst_retido_valor` | float | Total do ICMSST Retido | ✅ | ❌ | '-' |
| 167 | `l10n_br_icmsst_retido_valor_outros` | float | Total do ICMSST Retido (Outros) | ✅ | ❌ | '-' |
| 168 | `l10n_br_icmsst_substituto_valor` | float | Total do ICMSST Substituto | ✅ | ❌ | '-' |
| 169 | `l10n_br_icmsst_substituto_valor_outros` | float | Total do ICMSST Substituto (Outros) | ✅ | ❌ | '-' |
| 170 | `l10n_br_icmsst_valor` | float | Total do ICMSST | ✅ | ❌ | '-' |
| 171 | `l10n_br_icmsst_valor_outros` | float | Total do ICMSST (Outros) | ✅ | ❌ | '-' |
| 172 | `l10n_br_icmsst_valor_proprio` | float | Total do ICMSST (Próprio) | ✅ | ❌ | '-' |
| 173 | `l10n_br_ii_valor` | float | Total do II | ✅ | ❌ | '-' |
| 174 | `l10n_br_ii_valor_aduaneira` | float | Total do II Aduaneira | ✅ | ❌ | '-' |
| 175 | `l10n_br_ii_valor_afrmm` | float | Total do II AFRMM | ✅ | ❌ | '-' |
| 176 | `l10n_br_imposto_auto` | boolean | Calcular Impostos Automaticamente | ✅ | ❌ | '-' |
| 177 | `l10n_br_indicador_presenca` | selection [0=0 - Não se aplica, 1=1 - Operação presencial, 2=2 - Operação não presencial, pela internet, 3=3 - Operação não presencial, teleatendimento, 4=4 - NFC-e em operação com entrega a domicílio... (+2)] | Indicador Presença | ✅ | ❌ | '-' |
| 178 | `l10n_br_informacao_complementar` | text | Informação Complementar | ✅ | ❌ | '-' |
| 179 | `l10n_br_informacao_fiscal` | text | Informação Fiscal | ✅ | ❌ | '-' |
| 180 | `l10n_br_inss_ret_base` | float | Base do INSS Retido | ✅ | ❌ | '-' |
| 181 | `l10n_br_inss_ret_valor` | float | Valor do INSS Retido | ✅ | ❌ | '-' |
| 182 | `l10n_br_iof_valor` | float | Total do IOF | ✅ | ❌ | '-' |
| 183 | `l10n_br_ipi_valor` | float | Total do IPI | ✅ | ❌ | '-' |
| 184 | `l10n_br_ipi_valor_isento` | float | Total do IPI (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 185 | `l10n_br_ipi_valor_outros` | float | Total do IPI (Outros) | ✅ | ❌ | '-' |
| 186 | `l10n_br_irpj_ret_base` | float | Base do IRPJ Retido | ✅ | ❌ | '-' |
| 187 | `l10n_br_irpj_ret_valor` | float | Valor do IRPJ Retido | ✅ | ❌ | '-' |
| 188 | `l10n_br_irpj_valor` | float | Total do IRPJ | ✅ | ❌ | '-' |
| 189 | `l10n_br_is_valor` | float | Total do IS | ✅ | ❌ | '-' |
| 190 | `l10n_br_iss_municipio_id` | many2one → l10n_br_ciel_it_account.res.municipio | Município de Incidência do ISS | ✅ | ❌ | '-' |
| 191 | `l10n_br_iss_ret_base` | float | Base do ISS Retido | ✅ | ❌ | '-' |
| 192 | `l10n_br_iss_ret_valor` | float | Valor do ISS Retido | ✅ | ❌ | '-' |
| 193 | `l10n_br_iss_valor` | float | Total do ISS | ✅ | ❌ | '-' |
| 194 | `l10n_br_item_pedido_compra` | char | Item Pedido de Compra do Cliente | ✅ | ❌ | '-' |
| 195 | `l10n_br_local_despacho` | char | Local de despacho | ✅ | ❌ | '-' |
| 196 | `l10n_br_local_embarque` | char | Local de embarque | ✅ | ❌ | '-' |
| 197 | `l10n_br_marca` | char | Marca | ✅ | ❌ | '-' |
| 198 | `l10n_br_motivo` | text | Motivo Cancelamento | ✅ | ❌ | '-' |
| 199 | `l10n_br_municipio_fim_id` | many2one → l10n_br_ciel_it_account.res.municipio | Município de Destino | ✅ | ❌ | '-' |
| 200 | `l10n_br_municipio_inicio_id` | many2one → l10n_br_ciel_it_account.res.municipio | Município de Origem | ✅ | ❌ | '-' |
| 201 | `l10n_br_nfe_emails` | char | Email XML NF-e | ❌ | ❌ | '-' |
| 202 | `l10n_br_nfse_substituta` | boolean | NFS-e Substituta? | ✅ | ❌ | '-' |
| 203 | `l10n_br_numeracao_volume` | char | Númeração Volume | ✅ | ❌ | '-' |
| 204 | `l10n_br_numero_nf` | integer | Número da Nota Fiscal de Mercadoria | ✅ | ❌ | '-' |
| 205 | `l10n_br_numero_nfce` | char | Número da Nota Fiscal Eletrônica ao Consumidor | ✅ | ❌ | '-' |
| 206 | `l10n_br_numero_nfse` | char | Número da Nota Fiscal de Serviço | ✅ | ❌ | '-' |
| 207 | `l10n_br_numero_nfse_substituida` | char | Número da NFS-e Substituida | ✅ | ❌ | '-' |
| 208 | `l10n_br_numero_nota_fiscal` | char | Número da Nota Fiscal | ✅ | ❌ | '-' |
| 209 | `l10n_br_numero_rps` | integer | Número RPS | ✅ | ❌ | '-' |
| 210 | `l10n_br_numero_rps_substituido` | integer | Número RPS Substituido | ✅ | ❌ | '-' |
| 211 | `l10n_br_operacao_consumidor` | selection [0=0 - Normal, 1=1 - Consumidor Final] | Operação Consumidor Final | ✅ | ❌ | '-' |
| 212 | `l10n_br_operacao_id` | many2one → l10n_br_ciel_it_account.operacao | Operação | ❌ | ❌ | '-' |
| 213 | `l10n_br_pdf_aut_gnre` | binary | GNRE | ✅ | ❌ | '-' |
| 214 | `l10n_br_pdf_aut_gnre_fname` | char | Arquivo GNRE | ❌ | ❌ | '-' |
| 215 | `l10n_br_pdf_aut_nfe` | binary | DANFE NF-e | ✅ | ❌ | '-' |
| 216 | `l10n_br_pdf_aut_nfe_fname` | char | Arquivo DANFE NF-e | ❌ | ❌ | '-' |
| 217 | `l10n_br_pdf_can_nfe` | binary | DANFE NF-e Cancelamento | ✅ | ❌ | '-' |
| 218 | `l10n_br_pdf_can_nfe_fname` | char | Arquivo DANFE NF-e Cancelamento | ❌ | ❌ | '-' |
| 219 | `l10n_br_pdf_cce_nfe` | binary | DANFE CC-e | ✅ | ❌ | '-' |
| 220 | `l10n_br_pdf_cce_nfe_fname` | char | Arquivo DANFE CC-e | ❌ | ❌ | '-' |
| 221 | `l10n_br_pedido_compra` | char | Pedido de Compra do Cliente | ✅ | ❌ | '-' |
| 222 | `l10n_br_peso_bruto` | float | Peso Bruto | ✅ | ❌ | '-' |
| 223 | `l10n_br_peso_liquido` | float | Peso Líquido | ✅ | ❌ | '-' |
| 224 | `l10n_br_pis_ret_base` | float | Base do PIS Retido | ✅ | ❌ | '-' |
| 225 | `l10n_br_pis_ret_valor` | float | Valor do PIS Retido | ✅ | ❌ | '-' |
| 226 | `l10n_br_pis_valor` | float | Total do PIS | ✅ | ❌ | '-' |
| 227 | `l10n_br_pis_valor_isento` | float | Total do PIS (Isento/Não Tributável) | ✅ | ❌ | '-' |
| 228 | `l10n_br_pis_valor_outros` | float | Total do PIS (Outros) | ✅ | ❌ | '-' |
| 229 | `l10n_br_prod_valor` | float | Total dos Produtos | ✅ | ❌ | '-' |
| 230 | `l10n_br_rateio_frete_auto` | boolean | Rateio Frete Automatico | ✅ | ❌ | '-' |
| 231 | `l10n_br_seguro` | float | Total do Seguro | ✅ | ❌ | '-' |
| 232 | `l10n_br_sequencia_evento` | integer | Sequencia Evento NF-e | ✅ | ❌ | '-' |
| 233 | `l10n_br_serie_nf` | char | Série da Nota Fiscal | ✅ | ❌ | '-' |
| 234 | `l10n_br_serie_nf_substituido` | char | Série NFS-e Substituido | ✅ | ❌ | '-' |
| 235 | `l10n_br_show_nfe_btn` | boolean | Mostrar botão NF-e | ❌ | ❌ | '-' |
| 236 | `l10n_br_situacao_nf` | selection [rascunho=Rascunho, autorizado=Autorizado, excecao_autorizado=Exceção, cce=Carta de Correção, excecao_cce=Exceção... (+2)] | Situação NF-e | ✅ | ❌ | '-' |
| 237 | `l10n_br_tipo_documento` | selection [NFS=Nota Fiscal de Serviços Instituída por Municípios, NFSE=Nota Fiscal de Serviços Eletrônica - NFS-e, NDS=Nota de Débito de Serviços, FAT=Fatura, ND=Nota de Débito... (+32)] | Tipo Documento Fiscal | ✅ | ❌ | '-' |
| 238 | `l10n_br_tipo_imposto` | selection [cofins=COFINS, csll=CSLL, icms=ICMS, ii=II, inss=INSS... (+7)] | Tipo Imposto | ✅ | ❌ | '-' |
| 239 | `l10n_br_tipo_pedido` | selection [baixa-estoque=Saída: Baixa de Estoque, complemento-valor=Saída: Complemento de Preço, dev-comodato=Saída: Devolução de Comodato, compra=Saída: Devolução de Compra, dev-conserto=Saída: Devolução de Conserto... (+42)] | Tipo de Pedido (saída) | ✅ | ❌ | '-' |
| 240 | `l10n_br_tipo_pedido_entrada` | selection [ent-amostra=Entrada: Amostra Grátis, ent-bonificacao=Entrada: Bonificação, ent-comodato=Entrada: Comodato, comp-importacao=Entrada: Complementar de Importação, compra=Entrada: Compra... (+33)] | Tipo de Pedido (entrada) | ✅ | ❌ | '-' |
| 241 | `l10n_br_total_nfe` | float | Total da Nota Fiscal | ✅ | ❌ | '-' |
| 242 | `l10n_br_total_tributos` | float | Total dos Tributos | ✅ | ❌ | '-' |
| 243 | `l10n_br_uf_saida_pais` | char | Sigla UF de Saída | ✅ | ❌ | '-' |
| 244 | `l10n_br_veiculo_placa` | char | Placa | ✅ | ❌ | '-' |
| 245 | `l10n_br_veiculo_rntc` | char | RNTC | ✅ | ❌ | '-' |
| 246 | `l10n_br_veiculo_uf` | char | UF da Placa | ✅ | ❌ | '-' |
| 247 | `l10n_br_volumes` | integer | Volumes | ✅ | ❌ | '-' |
| 248 | `l10n_br_xml_aut_nfe` | binary | XML NF-e | ✅ | ❌ | '-' |
| 249 | `l10n_br_xml_aut_nfe_fname` | char | Arquivo XML NF-e | ❌ | ❌ | '-' |
| 250 | `l10n_br_xml_can_nfe` | binary | XML NF-e Cancelamento | ✅ | ❌ | '-' |
| 251 | `l10n_br_xml_can_nfe_fname` | char | Arquivo XML NF-e Cancelamento | ❌ | ❌ | '-' |
| 252 | `l10n_br_xml_cce_nfe` | binary | XML CC-e | ✅ | ❌ | '-' |
| 253 | `l10n_br_xml_cce_nfe_fname` | char | Arquivo XML CC-e | ❌ | ❌ | '-' |
| 254 | `l10n_br_xmotivo_nf` | char | Situação da Nota Fiscal | ✅ | ❌ | '-' |
| 255 | `landed_costs_ids` | one2many → stock.landed.cost | Landed Costs | ✅ | ❌ | '-' |
| 256 | `landed_costs_visible` | boolean | Landed Costs Visible | ❌ | ❌ | '-' |
| 257 | `laudos` | binary | Laudos | ✅ | ❌ | '-' |
| 258 | `laudos_filename` | char | Nome do arquivo de laudos | ✅ | ❌ | '-' |
| 259 | `line_ids` | one2many → account.move.line | Journal Items | ✅ | ❌ | [46 itens: [2703759, 2703760, 2703761]...] |
| 260 | `made_sequence_hole` | boolean | Made Sequence Hole | ❌ | ❌ | '-' |
| 261 | `medium_id` | many2one → utm.medium | Medium | ✅ | ❌ | False |
| 262 | `message_attachment_count` | integer | Attachment Count | ❌ | ❌ | 2 |
| 263 | `message_follower_ids` | one2many → mail.followers | Followers | ✅ | ❌ | [2578338, '2578339'] |
| 264 | `message_has_error` | boolean | Message Delivery error | ❌ | ❌ | False |
| 265 | `message_has_error_counter` | integer | Number of errors | ❌ | ❌ | 0 |
| 266 | `message_has_sms_error` | boolean | SMS Delivery error | ❌ | ❌ | False |
| 267 | `message_ids` | one2many → mail.message | Messages | ✅ | ❌ | [15 itens: [12420053, 12420051, 12420048]...] |
| 268 | `message_is_follower` | boolean | Is Follower | ❌ | ❌ | False |
| 269 | `message_main_attachment_id` | many2one → ir.attachment | Main Attachment | ✅ | ❌ | [265234, '3525116172424100033055001000142323100... |
| 270 | `message_needaction` | boolean | Action Needed | ❌ | ❌ | False |
| 271 | `message_needaction_counter` | integer | Number of Actions | ❌ | ❌ | 0 |
| 272 | `message_partner_ids` | many2many → res.partner | Followers (Partners) | ❌ | ❌ | [203957, '206233'] |
| 273 | `move_type` | selection [entry=Journal Entry, out_invoice=Customer Invoice, out_refund=Customer Credit Note, in_invoice=Vendor Bill, in_refund=Vendor Credit Note... (+2)] | Type | ✅ | ✅ | 'out_invoice' |
| 274 | `my_activity_date_deadline` | date | My Activity Deadline | ❌ | ❌ | False |
| 275 | `name` | char | Number | ✅ | ❌ | 'VND/2025/05453' |
| 276 | `narration` | html | Terms and Conditions | ✅ | ❌ | '-' |
| 277 | `need_cancel_request` | boolean | Need Cancel Request | ❌ | ❌ | '-' |
| 278 | `needed_terms` | binary | Needed Terms | ❌ | ❌ | '-' |
| 279 | `needed_terms_dirty` | boolean | Needed Terms Dirty | ❌ | ❌ | '-' |
| 280 | `parcelas_manual_id` | many2one → l10n_br_ciel_it_account.payment.parcela.manual | Parcelas Personalizada | ✅ | ❌ | '-' |
| 281 | `partner_bank_id` | many2one → res.partner.bank | Recipient Bank | ✅ | ❌ | '-' |
| 282 | `partner_contact_id` | many2one → res.partner | Contato | ✅ | ❌ | '-' |
| 283 | `partner_credit` | monetary | Partner Credit | ❌ | ❌ | '-' |
| 284 | `partner_credit_warning` | text | Partner Credit Warning | ❌ | ❌ | '-' |
| 285 | `partner_id` | many2one → res.partner | Partner | ✅ | ❌ | '-' |
| 286 | `partner_invoice_id` | many2one → res.partner | Endereço de Cobrança | ✅ | ❌ | '-' |
| 287 | `partner_shipping_id` | many2one → res.partner | Delivery Address | ✅ | ❌ | '-' |
| 288 | `payment_id` | many2one → account.payment | Payment | ✅ | ❌ | False |
| 289 | `payment_ids` | one2many → account.payment | Payments | ✅ | ❌ | '-' |
| 290 | `payment_line_ids` | many2many → account.move.line | Payment lines | ❌ | ❌ | '-' |
| 291 | `payment_provider_id` | many2one → payment.provider | Forma de Pagamento | ✅ | ❌ | '-' |
| 292 | `payment_reference` | char | Payment Reference | ✅ | ❌ | '-' |
| 293 | `payment_state` | selection [not_paid=Not Paid, in_payment=In Payment, paid=Paid, partial=Partially Paid, reversed=Reversed... (+1)] | Payment Status | ✅ | ❌ | '-' |
| 294 | `payment_state_before_switch` | char | Payment State Before Switch | ✅ | ❌ | '-' |
| 295 | `payment_term_details` | binary | Payment Term Details | ❌ | ❌ | '-' |
| 296 | `picking_ids` | many2many → stock.picking | Picking References | ✅ | ❌ | '-' |
| 297 | `picking_ok` | boolean | Picking OK | ✅ | ❌ | '-' |
| 298 | `posted_before` | boolean | Posted Before | ✅ | ❌ | '-' |
| 299 | `purchase_id` | many2one → purchase.order | Purchase Order | ❌ | ❌ | '-' |
| 300 | `purchase_order_count` | integer | Purchase Order Count | ❌ | ❌ | '-' |
| 301 | `purchase_vendor_bill_id` | many2one → purchase.bill.union | Auto-complete | ❌ | ❌ | '-' |
| 302 | `qr_code_method` | selection | Payment QR-code | ✅ | ❌ | '-' |
| 303 | `quick_edit_mode` | boolean | Quick Edit Mode | ❌ | ❌ | '-' |
| 304 | `quick_edit_total_amount` | monetary | Total (Tax inc.) | ✅ | ❌ | '-' |
| 305 | `quick_encoding_vals` | json | Quick Encoding Vals | ❌ | ❌ | '-' |
| 306 | `rating_ids` | one2many → rating.rating | Ratings | ✅ | ❌ | [] |
| 307 | `ref` | char | Reference | ✅ | ❌ | '' |
| 308 | `referencia_ids` | one2many → l10n_br_ciel_it_account.account.move.referencia | NF-e referência | ✅ | ❌ | '-' |
| 309 | `reinfs_2010_count` | integer | REINF 2010 Qtd. | ❌ | ❌ | '-' |
| 310 | `reinfs_2010_ids` | one2many → l10n_br_ciel_it_account.reinf.2010 | REINF 2010 | ❌ | ❌ | '-' |
| 311 | `reinfs_2020_count` | integer | REINF 2020 Qtd. | ❌ | ❌ | '-' |
| 312 | `reinfs_2020_ids` | one2many → l10n_br_ciel_it_account.reinf.2020 | REINF 2020 | ❌ | ❌ | '-' |
| 313 | `reinfs_2060_count` | integer | REINF 2060 Qtd. | ❌ | ❌ | '-' |
| 314 | `reinfs_2060_ids` | one2many → l10n_br_ciel_it_account.reinf.2060 | REINF 2060 | ✅ | ❌ | '-' |
| 315 | `reinfs_4010_count` | integer | REINF 4010 Qtd. | ❌ | ❌ | '-' |
| 316 | `reinfs_4010_ids` | one2many → l10n_br_ciel_it_account.reinf.4010 | REINF 4010 | ✅ | ❌ | '-' |
| 317 | `reinfs_4020_count` | integer | REINF 4020 Qtd. | ❌ | ❌ | '-' |
| 318 | `reinfs_4020_ids` | one2many → l10n_br_ciel_it_account.reinf.4020 | REINF 4020 | ❌ | ❌ | '-' |
| 319 | `reinfs_4080_count` | integer | REINF 4080 Qtd. | ❌ | ❌ | '-' |
| 320 | `reinfs_4080_ids` | one2many → l10n_br_ciel_it_account.reinf.4080 | REINF 4080 | ✅ | ❌ | '-' |
| 321 | `release_to_pay` | selection [yes=Yes, no=No, exception=Exception] | Release To Pay | ✅ | ❌ | '-' |
| 322 | `release_to_pay_manual` | selection [yes=Yes, no=No, exception=Exception] | Should Be Paid | ✅ | ❌ | '-' |
| 323 | `restrict_mode_hash_table` | boolean | Lock Posted Entries with Hash | ❌ | ❌ | '-' |
| 324 | `reversal_move_id` | one2many → account.move | Reversal Move | ✅ | ❌ | '-' |
| 325 | `reversed_entry_id` | many2one → account.move | Reversal of | ✅ | ❌ | '-' |
| 326 | `sale_order_count` | integer | Sale Order Count | ❌ | ❌ | '-' |
| 327 | `secure_sequence_number` | integer | Inalteralbility No Gap Sequence # | ✅ | ❌ | '-' |
| 328 | `send_and_print_values` | json | Send And Print Values | ✅ | ❌ | '-' |
| 329 | `sequence_number` | integer | Sequence Number | ✅ | ❌ | 5453 |
| 330 | `sequence_prefix` | char | Sequence Prefix | ✅ | ❌ | 'VND/2025/' |
| 331 | `show_delivery_date` | boolean | Show Delivery Date | ❌ | ❌ | '-' |
| 332 | `show_discount_details` | boolean | Show Discount Details | ❌ | ❌ | '-' |
| 333 | `show_name_warning` | boolean | Show Name Warning | ❌ | ❌ | '-' |
| 334 | `show_payment_term_details` | boolean | Show Payment Term Details | ❌ | ❌ | '-' |
| 335 | `show_reset_to_draft_button` | boolean | Show Reset To Draft Button | ❌ | ❌ | '-' |
| 336 | `show_update_fpos` | boolean | Has Fiscal Position Changed | ❌ | ❌ | '-' |
| 337 | `simples_nacional` | boolean | Emitente Simples Nacional | ✅ | ❌ | '-' |
| 338 | `source_id` | many2one → utm.source | Source | ✅ | ❌ | False |
| 339 | `state` | selection [draft=Draft, posted=Posted, cancel=Cancelled] | Status | ✅ | ✅ | 'posted' |
| 340 | `statement_id` | many2one → account.bank.statement | Statement | ❌ | ❌ | False |
| 341 | `statement_line_id` | many2one → account.bank.statement.line | Statement Line | ✅ | ❌ | False |
| 342 | `statement_line_ids` | one2many → account.bank.statement.line | Statements | ✅ | ❌ | '-' |
| 343 | `stock_move_id` | many2one → stock.move | Stock Move | ✅ | ❌ | '-' |
| 344 | `stock_valuation_layer_ids` | one2many → stock.valuation.layer | Stock Valuation Layer | ✅ | ❌ | '-' |
| 345 | `string_to_hash` | char | String To Hash | ❌ | ❌ | '-' |
| 346 | `suitable_journal_ids` | many2many → account.journal | Suitable Journal | ❌ | ❌ | '-' |
| 347 | `suspense_statement_line_id` | many2one → account.bank.statement.line | Request document from a bank statement line | ✅ | ❌ | '-' |
| 348 | `tax_calculation_rounding_method` | selection [round_per_line=Round per Line, round_globally=Round Globally] | Tax calculation rounding method | ❌ | ❌ | '-' |
| 349 | `tax_cash_basis_created_move_ids` | one2many → account.move | Cash Basis Entries | ✅ | ❌ | [] |
| 350 | `tax_cash_basis_origin_move_id` | many2one → account.move | Cash Basis Origin | ✅ | ❌ | False |
| 351 | `tax_cash_basis_rec_id` | many2one → account.partial.reconcile | Tax Cash Basis Entry of | ✅ | ❌ | False |
| 352 | `tax_closing_alert` | boolean | Tax Closing Alert | ❌ | ❌ | '-' |
| 353 | `tax_closing_end_date` | date | Tax Closing End Date | ✅ | ❌ | '-' |
| 354 | `tax_closing_show_multi_closing_warning` | boolean | Tax Closing Show Multi Closing Warning | ❌ | ❌ | '-' |
| 355 | `tax_country_code` | char | Tax Country Code | ❌ | ❌ | '-' |
| 356 | `tax_country_id` | many2one → res.country | Tax Country | ❌ | ❌ | '-' |
| 357 | `tax_lock_date_message` | char | Tax Lock Date Message | ❌ | ❌ | '-' |
| 358 | `tax_report_control_error` | boolean | Tax Report Control Error | ✅ | ❌ | '-' |
| 359 | `tax_totals` | binary | Invoice Totals | ❌ | ❌ | '-' |
| 360 | `team_id` | many2one → crm.team | Sales Team | ✅ | ❌ | '-' |
| 361 | `timesheet_count` | integer | Number of timesheets | ❌ | ❌ | '-' |
| 362 | `timesheet_encode_uom_id` | many2one → uom.uom | Timesheet Encoding Unit | ❌ | ❌ | '-' |
| 363 | `timesheet_ids` | one2many → account.analytic.line | Timesheets | ✅ | ❌ | '-' |
| 364 | `timesheet_total_duration` | integer | Timesheet Total Duration | ❌ | ❌ | '-' |
| 365 | `to_check` | boolean | To Check | ✅ | ❌ | '-' |
| 366 | `transaction_ids` | many2many → payment.transaction | Transactions | ✅ | ❌ | '-' |
| 367 | `transfer_model_id` | many2one → account.transfer.model | Originating Model | ✅ | ❌ | '-' |
| 368 | `type_name` | char | Type Name | ❌ | ❌ | '-' |
| 369 | `ubl_cii_xml_file` | binary | UBL/CII File | ✅ | ❌ | '-' |
| 370 | `ubl_cii_xml_id` | many2one → ir.attachment | Attachment | ❌ | ❌ | '-' |
| 371 | `user_id` | many2one → res.users | User | ❌ | ❌ | '-' |
| 372 | `usuario_id` | many2one → res.partner | Usuário | ✅ | ❌ | '-' |
| 373 | `website_message_ids` | one2many → mail.message | Website Messages | ✅ | ❌ | [] |
| 374 | `write_date` | datetime | Last Updated on | ✅ | ❌ | '-' |
| 375 | `write_uid` | many2one → res.users | Last Updated by | ✅ | ❌ | '-' |
| 376 | `x_studio_observao_interna` | text | Observação Interna | ✅ | ❌ | '-' |


### DETALHAMENTO DOS CAMPOS:

#### `access_token`
- **Label:** Security Token
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `'f9ab66d4-a0ae-4774-b982-03d8b2ae27f5'`

#### `access_url`
- **Label:** Portal Access URL
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Customer Portal URL
- **Valor Exemplo:** `'/my/invoices/416177'`

#### `access_warning`
- **Label:** Access warning
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `''`

#### `activity_calendar_event_id`
- **Label:** Next Activity Calendar Event
- **Tipo:** many2one → calendar.event
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `calendar.event`
- **Valor Exemplo:** `False`

#### `activity_date_deadline`
- **Label:** Next Activity Deadline
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `activity_exception_decoration`
- **Label:** Activity Exception Decoration
- **Tipo:** selection [warning=Alert, danger=Error]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['warning', 'Alert'], ['danger', 'Error']]
- **Descrição:** Type of the exception activity on record.
- **Valor Exemplo:** `False`

#### `activity_exception_icon`
- **Label:** Icon
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Icon to indicate an exception activity.
- **Valor Exemplo:** `False`

#### `activity_ids`
- **Label:** Activities
- **Tipo:** one2many → mail.activity
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.activity`
- **Valor Exemplo:** `[]`

#### `activity_state`
- **Label:** Activity State
- **Tipo:** selection [overdue=Overdue, today=Today, planned=Planned]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']]
- **Descrição:** Status based on activities
Overdue: Due date is already passed
Today: Activity date is today
Planned: Future activities.
- **Valor Exemplo:** `False`

#### `activity_summary`
- **Label:** Next Activity Summary
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `activity_type_icon`
- **Label:** Activity Type Icon
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Font awesome icon e.g. fa-tasks
- **Valor Exemplo:** `False`

#### `activity_type_id`
- **Label:** Next Activity Type
- **Tipo:** many2one → mail.activity.type
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.activity.type`
- **Valor Exemplo:** `False`

#### `activity_user_id`
- **Label:** Responsible User
- **Tipo:** many2one → res.users
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `False`

#### `adiantamento_id`
- **Label:** Adiantamento
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `agendamento_id`
- **Label:** Agendamento
- **Tipo:** selection [sim=Sim, nao=Não]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['sim', 'Sim'], ['nao', 'Não']]

#### `always_tax_exigible`
- **Label:** Always Tax Exigible
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `amount_paid`
- **Label:** Amount paid
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_residual`
- **Label:** Amount Due
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_residual_signed`
- **Label:** Amount Due Signed
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_tax`
- **Label:** Tax
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_tax_signed`
- **Label:** Tax Signed
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total`
- **Label:** Total
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total_in_currency_signed`
- **Label:** Total in Currency Signed
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total_signed`
- **Label:** Total Signed
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total_words`
- **Label:** Amount total in words
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_untaxed`
- **Label:** Untaxed Amount
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_untaxed_signed`
- **Label:** Untaxed Amount Signed
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_depreciated_value`
- **Label:** Cumulative Depreciation
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_depreciation_beginning_date`
- **Label:** Date of the beginning of the depreciation
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `asset_id`
- **Label:** Asset
- **Tipo:** many2one → account.asset
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.asset`

#### `asset_id_display_name`
- **Label:** Asset Id Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_ids`
- **Label:** Assets
- **Tipo:** one2many → account.asset
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.asset`

#### `asset_number_days`
- **Label:** Number of days
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `asset_remaining_value`
- **Label:** Depreciable Value
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_value_change`
- **Label:** Asset Value Change
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `attachment_ids`
- **Label:** Attachments
- **Tipo:** one2many → ir.attachment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `ir.attachment`

#### `authorized_transaction_ids`
- **Label:** Authorized Transactions
- **Tipo:** many2many → payment.transaction
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `payment.transaction`

#### `auto_generated`
- **Label:** Auto Generated Document
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `auto_invoice_id`
- **Label:** Source Invoice
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `auto_post`
- **Label:** Auto-post
- **Tipo:** selection [no=No, at_date=At Date, monthly=Monthly, quarterly=Quarterly, yearly=Yearly]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['no', 'No'], ['at_date', 'At Date'], ['monthly', 'Monthly'], ['quarterly', 'Quarterly'], ['yearly', 'Yearly']]
- **Descrição:** Specify whether this entry is posted automatically on its accounting date, and any similar recurring invoices.
- **Valor Exemplo:** `'no'`

#### `auto_post_origin_id`
- **Label:** First recurring entry
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `auto_post_until`
- **Label:** Auto-post until
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** This recurring move will be posted up to and including this date.

#### `bank_partner_id`
- **Label:** Bank Partner
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`
- **Descrição:** Technical field to get the domain on the bank

#### `campaign_id`
- **Label:** Campaign
- **Tipo:** many2one → utm.campaign
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `utm.campaign`
- **Descrição:** This is a name that helps you keep track of your different campaign efforts, e.g. Fall_Drive, Christmas_Special
- **Valor Exemplo:** `False`

#### `commercial_partner_id`
- **Label:** Commercial Entity
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`

#### `company_currency_id`
- **Label:** Company Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.currency`

#### `company_id`
- **Label:** Company
- **Tipo:** many2one → res.company
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.company`
- **Valor Exemplo:** `[4, 'NACOM GOYA - CD']`

#### `count_asset`
- **Label:** Count Asset
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `country_code`
- **Label:** Country Code
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The ISO country code in two chars. 
You can use this field for quick search.

#### `create_date`
- **Label:** Created on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `create_uid`
- **Label:** Created by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `currency_id`
- **Label:** Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Relacionamento:** `res.currency`

#### `date`
- **Label:** Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Valor Exemplo:** `'2025-11-28'`

#### `deferred_entry_type`
- **Label:** Deferred Entry Type
- **Tipo:** selection [expense=Deferred Expense, revenue=Deferred Revenue]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['expense', 'Deferred Expense'], ['revenue', 'Deferred Revenue']]

#### `deferred_move_ids`
- **Label:** Deferred Entries
- **Tipo:** many2many → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** The deferred entries created by this invoice

#### `deferred_original_move_ids`
- **Label:** Original Invoices
- **Tipo:** many2many → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** The original invoices that created the deferred entries

#### `delivery_date`
- **Label:** Delivery Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `depreciation_value`
- **Label:** Depreciation
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `dfe_id`
- **Label:** Documento
- **Tipo:** many2one → l10n_br_ciel_it_account.dfe
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.dfe`

#### `direction_sign`
- **Label:** Direction Sign
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Multiplicator depending on the document type, to convert a price into a balance

#### `display_inactive_currency_warning`
- **Label:** Display Inactive Currency Warning
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `display_name`
- **Label:** Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `display_qr_code`
- **Label:** Display QR-code
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `draft_asset_exists`
- **Label:** Draft Asset Exists
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `duplicated_ref_ids`
- **Label:** Duplicated Ref
- **Tipo:** many2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `edi_blocking_level`
- **Label:** Edi Blocking Level
- **Tipo:** selection [info=Info, warning=Warning, error=Error]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['info', 'Info'], ['warning', 'Warning'], ['error', 'Error']]

#### `edi_document_ids`
- **Label:** Edi Document
- **Tipo:** one2many → account.edi.document
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.edi.document`

#### `edi_error_count`
- **Label:** Edi Error Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** How many EDIs are in error for this move?

#### `edi_error_message`
- **Label:** Edi Error Message
- **Tipo:** html
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_show_abandon_cancel_button`
- **Label:** Edi Show Abandon Cancel Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_show_cancel_button`
- **Label:** Edi Show Cancel Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_show_force_cancel_button`
- **Label:** Edi Show Force Cancel Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_state`
- **Label:** Electronic invoicing
- **Tipo:** selection [to_send=To Send, sent=Sent, to_cancel=To Cancel, cancelled=Cancelled]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['to_send', 'To Send'], ['sent', 'Sent'], ['to_cancel', 'To Cancel'], ['cancelled', 'Cancelled']]
- **Descrição:** The aggregated state of all the EDIs with web-service of this move

#### `edi_web_services_to_process`
- **Label:** Edi Web Services To Process
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_attachment_id`
- **Label:** Extract Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `extract_can_show_banners`
- **Label:** Can show the ocr banners
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_can_show_send_button`
- **Label:** Can show the ocr send button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_detected_layout`
- **Label:** Extract Detected Layout Id
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_document_uuid`
- **Label:** ID of the request to IAP-OCR
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_error_message`
- **Label:** Error message
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_partner_name`
- **Label:** Extract Detected Partner Name
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_state`
- **Label:** Extract state
- **Tipo:** selection [no_extract_requested=No extract requested, not_enough_credit=Not enough credits, error_status=An error occurred, waiting_extraction=Waiting extraction, extract_not_ready=waiting extraction, but it is not ready... (+3)]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['no_extract_requested', 'No extract requested'], ['not_enough_credit', 'Not enough credits'], ['error_status', 'An error occurred'], ['waiting_extraction', 'Waiting extraction'], ['extract_not_ready', 'waiting extraction, but it is not ready'], ['waiting_validation', 'Waiting validation'], ['to_validate', 'To validate'], ['done', 'Completed flow']]

#### `extract_state_processed`
- **Label:** Extract State Processed
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_status`
- **Label:** Extract status
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `extract_word_ids`
- **Label:** Extract Word
- **Tipo:** one2many → account.invoice_extract.words
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.invoice_extract.words`

#### `fiscal_position_id`
- **Label:** Fiscal Position
- **Tipo:** many2one → account.fiscal.position
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.fiscal.position`
- **Descrição:** Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. The default value comes from the customer.

#### `force_release_to_pay`
- **Label:** Force Status
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Indicates whether the 'Should Be Paid' status is defined automatically or manually.

#### `has_message`
- **Label:** Has Message
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `True`

#### `has_reconciled_entries`
- **Label:** Has Reconciled Entries
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `hide_post_button`
- **Label:** Hide Post Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `highest_name`
- **Label:** Highest Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `id`
- **Label:** ID
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `416177`

#### `inalterable_hash`
- **Label:** Inalterability Hash
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `incoterm_location`
- **Label:** Incoterm Location
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_cash_rounding_id`
- **Label:** Cash Rounding Method
- **Tipo:** many2one → account.cash.rounding
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.cash.rounding`
- **Descrição:** Defines the smallest coinage of the currency that can be used to pay by cash.

#### `invoice_date`
- **Label:** Invoice/Bill Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_date_due`
- **Label:** Due Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_filter_type_domain`
- **Label:** Invoice Filter Type Domain
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_has_outstanding`
- **Label:** Invoice Has Outstanding
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_incoterm_id`
- **Label:** Tipo de Frete
- **Tipo:** many2one → account.incoterms
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.incoterms`
- **Descrição:** International Commercial Terms are a series of predefined commercial terms used in international transactions.

#### `invoice_line_ids`
- **Label:** Invoice lines
- **Tipo:** one2many → account.move.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`

#### `invoice_origin`
- **Label:** Origin
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The document(s) that generated the invoice.

#### `invoice_outstanding_credits_debits_widget`
- **Label:** Invoice Outstanding Credits Debits Widget
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_partner_display_name`
- **Label:** Invoice Partner Display Name
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_payment_term_id`
- **Label:** Payment Terms
- **Tipo:** many2one → account.payment.term
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment.term`

#### `invoice_payments_widget`
- **Label:** Invoice Payments Widget
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_pdf_report_file`
- **Label:** PDF File
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_pdf_report_id`
- **Label:** PDF Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `invoice_source_email`
- **Label:** Source Email
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_user_id`
- **Label:** Salesperson
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.users`

#### `invoice_vendor_bill_id`
- **Label:** Vendor Bill
- **Tipo:** many2one → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** Auto-complete from a past bill.

#### `is_being_sent`
- **Label:** Is Being Sent
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Is the move being sent asynchronously

#### `is_encerramento`
- **Label:** Lançamento de Encerramento
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Indica se o lançamento é de encerramento do exercício.

#### `is_in_extractable_state`
- **Label:** Is In Extractable State
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `is_move_sent`
- **Label:** Is Move Sent
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** It indicates that the invoice/payment has been sent or the PDF has been generated.

#### `is_storno`
- **Label:** Is Storno
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `journal_id`
- **Label:** Journal
- **Tipo:** many2one → account.journal
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Relacionamento:** `account.journal`
- **Valor Exemplo:** `[826, 'VENDA DE PRODUÇÃO']`

#### `l10n_br_calcular_imposto`
- **Label:** Calcular Impostos
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_carrier_id`
- **Label:** Carrier
- **Tipo:** many2one → delivery.carrier
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `delivery.carrier`

#### `l10n_br_cbs_valor`
- **Label:** Total do CBS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cfop_id`
- **Label:** CFOP
- **Tipo:** many2one → l10n_br_ciel_it_account.cfop
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.cfop`

#### `l10n_br_chave_nf`
- **Label:** Chave da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cnpj`
- **Label:** CNPJ
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_ret_base`
- **Label:** Base do Cofins Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_ret_valor`
- **Label:** Valor do Cofins Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_valor`
- **Label:** Total do Cofins
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_valor_isento`
- **Label:** Total do Cofins (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_valor_outros`
- **Label:** Total do Cofins (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_compra_indcom`
- **Label:** Destinação de Uso
- **Tipo:** selection [uso=Uso e Consumo, uso-prestacao=Uso na Prestação de Serviço, ind=Industrialização, com=Comercialização, ativo=Ativo... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['uso', 'Uso e Consumo'], ['uso-prestacao', 'Uso na Prestação de Serviço'], ['ind', 'Industrialização'], ['com', 'Comercialização'], ['ativo', 'Ativo'], ['garantia', 'Garantia'], ['out', 'Outros']]

#### `l10n_br_correcao`
- **Label:** Correção
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_ret_base`
- **Label:** Base do CSLL Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_csll_ret_valor`
- **Label:** Valor do CSLL Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_csll_valor`
- **Label:** Total do CSLL
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cstat_nf`
- **Label:** Status da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_data_nfse_substituida`
- **Label:** Data de Emissão da NFS-e Substituida
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_data_saida`
- **Label:** Data/Hora de Saída
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_dctf_imposto_codigo`
- **Label:** Código do Imposto DCTF
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_desc_valor`
- **Label:** Total do Desconto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_descricao_servico`
- **Label:** Descrição do Serviço
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_descricao_servico_show`
- **Label:** Mostrar Descrição do Serviço
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_despesas_acessorias`
- **Label:** Total da Despesas Acessórias
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_especie`
- **Label:** Espécie
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_fcp_dest_valor`
- **Label:** Total do Fundo de Combate a Pobreza
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_fcp_st_ant_valor`
- **Label:** Total do Fundo de Combate a Pobreza Retido Anteriormente por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_fcp_st_valor`
- **Label:** Total do Fundo de Combate a Pobreza Retido por ST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_frete`
- **Label:** Total do Frete
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_gnre_disponivel`
- **Label:** GNRE Disponível
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_gnre_numero_recibo`
- **Label:** GNRE - Número do Recibo
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_gnre_ok`
- **Label:** GNRE OK
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_handle_nfce`
- **Label:** Handle da Nota Fiscal Eletrônica ao Consumidor
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_handle_nfse`
- **Label:** Handle da Nota Fiscal de Serviço
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_mun_valor`
- **Label:** Total do IBS Município
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibs_uf_valor`
- **Label:** Total do IBS UF
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibs_valor`
- **Label:** Total do IBS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibscbs_base`
- **Label:** Total da Base de Cálculo do IBS/CBS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_base`
- **Label:** Total da Base de Cálculo do ICMS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_dest_valor`
- **Label:** Total do ICMS UF Destino
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_remet_valor`
- **Label:** Total do ICMS UF Remetente
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor`
- **Label:** Total do ICMS (Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_credito_presumido`
- **Label:** Total do ICMS (Crédito Presumido)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_desonerado`
- **Label:** Total do ICMS (Desonerado)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_efetivo`
- **Label:** Total do ICMS (Efetivo)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_isento`
- **Label:** Total do ICMS (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_outros`
- **Label:** Total do ICMS (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_base`
- **Label:** Total da Base de Cálculo do ICMSST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_retido_valor`
- **Label:** Total do ICMSST Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_retido_valor_outros`
- **Label:** Total do ICMSST Retido (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_substituto_valor`
- **Label:** Total do ICMSST Substituto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_substituto_valor_outros`
- **Label:** Total do ICMSST Substituto (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_valor`
- **Label:** Total do ICMSST
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_valor_outros`
- **Label:** Total do ICMSST (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_valor_proprio`
- **Label:** Total do ICMSST (Próprio)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ii_valor`
- **Label:** Total do II
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ii_valor_aduaneira`
- **Label:** Total do II Aduaneira
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ii_valor_afrmm`
- **Label:** Total do II AFRMM
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_imposto_auto`
- **Label:** Calcular Impostos Automaticamente
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_indicador_presenca`
- **Label:** Indicador Presença
- **Tipo:** selection [0=0 - Não se aplica, 1=1 - Operação presencial, 2=2 - Operação não presencial, pela internet, 3=3 - Operação não presencial, teleatendimento, 4=4 - NFC-e em operação com entrega a domicílio... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['0', '0 - Não se aplica'], ['1', '1 - Operação presencial'], ['2', '2 - Operação não presencial, pela internet'], ['3', '3 - Operação não presencial, teleatendimento'], ['4', '4 - NFC-e em operação com entrega a domicílio'], ['5', '5 - Operação presencial, fora do estabelecimento'], ['9', '9 - Operação não presencial, outros']]

#### `l10n_br_informacao_complementar`
- **Label:** Informação Complementar
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_informacao_fiscal`
- **Label:** Informação Fiscal
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_inss_ret_base`
- **Label:** Base do INSS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_inss_ret_valor`
- **Label:** Valor do INSS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iof_valor`
- **Label:** Total do IOF
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ipi_valor`
- **Label:** Total do IPI
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ipi_valor_isento`
- **Label:** Total do IPI (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ipi_valor_outros`
- **Label:** Total do IPI (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_irpj_ret_base`
- **Label:** Base do IRPJ Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_irpj_ret_valor`
- **Label:** Valor do IRPJ Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_irpj_valor`
- **Label:** Total do IRPJ
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_is_valor`
- **Label:** Total do IS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iss_municipio_id`
- **Label:** Município de Incidência do ISS
- **Tipo:** many2one → l10n_br_ciel_it_account.res.municipio
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.res.municipio`

#### `l10n_br_iss_ret_base`
- **Label:** Base do ISS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iss_ret_valor`
- **Label:** Valor do ISS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iss_valor`
- **Label:** Total do ISS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_item_pedido_compra`
- **Label:** Item Pedido de Compra do Cliente
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_local_despacho`
- **Label:** Local de despacho
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_local_embarque`
- **Label:** Local de embarque
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_marca`
- **Label:** Marca
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_motivo`
- **Label:** Motivo Cancelamento
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_municipio_fim_id`
- **Label:** Município de Destino
- **Tipo:** many2one → l10n_br_ciel_it_account.res.municipio
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.res.municipio`

#### `l10n_br_municipio_inicio_id`
- **Label:** Município de Origem
- **Tipo:** many2one → l10n_br_ciel_it_account.res.municipio
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.res.municipio`

#### `l10n_br_nfe_emails`
- **Label:** Email XML NF-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_nfse_substituta`
- **Label:** NFS-e Substituta?
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numeracao_volume`
- **Label:** Númeração Volume
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_numero_nf`
- **Label:** Número da Nota Fiscal de Mercadoria
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nfce`
- **Label:** Número da Nota Fiscal Eletrônica ao Consumidor
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nfse`
- **Label:** Número da Nota Fiscal de Serviço
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nfse_substituida`
- **Label:** Número da NFS-e Substituida
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nota_fiscal`
- **Label:** Número da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_numero_rps`
- **Label:** Número RPS
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_rps_substituido`
- **Label:** Número RPS Substituido
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_operacao_consumidor`
- **Label:** Operação Consumidor Final
- **Tipo:** selection [0=0 - Normal, 1=1 - Consumidor Final]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['0', '0 - Normal'], ['1', '1 - Consumidor Final']]

#### `l10n_br_operacao_id`
- **Label:** Operação
- **Tipo:** many2one → l10n_br_ciel_it_account.operacao
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.operacao`

#### `l10n_br_pdf_aut_gnre`
- **Label:** GNRE
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_aut_gnre_fname`
- **Label:** Arquivo GNRE
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_aut_nfe`
- **Label:** DANFE NF-e
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_aut_nfe_fname`
- **Label:** Arquivo DANFE NF-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_can_nfe`
- **Label:** DANFE NF-e Cancelamento
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_can_nfe_fname`
- **Label:** Arquivo DANFE NF-e Cancelamento
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_cce_nfe`
- **Label:** DANFE CC-e
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_cce_nfe_fname`
- **Label:** Arquivo DANFE CC-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pedido_compra`
- **Label:** Pedido de Compra do Cliente
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_peso_bruto`
- **Label:** Peso Bruto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_peso_liquido`
- **Label:** Peso Líquido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_ret_base`
- **Label:** Base do PIS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_ret_valor`
- **Label:** Valor do PIS Retido
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_valor`
- **Label:** Total do PIS
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_valor_isento`
- **Label:** Total do PIS (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_valor_outros`
- **Label:** Total do PIS (Outros)
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_prod_valor`
- **Label:** Total dos Produtos
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_rateio_frete_auto`
- **Label:** Rateio Frete Automatico
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_seguro`
- **Label:** Total do Seguro
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_sequencia_evento`
- **Label:** Sequencia Evento NF-e
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_serie_nf`
- **Label:** Série da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_serie_nf_substituido`
- **Label:** Série NFS-e Substituido
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_show_nfe_btn`
- **Label:** Mostrar botão NF-e
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_situacao_nf`
- **Label:** Situação NF-e
- **Tipo:** selection [rascunho=Rascunho, autorizado=Autorizado, excecao_autorizado=Exceção, cce=Carta de Correção, excecao_cce=Exceção... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['rascunho', 'Rascunho'], ['autorizado', 'Autorizado'], ['excecao_autorizado', 'Exceção'], ['cce', 'Carta de Correção'], ['excecao_cce', 'Exceção'], ['cancelado', 'Cancelado'], ['excecao_cancelado', 'Exceção']]

#### `l10n_br_tipo_documento`
- **Label:** Tipo Documento Fiscal
- **Tipo:** selection [NFS=Nota Fiscal de Serviços Instituída por Municípios, NFSE=Nota Fiscal de Serviços Eletrônica - NFS-e, NDS=Nota de Débito de Serviços, FAT=Fatura, ND=Nota de Débito... (+32)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['NFS', 'Nota Fiscal de Serviços Instituída por Municípios'], ['NFSE', 'Nota Fiscal de Serviços Eletrônica - NFS-e'], ['NDS', 'Nota de Débito de Serviços'], ['FAT', 'Fatura'], ['ND', 'Nota de Débito'], ['01', 'Nota Fiscal'], ['1B', 'Nota Fiscal Avulsa'], ['02', 'Nota Fiscal de Venda a Consumidor'], ['2D', 'Cupom Fiscal'], ['2E', 'Cupom Fiscal Bilhete de Passagem'], ['04', 'Nota Fiscal de Produtor'], ['06', 'Nota Fiscal/Conta de Energia Elétrica'], ['07', 'Nota Fiscal de Serviço de Transporte'], ['08', 'Conhecimento de Transporte Rodoviário de Cargas'], ['8B', 'Conhecimento de Transporte de Cargas Avulso'], ['09', 'Conhecimento de Transporte Aquaviário de Cargas'], ['10', 'Conhecimento Aéreo'], ['11', 'Conhecimento de Transporte Ferroviário de Cargas'], ['13', 'Bilhete de Passagem Rodoviário'], ['14', 'Bilhete de Passagem Aquaviário'], ['15', 'Bilhete de Passagem e Nota de Bagagem'], ['16', 'Bilhete de Passagem Ferroviário'], ['18', 'Resumo de Movimento Diário'], ['21', 'Nota Fiscal de Serviço de Comunicação'], ['22', 'Nota Fiscal de Serviço de Telecomunicação'], ['26', 'Conhecimento de Transporte Multimodal de Cargas'], ['27', 'Nota Fiscal De Transporte Ferroviário De Carga'], ['28', 'Nota Fiscal/Conta de Fornecimento de Gás Canalizado'], ['29', 'Nota Fiscal/Conta de Fornecimento de Água Canalizada'], ['55', 'Nota Fiscal Eletrônica (NF-e)'], ['57', 'Conhecimento de Transporte Eletrônico (CT-e)'], ['59', 'Cupom Fiscal Eletrônico (CF-e-SAT)'], ['60', 'Cupom Fiscal Eletrônico (CF-e-ECF)'], ['63', 'Bilhete de Passagem Eletrônico (BP-e)'], ['65', 'Nota Fiscal Eletrônica ao Consumidor Final (NFC-e)'], ['66', 'Nota Fiscal de Energia Elétrica Eletrônica - NF3e'], ['67', 'Conhecimento de Transporte Eletrônico (CT-e OS)']]

#### `l10n_br_tipo_imposto`
- **Label:** Tipo Imposto
- **Tipo:** selection [cofins=COFINS, csll=CSLL, icms=ICMS, ii=II, inss=INSS... (+7)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['cofins', 'COFINS'], ['csll', 'CSLL'], ['icms', 'ICMS'], ['ii', 'II'], ['inss', 'INSS'], ['ipi', 'IPI'], ['irrf', 'IRRF'], ['iss', 'ISS'], ['pis', 'PIS'], ['simples', 'Simples Nacional'], ['icmsst', 'ICMS ST'], ['fgts', 'FGTS']]

#### `l10n_br_tipo_pedido`
- **Label:** Tipo de Pedido (saída)
- **Tipo:** selection [baixa-estoque=Saída: Baixa de Estoque, complemento-valor=Saída: Complemento de Preço, dev-comodato=Saída: Devolução de Comodato, compra=Saída: Devolução de Compra, dev-conserto=Saída: Devolução de Conserto... (+42)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['baixa-estoque', 'Saída: Baixa de Estoque'], ['complemento-valor', 'Saída: Complemento de Preço'], ['dev-comodato', 'Saída: Devolução de Comodato'], ['compra', 'Saída: Devolução de Compra'], ['dev-conserto', 'Saída: Devolução de Conserto'], ['dev-consignacao', 'Saída: Devolução de Consignação'], ['dev-demonstracao', 'Saída: Devolução de Demonstração'], ['dev-industrializacao', 'Saída: Devolução de Industrialização'], ['dev-locacao', 'Saída: Devolução de Locação'], ['dev-mostruario', 'Saída: Devolução de Mostruário'], ['dev-teste', 'Saída: Devolução de Teste'], ['dev-vasilhame', 'Saída: Devolução de Vasilhame'], ['venda-locacao', 'Saída: Locação'], ['outro', 'Saída: Outros'], ['perda', 'Saída: Perda'], ['mostruario', 'Saída: Remessa de Mostruário'], ['vasilhame', 'Saída: Remessa de Vasilhame'], ['rem-venda-futura', 'Saída: Remessa de Venda p/ Entrega Futura'], ['ativo-fora', 'Saída: Remessa de bem do ativo imobilizado p/ uso Fora do Estabelecimento'], ['comodato', 'Saída: Remessa em Comodato'], ['consignacao', 'Saída: Remessa em Consignação'], ['garantia', 'Saída: Remessa em Garantia'], ['amostra', 'Saída: Remessa p/ Amostra Grátis'], ['bonificacao', 'Saída: Remessa p/ Bonificação'], ['conserto', 'Saída: Remessa p/ Conserto'], ['demonstracao', 'Saída: Remessa p/ Demonstração'], ['deposito', 'Saída: Remessa p/ Depósito'], ['exportacao', 'Saída: Remessa p/ Exportação'], ['feira', 'Saída: Remessa p/ Feira'], ['fora', 'Saída: Remessa p/ Fora do Estabelecimento'], ['industrializacao', 'Saída: Remessa p/ Industrialização'], ['rem-obra', 'Saída: Remessa p/ Obra'], ['teste', 'Saída: Remessa p/ Teste'], ['troca', 'Saída: Remessa p/ Troca'], ['uso-prestacao', 'Saída: Remessa p/ Uso na Prestação de Serviço'], ['locacao', 'Saída: Remessa para Locação'], ['rem-conta-ordem', 'Saída: Remessa por Conta e Ordem'], ['transf-filial', 'Saída: Transferencia entre Filiais'], ['venda', 'Saída: Venda'], ['venda-nfce', 'Saída: Venda Cupom Fiscal'], ['venda-armazem', 'Saída: Venda de Armazém Externo'], ['venda-industrializacao', 'Saída: Venda de Industrialização'], ['servico', 'Saída: Venda de Serviço'], ['venda-consignacao', 'Saída: Venda em Consignação'], ['venda_futura', 'Saída: Venda p/ Entrega Futura'], ['venda-conta-ordem', 'Saída: Venda por Conta e Ordem'], ['venda-conta-ordem-vendedor', 'Saída: Venda por Conta e Ordem por Vendedor']]

#### `l10n_br_tipo_pedido_entrada`
- **Label:** Tipo de Pedido (entrada)
- **Tipo:** selection [ent-amostra=Entrada: Amostra Grátis, ent-bonificacao=Entrada: Bonificação, ent-comodato=Entrada: Comodato, comp-importacao=Entrada: Complementar de Importação, compra=Entrada: Compra... (+33)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['ent-amostra', 'Entrada: Amostra Grátis'], ['ent-bonificacao', 'Entrada: Bonificação'], ['ent-comodato', 'Entrada: Comodato'], ['comp-importacao', 'Entrada: Complementar de Importação'], ['compra', 'Entrada: Compra'], ['compra-venda-ordem', 'Entrada: Compra Venda à Ordem'], ['compra-ent-futura', 'Entrada: Compra p/ Entrega Futura'], ['ent-conserto', 'Entrada: Conserto'], ['credito-imposto', 'Entrada: Crédito de Imposto'], ['ent-demonstracao', 'Entrada: Demonstração'], ['devolucao', 'Entrada: Devolução Emissão Própria'], ['devolucao_compra', 'Entrada: Devolução de Venda'], ['importacao', 'Entrada: Importação'], ['locacao', 'Entrada: Locação'], ['ent-mostruario', 'Entrada: Mostruário'], ['outro', 'Entrada: Outros'], ['retorno', 'Entrada: Outros Retorno'], ['compra-rec-venda-ordem', 'Entrada: Recebimento de Compra Venda à Ordem'], ['compra-rec-ent-futura', 'Entrada: Recebimento de Compra p/ Entrega Futura'], ['rem-industrializacao', 'Entrada: Remessa p/ Industrialização'], ['rem-conta-ordem', 'Entrada: Remessa por Conta e Ordem'], ['comodato', 'Entrada: Retorno de Comodato'], ['conserto', 'Entrada: Retorno de Conserto'], ['consignacao', 'Entrada: Retorno de Consignação'], ['demonstracao', 'Entrada: Retorno de Demonstração'], ['deposito', 'Entrada: Retorno de Depósito'], ['feira', 'Entrada: Retorno de Feira'], ['industrializacao', 'Entrada: Retorno de Industrialização'], ['ret-locacao', 'Entrada: Retorno de Locação'], ['mostruario', 'Entrada: Retorno de Mostruário'], ['troca', 'Entrada: Retorno de Troca'], ['vasilhame', 'Entrada: Retorno de Vasilhame'], ['ativo-fora', 'Entrada: Retorno de bem do ativo imobilizado p/ uso Fora do Estabelecimento'], ['servico', 'Entrada: Serviço'], ['serv-industrializacao', 'Entrada: Serviço de Industrialização'], ['transf-filial', 'Entrada: Transferencia entre Filiais'], ['importacao-transporte', 'Entrada: Transporte de Importação'], ['ent-vasilhame', 'Entrada: Vasilhame']]

#### `l10n_br_total_nfe`
- **Label:** Total da Nota Fiscal
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_total_tributos`
- **Label:** Total dos Tributos
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_uf_saida_pais`
- **Label:** Sigla UF de Saída
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_veiculo_placa`
- **Label:** Placa
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_veiculo_rntc`
- **Label:** RNTC
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_veiculo_uf`
- **Label:** UF da Placa
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_volumes`
- **Label:** Volumes
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xml_aut_nfe`
- **Label:** XML NF-e
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_xml_aut_nfe_fname`
- **Label:** Arquivo XML NF-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xml_can_nfe`
- **Label:** XML NF-e Cancelamento
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_xml_can_nfe_fname`
- **Label:** Arquivo XML NF-e Cancelamento
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xml_cce_nfe`
- **Label:** XML CC-e
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_xml_cce_nfe_fname`
- **Label:** Arquivo XML CC-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xmotivo_nf`
- **Label:** Situação da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `landed_costs_ids`
- **Label:** Landed Costs
- **Tipo:** one2many → stock.landed.cost
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.landed.cost`

#### `landed_costs_visible`
- **Label:** Landed Costs Visible
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `laudos`
- **Label:** Laudos
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `laudos_filename`
- **Label:** Nome do arquivo de laudos
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `line_ids`
- **Label:** Journal Items
- **Tipo:** one2many → account.move.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`
- **Valor Exemplo:** `[46 itens: [2703759, 2703760, 2703761]...]`

#### `made_sequence_hole`
- **Label:** Made Sequence Hole
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `medium_id`
- **Label:** Medium
- **Tipo:** many2one → utm.medium
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `utm.medium`
- **Descrição:** This is the method of delivery, e.g. Postcard, Email, or Banner Ad
- **Valor Exemplo:** `False`

#### `message_attachment_count`
- **Label:** Attachment Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `2`

#### `message_follower_ids`
- **Label:** Followers
- **Tipo:** one2many → mail.followers
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.followers`
- **Valor Exemplo:** `[2578338, '2578339']`

#### `message_has_error`
- **Label:** Message Delivery error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, some messages have a delivery error.
- **Valor Exemplo:** `False`

#### `message_has_error_counter`
- **Label:** Number of errors
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Number of messages with delivery error
- **Valor Exemplo:** `0`

#### `message_has_sms_error`
- **Label:** SMS Delivery error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, some messages have a delivery error.
- **Valor Exemplo:** `False`

#### `message_ids`
- **Label:** Messages
- **Tipo:** one2many → mail.message
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.message`
- **Valor Exemplo:** `[15 itens: [12420053, 12420051, 12420048]...]`

#### `message_is_follower`
- **Label:** Is Follower
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `message_main_attachment_id`
- **Label:** Main Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `ir.attachment`
- **Valor Exemplo:** `[265234, '35251161724241000330550010001423231004161777-nfe.p...']`

#### `message_needaction`
- **Label:** Action Needed
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, new messages require your attention.
- **Valor Exemplo:** `False`

#### `message_needaction_counter`
- **Label:** Number of Actions
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Number of messages requiring action
- **Valor Exemplo:** `0`

#### `message_partner_ids`
- **Label:** Followers (Partners)
- **Tipo:** many2many → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`
- **Valor Exemplo:** `[203957, '206233']`

#### `move_type`
- **Label:** Type
- **Tipo:** selection [entry=Journal Entry, out_invoice=Customer Invoice, out_refund=Customer Credit Note, in_invoice=Vendor Bill, in_refund=Vendor Credit Note... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Sim
- **Opções:** [['entry', 'Journal Entry'], ['out_invoice', 'Customer Invoice'], ['out_refund', 'Customer Credit Note'], ['in_invoice', 'Vendor Bill'], ['in_refund', 'Vendor Credit Note'], ['out_receipt', 'Sales Receipt'], ['in_receipt', 'Purchase Receipt']]
- **Valor Exemplo:** `'out_invoice'`

#### `my_activity_date_deadline`
- **Label:** My Activity Deadline
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `name`
- **Label:** Number
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `'VND/2025/05453'`

#### `narration`
- **Label:** Terms and Conditions
- **Tipo:** html
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `need_cancel_request`
- **Label:** Need Cancel Request
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `needed_terms`
- **Label:** Needed Terms
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `needed_terms_dirty`
- **Label:** Needed Terms Dirty
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `parcelas_manual_id`
- **Label:** Parcelas Personalizada
- **Tipo:** many2one → l10n_br_ciel_it_account.payment.parcela.manual
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.payment.parcela.manual`

#### `partner_bank_id`
- **Label:** Recipient Bank
- **Tipo:** many2one → res.partner.bank
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner.bank`
- **Descrição:** Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.

#### `partner_contact_id`
- **Label:** Contato
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`

#### `partner_credit`
- **Label:** Partner Credit
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `partner_credit_warning`
- **Label:** Partner Credit Warning
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `partner_id`
- **Label:** Partner
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`

#### `partner_invoice_id`
- **Label:** Endereço de Cobrança
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`

#### `partner_shipping_id`
- **Label:** Delivery Address
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`
- **Descrição:** The delivery address will be used in the computation of the fiscal position.

#### `payment_id`
- **Label:** Payment
- **Tipo:** many2one → account.payment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment`
- **Valor Exemplo:** `False`

#### `payment_ids`
- **Label:** Payments
- **Tipo:** one2many → account.payment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment`

#### `payment_line_ids`
- **Label:** Payment lines
- **Tipo:** many2many → account.move.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move.line`

#### `payment_provider_id`
- **Label:** Forma de Pagamento
- **Tipo:** many2one → payment.provider
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `payment.provider`

#### `payment_reference`
- **Label:** Payment Reference
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** The payment reference to set on journal items.

#### `payment_state`
- **Label:** Payment Status
- **Tipo:** selection [not_paid=Not Paid, in_payment=In Payment, paid=Paid, partial=Partially Paid, reversed=Reversed... (+1)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['not_paid', 'Not Paid'], ['in_payment', 'In Payment'], ['paid', 'Paid'], ['partial', 'Partially Paid'], ['reversed', 'Reversed'], ['invoicing_legacy', 'Invoicing App Legacy']]

#### `payment_state_before_switch`
- **Label:** Payment State Before Switch
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `payment_term_details`
- **Label:** Payment Term Details
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `picking_ids`
- **Label:** Picking References
- **Tipo:** many2many → stock.picking
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.picking`

#### `picking_ok`
- **Label:** Picking OK
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `posted_before`
- **Label:** Posted Before
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `purchase_id`
- **Label:** Purchase Order
- **Tipo:** many2one → purchase.order
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `purchase.order`
- **Descrição:** Auto-complete from a past purchase order.

#### `purchase_order_count`
- **Label:** Purchase Order Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `purchase_vendor_bill_id`
- **Label:** Auto-complete
- **Tipo:** many2one → purchase.bill.union
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `purchase.bill.union`
- **Descrição:** Auto-complete from a past bill / purchase order.

#### `qr_code_method`
- **Label:** Payment QR-code
- **Tipo:** selection
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Type of QR-code to be generated for the payment of this invoice, when printing it. If left blank, the first available and usable method will be used.

#### `quick_edit_mode`
- **Label:** Quick Edit Mode
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `quick_edit_total_amount`
- **Label:** Total (Tax inc.)
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Use this field to encode the total amount of the invoice.
Odoo will automatically create one invoice line with default values to match it.

#### `quick_encoding_vals`
- **Label:** Quick Encoding Vals
- **Tipo:** json
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `rating_ids`
- **Label:** Ratings
- **Tipo:** one2many → rating.rating
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `rating.rating`
- **Valor Exemplo:** `[]`

#### `ref`
- **Label:** Reference
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `''`

#### `referencia_ids`
- **Label:** NF-e referência
- **Tipo:** one2many → l10n_br_ciel_it_account.account.move.referencia
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.account.move.referencia`

#### `reinfs_2010_count`
- **Label:** REINF 2010 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2010_ids`
- **Label:** REINF 2010
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.2010
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.2010`

#### `reinfs_2020_count`
- **Label:** REINF 2020 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2020_ids`
- **Label:** REINF 2020
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.2020
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.2020`

#### `reinfs_2060_count`
- **Label:** REINF 2060 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2060_ids`
- **Label:** REINF 2060
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.2060
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.2060`

#### `reinfs_4010_count`
- **Label:** REINF 4010 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_4010_ids`
- **Label:** REINF 4010
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.4010
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.4010`

#### `reinfs_4020_count`
- **Label:** REINF 4020 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_4020_ids`
- **Label:** REINF 4020
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.4020
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.4020`

#### `reinfs_4080_count`
- **Label:** REINF 4080 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_4080_ids`
- **Label:** REINF 4080
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.4080
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.4080`

#### `release_to_pay`
- **Label:** Release To Pay
- **Tipo:** selection [yes=Yes, no=No, exception=Exception]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['yes', 'Yes'], ['no', 'No'], ['exception', 'Exception']]
- **Descrição:** This field can take the following values :
  * Yes: you should pay the bill, you have received the products
  * No, you should not pay the bill, you have not received the products
  * Exception, there is a difference between received and billed quantities
This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.

#### `release_to_pay_manual`
- **Label:** Should Be Paid
- **Tipo:** selection [yes=Yes, no=No, exception=Exception]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['yes', 'Yes'], ['no', 'No'], ['exception', 'Exception']]
- **Descrição:**   * Yes: you should pay the bill, you have received the products
  * No, you should not pay the bill, you have not received the products
  * Exception, there is a difference between received and billed quantities
This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.

#### `restrict_mode_hash_table`
- **Label:** Lock Posted Entries with Hash
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If ticked, the accounting entry or invoice receives a hash as soon as it is posted and cannot be modified anymore.

#### `reversal_move_id`
- **Label:** Reversal Move
- **Tipo:** one2many → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`

#### `reversed_entry_id`
- **Label:** Reversal of
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `sale_order_count`
- **Label:** Sale Order Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `secure_sequence_number`
- **Label:** Inalteralbility No Gap Sequence #
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `send_and_print_values`
- **Label:** Send And Print Values
- **Tipo:** json
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `sequence_number`
- **Label:** Sequence Number
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `5453`

#### `sequence_prefix`
- **Label:** Sequence Prefix
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'VND/2025/'`

#### `show_delivery_date`
- **Label:** Show Delivery Date
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_discount_details`
- **Label:** Show Discount Details
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_name_warning`
- **Label:** Show Name Warning
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `show_payment_term_details`
- **Label:** Show Payment Term Details
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_reset_to_draft_button`
- **Label:** Show Reset To Draft Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_update_fpos`
- **Label:** Has Fiscal Position Changed
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `simples_nacional`
- **Label:** Emitente Simples Nacional
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `source_id`
- **Label:** Source
- **Tipo:** many2one → utm.source
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `utm.source`
- **Descrição:** This is the source of the link, e.g. Search Engine, another domain, or name of email list
- **Valor Exemplo:** `False`

#### `state`
- **Label:** Status
- **Tipo:** selection [draft=Draft, posted=Posted, cancel=Cancelled]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Sim
- **Opções:** [['draft', 'Draft'], ['posted', 'Posted'], ['cancel', 'Cancelled']]
- **Valor Exemplo:** `'posted'`

#### `statement_id`
- **Label:** Statement
- **Tipo:** many2one → account.bank.statement
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.bank.statement`
- **Valor Exemplo:** `False`

#### `statement_line_id`
- **Label:** Statement Line
- **Tipo:** many2one → account.bank.statement.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.bank.statement.line`
- **Valor Exemplo:** `False`

#### `statement_line_ids`
- **Label:** Statements
- **Tipo:** one2many → account.bank.statement.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.bank.statement.line`

#### `stock_move_id`
- **Label:** Stock Move
- **Tipo:** many2one → stock.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.move`

#### `stock_valuation_layer_ids`
- **Label:** Stock Valuation Layer
- **Tipo:** one2many → stock.valuation.layer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.valuation.layer`

#### `string_to_hash`
- **Label:** String To Hash
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `suitable_journal_ids`
- **Label:** Suitable Journal
- **Tipo:** many2many → account.journal
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.journal`

#### `suspense_statement_line_id`
- **Label:** Request document from a bank statement line
- **Tipo:** many2one → account.bank.statement.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.bank.statement.line`

#### `tax_calculation_rounding_method`
- **Label:** Tax calculation rounding method
- **Tipo:** selection [round_per_line=Round per Line, round_globally=Round Globally]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['round_per_line', 'Round per Line'], ['round_globally', 'Round Globally']]

#### `tax_cash_basis_created_move_ids`
- **Label:** Cash Basis Entries
- **Tipo:** one2many → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** The cash basis entries created from the taxes on this entry, when reconciling its lines.
- **Valor Exemplo:** `[]`

#### `tax_cash_basis_origin_move_id`
- **Label:** Cash Basis Origin
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`
- **Descrição:** The journal entry from which this tax cash basis journal entry has been created.
- **Valor Exemplo:** `False`

#### `tax_cash_basis_rec_id`
- **Label:** Tax Cash Basis Entry of
- **Tipo:** many2one → account.partial.reconcile
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.partial.reconcile`
- **Valor Exemplo:** `False`

#### `tax_closing_alert`
- **Label:** Tax Closing Alert
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_closing_end_date`
- **Label:** Tax Closing End Date
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `tax_closing_show_multi_closing_warning`
- **Label:** Tax Closing Show Multi Closing Warning
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_country_code`
- **Label:** Tax Country Code
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_country_id`
- **Label:** Tax Country
- **Tipo:** many2one → res.country
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.country`

#### `tax_lock_date_message`
- **Label:** Tax Lock Date Message
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_report_control_error`
- **Label:** Tax Report Control Error
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `tax_totals`
- **Label:** Invoice Totals
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Edit Tax amounts if you encounter rounding issues.

#### `team_id`
- **Label:** Sales Team
- **Tipo:** many2one → crm.team
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `crm.team`

#### `timesheet_count`
- **Label:** Number of timesheets
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `timesheet_encode_uom_id`
- **Label:** Timesheet Encoding Unit
- **Tipo:** many2one → uom.uom
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `uom.uom`

#### `timesheet_ids`
- **Label:** Timesheets
- **Tipo:** one2many → account.analytic.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.analytic.line`

#### `timesheet_total_duration`
- **Label:** Timesheet Total Duration
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Total recorded duration, expressed in the encoding UoM, and rounded to the unit

#### `to_check`
- **Label:** To Check
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** If this checkbox is ticked, it means that the user was not sure of all the related information at the time of the creation of the move and that the move needs to be checked again.

#### `transaction_ids`
- **Label:** Transactions
- **Tipo:** many2many → payment.transaction
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `payment.transaction`

#### `transfer_model_id`
- **Label:** Originating Model
- **Tipo:** many2one → account.transfer.model
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.transfer.model`

#### `type_name`
- **Label:** Type Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `ubl_cii_xml_file`
- **Label:** UBL/CII File
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `ubl_cii_xml_id`
- **Label:** Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `user_id`
- **Label:** User
- **Tipo:** many2one → res.users
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `usuario_id`
- **Label:** Usuário
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`

#### `website_message_ids`
- **Label:** Website Messages
- **Tipo:** one2many → mail.message
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.message`
- **Descrição:** Website communication history
- **Valor Exemplo:** `[]`

#### `write_date`
- **Label:** Last Updated on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `write_uid`
- **Label:** Last Updated by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `x_studio_observao_interna`
- **Label:** Observação Interna
- **Tipo:** text
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não



================================================================================
## account.payment
**Descrição:** Pagamentos e recebimentos registrados no sistema
================================================================================

**Total de campos:** 437

**Exemplo encontrado:** ID = 17734

### CAMPOS:

| # | Campo | Tipo | Label | Armazenado | Obrigatório | Valor Exemplo |
|---|-------|------|-------|------------|-------------|---------------|
| 1 | `access_token` | char | Security Token | ❌ | ❌ | '-' |
| 2 | `access_url` | char | Portal Access URL | ❌ | ❌ | '-' |
| 3 | `access_warning` | text | Access warning | ❌ | ❌ | '-' |
| 4 | `activity_calendar_event_id` | many2one → calendar.event | Next Activity Calendar Event | ❌ | ❌ | False |
| 5 | `activity_date_deadline` | date | Next Activity Deadline | ❌ | ❌ | False |
| 6 | `activity_exception_decoration` | selection [warning=Alert, danger=Error] | Activity Exception Decoration | ❌ | ❌ | False |
| 7 | `activity_exception_icon` | char | Icon | ❌ | ❌ | False |
| 8 | `activity_ids` | one2many → mail.activity | Activities | ✅ | ❌ | [] |
| 9 | `activity_state` | selection [overdue=Overdue, today=Today, planned=Planned] | Activity State | ❌ | ❌ | False |
| 10 | `activity_summary` | char | Next Activity Summary | ❌ | ❌ | False |
| 11 | `activity_type_icon` | char | Activity Type Icon | ❌ | ❌ | False |
| 12 | `activity_type_id` | many2one → mail.activity.type | Next Activity Type | ❌ | ❌ | False |
| 13 | `activity_user_id` | many2one → res.users | Responsible User | ❌ | ❌ | False |
| 14 | `adiantamento_id` | boolean | Adiantamento | ❌ | ❌ | '-' |
| 15 | `agendamento_id` | selection [sim=Sim, nao=Não] | Agendamento | ❌ | ❌ | '-' |
| 16 | `always_tax_exigible` | boolean | Always Tax Exigible | ❌ | ❌ | '-' |
| 17 | `amount` | monetary | Amount | ✅ | ❌ | 107.25 |
| 18 | `amount_available_for_refund` | monetary | Amount Available For Refund | ❌ | ❌ | '-' |
| 19 | `amount_company_currency_signed` | monetary | Amount Company Currency Signed | ✅ | ❌ | '-' |
| 20 | `amount_paid` | monetary | Amount paid | ❌ | ❌ | '-' |
| 21 | `amount_residual` | monetary | Amount Due | ❌ | ❌ | '-' |
| 22 | `amount_residual_signed` | monetary | Amount Due Signed | ❌ | ❌ | '-' |
| 23 | `amount_signed` | monetary | Amount Signed | ❌ | ❌ | '-' |
| 24 | `amount_tax` | monetary | Tax | ❌ | ❌ | '-' |
| 25 | `amount_tax_signed` | monetary | Tax Signed | ❌ | ❌ | '-' |
| 26 | `amount_total` | monetary | Total | ❌ | ❌ | '-' |
| 27 | `amount_total_in_currency_signed` | monetary | Total in Currency Signed | ❌ | ❌ | '-' |
| 28 | `amount_total_signed` | monetary | Total Signed | ❌ | ❌ | '-' |
| 29 | `amount_total_words` | char | Amount total in words | ❌ | ❌ | '-' |
| 30 | `amount_untaxed` | monetary | Untaxed Amount | ❌ | ❌ | '-' |
| 31 | `amount_untaxed_signed` | monetary | Untaxed Amount Signed | ❌ | ❌ | '-' |
| 32 | `asset_depreciated_value` | monetary | Cumulative Depreciation | ❌ | ❌ | '-' |
| 33 | `asset_depreciation_beginning_date` | date | Date of the beginning of the depreciation | ❌ | ❌ | '-' |
| 34 | `asset_id` | many2one → account.asset | Asset | ❌ | ❌ | '-' |
| 35 | `asset_id_display_name` | char | Asset Id Display Name | ❌ | ❌ | '-' |
| 36 | `asset_ids` | one2many → account.asset | Assets | ❌ | ❌ | '-' |
| 37 | `asset_number_days` | integer | Number of days | ❌ | ❌ | '-' |
| 38 | `asset_remaining_value` | monetary | Depreciable Value | ❌ | ❌ | '-' |
| 39 | `asset_value_change` | boolean | Asset Value Change | ❌ | ❌ | '-' |
| 40 | `attachment_ids` | one2many → ir.attachment | Attachments | ❌ | ❌ | '-' |
| 41 | `authorized_transaction_ids` | many2many → payment.transaction | Authorized Transactions | ❌ | ❌ | '-' |
| 42 | `auto_generated` | boolean | Auto Generated Document | ❌ | ❌ | '-' |
| 43 | `auto_invoice_id` | many2one → account.move | Source Invoice | ❌ | ❌ | '-' |
| 44 | `auto_post` | selection [no=No, at_date=At Date, monthly=Monthly, quarterly=Quarterly, yearly=Yearly] | Auto-post | ❌ | ✅ | '-' |
| 45 | `auto_post_origin_id` | many2one → account.move | First recurring entry | ❌ | ❌ | '-' |
| 46 | `auto_post_until` | date | Auto-post until | ❌ | ❌ | '-' |
| 47 | `available_journal_ids` | many2many → account.journal | Available Journal | ❌ | ❌ | [46 itens: [388, 1018, 1055]...] |
| 48 | `available_partner_bank_ids` | many2many → res.partner.bank | Available Partner Bank | ❌ | ❌ | [] |
| 49 | `available_payment_method_line_ids` | many2many → account.payment.method.line | Available Payment Method Line | ❌ | ❌ | [151] |
| 50 | `bank_partner_id` | many2one → res.partner | Bank Partner | ❌ | ❌ | '-' |
| 51 | `batch_payment_id` | many2one → account.batch.payment | Batch Payment | ✅ | ❌ | '-' |
| 52 | `campaign_id` | many2one → utm.campaign | Campaign | ❌ | ❌ | '-' |
| 53 | `commercial_partner_id` | many2one → res.partner | Commercial Entity | ❌ | ❌ | '-' |
| 54 | `company_currency_id` | many2one → res.currency | Company Currency | ❌ | ❌ | '-' |
| 55 | `company_id` | many2one → res.company | Company | ❌ | ❌ | '-' |
| 56 | `count_asset` | integer | Count Asset | ❌ | ❌ | '-' |
| 57 | `country_code` | char | Country Code | ❌ | ❌ | '-' |
| 58 | `create_date` | datetime | Created on | ✅ | ❌ | '-' |
| 59 | `create_in_state_sale` | selection [draft=Draft, confirm=Confirm] | Situação do Pagamento | ✅ | ❌ | '-' |
| 60 | `create_uid` | many2one → res.users | Created by | ✅ | ❌ | '-' |
| 61 | `currency_id` | many2one → res.currency | Currency | ✅ | ❌ | [6, 'BRL'] |
| 62 | `date` | date | Date | ❌ | ✅ | '-' |
| 63 | `deferred_entry_type` | selection [expense=Deferred Expense, revenue=Deferred Revenue] | Deferred Entry Type | ❌ | ❌ | '-' |
| 64 | `deferred_move_ids` | many2many → account.move | Deferred Entries | ❌ | ❌ | '-' |
| 65 | `deferred_original_move_ids` | many2many → account.move | Original Invoices | ❌ | ❌ | '-' |
| 66 | `delivery_date` | date | Delivery Date | ❌ | ❌ | '-' |
| 67 | `depreciation_value` | monetary | Depreciation | ❌ | ❌ | '-' |
| 68 | `destination_account_id` | many2one → account.account | Destination Account | ✅ | ❌ | [24801, '1120100001 CLIENTES NACIONAIS'] |
| 69 | `destination_journal_id` | many2one → account.journal | Destination Journal | ✅ | ❌ | False |
| 70 | `dfe_id` | many2one → l10n_br_ciel_it_account.dfe | Documento | ❌ | ❌ | '-' |
| 71 | `direction_sign` | integer | Direction Sign | ❌ | ❌ | '-' |
| 72 | `display_inactive_currency_warning` | boolean | Display Inactive Currency Warning | ❌ | ❌ | '-' |
| 73 | `display_name` | char | Display Name | ❌ | ❌ | '-' |
| 74 | `display_qr_code` | boolean | Display QR-code | ❌ | ❌ | '-' |
| 75 | `draft_asset_exists` | boolean | Draft Asset Exists | ❌ | ❌ | '-' |
| 76 | `duplicated_ref_ids` | many2many → account.move | Duplicated Ref | ❌ | ❌ | '-' |
| 77 | `edi_blocking_level` | selection [info=Info, warning=Warning, error=Error] | Edi Blocking Level | ❌ | ❌ | '-' |
| 78 | `edi_document_ids` | one2many → account.edi.document | Edi Document | ❌ | ❌ | '-' |
| 79 | `edi_error_count` | integer | Edi Error Count | ❌ | ❌ | '-' |
| 80 | `edi_error_message` | html | Edi Error Message | ❌ | ❌ | '-' |
| 81 | `edi_show_abandon_cancel_button` | boolean | Edi Show Abandon Cancel Button | ❌ | ❌ | '-' |
| 82 | `edi_show_cancel_button` | boolean | Edi Show Cancel Button | ❌ | ❌ | '-' |
| 83 | `edi_show_force_cancel_button` | boolean | Edi Show Force Cancel Button | ❌ | ❌ | '-' |
| 84 | `edi_state` | selection [to_send=To Send, sent=Sent, to_cancel=To Cancel, cancelled=Cancelled] | Electronic invoicing | ❌ | ❌ | '-' |
| 85 | `edi_web_services_to_process` | text | Edi Web Services To Process | ❌ | ❌ | '-' |
| 86 | `extract_attachment_id` | many2one → ir.attachment | Extract Attachment | ❌ | ❌ | '-' |
| 87 | `extract_can_show_banners` | boolean | Can show the ocr banners | ❌ | ❌ | '-' |
| 88 | `extract_can_show_send_button` | boolean | Can show the ocr send button | ❌ | ❌ | '-' |
| 89 | `extract_detected_layout` | integer | Extract Detected Layout Id | ❌ | ❌ | '-' |
| 90 | `extract_document_uuid` | char | ID of the request to IAP-OCR | ❌ | ❌ | '-' |
| 91 | `extract_error_message` | text | Error message | ❌ | ❌ | '-' |
| 92 | `extract_partner_name` | char | Extract Detected Partner Name | ❌ | ❌ | '-' |
| 93 | `extract_state` | selection [no_extract_requested=No extract requested, not_enough_credit=Not enough credits, error_status=An error occurred, waiting_extraction=Waiting extraction, extract_not_ready=waiting extraction, but it is not ready... (+3)] | Extract state | ❌ | ✅ | '-' |
| 94 | `extract_state_processed` | boolean | Extract State Processed | ❌ | ❌ | '-' |
| 95 | `extract_status` | char | Extract status | ❌ | ❌ | '-' |
| 96 | `extract_word_ids` | one2many → account.invoice_extract.words | Extract Word | ❌ | ❌ | '-' |
| 97 | `fiscal_position_id` | many2one → account.fiscal.position | Fiscal Position | ❌ | ❌ | '-' |
| 98 | `force_release_to_pay` | boolean | Force Status | ❌ | ❌ | '-' |
| 99 | `has_message` | boolean | Has Message | ❌ | ❌ | True |
| 100 | `has_reconciled_entries` | boolean | Has Reconciled Entries | ❌ | ❌ | '-' |
| 101 | `hide_post_button` | boolean | Hide Post Button | ❌ | ❌ | '-' |
| 102 | `highest_name` | char | Highest Name | ❌ | ❌ | '-' |
| 103 | `id` | integer | ID | ✅ | ❌ | 17734 |
| 104 | `inalterable_hash` | char | Inalterability Hash | ❌ | ❌ | '-' |
| 105 | `incoterm_location` | char | Incoterm Location | ❌ | ❌ | '-' |
| 106 | `invoice_cash_rounding_id` | many2one → account.cash.rounding | Cash Rounding Method | ❌ | ❌ | '-' |
| 107 | `invoice_date` | date | Invoice/Bill Date | ❌ | ❌ | '-' |
| 108 | `invoice_date_due` | date | Due Date | ❌ | ❌ | '-' |
| 109 | `invoice_filter_type_domain` | char | Invoice Filter Type Domain | ❌ | ❌ | '-' |
| 110 | `invoice_has_outstanding` | boolean | Invoice Has Outstanding | ❌ | ❌ | '-' |
| 111 | `invoice_incoterm_id` | many2one → account.incoterms | Tipo de Frete | ❌ | ❌ | '-' |
| 112 | `invoice_line_ids` | one2many → account.move.line | Invoice lines | ❌ | ❌ | '-' |
| 113 | `invoice_origin` | char | Origin | ❌ | ❌ | '-' |
| 114 | `invoice_outstanding_credits_debits_widget` | binary | Invoice Outstanding Credits Debits Widget | ❌ | ❌ | '-' |
| 115 | `invoice_partner_display_name` | char | Invoice Partner Display Name | ❌ | ❌ | '-' |
| 116 | `invoice_payment_term_id` | many2one → account.payment.term | Payment Terms | ❌ | ❌ | '-' |
| 117 | `invoice_payments_widget` | binary | Invoice Payments Widget | ❌ | ❌ | '-' |
| 118 | `invoice_pdf_report_file` | binary | PDF File | ❌ | ❌ | '-' |
| 119 | `invoice_pdf_report_id` | many2one → ir.attachment | PDF Attachment | ❌ | ❌ | '-' |
| 120 | `invoice_source_email` | char | Source Email | ❌ | ❌ | '-' |
| 121 | `invoice_user_id` | many2one → res.users | Salesperson | ❌ | ❌ | '-' |
| 122 | `invoice_vendor_bill_id` | many2one → account.move | Vendor Bill | ❌ | ❌ | '-' |
| 123 | `is_being_sent` | boolean | Is Being Sent | ❌ | ❌ | '-' |
| 124 | `is_donation` | boolean | Is Donation | ❌ | ❌ | '-' |
| 125 | `is_encerramento` | boolean | Lançamento de Encerramento | ❌ | ❌ | '-' |
| 126 | `is_in_extractable_state` | boolean | Is In Extractable State | ❌ | ❌ | '-' |
| 127 | `is_internal_transfer` | boolean | Internal Transfer | ✅ | ❌ | False |
| 128 | `is_matched` | boolean | Is Matched With a Bank Statement | ✅ | ❌ | True |
| 129 | `is_move_sent` | boolean | Is Move Sent | ❌ | ❌ | '-' |
| 130 | `is_reconciled` | boolean | Is Reconciled | ✅ | ❌ | True |
| 131 | `is_storno` | boolean | Is Storno | ❌ | ❌ | '-' |
| 132 | `journal_id` | many2one → account.journal | Journal | ❌ | ✅ | '-' |
| 133 | `l10n_br_arquivo_cobranca_escritural_id` | many2one → l10n_br_ciel_it_account.arquivo.cobranca.escritural | Arquivo Remessa Manual | ✅ | ❌ | '-' |
| 134 | `l10n_br_calcular_imposto` | boolean | Calcular Impostos | ❌ | ❌ | '-' |
| 135 | `l10n_br_carrier_id` | many2one → delivery.carrier | Carrier | ❌ | ❌ | '-' |
| 136 | `l10n_br_cbs_valor` | float | Total do CBS | ❌ | ❌ | '-' |
| 137 | `l10n_br_cfop_id` | many2one → l10n_br_ciel_it_account.cfop | CFOP | ❌ | ❌ | '-' |
| 138 | `l10n_br_chave_nf` | char | Chave da Nota Fiscal | ❌ | ❌ | '-' |
| 139 | `l10n_br_cnpj` | char | CNPJ | ❌ | ❌ | '-' |
| 140 | `l10n_br_cobranca_arquivo_remessa` | char | Arquivo Remessa Automática | ✅ | ❌ | '-' |
| 141 | `l10n_br_cobranca_data_desconto` | date | Data Limite p/ Desconto | ✅ | ❌ | '-' |
| 142 | `l10n_br_cobranca_idintegracao` | char | Id Integração | ✅ | ❌ | '-' |
| 143 | `l10n_br_cobranca_nossonumero` | char | Nosso Numero | ✅ | ❌ | '-' |
| 144 | `l10n_br_cobranca_parcela` | integer | Parcela | ✅ | ❌ | '-' |
| 145 | `l10n_br_cobranca_protocolo` | char | Protocolo | ✅ | ❌ | '-' |
| 146 | `l10n_br_cobranca_situacao` | selection [SALVO=Salvo, PENDENTE_RETENTATIVA=Pendente, FALHA=Falha, EMITIDO=Emitido, REJEITADO=Rejeitado... (+3)] | Situação | ✅ | ❌ | '-' |
| 147 | `l10n_br_cobranca_situacao_mensagem` | char | Mensagem | ✅ | ❌ | '-' |
| 148 | `l10n_br_cobranca_tipo_desconto` | selection [0=0 - Sem instrução de desconto., 1=1 - Valor Fixo Até a Data Informada., 2=2 - Percentual Até a Data Informada., 3=3 - Valor por Antecipação Dia Corrido.., 4=4 - Valor por Antecipação Dia Útil.... (+2)] | Tipo Desconto | ✅ | ❌ | '-' |
| 149 | `l10n_br_cobranca_transmissao` | selection [webservice=Webservice / Ecommerce, automatico=Remessa Automática (VAN), manual=Remessa Manual (Internet Bank)] | Tipo Transmissão | ✅ | ❌ | '-' |
| 150 | `l10n_br_cobranca_valor_desconto` | float | Valor Desconto | ✅ | ❌ | '-' |
| 151 | `l10n_br_cofins_ret_base` | float | Base do Cofins Retido | ❌ | ❌ | '-' |
| 152 | `l10n_br_cofins_ret_valor` | float | Valor do Cofins Retido | ❌ | ❌ | '-' |
| 153 | `l10n_br_cofins_valor` | float | Total do Cofins | ❌ | ❌ | '-' |
| 154 | `l10n_br_cofins_valor_isento` | float | Total do Cofins (Isento/Não Tributável) | ❌ | ❌ | '-' |
| 155 | `l10n_br_cofins_valor_outros` | float | Total do Cofins (Outros) | ❌ | ❌ | '-' |
| 156 | `l10n_br_compra_indcom` | selection [uso=Uso e Consumo, uso-prestacao=Uso na Prestação de Serviço, ind=Industrialização, com=Comercialização, ativo=Ativo... (+2)] | Destinação de Uso | ❌ | ❌ | '-' |
| 157 | `l10n_br_correcao` | text | Correção | ❌ | ❌ | '-' |
| 158 | `l10n_br_csll_ret_base` | float | Base do CSLL Retido | ❌ | ❌ | '-' |
| 159 | `l10n_br_csll_ret_valor` | float | Valor do CSLL Retido | ❌ | ❌ | '-' |
| 160 | `l10n_br_csll_valor` | float | Total do CSLL | ❌ | ❌ | '-' |
| 161 | `l10n_br_cstat_nf` | char | Status da Nota Fiscal | ❌ | ❌ | '-' |
| 162 | `l10n_br_dados_pagamento_count` | integer | Dados de Pagamento (CNAB) Qty | ✅ | ❌ | '-' |
| 163 | `l10n_br_dados_pagamento_data` | date | Data de Pagamento (CNAB) | ✅ | ❌ | '-' |
| 164 | `l10n_br_dados_pagamento_id` | one2many → l10n_br_ciel_it_account.dados.pagamento | Dados de Pagamento (CNAB) | ✅ | ❌ | '-' |
| 165 | `l10n_br_dados_pagamento_state` | selection [CREATED=Criado, PAID=Pago, SCHEDULED=Agendado, CANCELLED=Cancelado, REJECTED=Rejeitado... (+2)] | Status CNAB | ✅ | ❌ | '-' |
| 166 | `l10n_br_data_nfse_substituida` | date | Data de Emissão da NFS-e Substituida | ❌ | ❌ | '-' |
| 167 | `l10n_br_data_saida` | datetime | Data/Hora de Saída | ❌ | ❌ | '-' |
| 168 | `l10n_br_dctf_imposto_codigo` | char | Código do Imposto DCTF | ❌ | ❌ | '-' |
| 169 | `l10n_br_desc_valor` | float | Total do Desconto | ❌ | ❌ | '-' |
| 170 | `l10n_br_descricao_servico` | text | Descrição do Serviço | ❌ | ❌ | '-' |
| 171 | `l10n_br_descricao_servico_show` | boolean | Mostrar Descrição do Serviço | ❌ | ❌ | '-' |
| 172 | `l10n_br_despesas_acessorias` | float | Total da Despesas Acessórias | ❌ | ❌ | '-' |
| 173 | `l10n_br_especie` | char | Espécie | ❌ | ❌ | '-' |
| 174 | `l10n_br_fcp_dest_valor` | float | Total do Fundo de Combate a Pobreza | ❌ | ❌ | '-' |
| 175 | `l10n_br_fcp_st_ant_valor` | float | Total do Fundo de Combate a Pobreza Retido Anteriormente por ST | ❌ | ❌ | '-' |
| 176 | `l10n_br_fcp_st_valor` | float | Total do Fundo de Combate a Pobreza Retido por ST | ❌ | ❌ | '-' |
| 177 | `l10n_br_frete` | float | Total do Frete | ❌ | ❌ | '-' |
| 178 | `l10n_br_gnre_disponivel` | boolean | GNRE Disponível | ❌ | ❌ | '-' |
| 179 | `l10n_br_gnre_numero_recibo` | char | GNRE - Número do Recibo | ❌ | ❌ | '-' |
| 180 | `l10n_br_gnre_ok` | boolean | GNRE OK | ❌ | ❌ | '-' |
| 181 | `l10n_br_handle_nfce` | integer | Handle da Nota Fiscal Eletrônica ao Consumidor | ❌ | ❌ | '-' |
| 182 | `l10n_br_handle_nfse` | integer | Handle da Nota Fiscal de Serviço | ❌ | ❌ | '-' |
| 183 | `l10n_br_ibs_mun_valor` | float | Total do IBS Município | ❌ | ❌ | '-' |
| 184 | `l10n_br_ibs_uf_valor` | float | Total do IBS UF | ❌ | ❌ | '-' |
| 185 | `l10n_br_ibs_valor` | float | Total do IBS | ❌ | ❌ | '-' |
| 186 | `l10n_br_ibscbs_base` | float | Total da Base de Cálculo do IBS/CBS | ❌ | ❌ | '-' |
| 187 | `l10n_br_icms_base` | float | Total da Base de Cálculo do ICMS | ❌ | ❌ | '-' |
| 188 | `l10n_br_icms_dest_valor` | float | Total do ICMS UF Destino | ❌ | ❌ | '-' |
| 189 | `l10n_br_icms_remet_valor` | float | Total do ICMS UF Remetente | ❌ | ❌ | '-' |
| 190 | `l10n_br_icms_valor` | float | Total do ICMS (Tributável) | ❌ | ❌ | '-' |
| 191 | `l10n_br_icms_valor_credito_presumido` | float | Total do ICMS (Crédito Presumido) | ❌ | ❌ | '-' |
| 192 | `l10n_br_icms_valor_desonerado` | float | Total do ICMS (Desonerado) | ❌ | ❌ | '-' |
| 193 | `l10n_br_icms_valor_efetivo` | float | Total do ICMS (Efetivo) | ❌ | ❌ | '-' |
| 194 | `l10n_br_icms_valor_isento` | float | Total do ICMS (Isento/Não Tributável) | ❌ | ❌ | '-' |
| 195 | `l10n_br_icms_valor_outros` | float | Total do ICMS (Outros) | ❌ | ❌ | '-' |
| 196 | `l10n_br_icmsst_base` | float | Total da Base de Cálculo do ICMSST | ❌ | ❌ | '-' |
| 197 | `l10n_br_icmsst_retido_valor` | float | Total do ICMSST Retido | ❌ | ❌ | '-' |
| 198 | `l10n_br_icmsst_retido_valor_outros` | float | Total do ICMSST Retido (Outros) | ❌ | ❌ | '-' |
| 199 | `l10n_br_icmsst_substituto_valor` | float | Total do ICMSST Substituto | ❌ | ❌ | '-' |
| 200 | `l10n_br_icmsst_substituto_valor_outros` | float | Total do ICMSST Substituto (Outros) | ❌ | ❌ | '-' |
| 201 | `l10n_br_icmsst_valor` | float | Total do ICMSST | ❌ | ❌ | '-' |
| 202 | `l10n_br_icmsst_valor_outros` | float | Total do ICMSST (Outros) | ❌ | ❌ | '-' |
| 203 | `l10n_br_icmsst_valor_proprio` | float | Total do ICMSST (Próprio) | ❌ | ❌ | '-' |
| 204 | `l10n_br_ii_valor` | float | Total do II | ❌ | ❌ | '-' |
| 205 | `l10n_br_ii_valor_aduaneira` | float | Total do II Aduaneira | ❌ | ❌ | '-' |
| 206 | `l10n_br_ii_valor_afrmm` | float | Total do II AFRMM | ❌ | ❌ | '-' |
| 207 | `l10n_br_imposto_auto` | boolean | Calcular Impostos Automaticamente | ❌ | ❌ | '-' |
| 208 | `l10n_br_indicador_presenca` | selection [0=0 - Não se aplica, 1=1 - Operação presencial, 2=2 - Operação não presencial, pela internet, 3=3 - Operação não presencial, teleatendimento, 4=4 - NFC-e em operação com entrega a domicílio... (+2)] | Indicador Presença | ❌ | ❌ | '-' |
| 209 | `l10n_br_informacao_complementar` | text | Informação Complementar | ❌ | ❌ | '-' |
| 210 | `l10n_br_informacao_fiscal` | text | Informação Fiscal | ❌ | ❌ | '-' |
| 211 | `l10n_br_inss_ret_base` | float | Base do INSS Retido | ❌ | ❌ | '-' |
| 212 | `l10n_br_inss_ret_valor` | float | Valor do INSS Retido | ❌ | ❌ | '-' |
| 213 | `l10n_br_iof_valor` | float | Total do IOF | ❌ | ❌ | '-' |
| 214 | `l10n_br_ipi_valor` | float | Total do IPI | ❌ | ❌ | '-' |
| 215 | `l10n_br_ipi_valor_isento` | float | Total do IPI (Isento/Não Tributável) | ❌ | ❌ | '-' |
| 216 | `l10n_br_ipi_valor_outros` | float | Total do IPI (Outros) | ❌ | ❌ | '-' |
| 217 | `l10n_br_irpj_ret_base` | float | Base do IRPJ Retido | ❌ | ❌ | '-' |
| 218 | `l10n_br_irpj_ret_valor` | float | Valor do IRPJ Retido | ❌ | ❌ | '-' |
| 219 | `l10n_br_irpj_valor` | float | Total do IRPJ | ❌ | ❌ | '-' |
| 220 | `l10n_br_is_advanced` | boolean | Adiantamento? | ✅ | ❌ | '-' |
| 221 | `l10n_br_is_valor` | float | Total do IS | ❌ | ❌ | '-' |
| 222 | `l10n_br_iss_municipio_id` | many2one → l10n_br_ciel_it_account.res.municipio | Município de Incidência do ISS | ❌ | ❌ | '-' |
| 223 | `l10n_br_iss_ret_base` | float | Base do ISS Retido | ❌ | ❌ | '-' |
| 224 | `l10n_br_iss_ret_valor` | float | Valor do ISS Retido | ❌ | ❌ | '-' |
| 225 | `l10n_br_iss_valor` | float | Total do ISS | ❌ | ❌ | '-' |
| 226 | `l10n_br_item_pedido_compra` | char | Item Pedido de Compra do Cliente | ❌ | ❌ | '-' |
| 227 | `l10n_br_local_despacho` | char | Local de despacho | ❌ | ❌ | '-' |
| 228 | `l10n_br_local_embarque` | char | Local de embarque | ❌ | ❌ | '-' |
| 229 | `l10n_br_marca` | char | Marca | ❌ | ❌ | '-' |
| 230 | `l10n_br_motivo` | text | Motivo Cancelamento | ❌ | ❌ | '-' |
| 231 | `l10n_br_municipio_fim_id` | many2one → l10n_br_ciel_it_account.res.municipio | Município de Destino | ❌ | ❌ | '-' |
| 232 | `l10n_br_municipio_inicio_id` | many2one → l10n_br_ciel_it_account.res.municipio | Município de Origem | ❌ | ❌ | '-' |
| 233 | `l10n_br_nfe_emails` | char | Email XML NF-e | ❌ | ❌ | '-' |
| 234 | `l10n_br_nfse_substituta` | boolean | NFS-e Substituta? | ❌ | ❌ | '-' |
| 235 | `l10n_br_numeracao_volume` | char | Númeração Volume | ❌ | ❌ | '-' |
| 236 | `l10n_br_numero_nf` | integer | Número da Nota Fiscal de Mercadoria | ❌ | ❌ | '-' |
| 237 | `l10n_br_numero_nfce` | char | Número da Nota Fiscal Eletrônica ao Consumidor | ❌ | ❌ | '-' |
| 238 | `l10n_br_numero_nfse` | char | Número da Nota Fiscal de Serviço | ❌ | ❌ | '-' |
| 239 | `l10n_br_numero_nfse_substituida` | char | Número da NFS-e Substituida | ❌ | ❌ | '-' |
| 240 | `l10n_br_numero_nota_fiscal` | char | Número da Nota Fiscal | ❌ | ❌ | '-' |
| 241 | `l10n_br_numero_rps` | integer | Número RPS | ❌ | ❌ | '-' |
| 242 | `l10n_br_numero_rps_substituido` | integer | Número RPS Substituido | ❌ | ❌ | '-' |
| 243 | `l10n_br_operacao_consumidor` | selection [0=0 - Normal, 1=1 - Consumidor Final] | Operação Consumidor Final | ❌ | ❌ | '-' |
| 244 | `l10n_br_operacao_id` | many2one → l10n_br_ciel_it_account.operacao | Operação | ❌ | ❌ | '-' |
| 245 | `l10n_br_paga` | boolean | Parcela Paga? | ✅ | ❌ | '-' |
| 246 | `l10n_br_pdf_aut_gnre` | binary | GNRE | ❌ | ❌ | '-' |
| 247 | `l10n_br_pdf_aut_gnre_fname` | char | Arquivo GNRE | ❌ | ❌ | '-' |
| 248 | `l10n_br_pdf_aut_nfe` | binary | DANFE NF-e | ❌ | ❌ | '-' |
| 249 | `l10n_br_pdf_aut_nfe_fname` | char | Arquivo DANFE NF-e | ❌ | ❌ | '-' |
| 250 | `l10n_br_pdf_boleto` | binary | Boleto | ✅ | ❌ | '-' |
| 251 | `l10n_br_pdf_boleto_fname` | char | Arquivo Boleto | ❌ | ❌ | '-' |
| 252 | `l10n_br_pdf_can_nfe` | binary | DANFE NF-e Cancelamento | ❌ | ❌ | '-' |
| 253 | `l10n_br_pdf_can_nfe_fname` | char | Arquivo DANFE NF-e Cancelamento | ❌ | ❌ | '-' |
| 254 | `l10n_br_pdf_cce_nfe` | binary | DANFE CC-e | ❌ | ❌ | '-' |
| 255 | `l10n_br_pdf_cce_nfe_fname` | char | Arquivo DANFE CC-e | ❌ | ❌ | '-' |
| 256 | `l10n_br_pedido_compra` | char | Pedido de Compra do Cliente | ❌ | ❌ | '-' |
| 257 | `l10n_br_peso_bruto` | float | Peso Bruto | ❌ | ❌ | '-' |
| 258 | `l10n_br_peso_liquido` | float | Peso Líquido | ❌ | ❌ | '-' |
| 259 | `l10n_br_pis_ret_base` | float | Base do PIS Retido | ❌ | ❌ | '-' |
| 260 | `l10n_br_pis_ret_valor` | float | Valor do PIS Retido | ❌ | ❌ | '-' |
| 261 | `l10n_br_pis_valor` | float | Total do PIS | ❌ | ❌ | '-' |
| 262 | `l10n_br_pis_valor_isento` | float | Total do PIS (Isento/Não Tributável) | ❌ | ❌ | '-' |
| 263 | `l10n_br_pis_valor_outros` | float | Total do PIS (Outros) | ❌ | ❌ | '-' |
| 264 | `l10n_br_prod_valor` | float | Total dos Produtos | ❌ | ❌ | '-' |
| 265 | `l10n_br_rateio_frete_auto` | boolean | Rateio Frete Automatico | ❌ | ❌ | '-' |
| 266 | `l10n_br_seguro` | float | Total do Seguro | ❌ | ❌ | '-' |
| 267 | `l10n_br_sequencia_evento` | integer | Sequencia Evento NF-e | ❌ | ❌ | '-' |
| 268 | `l10n_br_serie_nf` | char | Série da Nota Fiscal | ❌ | ❌ | '-' |
| 269 | `l10n_br_serie_nf_substituido` | char | Série NFS-e Substituido | ❌ | ❌ | '-' |
| 270 | `l10n_br_show_nfe_btn` | boolean | Mostrar botão NF-e | ❌ | ❌ | '-' |
| 271 | `l10n_br_situacao_nf` | selection [rascunho=Rascunho, autorizado=Autorizado, excecao_autorizado=Exceção, cce=Carta de Correção, excecao_cce=Exceção... (+2)] | Situação NF-e | ❌ | ❌ | '-' |
| 272 | `l10n_br_tipo_documento` | selection [NFS=Nota Fiscal de Serviços Instituída por Municípios, NFSE=Nota Fiscal de Serviços Eletrônica - NFS-e, NDS=Nota de Débito de Serviços, FAT=Fatura, ND=Nota de Débito... (+32)] | Tipo Documento Fiscal | ❌ | ❌ | '-' |
| 273 | `l10n_br_tipo_imposto` | selection [cofins=COFINS, csll=CSLL, icms=ICMS, ii=II, inss=INSS... (+7)] | Tipo Imposto | ❌ | ❌ | '-' |
| 274 | `l10n_br_tipo_pedido` | selection [baixa-estoque=Saída: Baixa de Estoque, complemento-valor=Saída: Complemento de Preço, dev-comodato=Saída: Devolução de Comodato, compra=Saída: Devolução de Compra, dev-conserto=Saída: Devolução de Conserto... (+42)] | Tipo de Pedido (saída) | ❌ | ❌ | '-' |
| 275 | `l10n_br_tipo_pedido_entrada` | selection [ent-amostra=Entrada: Amostra Grátis, ent-bonificacao=Entrada: Bonificação, ent-comodato=Entrada: Comodato, comp-importacao=Entrada: Complementar de Importação, compra=Entrada: Compra... (+33)] | Tipo de Pedido (entrada) | ❌ | ❌ | '-' |
| 276 | `l10n_br_total_nfe` | float | Total da Nota Fiscal | ❌ | ❌ | '-' |
| 277 | `l10n_br_total_tributos` | float | Total dos Tributos | ❌ | ❌ | '-' |
| 278 | `l10n_br_uf_saida_pais` | char | Sigla UF de Saída | ❌ | ❌ | '-' |
| 279 | `l10n_br_veiculo_placa` | char | Placa | ❌ | ❌ | '-' |
| 280 | `l10n_br_veiculo_rntc` | char | RNTC | ❌ | ❌ | '-' |
| 281 | `l10n_br_veiculo_uf` | char | UF da Placa | ❌ | ❌ | '-' |
| 282 | `l10n_br_volumes` | integer | Volumes | ❌ | ❌ | '-' |
| 283 | `l10n_br_xml_aut_nfe` | binary | XML NF-e | ❌ | ❌ | '-' |
| 284 | `l10n_br_xml_aut_nfe_fname` | char | Arquivo XML NF-e | ❌ | ❌ | '-' |
| 285 | `l10n_br_xml_can_nfe` | binary | XML NF-e Cancelamento | ❌ | ❌ | '-' |
| 286 | `l10n_br_xml_can_nfe_fname` | char | Arquivo XML NF-e Cancelamento | ❌ | ❌ | '-' |
| 287 | `l10n_br_xml_cce_nfe` | binary | XML CC-e | ❌ | ❌ | '-' |
| 288 | `l10n_br_xml_cce_nfe_fname` | char | Arquivo XML CC-e | ❌ | ❌ | '-' |
| 289 | `l10n_br_xmotivo_nf` | char | Situação da Nota Fiscal | ❌ | ❌ | '-' |
| 290 | `landed_costs_ids` | one2many → stock.landed.cost | Landed Costs | ❌ | ❌ | '-' |
| 291 | `landed_costs_visible` | boolean | Landed Costs Visible | ❌ | ❌ | '-' |
| 292 | `laudos` | binary | Laudos | ❌ | ❌ | '-' |
| 293 | `laudos_filename` | char | Nome do arquivo de laudos | ❌ | ❌ | '-' |
| 294 | `line_ids` | one2many → account.move.line | Journal Items | ❌ | ❌ | '-' |
| 295 | `made_sequence_hole` | boolean | Made Sequence Hole | ❌ | ❌ | '-' |
| 296 | `medium_id` | many2one → utm.medium | Medium | ❌ | ❌ | '-' |
| 297 | `message_attachment_count` | integer | Attachment Count | ❌ | ❌ | 0 |
| 298 | `message_follower_ids` | one2many → mail.followers | Followers | ✅ | ❌ | [2577513] |
| 299 | `message_has_error` | boolean | Message Delivery error | ❌ | ❌ | False |
| 300 | `message_has_error_counter` | integer | Number of errors | ❌ | ❌ | 0 |
| 301 | `message_has_sms_error` | boolean | SMS Delivery error | ❌ | ❌ | False |
| 302 | `message_ids` | one2many → mail.message | Messages | ✅ | ❌ | [12417805] |
| 303 | `message_is_follower` | boolean | Is Follower | ❌ | ❌ | False |
| 304 | `message_main_attachment_id` | many2one → ir.attachment | Main Attachment | ✅ | ❌ | False |
| 305 | `message_needaction` | boolean | Action Needed | ❌ | ❌ | False |
| 306 | `message_needaction_counter` | integer | Number of Actions | ❌ | ❌ | 0 |
| 307 | `message_partner_ids` | many2many → res.partner | Followers (Partners) | ❌ | ❌ | [207026] |
| 308 | `move_id` | many2one → account.move | Journal Entry | ✅ | ✅ | [416054, 'PDEVOL/2025/00298 (VND/2025/05333)'] |
| 309 | `move_type` | selection [entry=Journal Entry, out_invoice=Customer Invoice, out_refund=Customer Credit Note, in_invoice=Vendor Bill, in_refund=Vendor Credit Note... (+2)] | Type | ❌ | ✅ | '-' |
| 310 | `my_activity_date_deadline` | date | My Activity Deadline | ❌ | ❌ | False |
| 311 | `name` | char | Number | ❌ | ❌ | '-' |
| 312 | `narration` | html | Terms and Conditions | ❌ | ❌ | '-' |
| 313 | `need_cancel_request` | boolean | Need Cancel Request | ❌ | ❌ | '-' |
| 314 | `needed_terms` | binary | Needed Terms | ❌ | ❌ | '-' |
| 315 | `needed_terms_dirty` | boolean | Needed Terms Dirty | ❌ | ❌ | '-' |
| 316 | `outstanding_account_id` | many2one → account.account | Outstanding Account | ✅ | ❌ | [22246, '1120900002 ( - ) DEVOLUCOES A COMPENSAR'] |
| 317 | `paired_internal_transfer_payment_id` | many2one → account.payment | Paired Internal Transfer Payment | ✅ | ❌ | False |
| 318 | `parcelas_manual_id` | many2one → l10n_br_ciel_it_account.payment.parcela.manual | Parcelas Personalizada | ❌ | ❌ | '-' |
| 319 | `partner_bank_id` | many2one → res.partner.bank | Recipient Bank Account | ✅ | ❌ | False |
| 320 | `partner_contact_id` | many2one → res.partner | Contato | ❌ | ❌ | '-' |
| 321 | `partner_credit` | monetary | Partner Credit | ❌ | ❌ | '-' |
| 322 | `partner_credit_warning` | text | Partner Credit Warning | ❌ | ❌ | '-' |
| 323 | `partner_id` | many2one → res.partner | Customer/Vendor | ✅ | ❌ | [205205, 'REDE ASSAI LJ 336'] |
| 324 | `partner_invoice_id` | many2one → res.partner | Endereço de Cobrança | ❌ | ❌ | '-' |
| 325 | `partner_shipping_id` | many2one → res.partner | Delivery Address | ❌ | ❌ | '-' |
| 326 | `partner_type` | selection [customer=Customer, supplier=Vendor] | Partner Type | ✅ | ✅ | 'customer' |
| 327 | `payment_id` | many2one → account.payment | Payment | ❌ | ❌ | '-' |
| 328 | `payment_ids` | one2many → account.payment | Payments | ❌ | ❌ | '-' |
| 329 | `payment_line_ids` | many2many → account.move.line | Payment lines | ❌ | ❌ | '-' |
| 330 | `payment_method_code` | char | Code | ❌ | ❌ | '-' |
| 331 | `payment_method_id` | many2one → account.payment.method | Method | ✅ | ❌ | [1, 'Manual'] |
| 332 | `payment_method_line_id` | many2one → account.payment.method.line | Payment Method | ✅ | ❌ | [151, 'Manual'] |
| 333 | `payment_method_name` | char | Name | ❌ | ❌ | '-' |
| 334 | `payment_provider_id` | many2one → payment.provider | Forma de Pagamento | ❌ | ❌ | '-' |
| 335 | `payment_reference` | char | Payment Reference | ✅ | ❌ | False |
| 336 | `payment_state` | selection [not_paid=Not Paid, in_payment=In Payment, paid=Paid, partial=Partially Paid, reversed=Reversed... (+1)] | Payment Status | ❌ | ❌ | '-' |
| 337 | `payment_state_before_switch` | char | Payment State Before Switch | ❌ | ❌ | '-' |
| 338 | `payment_term_details` | binary | Payment Term Details | ❌ | ❌ | '-' |
| 339 | `payment_token_id` | many2one → payment.token | Saved Payment Token | ✅ | ❌ | '-' |
| 340 | `payment_transaction_id` | many2one → payment.transaction | Payment Transaction | ✅ | ❌ | '-' |
| 341 | `payment_type` | selection [outbound=Send, inbound=Receive] | Payment Type | ✅ | ✅ | 'inbound' |
| 342 | `picking_ids` | many2many → stock.picking | Picking References | ❌ | ❌ | '-' |
| 343 | `picking_ok` | boolean | Picking OK | ❌ | ❌ | '-' |
| 344 | `posted_before` | boolean | Posted Before | ❌ | ❌ | '-' |
| 345 | `purchase_id` | many2one → purchase.order | Purchase Order | ❌ | ❌ | '-' |
| 346 | `purchase_order_count` | integer | Purchase Order Count | ❌ | ❌ | '-' |
| 347 | `purchase_vendor_bill_id` | many2one → purchase.bill.union | Auto-complete | ❌ | ❌ | '-' |
| 348 | `qr_code` | html | QR Code URL | ❌ | ❌ | False |
| 349 | `qr_code_method` | selection | Payment QR-code | ❌ | ❌ | '-' |
| 350 | `quick_edit_mode` | boolean | Quick Edit Mode | ❌ | ❌ | '-' |
| 351 | `quick_edit_total_amount` | monetary | Total (Tax inc.) | ❌ | ❌ | '-' |
| 352 | `quick_encoding_vals` | json | Quick Encoding Vals | ❌ | ❌ | '-' |
| 353 | `rating_ids` | one2many → rating.rating | Ratings | ✅ | ❌ | [] |
| 354 | `reconciled_bill_ids` | many2many → account.move | Reconciled Bills | ❌ | ❌ | [] |
| 355 | `reconciled_bills_count` | integer | # Reconciled Bills | ❌ | ❌ | '-' |
| 356 | `reconciled_invoice_ids` | many2many → account.move | Reconciled Invoices | ❌ | ❌ | [412760] |
| 357 | `reconciled_invoices_count` | integer | # Reconciled Invoices | ❌ | ❌ | 1 |
| 358 | `reconciled_invoices_type` | selection [credit_note=Credit Note, invoice=Invoice] | Reconciled Invoices Type | ❌ | ❌ | 'invoice' |
| 359 | `reconciled_statement_line_ids` | many2many → account.bank.statement.line | Reconciled Statement Lines | ❌ | ❌ | '-' |
| 360 | `reconciled_statement_lines_count` | integer | # Reconciled Statement Lines | ❌ | ❌ | '-' |
| 361 | `ref` | char | Reference | ❌ | ❌ | '-' |
| 362 | `referencia_ids` | one2many → l10n_br_ciel_it_account.account.move.referencia | NF-e referência | ❌ | ❌ | '-' |
| 363 | `refunds_count` | integer | Refunds Count | ❌ | ❌ | '-' |
| 364 | `reinfs_2010_count` | integer | REINF 2010 Qtd. | ❌ | ❌ | '-' |
| 365 | `reinfs_2010_ids` | one2many → l10n_br_ciel_it_account.reinf.2010 | REINF 2010 | ❌ | ❌ | '-' |
| 366 | `reinfs_2020_count` | integer | REINF 2020 Qtd. | ❌ | ❌ | '-' |
| 367 | `reinfs_2020_ids` | one2many → l10n_br_ciel_it_account.reinf.2020 | REINF 2020 | ❌ | ❌ | '-' |
| 368 | `reinfs_2060_count` | integer | REINF 2060 Qtd. | ❌ | ❌ | '-' |
| 369 | `reinfs_2060_ids` | one2many → l10n_br_ciel_it_account.reinf.2060 | REINF 2060 | ❌ | ❌ | '-' |
| 370 | `reinfs_4010_count` | integer | REINF 4010 Qtd. | ❌ | ❌ | '-' |
| 371 | `reinfs_4010_ids` | one2many → l10n_br_ciel_it_account.reinf.4010 | REINF 4010 | ❌ | ❌ | '-' |
| 372 | `reinfs_4020_count` | integer | REINF 4020 Qtd. | ❌ | ❌ | '-' |
| 373 | `reinfs_4020_ids` | one2many → l10n_br_ciel_it_account.reinf.4020 | REINF 4020 | ❌ | ❌ | '-' |
| 374 | `reinfs_4080_count` | integer | REINF 4080 Qtd. | ❌ | ❌ | '-' |
| 375 | `reinfs_4080_ids` | one2many → l10n_br_ciel_it_account.reinf.4080 | REINF 4080 | ❌ | ❌ | '-' |
| 376 | `release_to_pay` | selection [yes=Yes, no=No, exception=Exception] | Release To Pay | ❌ | ❌ | '-' |
| 377 | `release_to_pay_manual` | selection [yes=Yes, no=No, exception=Exception] | Should Be Paid | ❌ | ❌ | '-' |
| 378 | `require_partner_bank_account` | boolean | Require Partner Bank Account | ❌ | ❌ | '-' |
| 379 | `restrict_mode_hash_table` | boolean | Lock Posted Entries with Hash | ❌ | ❌ | '-' |
| 380 | `reversal_move_id` | one2many → account.move | Reversal Move | ❌ | ❌ | '-' |
| 381 | `reversed_entry_id` | many2one → account.move | Reversal of | ❌ | ❌ | '-' |
| 382 | `sale_id` | many2one → sale.order | Pedido de Venda | ✅ | ❌ | '-' |
| 383 | `sale_order_count` | integer | Sale Order Count | ❌ | ❌ | '-' |
| 384 | `secure_sequence_number` | integer | Inalteralbility No Gap Sequence # | ❌ | ❌ | '-' |
| 385 | `send_and_print_values` | json | Send And Print Values | ❌ | ❌ | '-' |
| 386 | `sequence_number` | integer | Sequence Number | ❌ | ❌ | '-' |
| 387 | `sequence_prefix` | char | Sequence Prefix | ❌ | ❌ | '-' |
| 388 | `show_delivery_date` | boolean | Show Delivery Date | ❌ | ❌ | '-' |
| 389 | `show_discount_details` | boolean | Show Discount Details | ❌ | ❌ | '-' |
| 390 | `show_name_warning` | boolean | Show Name Warning | ❌ | ❌ | '-' |
| 391 | `show_partner_bank_account` | boolean | Show Partner Bank Account | ❌ | ❌ | '-' |
| 392 | `show_payment_term_details` | boolean | Show Payment Term Details | ❌ | ❌ | '-' |
| 393 | `show_reset_to_draft_button` | boolean | Show Reset To Draft Button | ❌ | ❌ | '-' |
| 394 | `show_update_fpos` | boolean | Has Fiscal Position Changed | ❌ | ❌ | '-' |
| 395 | `simples_nacional` | boolean | Emitente Simples Nacional | ❌ | ❌ | '-' |
| 396 | `source_id` | many2one → utm.source | Source | ❌ | ❌ | '-' |
| 397 | `source_payment_id` | many2one → account.payment | Source Payment | ✅ | ❌ | '-' |
| 398 | `state` | selection [draft=Draft, posted=Posted, cancel=Cancelled] | Status | ❌ | ✅ | '-' |
| 399 | `statement_id` | many2one → account.bank.statement | Statement | ❌ | ❌ | '-' |
| 400 | `statement_line_id` | many2one → account.bank.statement.line | Statement Line | ❌ | ❌ | '-' |
| 401 | `statement_line_ids` | one2many → account.bank.statement.line | Statements | ❌ | ❌ | '-' |
| 402 | `stock_move_id` | many2one → stock.move | Stock Move | ❌ | ❌ | '-' |
| 403 | `stock_valuation_layer_ids` | one2many → stock.valuation.layer | Stock Valuation Layer | ❌ | ❌ | '-' |
| 404 | `string_to_hash` | char | String To Hash | ❌ | ❌ | '-' |
| 405 | `suitable_journal_ids` | many2many → account.journal | Suitable Journal | ❌ | ❌ | '-' |
| 406 | `suitable_payment_token_ids` | many2many → payment.token | Suitable Payment Token | ❌ | ❌ | '-' |
| 407 | `suspense_statement_line_id` | many2one → account.bank.statement.line | Request document from a bank statement line | ❌ | ❌ | '-' |
| 408 | `tax_calculation_rounding_method` | selection [round_per_line=Round per Line, round_globally=Round Globally] | Tax calculation rounding method | ❌ | ❌ | '-' |
| 409 | `tax_cash_basis_created_move_ids` | one2many → account.move | Cash Basis Entries | ❌ | ❌ | '-' |
| 410 | `tax_cash_basis_origin_move_id` | many2one → account.move | Cash Basis Origin | ❌ | ❌ | '-' |
| 411 | `tax_cash_basis_rec_id` | many2one → account.partial.reconcile | Tax Cash Basis Entry of | ❌ | ❌ | '-' |
| 412 | `tax_closing_alert` | boolean | Tax Closing Alert | ❌ | ❌ | '-' |
| 413 | `tax_closing_end_date` | date | Tax Closing End Date | ❌ | ❌ | '-' |
| 414 | `tax_closing_show_multi_closing_warning` | boolean | Tax Closing Show Multi Closing Warning | ❌ | ❌ | '-' |
| 415 | `tax_country_code` | char | Tax Country Code | ❌ | ❌ | '-' |
| 416 | `tax_country_id` | many2one → res.country | Tax Country | ❌ | ❌ | '-' |
| 417 | `tax_lock_date_message` | char | Tax Lock Date Message | ❌ | ❌ | '-' |
| 418 | `tax_report_control_error` | boolean | Tax Report Control Error | ❌ | ❌ | '-' |
| 419 | `tax_totals` | binary | Invoice Totals | ❌ | ❌ | '-' |
| 420 | `team_id` | many2one → crm.team | Sales Team | ❌ | ❌ | '-' |
| 421 | `timesheet_count` | integer | Number of timesheets | ❌ | ❌ | '-' |
| 422 | `timesheet_encode_uom_id` | many2one → uom.uom | Timesheet Encoding Unit | ❌ | ❌ | '-' |
| 423 | `timesheet_ids` | one2many → account.analytic.line | Timesheets | ❌ | ❌ | '-' |
| 424 | `timesheet_total_duration` | integer | Timesheet Total Duration | ❌ | ❌ | '-' |
| 425 | `to_check` | boolean | To Check | ❌ | ❌ | '-' |
| 426 | `transaction_ids` | many2many → payment.transaction | Transactions | ❌ | ❌ | '-' |
| 427 | `transfer_model_id` | many2one → account.transfer.model | Originating Model | ❌ | ❌ | '-' |
| 428 | `type_name` | char | Type Name | ❌ | ❌ | '-' |
| 429 | `ubl_cii_xml_file` | binary | UBL/CII File | ❌ | ❌ | '-' |
| 430 | `ubl_cii_xml_id` | many2one → ir.attachment | Attachment | ❌ | ❌ | '-' |
| 431 | `use_electronic_payment_method` | boolean | Use Electronic Payment Method | ❌ | ❌ | '-' |
| 432 | `user_id` | many2one → res.users | User | ❌ | ❌ | '-' |
| 433 | `usuario_id` | many2one → res.partner | Usuário | ❌ | ❌ | '-' |
| 434 | `website_message_ids` | one2many → mail.message | Website Messages | ✅ | ❌ | [] |
| 435 | `write_date` | datetime | Last Updated on | ✅ | ❌ | '-' |
| 436 | `write_uid` | many2one → res.users | Last Updated by | ✅ | ❌ | '-' |
| 437 | `x_studio_observao_interna` | text | Observação Interna | ❌ | ❌ | '-' |


### DETALHAMENTO DOS CAMPOS:

#### `access_token`
- **Label:** Security Token
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `access_url`
- **Label:** Portal Access URL
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Customer Portal URL

#### `access_warning`
- **Label:** Access warning
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `activity_calendar_event_id`
- **Label:** Next Activity Calendar Event
- **Tipo:** many2one → calendar.event
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `calendar.event`
- **Valor Exemplo:** `False`

#### `activity_date_deadline`
- **Label:** Next Activity Deadline
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `activity_exception_decoration`
- **Label:** Activity Exception Decoration
- **Tipo:** selection [warning=Alert, danger=Error]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['warning', 'Alert'], ['danger', 'Error']]
- **Descrição:** Type of the exception activity on record.
- **Valor Exemplo:** `False`

#### `activity_exception_icon`
- **Label:** Icon
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Icon to indicate an exception activity.
- **Valor Exemplo:** `False`

#### `activity_ids`
- **Label:** Activities
- **Tipo:** one2many → mail.activity
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.activity`
- **Valor Exemplo:** `[]`

#### `activity_state`
- **Label:** Activity State
- **Tipo:** selection [overdue=Overdue, today=Today, planned=Planned]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']]
- **Descrição:** Status based on activities
Overdue: Due date is already passed
Today: Activity date is today
Planned: Future activities.
- **Valor Exemplo:** `False`

#### `activity_summary`
- **Label:** Next Activity Summary
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `activity_type_icon`
- **Label:** Activity Type Icon
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Font awesome icon e.g. fa-tasks
- **Valor Exemplo:** `False`

#### `activity_type_id`
- **Label:** Next Activity Type
- **Tipo:** many2one → mail.activity.type
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.activity.type`
- **Valor Exemplo:** `False`

#### `activity_user_id`
- **Label:** Responsible User
- **Tipo:** many2one → res.users
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `False`

#### `adiantamento_id`
- **Label:** Adiantamento
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `agendamento_id`
- **Label:** Agendamento
- **Tipo:** selection [sim=Sim, nao=Não]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['sim', 'Sim'], ['nao', 'Não']]

#### `always_tax_exigible`
- **Label:** Always Tax Exigible
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `amount`
- **Label:** Amount
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `107.25`

#### `amount_available_for_refund`
- **Label:** Amount Available For Refund
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_company_currency_signed`
- **Label:** Amount Company Currency Signed
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_paid`
- **Label:** Amount paid
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_residual`
- **Label:** Amount Due
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_residual_signed`
- **Label:** Amount Due Signed
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_signed`
- **Label:** Amount Signed
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Negative value of amount field if payment_type is outbound

#### `amount_tax`
- **Label:** Tax
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_tax_signed`
- **Label:** Tax Signed
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total`
- **Label:** Total
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total_in_currency_signed`
- **Label:** Total in Currency Signed
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total_signed`
- **Label:** Total Signed
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_total_words`
- **Label:** Amount total in words
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_untaxed`
- **Label:** Untaxed Amount
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `amount_untaxed_signed`
- **Label:** Untaxed Amount Signed
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_depreciated_value`
- **Label:** Cumulative Depreciation
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_depreciation_beginning_date`
- **Label:** Date of the beginning of the depreciation
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `asset_id`
- **Label:** Asset
- **Tipo:** many2one → account.asset
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.asset`

#### `asset_id_display_name`
- **Label:** Asset Id Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_ids`
- **Label:** Assets
- **Tipo:** one2many → account.asset
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.asset`

#### `asset_number_days`
- **Label:** Number of days
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `asset_remaining_value`
- **Label:** Depreciable Value
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `asset_value_change`
- **Label:** Asset Value Change
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `attachment_ids`
- **Label:** Attachments
- **Tipo:** one2many → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `ir.attachment`

#### `authorized_transaction_ids`
- **Label:** Authorized Transactions
- **Tipo:** many2many → payment.transaction
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `payment.transaction`

#### `auto_generated`
- **Label:** Auto Generated Document
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `auto_invoice_id`
- **Label:** Source Invoice
- **Tipo:** many2one → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `auto_post`
- **Label:** Auto-post
- **Tipo:** selection [no=No, at_date=At Date, monthly=Monthly, quarterly=Quarterly, yearly=Yearly]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['no', 'No'], ['at_date', 'At Date'], ['monthly', 'Monthly'], ['quarterly', 'Quarterly'], ['yearly', 'Yearly']]
- **Descrição:** Specify whether this entry is posted automatically on its accounting date, and any similar recurring invoices.

#### `auto_post_origin_id`
- **Label:** First recurring entry
- **Tipo:** many2one → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `auto_post_until`
- **Label:** Auto-post until
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** This recurring move will be posted up to and including this date.

#### `available_journal_ids`
- **Label:** Available Journal
- **Tipo:** many2many → account.journal
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.journal`
- **Valor Exemplo:** `[46 itens: [388, 1018, 1055]...]`

#### `available_partner_bank_ids`
- **Label:** Available Partner Bank
- **Tipo:** many2many → res.partner.bank
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner.bank`
- **Valor Exemplo:** `[]`

#### `available_payment_method_line_ids`
- **Label:** Available Payment Method Line
- **Tipo:** many2many → account.payment.method.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.payment.method.line`
- **Valor Exemplo:** `[151]`

#### `bank_partner_id`
- **Label:** Bank Partner
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`
- **Descrição:** Technical field to get the domain on the bank

#### `batch_payment_id`
- **Label:** Batch Payment
- **Tipo:** many2one → account.batch.payment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.batch.payment`

#### `campaign_id`
- **Label:** Campaign
- **Tipo:** many2one → utm.campaign
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `utm.campaign`
- **Descrição:** This is a name that helps you keep track of your different campaign efforts, e.g. Fall_Drive, Christmas_Special

#### `commercial_partner_id`
- **Label:** Commercial Entity
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`

#### `company_currency_id`
- **Label:** Company Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.currency`

#### `company_id`
- **Label:** Company
- **Tipo:** many2one → res.company
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.company`

#### `count_asset`
- **Label:** Count Asset
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `country_code`
- **Label:** Country Code
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The ISO country code in two chars. 
You can use this field for quick search.

#### `create_date`
- **Label:** Created on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `create_in_state_sale`
- **Label:** Situação do Pagamento
- **Tipo:** selection [draft=Draft, confirm=Confirm]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['draft', 'Draft'], ['confirm', 'Confirm']]

#### `create_uid`
- **Label:** Created by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `currency_id`
- **Label:** Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.currency`
- **Descrição:** The payment's currency.
- **Valor Exemplo:** `[6, 'BRL']`

#### `date`
- **Label:** Date
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Sim
- **Somente Leitura:** Não

#### `deferred_entry_type`
- **Label:** Deferred Entry Type
- **Tipo:** selection [expense=Deferred Expense, revenue=Deferred Revenue]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['expense', 'Deferred Expense'], ['revenue', 'Deferred Revenue']]

#### `deferred_move_ids`
- **Label:** Deferred Entries
- **Tipo:** many2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** The deferred entries created by this invoice

#### `deferred_original_move_ids`
- **Label:** Original Invoices
- **Tipo:** many2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** The original invoices that created the deferred entries

#### `delivery_date`
- **Label:** Delivery Date
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `depreciation_value`
- **Label:** Depreciation
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `destination_account_id`
- **Label:** Destination Account
- **Tipo:** many2one → account.account
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.account`
- **Valor Exemplo:** `[24801, '1120100001 CLIENTES NACIONAIS']`

#### `destination_journal_id`
- **Label:** Destination Journal
- **Tipo:** many2one → account.journal
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.journal`
- **Valor Exemplo:** `False`

#### `dfe_id`
- **Label:** Documento
- **Tipo:** many2one → l10n_br_ciel_it_account.dfe
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.dfe`

#### `direction_sign`
- **Label:** Direction Sign
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Multiplicator depending on the document type, to convert a price into a balance

#### `display_inactive_currency_warning`
- **Label:** Display Inactive Currency Warning
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `display_name`
- **Label:** Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `display_qr_code`
- **Label:** Display QR-code
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `draft_asset_exists`
- **Label:** Draft Asset Exists
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `duplicated_ref_ids`
- **Label:** Duplicated Ref
- **Tipo:** many2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `edi_blocking_level`
- **Label:** Edi Blocking Level
- **Tipo:** selection [info=Info, warning=Warning, error=Error]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['info', 'Info'], ['warning', 'Warning'], ['error', 'Error']]

#### `edi_document_ids`
- **Label:** Edi Document
- **Tipo:** one2many → account.edi.document
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.edi.document`

#### `edi_error_count`
- **Label:** Edi Error Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** How many EDIs are in error for this move?

#### `edi_error_message`
- **Label:** Edi Error Message
- **Tipo:** html
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_show_abandon_cancel_button`
- **Label:** Edi Show Abandon Cancel Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_show_cancel_button`
- **Label:** Edi Show Cancel Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_show_force_cancel_button`
- **Label:** Edi Show Force Cancel Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `edi_state`
- **Label:** Electronic invoicing
- **Tipo:** selection [to_send=To Send, sent=Sent, to_cancel=To Cancel, cancelled=Cancelled]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['to_send', 'To Send'], ['sent', 'Sent'], ['to_cancel', 'To Cancel'], ['cancelled', 'Cancelled']]
- **Descrição:** The aggregated state of all the EDIs with web-service of this move

#### `edi_web_services_to_process`
- **Label:** Edi Web Services To Process
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_attachment_id`
- **Label:** Extract Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `extract_can_show_banners`
- **Label:** Can show the ocr banners
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_can_show_send_button`
- **Label:** Can show the ocr send button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_detected_layout`
- **Label:** Extract Detected Layout Id
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_document_uuid`
- **Label:** ID of the request to IAP-OCR
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_error_message`
- **Label:** Error message
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_partner_name`
- **Label:** Extract Detected Partner Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_state`
- **Label:** Extract state
- **Tipo:** selection [no_extract_requested=No extract requested, not_enough_credit=Not enough credits, error_status=An error occurred, waiting_extraction=Waiting extraction, extract_not_ready=waiting extraction, but it is not ready... (+3)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['no_extract_requested', 'No extract requested'], ['not_enough_credit', 'Not enough credits'], ['error_status', 'An error occurred'], ['waiting_extraction', 'Waiting extraction'], ['extract_not_ready', 'waiting extraction, but it is not ready'], ['waiting_validation', 'Waiting validation'], ['to_validate', 'To validate'], ['done', 'Completed flow']]

#### `extract_state_processed`
- **Label:** Extract State Processed
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `extract_status`
- **Label:** Extract status
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `extract_word_ids`
- **Label:** Extract Word
- **Tipo:** one2many → account.invoice_extract.words
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.invoice_extract.words`

#### `fiscal_position_id`
- **Label:** Fiscal Position
- **Tipo:** many2one → account.fiscal.position
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.fiscal.position`
- **Descrição:** Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. The default value comes from the customer.

#### `force_release_to_pay`
- **Label:** Force Status
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Indicates whether the 'Should Be Paid' status is defined automatically or manually.

#### `has_message`
- **Label:** Has Message
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `True`

#### `has_reconciled_entries`
- **Label:** Has Reconciled Entries
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `hide_post_button`
- **Label:** Hide Post Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `highest_name`
- **Label:** Highest Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `id`
- **Label:** ID
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `17734`

#### `inalterable_hash`
- **Label:** Inalterability Hash
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `incoterm_location`
- **Label:** Incoterm Location
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_cash_rounding_id`
- **Label:** Cash Rounding Method
- **Tipo:** many2one → account.cash.rounding
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.cash.rounding`
- **Descrição:** Defines the smallest coinage of the currency that can be used to pay by cash.

#### `invoice_date`
- **Label:** Invoice/Bill Date
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_date_due`
- **Label:** Due Date
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_filter_type_domain`
- **Label:** Invoice Filter Type Domain
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_has_outstanding`
- **Label:** Invoice Has Outstanding
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_incoterm_id`
- **Label:** Tipo de Frete
- **Tipo:** many2one → account.incoterms
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.incoterms`
- **Descrição:** International Commercial Terms are a series of predefined commercial terms used in international transactions.

#### `invoice_line_ids`
- **Label:** Invoice lines
- **Tipo:** one2many → account.move.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`

#### `invoice_origin`
- **Label:** Origin
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** The document(s) that generated the invoice.

#### `invoice_outstanding_credits_debits_widget`
- **Label:** Invoice Outstanding Credits Debits Widget
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_partner_display_name`
- **Label:** Invoice Partner Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_payment_term_id`
- **Label:** Payment Terms
- **Tipo:** many2one → account.payment.term
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment.term`

#### `invoice_payments_widget`
- **Label:** Invoice Payments Widget
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `invoice_pdf_report_file`
- **Label:** PDF File
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_pdf_report_id`
- **Label:** PDF Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `invoice_source_email`
- **Label:** Source Email
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `invoice_user_id`
- **Label:** Salesperson
- **Tipo:** many2one → res.users
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.users`

#### `invoice_vendor_bill_id`
- **Label:** Vendor Bill
- **Tipo:** many2one → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** Auto-complete from a past bill.

#### `is_being_sent`
- **Label:** Is Being Sent
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Is the move being sent asynchronously

#### `is_donation`
- **Label:** Is Donation
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `is_encerramento`
- **Label:** Lançamento de Encerramento
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Indica se o lançamento é de encerramento do exercício.

#### `is_in_extractable_state`
- **Label:** Is In Extractable State
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `is_internal_transfer`
- **Label:** Internal Transfer
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Valor Exemplo:** `False`

#### `is_matched`
- **Label:** Is Matched With a Bank Statement
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `True`

#### `is_move_sent`
- **Label:** Is Move Sent
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** It indicates that the invoice/payment has been sent or the PDF has been generated.

#### `is_reconciled`
- **Label:** Is Reconciled
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `True`

#### `is_storno`
- **Label:** Is Storno
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `journal_id`
- **Label:** Journal
- **Tipo:** many2one → account.journal
- **Armazenado:** Não (calculado)
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Relacionamento:** `account.journal`

#### `l10n_br_arquivo_cobranca_escritural_id`
- **Label:** Arquivo Remessa Manual
- **Tipo:** many2one → l10n_br_ciel_it_account.arquivo.cobranca.escritural
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.arquivo.cobranca.escritural`

#### `l10n_br_calcular_imposto`
- **Label:** Calcular Impostos
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_carrier_id`
- **Label:** Carrier
- **Tipo:** many2one → delivery.carrier
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `delivery.carrier`

#### `l10n_br_cbs_valor`
- **Label:** Total do CBS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cfop_id`
- **Label:** CFOP
- **Tipo:** many2one → l10n_br_ciel_it_account.cfop
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.cfop`

#### `l10n_br_chave_nf`
- **Label:** Chave da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cnpj`
- **Label:** CNPJ
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cobranca_arquivo_remessa`
- **Label:** Arquivo Remessa Automática
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_data_desconto`
- **Label:** Data Limite p/ Desconto
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_idintegracao`
- **Label:** Id Integração
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_nossonumero`
- **Label:** Nosso Numero
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_parcela`
- **Label:** Parcela
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_protocolo`
- **Label:** Protocolo
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_situacao`
- **Label:** Situação
- **Tipo:** selection [SALVO=Salvo, PENDENTE_RETENTATIVA=Pendente, FALHA=Falha, EMITIDO=Emitido, REJEITADO=Rejeitado... (+3)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['SALVO', 'Salvo'], ['PENDENTE_RETENTATIVA', 'Pendente'], ['FALHA', 'Falha'], ['EMITIDO', 'Emitido'], ['REJEITADO', 'Rejeitado'], ['REGISTRADO', 'Registrado'], ['LIQUIDADO', 'Liquidado'], ['BAIXADO', 'Baixado']]

#### `l10n_br_cobranca_situacao_mensagem`
- **Label:** Mensagem
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cobranca_tipo_desconto`
- **Label:** Tipo Desconto
- **Tipo:** selection [0=0 - Sem instrução de desconto., 1=1 - Valor Fixo Até a Data Informada., 2=2 - Percentual Até a Data Informada., 3=3 - Valor por Antecipação Dia Corrido.., 4=4 - Valor por Antecipação Dia Útil.... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['0', '0 - Sem instrução de desconto.'], ['1', '1 - Valor Fixo Até a Data Informada.'], ['2', '2 - Percentual Até a Data Informada.'], ['3', '3 - Valor por Antecipação Dia Corrido..'], ['4', '4 - Valor por Antecipação Dia Útil.'], ['5', '5 - Percentual Sobre o Valor Nominal Dia Corrido.'], ['6', '6 - Percentual Sobre o Valor Nominal Dia Útil.']]

#### `l10n_br_cobranca_transmissao`
- **Label:** Tipo Transmissão
- **Tipo:** selection [webservice=Webservice / Ecommerce, automatico=Remessa Automática (VAN), manual=Remessa Manual (Internet Bank)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['webservice', 'Webservice / Ecommerce'], ['automatico', 'Remessa Automática (VAN)'], ['manual', 'Remessa Manual (Internet Bank)']]

#### `l10n_br_cobranca_valor_desconto`
- **Label:** Valor Desconto
- **Tipo:** float
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_cofins_ret_base`
- **Label:** Base do Cofins Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_ret_valor`
- **Label:** Valor do Cofins Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_valor`
- **Label:** Total do Cofins
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_valor_isento`
- **Label:** Total do Cofins (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cofins_valor_outros`
- **Label:** Total do Cofins (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_compra_indcom`
- **Label:** Destinação de Uso
- **Tipo:** selection [uso=Uso e Consumo, uso-prestacao=Uso na Prestação de Serviço, ind=Industrialização, com=Comercialização, ativo=Ativo... (+2)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['uso', 'Uso e Consumo'], ['uso-prestacao', 'Uso na Prestação de Serviço'], ['ind', 'Industrialização'], ['com', 'Comercialização'], ['ativo', 'Ativo'], ['garantia', 'Garantia'], ['out', 'Outros']]

#### `l10n_br_correcao`
- **Label:** Correção
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_csll_ret_base`
- **Label:** Base do CSLL Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_csll_ret_valor`
- **Label:** Valor do CSLL Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_csll_valor`
- **Label:** Total do CSLL
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_cstat_nf`
- **Label:** Status da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_dados_pagamento_count`
- **Label:** Dados de Pagamento (CNAB) Qty
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_dados_pagamento_data`
- **Label:** Data de Pagamento (CNAB)
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_dados_pagamento_id`
- **Label:** Dados de Pagamento (CNAB)
- **Tipo:** one2many → l10n_br_ciel_it_account.dados.pagamento
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.dados.pagamento`

#### `l10n_br_dados_pagamento_state`
- **Label:** Status CNAB
- **Tipo:** selection [CREATED=Criado, PAID=Pago, SCHEDULED=Agendado, CANCELLED=Cancelado, REJECTED=Rejeitado... (+2)]
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['CREATED', 'Criado'], ['PAID', 'Pago'], ['SCHEDULED', 'Agendado'], ['CANCELLED', 'Cancelado'], ['REJECTED', 'Rejeitado'], ['REFUNDED', 'Reembolsado'], ['STATEMENT', 'Extrato']]

#### `l10n_br_data_nfse_substituida`
- **Label:** Data de Emissão da NFS-e Substituida
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_data_saida`
- **Label:** Data/Hora de Saída
- **Tipo:** datetime
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_dctf_imposto_codigo`
- **Label:** Código do Imposto DCTF
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_desc_valor`
- **Label:** Total do Desconto
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_descricao_servico`
- **Label:** Descrição do Serviço
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_descricao_servico_show`
- **Label:** Mostrar Descrição do Serviço
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_despesas_acessorias`
- **Label:** Total da Despesas Acessórias
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_especie`
- **Label:** Espécie
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_fcp_dest_valor`
- **Label:** Total do Fundo de Combate a Pobreza
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_fcp_st_ant_valor`
- **Label:** Total do Fundo de Combate a Pobreza Retido Anteriormente por ST
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_fcp_st_valor`
- **Label:** Total do Fundo de Combate a Pobreza Retido por ST
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_frete`
- **Label:** Total do Frete
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_gnre_disponivel`
- **Label:** GNRE Disponível
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_gnre_numero_recibo`
- **Label:** GNRE - Número do Recibo
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_gnre_ok`
- **Label:** GNRE OK
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_handle_nfce`
- **Label:** Handle da Nota Fiscal Eletrônica ao Consumidor
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_handle_nfse`
- **Label:** Handle da Nota Fiscal de Serviço
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_ibs_mun_valor`
- **Label:** Total do IBS Município
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibs_uf_valor`
- **Label:** Total do IBS UF
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibs_valor`
- **Label:** Total do IBS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ibscbs_base`
- **Label:** Total da Base de Cálculo do IBS/CBS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_base`
- **Label:** Total da Base de Cálculo do ICMS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_dest_valor`
- **Label:** Total do ICMS UF Destino
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_remet_valor`
- **Label:** Total do ICMS UF Remetente
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor`
- **Label:** Total do ICMS (Tributável)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_credito_presumido`
- **Label:** Total do ICMS (Crédito Presumido)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_desonerado`
- **Label:** Total do ICMS (Desonerado)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_efetivo`
- **Label:** Total do ICMS (Efetivo)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_isento`
- **Label:** Total do ICMS (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icms_valor_outros`
- **Label:** Total do ICMS (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_base`
- **Label:** Total da Base de Cálculo do ICMSST
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_retido_valor`
- **Label:** Total do ICMSST Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_retido_valor_outros`
- **Label:** Total do ICMSST Retido (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_substituto_valor`
- **Label:** Total do ICMSST Substituto
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_substituto_valor_outros`
- **Label:** Total do ICMSST Substituto (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_valor`
- **Label:** Total do ICMSST
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_valor_outros`
- **Label:** Total do ICMSST (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_icmsst_valor_proprio`
- **Label:** Total do ICMSST (Próprio)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ii_valor`
- **Label:** Total do II
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ii_valor_aduaneira`
- **Label:** Total do II Aduaneira
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ii_valor_afrmm`
- **Label:** Total do II AFRMM
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_imposto_auto`
- **Label:** Calcular Impostos Automaticamente
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_indicador_presenca`
- **Label:** Indicador Presença
- **Tipo:** selection [0=0 - Não se aplica, 1=1 - Operação presencial, 2=2 - Operação não presencial, pela internet, 3=3 - Operação não presencial, teleatendimento, 4=4 - NFC-e em operação com entrega a domicílio... (+2)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['0', '0 - Não se aplica'], ['1', '1 - Operação presencial'], ['2', '2 - Operação não presencial, pela internet'], ['3', '3 - Operação não presencial, teleatendimento'], ['4', '4 - NFC-e em operação com entrega a domicílio'], ['5', '5 - Operação presencial, fora do estabelecimento'], ['9', '9 - Operação não presencial, outros']]

#### `l10n_br_informacao_complementar`
- **Label:** Informação Complementar
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_informacao_fiscal`
- **Label:** Informação Fiscal
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_inss_ret_base`
- **Label:** Base do INSS Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_inss_ret_valor`
- **Label:** Valor do INSS Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iof_valor`
- **Label:** Total do IOF
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ipi_valor`
- **Label:** Total do IPI
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ipi_valor_isento`
- **Label:** Total do IPI (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_ipi_valor_outros`
- **Label:** Total do IPI (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_irpj_ret_base`
- **Label:** Base do IRPJ Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_irpj_ret_valor`
- **Label:** Valor do IRPJ Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_irpj_valor`
- **Label:** Total do IRPJ
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_is_advanced`
- **Label:** Adiantamento?
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_is_valor`
- **Label:** Total do IS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iss_municipio_id`
- **Label:** Município de Incidência do ISS
- **Tipo:** many2one → l10n_br_ciel_it_account.res.municipio
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.res.municipio`

#### `l10n_br_iss_ret_base`
- **Label:** Base do ISS Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iss_ret_valor`
- **Label:** Valor do ISS Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_iss_valor`
- **Label:** Total do ISS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_item_pedido_compra`
- **Label:** Item Pedido de Compra do Cliente
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_local_despacho`
- **Label:** Local de despacho
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_local_embarque`
- **Label:** Local de embarque
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_marca`
- **Label:** Marca
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_motivo`
- **Label:** Motivo Cancelamento
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_municipio_fim_id`
- **Label:** Município de Destino
- **Tipo:** many2one → l10n_br_ciel_it_account.res.municipio
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.res.municipio`

#### `l10n_br_municipio_inicio_id`
- **Label:** Município de Origem
- **Tipo:** many2one → l10n_br_ciel_it_account.res.municipio
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.res.municipio`

#### `l10n_br_nfe_emails`
- **Label:** Email XML NF-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_nfse_substituta`
- **Label:** NFS-e Substituta?
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numeracao_volume`
- **Label:** Númeração Volume
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_numero_nf`
- **Label:** Número da Nota Fiscal de Mercadoria
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nfce`
- **Label:** Número da Nota Fiscal Eletrônica ao Consumidor
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nfse`
- **Label:** Número da Nota Fiscal de Serviço
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nfse_substituida`
- **Label:** Número da NFS-e Substituida
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_nota_fiscal`
- **Label:** Número da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_numero_rps`
- **Label:** Número RPS
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_numero_rps_substituido`
- **Label:** Número RPS Substituido
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_operacao_consumidor`
- **Label:** Operação Consumidor Final
- **Tipo:** selection [0=0 - Normal, 1=1 - Consumidor Final]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['0', '0 - Normal'], ['1', '1 - Consumidor Final']]

#### `l10n_br_operacao_id`
- **Label:** Operação
- **Tipo:** many2one → l10n_br_ciel_it_account.operacao
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.operacao`

#### `l10n_br_paga`
- **Label:** Parcela Paga?
- **Tipo:** boolean
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_aut_gnre`
- **Label:** GNRE
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_aut_gnre_fname`
- **Label:** Arquivo GNRE
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_aut_nfe`
- **Label:** DANFE NF-e
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_aut_nfe_fname`
- **Label:** Arquivo DANFE NF-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_boleto`
- **Label:** Boleto
- **Tipo:** binary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_boleto_fname`
- **Label:** Arquivo Boleto
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_can_nfe`
- **Label:** DANFE NF-e Cancelamento
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_can_nfe_fname`
- **Label:** Arquivo DANFE NF-e Cancelamento
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pdf_cce_nfe`
- **Label:** DANFE CC-e
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_pdf_cce_nfe_fname`
- **Label:** Arquivo DANFE CC-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pedido_compra`
- **Label:** Pedido de Compra do Cliente
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_peso_bruto`
- **Label:** Peso Bruto
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_peso_liquido`
- **Label:** Peso Líquido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_ret_base`
- **Label:** Base do PIS Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_ret_valor`
- **Label:** Valor do PIS Retido
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_valor`
- **Label:** Total do PIS
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_valor_isento`
- **Label:** Total do PIS (Isento/Não Tributável)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_pis_valor_outros`
- **Label:** Total do PIS (Outros)
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_prod_valor`
- **Label:** Total dos Produtos
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_rateio_frete_auto`
- **Label:** Rateio Frete Automatico
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_seguro`
- **Label:** Total do Seguro
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_sequencia_evento`
- **Label:** Sequencia Evento NF-e
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_serie_nf`
- **Label:** Série da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_serie_nf_substituido`
- **Label:** Série NFS-e Substituido
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_show_nfe_btn`
- **Label:** Mostrar botão NF-e
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_situacao_nf`
- **Label:** Situação NF-e
- **Tipo:** selection [rascunho=Rascunho, autorizado=Autorizado, excecao_autorizado=Exceção, cce=Carta de Correção, excecao_cce=Exceção... (+2)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['rascunho', 'Rascunho'], ['autorizado', 'Autorizado'], ['excecao_autorizado', 'Exceção'], ['cce', 'Carta de Correção'], ['excecao_cce', 'Exceção'], ['cancelado', 'Cancelado'], ['excecao_cancelado', 'Exceção']]

#### `l10n_br_tipo_documento`
- **Label:** Tipo Documento Fiscal
- **Tipo:** selection [NFS=Nota Fiscal de Serviços Instituída por Municípios, NFSE=Nota Fiscal de Serviços Eletrônica - NFS-e, NDS=Nota de Débito de Serviços, FAT=Fatura, ND=Nota de Débito... (+32)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['NFS', 'Nota Fiscal de Serviços Instituída por Municípios'], ['NFSE', 'Nota Fiscal de Serviços Eletrônica - NFS-e'], ['NDS', 'Nota de Débito de Serviços'], ['FAT', 'Fatura'], ['ND', 'Nota de Débito'], ['01', 'Nota Fiscal'], ['1B', 'Nota Fiscal Avulsa'], ['02', 'Nota Fiscal de Venda a Consumidor'], ['2D', 'Cupom Fiscal'], ['2E', 'Cupom Fiscal Bilhete de Passagem'], ['04', 'Nota Fiscal de Produtor'], ['06', 'Nota Fiscal/Conta de Energia Elétrica'], ['07', 'Nota Fiscal de Serviço de Transporte'], ['08', 'Conhecimento de Transporte Rodoviário de Cargas'], ['8B', 'Conhecimento de Transporte de Cargas Avulso'], ['09', 'Conhecimento de Transporte Aquaviário de Cargas'], ['10', 'Conhecimento Aéreo'], ['11', 'Conhecimento de Transporte Ferroviário de Cargas'], ['13', 'Bilhete de Passagem Rodoviário'], ['14', 'Bilhete de Passagem Aquaviário'], ['15', 'Bilhete de Passagem e Nota de Bagagem'], ['16', 'Bilhete de Passagem Ferroviário'], ['18', 'Resumo de Movimento Diário'], ['21', 'Nota Fiscal de Serviço de Comunicação'], ['22', 'Nota Fiscal de Serviço de Telecomunicação'], ['26', 'Conhecimento de Transporte Multimodal de Cargas'], ['27', 'Nota Fiscal De Transporte Ferroviário De Carga'], ['28', 'Nota Fiscal/Conta de Fornecimento de Gás Canalizado'], ['29', 'Nota Fiscal/Conta de Fornecimento de Água Canalizada'], ['55', 'Nota Fiscal Eletrônica (NF-e)'], ['57', 'Conhecimento de Transporte Eletrônico (CT-e)'], ['59', 'Cupom Fiscal Eletrônico (CF-e-SAT)'], ['60', 'Cupom Fiscal Eletrônico (CF-e-ECF)'], ['63', 'Bilhete de Passagem Eletrônico (BP-e)'], ['65', 'Nota Fiscal Eletrônica ao Consumidor Final (NFC-e)'], ['66', 'Nota Fiscal de Energia Elétrica Eletrônica - NF3e'], ['67', 'Conhecimento de Transporte Eletrônico (CT-e OS)']]

#### `l10n_br_tipo_imposto`
- **Label:** Tipo Imposto
- **Tipo:** selection [cofins=COFINS, csll=CSLL, icms=ICMS, ii=II, inss=INSS... (+7)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['cofins', 'COFINS'], ['csll', 'CSLL'], ['icms', 'ICMS'], ['ii', 'II'], ['inss', 'INSS'], ['ipi', 'IPI'], ['irrf', 'IRRF'], ['iss', 'ISS'], ['pis', 'PIS'], ['simples', 'Simples Nacional'], ['icmsst', 'ICMS ST'], ['fgts', 'FGTS']]

#### `l10n_br_tipo_pedido`
- **Label:** Tipo de Pedido (saída)
- **Tipo:** selection [baixa-estoque=Saída: Baixa de Estoque, complemento-valor=Saída: Complemento de Preço, dev-comodato=Saída: Devolução de Comodato, compra=Saída: Devolução de Compra, dev-conserto=Saída: Devolução de Conserto... (+42)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['baixa-estoque', 'Saída: Baixa de Estoque'], ['complemento-valor', 'Saída: Complemento de Preço'], ['dev-comodato', 'Saída: Devolução de Comodato'], ['compra', 'Saída: Devolução de Compra'], ['dev-conserto', 'Saída: Devolução de Conserto'], ['dev-consignacao', 'Saída: Devolução de Consignação'], ['dev-demonstracao', 'Saída: Devolução de Demonstração'], ['dev-industrializacao', 'Saída: Devolução de Industrialização'], ['dev-locacao', 'Saída: Devolução de Locação'], ['dev-mostruario', 'Saída: Devolução de Mostruário'], ['dev-teste', 'Saída: Devolução de Teste'], ['dev-vasilhame', 'Saída: Devolução de Vasilhame'], ['venda-locacao', 'Saída: Locação'], ['outro', 'Saída: Outros'], ['perda', 'Saída: Perda'], ['mostruario', 'Saída: Remessa de Mostruário'], ['vasilhame', 'Saída: Remessa de Vasilhame'], ['rem-venda-futura', 'Saída: Remessa de Venda p/ Entrega Futura'], ['ativo-fora', 'Saída: Remessa de bem do ativo imobilizado p/ uso Fora do Estabelecimento'], ['comodato', 'Saída: Remessa em Comodato'], ['consignacao', 'Saída: Remessa em Consignação'], ['garantia', 'Saída: Remessa em Garantia'], ['amostra', 'Saída: Remessa p/ Amostra Grátis'], ['bonificacao', 'Saída: Remessa p/ Bonificação'], ['conserto', 'Saída: Remessa p/ Conserto'], ['demonstracao', 'Saída: Remessa p/ Demonstração'], ['deposito', 'Saída: Remessa p/ Depósito'], ['exportacao', 'Saída: Remessa p/ Exportação'], ['feira', 'Saída: Remessa p/ Feira'], ['fora', 'Saída: Remessa p/ Fora do Estabelecimento'], ['industrializacao', 'Saída: Remessa p/ Industrialização'], ['rem-obra', 'Saída: Remessa p/ Obra'], ['teste', 'Saída: Remessa p/ Teste'], ['troca', 'Saída: Remessa p/ Troca'], ['uso-prestacao', 'Saída: Remessa p/ Uso na Prestação de Serviço'], ['locacao', 'Saída: Remessa para Locação'], ['rem-conta-ordem', 'Saída: Remessa por Conta e Ordem'], ['transf-filial', 'Saída: Transferencia entre Filiais'], ['venda', 'Saída: Venda'], ['venda-nfce', 'Saída: Venda Cupom Fiscal'], ['venda-armazem', 'Saída: Venda de Armazém Externo'], ['venda-industrializacao', 'Saída: Venda de Industrialização'], ['servico', 'Saída: Venda de Serviço'], ['venda-consignacao', 'Saída: Venda em Consignação'], ['venda_futura', 'Saída: Venda p/ Entrega Futura'], ['venda-conta-ordem', 'Saída: Venda por Conta e Ordem'], ['venda-conta-ordem-vendedor', 'Saída: Venda por Conta e Ordem por Vendedor']]

#### `l10n_br_tipo_pedido_entrada`
- **Label:** Tipo de Pedido (entrada)
- **Tipo:** selection [ent-amostra=Entrada: Amostra Grátis, ent-bonificacao=Entrada: Bonificação, ent-comodato=Entrada: Comodato, comp-importacao=Entrada: Complementar de Importação, compra=Entrada: Compra... (+33)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['ent-amostra', 'Entrada: Amostra Grátis'], ['ent-bonificacao', 'Entrada: Bonificação'], ['ent-comodato', 'Entrada: Comodato'], ['comp-importacao', 'Entrada: Complementar de Importação'], ['compra', 'Entrada: Compra'], ['compra-venda-ordem', 'Entrada: Compra Venda à Ordem'], ['compra-ent-futura', 'Entrada: Compra p/ Entrega Futura'], ['ent-conserto', 'Entrada: Conserto'], ['credito-imposto', 'Entrada: Crédito de Imposto'], ['ent-demonstracao', 'Entrada: Demonstração'], ['devolucao', 'Entrada: Devolução Emissão Própria'], ['devolucao_compra', 'Entrada: Devolução de Venda'], ['importacao', 'Entrada: Importação'], ['locacao', 'Entrada: Locação'], ['ent-mostruario', 'Entrada: Mostruário'], ['outro', 'Entrada: Outros'], ['retorno', 'Entrada: Outros Retorno'], ['compra-rec-venda-ordem', 'Entrada: Recebimento de Compra Venda à Ordem'], ['compra-rec-ent-futura', 'Entrada: Recebimento de Compra p/ Entrega Futura'], ['rem-industrializacao', 'Entrada: Remessa p/ Industrialização'], ['rem-conta-ordem', 'Entrada: Remessa por Conta e Ordem'], ['comodato', 'Entrada: Retorno de Comodato'], ['conserto', 'Entrada: Retorno de Conserto'], ['consignacao', 'Entrada: Retorno de Consignação'], ['demonstracao', 'Entrada: Retorno de Demonstração'], ['deposito', 'Entrada: Retorno de Depósito'], ['feira', 'Entrada: Retorno de Feira'], ['industrializacao', 'Entrada: Retorno de Industrialização'], ['ret-locacao', 'Entrada: Retorno de Locação'], ['mostruario', 'Entrada: Retorno de Mostruário'], ['troca', 'Entrada: Retorno de Troca'], ['vasilhame', 'Entrada: Retorno de Vasilhame'], ['ativo-fora', 'Entrada: Retorno de bem do ativo imobilizado p/ uso Fora do Estabelecimento'], ['servico', 'Entrada: Serviço'], ['serv-industrializacao', 'Entrada: Serviço de Industrialização'], ['transf-filial', 'Entrada: Transferencia entre Filiais'], ['importacao-transporte', 'Entrada: Transporte de Importação'], ['ent-vasilhame', 'Entrada: Vasilhame']]

#### `l10n_br_total_nfe`
- **Label:** Total da Nota Fiscal
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_total_tributos`
- **Label:** Total dos Tributos
- **Tipo:** float
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_uf_saida_pais`
- **Label:** Sigla UF de Saída
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_veiculo_placa`
- **Label:** Placa
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_veiculo_rntc`
- **Label:** RNTC
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_veiculo_uf`
- **Label:** UF da Placa
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_volumes`
- **Label:** Volumes
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xml_aut_nfe`
- **Label:** XML NF-e
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_xml_aut_nfe_fname`
- **Label:** Arquivo XML NF-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xml_can_nfe`
- **Label:** XML NF-e Cancelamento
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_xml_can_nfe_fname`
- **Label:** Arquivo XML NF-e Cancelamento
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xml_cce_nfe`
- **Label:** XML CC-e
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `l10n_br_xml_cce_nfe_fname`
- **Label:** Arquivo XML CC-e
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `l10n_br_xmotivo_nf`
- **Label:** Situação da Nota Fiscal
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `landed_costs_ids`
- **Label:** Landed Costs
- **Tipo:** one2many → stock.landed.cost
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.landed.cost`

#### `landed_costs_visible`
- **Label:** Landed Costs Visible
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `laudos`
- **Label:** Laudos
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `laudos_filename`
- **Label:** Nome do arquivo de laudos
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `line_ids`
- **Label:** Journal Items
- **Tipo:** one2many → account.move.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`

#### `made_sequence_hole`
- **Label:** Made Sequence Hole
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `medium_id`
- **Label:** Medium
- **Tipo:** many2one → utm.medium
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `utm.medium`
- **Descrição:** This is the method of delivery, e.g. Postcard, Email, or Banner Ad

#### `message_attachment_count`
- **Label:** Attachment Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `0`

#### `message_follower_ids`
- **Label:** Followers
- **Tipo:** one2many → mail.followers
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.followers`
- **Valor Exemplo:** `[2577513]`

#### `message_has_error`
- **Label:** Message Delivery error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, some messages have a delivery error.
- **Valor Exemplo:** `False`

#### `message_has_error_counter`
- **Label:** Number of errors
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Number of messages with delivery error
- **Valor Exemplo:** `0`

#### `message_has_sms_error`
- **Label:** SMS Delivery error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, some messages have a delivery error.
- **Valor Exemplo:** `False`

#### `message_ids`
- **Label:** Messages
- **Tipo:** one2many → mail.message
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.message`
- **Valor Exemplo:** `[12417805]`

#### `message_is_follower`
- **Label:** Is Follower
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `message_main_attachment_id`
- **Label:** Main Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `ir.attachment`
- **Valor Exemplo:** `False`

#### `message_needaction`
- **Label:** Action Needed
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If checked, new messages require your attention.
- **Valor Exemplo:** `False`

#### `message_needaction_counter`
- **Label:** Number of Actions
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Number of messages requiring action
- **Valor Exemplo:** `0`

#### `message_partner_ids`
- **Label:** Followers (Partners)
- **Tipo:** many2many → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`
- **Valor Exemplo:** `[207026]`

#### `move_id`
- **Label:** Journal Entry
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`
- **Valor Exemplo:** `[416054, 'PDEVOL/2025/00298 (VND/2025/05333)']`

#### `move_type`
- **Label:** Type
- **Tipo:** selection [entry=Journal Entry, out_invoice=Customer Invoice, out_refund=Customer Credit Note, in_invoice=Vendor Bill, in_refund=Vendor Credit Note... (+2)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Sim
- **Somente Leitura:** Sim
- **Opções:** [['entry', 'Journal Entry'], ['out_invoice', 'Customer Invoice'], ['out_refund', 'Customer Credit Note'], ['in_invoice', 'Vendor Bill'], ['in_refund', 'Vendor Credit Note'], ['out_receipt', 'Sales Receipt'], ['in_receipt', 'Purchase Receipt']]

#### `my_activity_date_deadline`
- **Label:** My Activity Deadline
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `name`
- **Label:** Number
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `narration`
- **Label:** Terms and Conditions
- **Tipo:** html
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `need_cancel_request`
- **Label:** Need Cancel Request
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `needed_terms`
- **Label:** Needed Terms
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `needed_terms_dirty`
- **Label:** Needed Terms Dirty
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `outstanding_account_id`
- **Label:** Outstanding Account
- **Tipo:** many2one → account.account
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.account`
- **Valor Exemplo:** `[22246, '1120900002 ( - ) DEVOLUCOES A COMPENSAR']`

#### `paired_internal_transfer_payment_id`
- **Label:** Paired Internal Transfer Payment
- **Tipo:** many2one → account.payment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment`
- **Descrição:** When an internal transfer is posted, a paired payment is created. They are cross referenced through this field
- **Valor Exemplo:** `False`

#### `parcelas_manual_id`
- **Label:** Parcelas Personalizada
- **Tipo:** many2one → l10n_br_ciel_it_account.payment.parcela.manual
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `l10n_br_ciel_it_account.payment.parcela.manual`

#### `partner_bank_id`
- **Label:** Recipient Bank Account
- **Tipo:** many2one → res.partner.bank
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner.bank`
- **Valor Exemplo:** `False`

#### `partner_contact_id`
- **Label:** Contato
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`

#### `partner_credit`
- **Label:** Partner Credit
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `partner_credit_warning`
- **Label:** Partner Credit Warning
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `partner_id`
- **Label:** Customer/Vendor
- **Tipo:** many2one → res.partner
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`
- **Valor Exemplo:** `[205205, 'REDE ASSAI LJ 336']`

#### `partner_invoice_id`
- **Label:** Endereço de Cobrança
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.partner`

#### `partner_shipping_id`
- **Label:** Delivery Address
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`
- **Descrição:** The delivery address will be used in the computation of the fiscal position.

#### `partner_type`
- **Label:** Partner Type
- **Tipo:** selection [customer=Customer, supplier=Vendor]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['customer', 'Customer'], ['supplier', 'Vendor']]
- **Valor Exemplo:** `'customer'`

#### `payment_id`
- **Label:** Payment
- **Tipo:** many2one → account.payment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment`

#### `payment_ids`
- **Label:** Payments
- **Tipo:** one2many → account.payment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment`

#### `payment_line_ids`
- **Label:** Payment lines
- **Tipo:** many2many → account.move.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move.line`

#### `payment_method_code`
- **Label:** Code
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `payment_method_id`
- **Label:** Method
- **Tipo:** many2one → account.payment.method
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.payment.method`
- **Valor Exemplo:** `[1, 'Manual']`

#### `payment_method_line_id`
- **Label:** Payment Method
- **Tipo:** many2one → account.payment.method.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.payment.method.line`
- **Descrição:** Manual: Pay or Get paid by any method outside of Odoo.
Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.
Check: Pay bills by check and print it from Odoo.
Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.
SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.
SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.

- **Valor Exemplo:** `[151, 'Manual']`

#### `payment_method_name`
- **Label:** Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `payment_provider_id`
- **Label:** Forma de Pagamento
- **Tipo:** many2one → payment.provider
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `payment.provider`

#### `payment_reference`
- **Label:** Payment Reference
- **Tipo:** char
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Reference of the document used to issue this payment. Eg. check number, file name, etc.
- **Valor Exemplo:** `False`

#### `payment_state`
- **Label:** Payment Status
- **Tipo:** selection [not_paid=Not Paid, in_payment=In Payment, paid=Paid, partial=Partially Paid, reversed=Reversed... (+1)]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['not_paid', 'Not Paid'], ['in_payment', 'In Payment'], ['paid', 'Paid'], ['partial', 'Partially Paid'], ['reversed', 'Reversed'], ['invoicing_legacy', 'Invoicing App Legacy']]

#### `payment_state_before_switch`
- **Label:** Payment State Before Switch
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `payment_term_details`
- **Label:** Payment Term Details
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `payment_token_id`
- **Label:** Saved Payment Token
- **Tipo:** many2one → payment.token
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `payment.token`
- **Descrição:** Note that only tokens from providers allowing to capture the amount are available.

#### `payment_transaction_id`
- **Label:** Payment Transaction
- **Tipo:** many2one → payment.transaction
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `payment.transaction`

#### `payment_type`
- **Label:** Payment Type
- **Tipo:** selection [outbound=Send, inbound=Receive]
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Opções:** [['outbound', 'Send'], ['inbound', 'Receive']]
- **Valor Exemplo:** `'inbound'`

#### `picking_ids`
- **Label:** Picking References
- **Tipo:** many2many → stock.picking
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.picking`

#### `picking_ok`
- **Label:** Picking OK
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `posted_before`
- **Label:** Posted Before
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `purchase_id`
- **Label:** Purchase Order
- **Tipo:** many2one → purchase.order
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `purchase.order`
- **Descrição:** Auto-complete from a past purchase order.

#### `purchase_order_count`
- **Label:** Purchase Order Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `purchase_vendor_bill_id`
- **Label:** Auto-complete
- **Tipo:** many2one → purchase.bill.union
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `purchase.bill.union`
- **Descrição:** Auto-complete from a past bill / purchase order.

#### `qr_code`
- **Label:** QR Code URL
- **Tipo:** html
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `False`

#### `qr_code_method`
- **Label:** Payment QR-code
- **Tipo:** selection
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Type of QR-code to be generated for the payment of this invoice, when printing it. If left blank, the first available and usable method will be used.

#### `quick_edit_mode`
- **Label:** Quick Edit Mode
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `quick_edit_total_amount`
- **Label:** Total (Tax inc.)
- **Tipo:** monetary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Use this field to encode the total amount of the invoice.
Odoo will automatically create one invoice line with default values to match it.

#### `quick_encoding_vals`
- **Label:** Quick Encoding Vals
- **Tipo:** json
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `rating_ids`
- **Label:** Ratings
- **Tipo:** one2many → rating.rating
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `rating.rating`
- **Valor Exemplo:** `[]`

#### `reconciled_bill_ids`
- **Label:** Reconciled Bills
- **Tipo:** many2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`
- **Descrição:** Invoices whose journal items have been reconciled with these payments.
- **Valor Exemplo:** `[]`

#### `reconciled_bills_count`
- **Label:** # Reconciled Bills
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reconciled_invoice_ids`
- **Label:** Reconciled Invoices
- **Tipo:** many2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`
- **Descrição:** Invoices whose journal items have been reconciled with these payments.
- **Valor Exemplo:** `[412760]`

#### `reconciled_invoices_count`
- **Label:** # Reconciled Invoices
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `1`

#### `reconciled_invoices_type`
- **Label:** Reconciled Invoices Type
- **Tipo:** selection [credit_note=Credit Note, invoice=Invoice]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['credit_note', 'Credit Note'], ['invoice', 'Invoice']]
- **Valor Exemplo:** `'invoice'`

#### `reconciled_statement_line_ids`
- **Label:** Reconciled Statement Lines
- **Tipo:** many2many → account.bank.statement.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.bank.statement.line`
- **Descrição:** Statements lines matched to this payment

#### `reconciled_statement_lines_count`
- **Label:** # Reconciled Statement Lines
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `ref`
- **Label:** Reference
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `referencia_ids`
- **Label:** NF-e referência
- **Tipo:** one2many → l10n_br_ciel_it_account.account.move.referencia
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.account.move.referencia`

#### `refunds_count`
- **Label:** Refunds Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2010_count`
- **Label:** REINF 2010 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2010_ids`
- **Label:** REINF 2010
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.2010
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.2010`

#### `reinfs_2020_count`
- **Label:** REINF 2020 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2020_ids`
- **Label:** REINF 2020
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.2020
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.2020`

#### `reinfs_2060_count`
- **Label:** REINF 2060 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_2060_ids`
- **Label:** REINF 2060
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.2060
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.2060`

#### `reinfs_4010_count`
- **Label:** REINF 4010 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_4010_ids`
- **Label:** REINF 4010
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.4010
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.4010`

#### `reinfs_4020_count`
- **Label:** REINF 4020 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_4020_ids`
- **Label:** REINF 4020
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.4020
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.4020`

#### `reinfs_4080_count`
- **Label:** REINF 4080 Qtd.
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `reinfs_4080_ids`
- **Label:** REINF 4080
- **Tipo:** one2many → l10n_br_ciel_it_account.reinf.4080
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `l10n_br_ciel_it_account.reinf.4080`

#### `release_to_pay`
- **Label:** Release To Pay
- **Tipo:** selection [yes=Yes, no=No, exception=Exception]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['yes', 'Yes'], ['no', 'No'], ['exception', 'Exception']]
- **Descrição:** This field can take the following values :
  * Yes: you should pay the bill, you have received the products
  * No, you should not pay the bill, you have not received the products
  * Exception, there is a difference between received and billed quantities
This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.

#### `release_to_pay_manual`
- **Label:** Should Be Paid
- **Tipo:** selection [yes=Yes, no=No, exception=Exception]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Opções:** [['yes', 'Yes'], ['no', 'No'], ['exception', 'Exception']]
- **Descrição:**   * Yes: you should pay the bill, you have received the products
  * No, you should not pay the bill, you have not received the products
  * Exception, there is a difference between received and billed quantities
This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.

#### `require_partner_bank_account`
- **Label:** Require Partner Bank Account
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `restrict_mode_hash_table`
- **Label:** Lock Posted Entries with Hash
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** If ticked, the accounting entry or invoice receives a hash as soon as it is posted and cannot be modified anymore.

#### `reversal_move_id`
- **Label:** Reversal Move
- **Tipo:** one2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`

#### `reversed_entry_id`
- **Label:** Reversal of
- **Tipo:** many2one → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`

#### `sale_id`
- **Label:** Pedido de Venda
- **Tipo:** many2one → sale.order
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `sale.order`

#### `sale_order_count`
- **Label:** Sale Order Count
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `secure_sequence_number`
- **Label:** Inalteralbility No Gap Sequence #
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `send_and_print_values`
- **Label:** Send And Print Values
- **Tipo:** json
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `sequence_number`
- **Label:** Sequence Number
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `sequence_prefix`
- **Label:** Sequence Prefix
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_delivery_date`
- **Label:** Show Delivery Date
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_discount_details`
- **Label:** Show Discount Details
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_name_warning`
- **Label:** Show Name Warning
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `show_partner_bank_account`
- **Label:** Show Partner Bank Account
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_payment_term_details`
- **Label:** Show Payment Term Details
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_reset_to_draft_button`
- **Label:** Show Reset To Draft Button
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `show_update_fpos`
- **Label:** Has Fiscal Position Changed
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `simples_nacional`
- **Label:** Emitente Simples Nacional
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `source_id`
- **Label:** Source
- **Tipo:** many2one → utm.source
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `utm.source`
- **Descrição:** This is the source of the link, e.g. Search Engine, another domain, or name of email list

#### `source_payment_id`
- **Label:** Source Payment
- **Tipo:** many2one → account.payment
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.payment`
- **Descrição:** The source payment of related refund payments

#### `state`
- **Label:** Status
- **Tipo:** selection [draft=Draft, posted=Posted, cancel=Cancelled]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Sim
- **Somente Leitura:** Sim
- **Opções:** [['draft', 'Draft'], ['posted', 'Posted'], ['cancel', 'Cancelled']]

#### `statement_id`
- **Label:** Statement
- **Tipo:** many2one → account.bank.statement
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.bank.statement`

#### `statement_line_id`
- **Label:** Statement Line
- **Tipo:** many2one → account.bank.statement.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.bank.statement.line`

#### `statement_line_ids`
- **Label:** Statements
- **Tipo:** one2many → account.bank.statement.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.bank.statement.line`

#### `stock_move_id`
- **Label:** Stock Move
- **Tipo:** many2one → stock.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.move`

#### `stock_valuation_layer_ids`
- **Label:** Stock Valuation Layer
- **Tipo:** one2many → stock.valuation.layer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `stock.valuation.layer`

#### `string_to_hash`
- **Label:** String To Hash
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `suitable_journal_ids`
- **Label:** Suitable Journal
- **Tipo:** many2many → account.journal
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.journal`

#### `suitable_payment_token_ids`
- **Label:** Suitable Payment Token
- **Tipo:** many2many → payment.token
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `payment.token`

#### `suspense_statement_line_id`
- **Label:** Request document from a bank statement line
- **Tipo:** many2one → account.bank.statement.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.bank.statement.line`

#### `tax_calculation_rounding_method`
- **Label:** Tax calculation rounding method
- **Tipo:** selection [round_per_line=Round per Line, round_globally=Round Globally]
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Opções:** [['round_per_line', 'Round per Line'], ['round_globally', 'Round Globally']]

#### `tax_cash_basis_created_move_ids`
- **Label:** Cash Basis Entries
- **Tipo:** one2many → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Descrição:** The cash basis entries created from the taxes on this entry, when reconciling its lines.

#### `tax_cash_basis_origin_move_id`
- **Label:** Cash Basis Origin
- **Tipo:** many2one → account.move
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.move`
- **Descrição:** The journal entry from which this tax cash basis journal entry has been created.

#### `tax_cash_basis_rec_id`
- **Label:** Tax Cash Basis Entry of
- **Tipo:** many2one → account.partial.reconcile
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.partial.reconcile`

#### `tax_closing_alert`
- **Label:** Tax Closing Alert
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_closing_end_date`
- **Label:** Tax Closing End Date
- **Tipo:** date
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `tax_closing_show_multi_closing_warning`
- **Label:** Tax Closing Show Multi Closing Warning
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_country_code`
- **Label:** Tax Country Code
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_country_id`
- **Label:** Tax Country
- **Tipo:** many2one → res.country
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.country`

#### `tax_lock_date_message`
- **Label:** Tax Lock Date Message
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `tax_report_control_error`
- **Label:** Tax Report Control Error
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `tax_totals`
- **Label:** Invoice Totals
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Edit Tax amounts if you encounter rounding issues.

#### `team_id`
- **Label:** Sales Team
- **Tipo:** many2one → crm.team
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `crm.team`

#### `timesheet_count`
- **Label:** Number of timesheets
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `timesheet_encode_uom_id`
- **Label:** Timesheet Encoding Unit
- **Tipo:** many2one → uom.uom
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `uom.uom`

#### `timesheet_ids`
- **Label:** Timesheets
- **Tipo:** one2many → account.analytic.line
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `account.analytic.line`

#### `timesheet_total_duration`
- **Label:** Timesheet Total Duration
- **Tipo:** integer
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Descrição:** Total recorded duration, expressed in the encoding UoM, and rounded to the unit

#### `to_check`
- **Label:** To Check
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** If this checkbox is ticked, it means that the user was not sure of all the related information at the time of the creation of the move and that the move needs to be checked again.

#### `transaction_ids`
- **Label:** Transactions
- **Tipo:** many2many → payment.transaction
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `payment.transaction`

#### `transfer_model_id`
- **Label:** Originating Model
- **Tipo:** many2one → account.transfer.model
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.transfer.model`

#### `type_name`
- **Label:** Type Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `ubl_cii_xml_file`
- **Label:** UBL/CII File
- **Tipo:** binary
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não

#### `ubl_cii_xml_id`
- **Label:** Attachment
- **Tipo:** many2one → ir.attachment
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `ir.attachment`

#### `use_electronic_payment_method`
- **Label:** Use Electronic Payment Method
- **Tipo:** boolean
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `user_id`
- **Label:** User
- **Tipo:** many2one → res.users
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `usuario_id`
- **Label:** Usuário
- **Tipo:** many2one → res.partner
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.partner`

#### `website_message_ids`
- **Label:** Website Messages
- **Tipo:** one2many → mail.message
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `mail.message`
- **Descrição:** Website communication history
- **Valor Exemplo:** `[]`

#### `write_date`
- **Label:** Last Updated on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim

#### `write_uid`
- **Label:** Last Updated by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`

#### `x_studio_observao_interna`
- **Label:** Observação Interna
- **Tipo:** text
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Não



================================================================================
## account.partial.reconcile
**Descrição:** Reconciliações parciais - vincula débito com crédito
================================================================================

**Total de campos:** 18

**Exemplo encontrado:** ID = 202

### CAMPOS:

| # | Campo | Tipo | Label | Armazenado | Obrigatório | Valor Exemplo |
|---|-------|------|-------|------------|-------------|---------------|
| 1 | `amount` | monetary | Amount | ✅ | ❌ | 5068.3 |
| 2 | `company_currency_id` | many2one → res.currency | Company Currency | ❌ | ❌ | [6, 'BRL'] |
| 3 | `company_id` | many2one → res.company | Company | ✅ | ❌ | [1, 'NACOM GOYA - FB'] |
| 4 | `create_date` | datetime | Created on | ✅ | ❌ | '2024-08-01 21:03:09' |
| 5 | `create_uid` | many2one → res.users | Created by | ✅ | ❌ | [20, 'Vanderleia Cristina de Sene Castro'] |
| 6 | `credit_amount_currency` | monetary | Credit Amount Currency | ✅ | ❌ | 5068.3 |
| 7 | `credit_currency_id` | many2one → res.currency | Currency of the credit journal item. | ✅ | ❌ | [6, 'BRL'] |
| 8 | `credit_move_id` | many2one → account.move.line | Credit Move | ✅ | ✅ | [68956, 'COM2/2024/07/0016 1035067'] |
| 9 | `debit_amount_currency` | monetary | Debit Amount Currency | ✅ | ❌ | 5068.3 |
| 10 | `debit_currency_id` | many2one → res.currency | Currency of the debit journal item. | ✅ | ❌ | [6, 'BRL'] |
| 11 | `debit_move_id` | many2one → account.move.line | Debit Move | ✅ | ✅ | [106615, 'PGRA1/2024/00002 (1035067) Pagamento ... |
| 12 | `display_name` | char | Display Name | ❌ | ❌ | 'account.partial.reconcile,202' |
| 13 | `exchange_move_id` | many2one → account.move | Exchange Move | ✅ | ❌ | False |
| 14 | `full_reconcile_id` | many2one → account.full.reconcile | Full Reconcile | ✅ | ❌ | [133, 'account.full.reconcile,133'] |
| 15 | `id` | integer | ID | ✅ | ❌ | 202 |
| 16 | `max_date` | date | Max Date of Matched Lines | ✅ | ❌ | '2024-07-18' |
| 17 | `write_date` | datetime | Last Updated on | ✅ | ❌ | '2024-08-01 21:03:09' |
| 18 | `write_uid` | many2one → res.users | Last Updated by | ✅ | ❌ | [20, 'Vanderleia Cristina de Sene Castro'] |


### DETALHAMENTO DOS CAMPOS:

#### `amount`
- **Label:** Amount
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Always positive amount concerned by this matching expressed in the company currency.
- **Valor Exemplo:** `5068.3`

#### `company_currency_id`
- **Label:** Company Currency
- **Tipo:** many2one → res.currency
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.currency`
- **Descrição:** Utility field to express amount currency
- **Valor Exemplo:** `[6, 'BRL']`

#### `company_id`
- **Label:** Company
- **Tipo:** many2one → res.company
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `res.company`
- **Valor Exemplo:** `[1, 'NACOM GOYA - FB']`

#### `create_date`
- **Label:** Created on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2024-08-01 21:03:09'`

#### `create_uid`
- **Label:** Created by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `[20, 'Vanderleia Cristina de Sene Castro']`

#### `credit_amount_currency`
- **Label:** Credit Amount Currency
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Always positive amount concerned by this matching expressed in the credit line foreign currency.
- **Valor Exemplo:** `5068.3`

#### `credit_currency_id`
- **Label:** Currency of the credit journal item.
- **Tipo:** many2one → res.currency
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.currency`
- **Valor Exemplo:** `[6, 'BRL']`

#### `credit_move_id`
- **Label:** Credit Move
- **Tipo:** many2one → account.move.line
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`
- **Valor Exemplo:** `[68956, 'COM2/2024/07/0016 1035067']`

#### `debit_amount_currency`
- **Label:** Debit Amount Currency
- **Tipo:** monetary
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Descrição:** Always positive amount concerned by this matching expressed in the debit line foreign currency.
- **Valor Exemplo:** `5068.3`

#### `debit_currency_id`
- **Label:** Currency of the debit journal item.
- **Tipo:** many2one → res.currency
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.currency`
- **Valor Exemplo:** `[6, 'BRL']`

#### `debit_move_id`
- **Label:** Debit Move
- **Tipo:** many2one → account.move.line
- **Armazenado:** Sim
- **Obrigatório:** Sim
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`
- **Valor Exemplo:** `[106615, 'PGRA1/2024/00002 (1035067) Pagamento de fornecedor...']`

#### `display_name`
- **Label:** Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'account.partial.reconcile,202'`

#### `exchange_move_id`
- **Label:** Exchange Move
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Valor Exemplo:** `False`

#### `full_reconcile_id`
- **Label:** Full Reconcile
- **Tipo:** many2one → account.full.reconcile
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.full.reconcile`
- **Valor Exemplo:** `[133, 'account.full.reconcile,133']`

#### `id`
- **Label:** ID
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `202`

#### `max_date`
- **Label:** Max Date of Matched Lines
- **Tipo:** date
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2024-07-18'`

#### `write_date`
- **Label:** Last Updated on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2024-08-01 21:03:09'`

#### `write_uid`
- **Label:** Last Updated by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `[20, 'Vanderleia Cristina de Sene Castro']`



================================================================================
## account.full.reconcile
**Descrição:** Reconciliações completas - quando saldo = 0
================================================================================

**Total de campos:** 9

**Exemplo encontrado:** ID = 1

### CAMPOS:

| # | Campo | Tipo | Label | Armazenado | Obrigatório | Valor Exemplo |
|---|-------|------|-------|------------|-------------|---------------|
| 1 | `create_date` | datetime | Created on | ✅ | ❌ | '2022-12-08 15:28:27' |
| 2 | `create_uid` | many2one → res.users | Created by | ✅ | ❌ | [6, 'Suporte - CIEL IT'] |
| 3 | `display_name` | char | Display Name | ❌ | ❌ | 'account.full.reconcile,1' |
| 4 | `exchange_move_id` | many2one → account.move | Exchange Move | ✅ | ❌ | False |
| 5 | `id` | integer | ID | ✅ | ❌ | 1 |
| 6 | `partial_reconcile_ids` | one2many → account.partial.reconcile | Reconciliation Parts | ✅ | ❌ | [] |
| 7 | `reconciled_line_ids` | one2many → account.move.line | Matched Journal Items | ✅ | ❌ | [] |
| 8 | `write_date` | datetime | Last Updated on | ✅ | ❌ | '2022-12-08 15:28:27' |
| 9 | `write_uid` | many2one → res.users | Last Updated by | ✅ | ❌ | [6, 'Suporte - CIEL IT'] |


### DETALHAMENTO DOS CAMPOS:

#### `create_date`
- **Label:** Created on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2022-12-08 15:28:27'`

#### `create_uid`
- **Label:** Created by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `[6, 'Suporte - CIEL IT']`

#### `display_name`
- **Label:** Display Name
- **Tipo:** char
- **Armazenado:** Não (calculado)
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'account.full.reconcile,1'`

#### `exchange_move_id`
- **Label:** Exchange Move
- **Tipo:** many2one → account.move
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move`
- **Valor Exemplo:** `False`

#### `id`
- **Label:** ID
- **Tipo:** integer
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `1`

#### `partial_reconcile_ids`
- **Label:** Reconciliation Parts
- **Tipo:** one2many → account.partial.reconcile
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.partial.reconcile`
- **Valor Exemplo:** `[]`

#### `reconciled_line_ids`
- **Label:** Matched Journal Items
- **Tipo:** one2many → account.move.line
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Não
- **Relacionamento:** `account.move.line`
- **Valor Exemplo:** `[]`

#### `write_date`
- **Label:** Last Updated on
- **Tipo:** datetime
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Valor Exemplo:** `'2022-12-08 15:28:27'`

#### `write_uid`
- **Label:** Last Updated by
- **Tipo:** many2one → res.users
- **Armazenado:** Sim
- **Obrigatório:** Não
- **Somente Leitura:** Sim
- **Relacionamento:** `res.users`
- **Valor Exemplo:** `[6, 'Suporte - CIEL IT']`



---
## RESUMO

| Tabela | Total Campos |
|--------|-------------|
| account.move.line | 315 |
| account.move | 376 |
| account.payment | 437 |
| account.partial.reconcile | 18 |
| account.full.reconcile | 9 |
| **TOTAL** | **1155** |


---
## RELACIONAMENTOS ENTRE TABELAS

```
account.move.line (Título/Parcela)
    ├── move_id → account.move (Documento fiscal)
    ├── payment_id → account.payment (Pagamento vinculado)
    ├── matched_credit_ids → account.partial.reconcile
    ├── matched_debit_ids → account.partial.reconcile
    └── full_reconcile_id → account.full.reconcile

account.move (Documento Fiscal)
    ├── line_ids → account.move.line (Linhas do documento)
    └── payment_id → account.payment (Se for documento de pagamento)

account.payment (Pagamento)
    ├── move_id → account.move (Documento contábil do pagamento)
    └── reconciled_invoice_ids → account.move (Faturas reconciliadas)

account.partial.reconcile (Reconciliação Parcial)
    ├── debit_move_id → account.move.line (Linha de débito - título)
    ├── credit_move_id → account.move.line (Linha de crédito - pagamento)
    └── full_reconcile_id → account.full.reconcile

account.full.reconcile (Reconciliação Completa)
    ├── partial_reconcile_ids → account.partial.reconcile
    └── reconciled_line_ids → account.move.line
```
