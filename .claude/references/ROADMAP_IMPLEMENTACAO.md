# ROADMAP DE IMPLEMENTACAO - Consultas Odoo

**Data de Criacao:** 02/12/2025
**Ultima Atualizacao:** 02/12/2025
**Status:** Documento vivo - atualizar conforme implementacoes

---

## Visao Geral da Arquitetura Odoo

O Odoo utiliza uma arquitetura de modelos relacionais com XML-RPC para comunicacao.
Os principais dominios de dados relevantes para o sistema de fretes sao:

```
                    ODOO ERP
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │  ┌─────────────┐      ┌─────────────┐          │
    │  │   FISCAL    │      │  FINANCEIRO │          │
    │  │             │      │             │          │
    │  │  - DFE      │      │ - Faturas   │          │
    │  │  - CTe      │      │ - Parcelas  │          │
    │  │  - NFe      │      │ - Pagamentos│          │
    │  └──────┬──────┘      └──────┬──────┘          │
    │         │                    │                  │
    │         └────────┬───────────┘                  │
    │                  │                              │
    │         ┌────────▼────────┐                     │
    │         │    COMPRAS      │                     │
    │         │                 │                     │
    │         │ - Purchase Order│                     │
    │         │ - Recebimentos  │                     │
    │         └────────┬────────┘                     │
    │                  │                              │
    │         ┌────────▼────────┐                     │
    │         │   CADASTROS     │                     │
    │         │                 │                     │
    │         │ - Parceiros     │                     │
    │         │ - Produtos      │                     │
    │         └─────────────────┘                     │
    │                                                 │
    └─────────────────────────────────────────────────┘
```

---

## Status de Implementacao

| Modelo | Status | Skill |
|--------|--------|-------|
| DFE (Documentos Fiscais) | ✅ IMPLEMENTADO | rastreando-odoo |
| DFE Lines | ✅ IMPLEMENTADO | rastreando-odoo |
| DFE Pagamentos | ✅ IMPLEMENTADO | rastreando-odoo |
| res.partner | ✅ IMPLEMENTADO | rastreando-odoo |
| account.move | ✅ IMPLEMENTADO | rastreando-odoo |
| account.move.line | ✅ IMPLEMENTADO | rastreando-odoo |
| purchase.order | ✅ IMPLEMENTADO | rastreando-odoo |
| purchase.order.line | ✅ IMPLEMENTADO | rastreando-odoo |
| sale.order | ✅ IMPLEMENTADO | rastreando-odoo |
| stock.picking | ✅ IMPLEMENTADO | rastreando-odoo |
| account.full.reconcile | ✅ IMPLEMENTADO | rastreando-odoo |
| product.product | 🔍 | descobrindo-odoo-estrutura |

> **NOTA**: Skills `consultando-odoo-*` foram consolidadas em `rastreando-odoo` (16/12/2025)

**Legenda:**
- ✅ IMPLEMENTADO: Script funcional e documentacao completa
- 🟡 PARCIAL: Campos mapeados, falta script
- 📋 MAPEADO: Campos descobertos nesta sessao, aguarda implementacao
- ⬜ PENDENTE: Nao mapeado ainda

---

## DOMINIO 1: FISCAL (DFE)

### 1.1 Modelo Principal: l10n_br_ciel_it_account.dfe

**Status:** ✅ IMPLEMENTADO

**Descricao:** Documento Fiscal Eletronico - armazena todas as notas fiscais recebidas (NFe, CTe, NFSe)

#### Campos de Identificacao
| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID interno | PK |
| `protnfe_infnfe_chnfe` | char | Chave de acesso 44 digitos | Identificador unico |
| `nfe_infnfe_ide_nnf` | char | Numero da NF | Busca |
| `nfe_infnfe_ide_serie` | char | Serie | Complemento numero |
| `nfe_infnfe_ide_mod` | char | Modelo: 55=NFe, 57=CTe | Tipo documento |
| `company_id` | many2one | Empresa destinataria | Filtro obrigatorio |

#### Campos de Finalidade
| Campo | Tipo | Valores | Uso |
|-------|------|---------|-----|
| `nfe_infnfe_ide_finnfe` | selection | 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolucao | Subtipo |
| `is_cte` | boolean | True/False | Identificar CTe |
| `l10n_br_tipo_pedido` | selection | servico, mercadoria, etc | Tipo pedido |

#### Campos de Datas
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_ide_dhemi` | datetime | Data/hora emissao |
| `nfe_infnfe_ide_dhsaient` | datetime | Data/hora saida/entrada |
| `l10n_br_date_in` | date | Data entrada no sistema |
| `l10n_br_data_entrada` | date | Data de lancamento |

#### Campos do Emitente (Fornecedor)
| Campo | Tipo | Formato | Observacao |
|-------|------|---------|------------|
| `partner_id` | many2one | ID res.partner | Relacionamento |
| `nfe_infnfe_emit_cnpj` | char | XX.XXX.XXX/XXXX-XX | **COM pontuacao** |
| `nfe_infnfe_emit_cpf` | char | - | Pessoa fisica |
| `nfe_infnfe_emit_xnome` | char | - | Razao social |
| `nfe_infnfe_emit_xfant` | char | - | Nome fantasia |
| `nfe_infnfe_emit_ie` | char | - | Inscricao estadual |
| `nfe_infnfe_emit_ender_xlgr` | char | - | Logradouro |
| `nfe_infnfe_emit_ender_xmun` | char | - | Municipio |
| `nfe_infnfe_emit_ender_uf` | char | - | UF |

#### Campos do Destinatario (Empresa)
| Campo | Tipo | Formato | Observacao |
|-------|------|---------|------------|
| `partner_dest_id` | many2one | ID res.partner | Relacionamento |
| `nfe_infnfe_dest_cnpj` | char | XXXXXXXXXXXXXX | **SEM pontuacao** |
| `nfe_infnfe_dest_cpf` | char | - | Pessoa fisica |
| `nfe_infnfe_dest_uf` | char | - | UF |

> **ATENCAO:** O campo `nfe_infnfe_dest_xnome` NAO EXISTE. Usar `partner_dest_id` para dados do destinatario.

#### Campos de Totais Gerais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icmstot_vnf` | float | **Valor Total da NF** |
| `nfe_infnfe_total_icmstot_vprod` | float | Valor produtos |
| `nfe_infnfe_total_icms_vdesc` | float | Valor desconto |
| `nfe_infnfe_total_icms_vfrete` | float | Valor frete |
| `nfe_infnfe_total_icms_vseg` | float | Valor seguro |
| `nfe_infnfe_total_icms_voutro` | float | Outras despesas |

#### Campos de ICMS (Totais)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vbc` | float | Base de calculo ICMS |
| `nfe_infnfe_total_icms_vicms` | float | **Valor ICMS** |
| `nfe_infnfe_total_icms_vicmsdeson` | char | ICMS desonerado |

#### Campos de ICMS-ST (Totais)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vbcst` | float | Base ICMS-ST |
| `nfe_infnfe_total_icms_vst` | float | **Valor ICMS-ST** |

#### Campos de PIS/COFINS/IPI (Totais)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nfe_infnfe_total_icms_vpis` | float | Valor PIS |
| `nfe_infnfe_total_icms_vcofins` | float | Valor COFINS |
| `nfe_infnfe_total_icms_vipi` | float | Valor IPI |

#### Campos de Status
| Campo | Tipo | Valores |
|-------|------|---------|
| `l10n_br_status` | selection | 01=Novo, 02=Manifestado, 03=Ciencia, **04=PO**, 05=Faturado, 06=Cancelado, 07=Denegado |
| `state` | selection | Estado do registro |
| `active` | boolean | Ativo/Inativo |

> **IMPORTANTE:** Status '04' (PO) indica documento pronto para lancamento.

#### Campos de CTe Especificos
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cte_infcte_ide_cmunini` | char | Codigo municipio origem |
| `cte_infcte_ide_cmunfim` | char | Codigo municipio destino |
| `cte_infcte_ide_toma3_toma` | char | Tomador (0=Rem, 1=Exp, 2=Rec, 3=Dest) |

#### Campos de Relacionamento
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_id` | many2one | Parceiro emitente (res.partner) |
| `partner_dest_id` | many2one | Parceiro destinatario |
| `purchase_id` | many2one | Pedido de compra vinculado |
| `purchase_fiscal_id` | many2one | PO de escrituracao |
| `invoice_ids` | one2many | Faturas vinculadas |
| `refs_ids` | one2many | NF referenciadas |
| `payment_reference` | char | Referencia pagamento |

#### Campos de Arquivo
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_pdf_dfe` | binary | DANFE PDF (base64) |
| `l10n_br_pdf_dfe_fname` | char | Nome arquivo PDF |
| `l10n_br_xml_dfe` | binary | XML (base64) |
| `l10n_br_xml_dfe_fname` | char | Nome arquivo XML |
| `l10n_br_body_xml_dfe` | text | Conteudo XML |

---

### 1.2 Modelo Linhas: l10n_br_ciel_it_account.dfe.line

**Status:** ✅ IMPLEMENTADO

**Descricao:** Itens/produtos do documento fiscal

#### Campos de Produto
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID da linha |
| `dfe_id` | many2one | DFE pai |
| `product_id` | many2one | Produto vinculado |
| `det_prod_cprod` | char | Codigo produto (fornecedor) |
| `det_prod_xprod` | char | Descricao produto |
| `det_prod_ncm` | char | NCM |
| `det_prod_cfop` | char | CFOP |
| `det_infadprod` | char | Dados adicionais |

#### Campos de Quantidade/Valor
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_prod_qcom` | float | Quantidade |
| `det_prod_ucom` | char | Unidade |
| `det_prod_vuncom` | float | Valor unitario |
| `det_prod_vprod` | float | Valor total item |
| `det_prod_vdesc` | float | Desconto |
| `det_prod_vfrete` | float | Frete (rateio) |
| `det_prod_vseg` | float | Seguro (rateio) |
| `det_prod_voutro` | float | Outros (rateio) |

#### Campos de Pedido do Cliente
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_prod_xped` | char | Numero pedido cliente |
| `det_prod_nitemped` | char | Item pedido cliente |

#### Campos de ICMS (Linha)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_icms_cst` | char | **CST ICMS** |
| `det_imposto_icms_orig` | char | Origem mercadoria (0-8) |
| `det_imposto_icms_vbc` | float | Base calculo |
| `det_imposto_icms_picms` | float | **Aliquota %** |
| `det_imposto_icms_vicms` | float | Valor ICMS |
| `det_imposto_icms_predbc` | float | % Reducao base |

#### Campos de ICMS Simples Nacional (Linha)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_icms_pcredsn` | float | % Credito SN |
| `det_imposto_icms_vcredicmssn` | float | Valor credito SN |

#### Campos de ICMS-ST (Linha)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_icms_vbcst` | float | Base ICMS-ST |
| `det_imposto_icms_vicmsst` | float | Valor ICMS-ST |
| `det_imposto_icms_vbcstret` | float | Base ST retido |
| `det_imposto_icms_vicmsstret` | float | Valor ST retido |
| `det_imposto_icms_vicmssubstituto` | float | Valor substituto |

#### Campos de PIS (Linha)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_pis_cst` | char | CST PIS |
| `det_imposto_pis_vbc` | float | Base PIS |
| `det_imposto_pis_ppis` | float | Aliquota % |
| `det_imposto_pis_vpis` | float | Valor PIS |

#### Campos de COFINS (Linha)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_cofins_cst` | char | CST COFINS |
| `det_imposto_cofins_vbc` | float | Base COFINS |
| `det_imposto_cofins_pcofins` | float | Aliquota % |
| `det_imposto_cofins_vcofins` | float | Valor COFINS |

#### Campos de IPI (Linha)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `det_imposto_ipi_cst` | char | CST IPI |
| `det_imposto_ipi_vbc` | float | Base IPI |
| `det_imposto_ipi_pipi` | float | Aliquota % |
| `det_imposto_ipi_vipi` | float | Valor IPI |

#### Campos de Centro de Custo
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `account_analytic_id` | many2one | Conta analitica |
| `analytic_distribution` | json | Distribuicao analitica |

---

### 1.3 Modelo Pagamentos: l10n_br_ciel_it_account.dfe.pagamento

**Status:** 🟡 PARCIAL (mapeado, falta script)

**Descricao:** Duplicatas/parcelas do documento fiscal

#### Campos Principais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `dfe_id` | many2one | DFE vinculado |
| `company_id` | many2one | Empresa |

#### Campos da Duplicata
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cobr_dup_ndup` | char | Numero da parcela |
| `cobr_dup_dvenc` | date | **Data vencimento** |
| `cobr_dup_vdup` | float | **Valor parcela** |

---

## DOMINIO 2: FINANCEIRO

### 2.1 Modelo: account.move

**Status:** 📋 MAPEADO (aguarda implementacao)

**Descricao:** Faturas e documentos contabeis

#### Campos Principais (Descobertos via DOCUMENTACAO_TABELAS_ODOO_CONTAS_RECEBER.md)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `name` | char | Numero documento |
| `move_type` | selection | Tipo: out_invoice, in_invoice, out_refund, in_refund |
| `state` | selection | Estado: draft, posted, cancel |
| `partner_id` | many2one | Parceiro |
| `invoice_date` | date | Data fatura |
| `invoice_date_due` | date | Data vencimento |
| `amount_total` | float | Valor total |
| `amount_residual` | float | Valor residual (em aberto) |
| `company_id` | many2one | Empresa |
| `journal_id` | many2one | Diario |

#### Subtipos por move_type
| Valor | Descricao | Uso |
|-------|-----------|-----|
| `out_invoice` | Fatura de venda | Contas a receber |
| `in_invoice` | Fatura de compra | Contas a pagar |
| `out_refund` | Nota credito venda | Devolucao cliente |
| `in_refund` | Nota credito compra | Devolucao fornecedor |
| `entry` | Lancamento manual | Ajustes |

#### Relacionamentos
- `invoice_line_ids` -> account.move.line (itens)
- `payment_ids` -> account.payment (pagamentos)

---

### 2.2 Modelo: account.move.line

**Status:** 📋 MAPEADO (aguarda implementacao)

**Descricao:** Linhas de movimento contabil - parcelas a pagar/receber

#### Campos Principais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `move_id` | many2one | Fatura pai |
| `account_id` | many2one | Conta contabil |
| `partner_id` | many2one | Parceiro |
| `name` | char | Descricao |
| `date` | date | Data |
| `date_maturity` | date | **Data vencimento** |
| `debit` | float | Debito |
| `credit` | float | Credito |
| `balance` | float | Saldo |
| `amount_currency` | float | Valor moeda |
| `amount_residual` | float | **Valor em aberto** |
| `amount_residual_currency` | float | Residual moeda |
| `reconciled` | boolean | Conciliado |
| `full_reconcile_id` | many2one | Conciliacao completa |

#### Campos Brasileiros
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `dfe_line_id` | many2one | Vinculo linha DFE |
| `l10n_br_cfop_id` | many2one | CFOP |
| `l10n_br_cobranca_nossonumero` | char | Nosso numero boleto |
| `l10n_br_cobranca_situacao` | selection | Situacao cobranca |

#### Filtros Uteis
```python
# Contas a receber em aberto
[('account_id.account_type', '=', 'asset_receivable'), ('amount_residual', '>', 0)]

# Contas a pagar em aberto
[('account_id.account_type', '=', 'liability_payable'), ('amount_residual', '>', 0)]

# Vencidos
[('date_maturity', '<', 'hoje'), ('amount_residual', '>', 0)]
```

---

### 2.3 Modelo: account.payment

**Status:** ⬜ PENDENTE

**Descricao:** Pagamentos e recebimentos

#### Campos Principais (a mapear)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `name` | char | Numero |
| `payment_type` | selection | inbound/outbound |
| `partner_id` | many2one | Parceiro |
| `amount` | float | Valor |
| `date` | date | Data |
| `state` | selection | Estado |

---

## DOMINIO 3: COMPRAS

### 3.1 Modelo: purchase.order

**Status:** 📋 MAPEADO (aguarda implementacao)

**Descricao:** Pedidos de compra

#### Campos Principais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `name` | char | Numero PO |
| `partner_id` | many2one | Fornecedor |
| `date_order` | datetime | Data pedido |
| `date_planned` | datetime | Data prevista |
| `state` | selection | Estado |
| `amount_total` | float | Valor total |
| `company_id` | many2one | Empresa |
| `picking_type_id` | many2one | Tipo recebimento |

#### Estados (state)
| Valor | Descricao |
|-------|-----------|
| `draft` | Rascunho |
| `sent` | Enviado |
| `to approve` | Aguardando aprovacao |
| `purchase` | Confirmado |
| `done` | Concluido |
| `cancel` | Cancelado |

#### Relacionamentos com DFE
| Campo | Descricao |
|-------|-----------|
| `dfe_ids` | DFEs vinculados |
| `invoice_ids` | Faturas geradas |

---

## DOMINIO 4: CADASTROS

### 4.1 Modelo: res.partner

**Status:** 📋 MAPEADO (aguarda implementacao)

**Descricao:** Parceiros (fornecedores, clientes, transportadoras)

#### Campos Principais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `name` | char | Nome/Razao social |
| `display_name` | char | Nome exibicao |
| `is_company` | boolean | Empresa/Pessoa |
| `company_type` | selection | company/person |
| `vat` | char | CNPJ/CPF (sem formatacao) |
| `l10n_br_cnpj_cpf` | char | CNPJ/CPF formatado |
| `l10n_br_ie` | char | Inscricao estadual |
| `email` | char | Email |
| `phone` | char | Telefone |
| `mobile` | char | Celular |

#### Campos de Endereco
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `street` | char | Logradouro |
| `street2` | char | Complemento |
| `city` | char | Cidade |
| `state_id` | many2one | Estado (res.country.state) |
| `zip` | char | CEP |
| `country_id` | many2one | Pais |

#### Campos de Tipo
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `supplier_rank` | integer | Ranking fornecedor (>0 = fornecedor) |
| `customer_rank` | integer | Ranking cliente (>0 = cliente) |
| `is_company` | boolean | Eh empresa |

#### Filtros Uteis
```python
# Fornecedores
[('supplier_rank', '>', 0)]

# Clientes
[('customer_rank', '>', 0)]

# Por CNPJ
[('vat', 'ilike', '18467441')]  # ou l10n_br_cnpj_cpf

# Por UF
[('state_id.code', '=', 'SP')]
```

---

### 4.2 Modelo: product.product

**Status:** ⬜ PENDENTE

**Descricao:** Produtos

#### Campos Principais (a mapear)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID |
| `name` | char | Nome |
| `default_code` | char | Codigo interno |
| `barcode` | char | Codigo barras |
| `list_price` | float | Preco venda |
| `standard_price` | float | Preco custo |
| `categ_id` | many2one | Categoria |
| `uom_id` | many2one | Unidade medida |

#### Campos Brasileiros (a mapear)
- NCM
- Origem
- CFOP padrao
- Aliquotas padrao

---

## DIAGRAMA DE RELACIONAMENTOS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RELACIONAMENTOS ODOO                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   res.partner ◄────────────────────────────────────────────┐            │
│   (Fornecedor)                                             │            │
│       │                                                    │            │
│       │ partner_id                                         │            │
│       ▼                                                    │            │
│   l10n_br_ciel_it_account.dfe ─────────────────────────────┤            │
│   (Documento Fiscal)                                       │            │
│       │                                                    │            │
│       ├── dfe.line (Itens)                                │            │
│       │       └── product_id ──► product.product          │            │
│       │                                                    │            │
│       ├── dfe.pagamento (Duplicatas)                      │            │
│       │                                                    │            │
│       │ purchase_id                                        │            │
│       ▼                                                    │            │
│   purchase.order ──────────────────────────────────────────┤            │
│   (Pedido Compra)                                          │            │
│       │                                                    │            │
│       │ action_create_invoice                              │            │
│       ▼                                                    │            │
│   account.move ────────────────────────────────────────────┘            │
│   (Fatura)                                                              │
│       │                                                                 │
│       └── account.move.line (Parcelas)                                  │
│               │                                                         │
│               └── dfe_line_id ──► dfe.line                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ROADMAP DE IMPLEMENTACAO

### Fase 1: DFE Avancado (Curto Prazo) ✅ CONCLUIDA
**Prioridade:** Alta
**Esforco:** Baixo (mesmo modelo)
**Data conclusao:** 02/12/2025

1. [x] Adicionar filtro `--ncm` para buscar por NCM
2. [x] Adicionar filtro `--cfop` para buscar por CFOP
3. [x] Adicionar filtro `--com-icms-st` (vst > 0)
4. [x] Adicionar filtro `--com-ipi` (vipi > 0)
5. [x] Adicionar filtro `--valor-min` e `--valor-max`
6. [x] Implementar consulta de pagamentos (dfe.pagamento)

### Fase 2: Parceiros/Cadastros (Curto Prazo) ✅ CONCLUIDA
**Prioridade:** Alta
**Esforco:** Medio
**Data conclusao:** 02/12/2025
**Skill criada:** consultando-odoo-cadastros

1. [x] Mapear campos res.partner com skill descobrindo-odoo-estrutura (316 campos)
2. [x] Mapear campos delivery.carrier para transportadoras (34 campos)
3. [x] Criar skill separada: consultando-odoo-cadastros
4. [x] Criar documentacao reference/PARTNER.md
5. [x] Criar documentacao reference/CARRIER.md
6. [x] Implementar `--tipo partner` e `--tipo transportadora`
7. [x] Subtipos partner: fornecedor, cliente, todos
8. [x] Filtros: --cnpj, --nome, --uf, --cidade, --ie, --email
9. [x] Opcoes de saida: --endereco, --fiscal, --detalhes, --json

### Fase 3: Financeiro (Medio Prazo) ✅ CONCLUIDA
**Prioridade:** Media
**Esforco:** Alto
**Data conclusao:** 02/12/2025
**Skill criada:** consultando-odoo-financeiro

1. [x] Mapear campos account.move (376 campos) e account.move.line (315 campos)
2. [x] Criar skill separada: consultando-odoo-financeiro
3. [x] Criar documentacao reference/FINANCEIRO.md
4. [x] Implementar subtipos: a-pagar, a-receber, vencidos, a-vencer, todos
5. [x] Filtros: --vencimento-ate, --vencimento-de, --parceiro, --cnpj
6. [x] Filtros avancados: --valor-min, --valor-max, --dias-atraso
7. [x] Opcoes de saida: --detalhes (parcelas), --resumo (totalizadores), --json

### Fase 4: Compras (Medio Prazo) ✅ CONCLUIDA
**Prioridade:** Media
**Esforco:** Medio
**Data conclusao:** 02/12/2025
**Skill criada:** consultando-odoo-compras

1. [x] Mapear campos purchase.order (165 campos) e purchase.order.line (201 campos)
2. [x] Criar skill separada: consultando-odoo-compras
3. [x] Criar documentacao reference/PURCHASE.md
4. [x] Implementar subtipos: pendentes, confirmados, recebidos, a-faturar, cancelados, todos
5. [x] Filtros: --fornecedor, --cnpj, --numero-po, --data-inicio, --data-fim
6. [x] Filtros avancados: --valor-min, --valor-max, --produto, --origem
7. [x] Opcoes de saida: --detalhes (linhas), --fiscais (tributos), --resumo (totalizadores), --json

### Fase 5: Produtos (Longo Prazo) ✅ CONCLUIDA
**Prioridade:** Baixa
**Esforco:** Medio
**Data conclusao:** 02/12/2025
**Skill criada:** consultando-odoo-produtos

1. [x] Mapear campos product.product (229 campos) e product.template (196 campos)
2. [x] Criar skill separada: consultando-odoo-produtos
3. [x] Criar documentacao reference/PRODUCT.md
4. [x] Implementar subtipos: ativos, inativos, vendaveis, compraveis, estocaveis, servicos, consumiveis, todos
5. [x] Filtros: --codigo, --nome, --barcode, --categoria, --ncm, --fornecedor, --preco-min/max, --com-estoque, --sem-estoque
6. [x] Opcoes de saida: --detalhes (fornecedores, estoque), --fiscais (NCM, origem), --resumo (totalizadores), --json

---

## TABELAS DE CST (Referencia Rapida)

### CST ICMS
| CST | Descricao | Quando Usar |
|-----|-----------|-------------|
| 00 | Tributada integralmente | Operacao normal |
| 10 | Com cobranca ICMS-ST | Substituicao tributaria |
| 20 | Com reducao de base | Base reduzida |
| 30 | Isenta com ST | Isento mas tem ST |
| 40 | Isenta | Isencao |
| 41 | Nao tributada | Fora do campo de incidencia |
| 50 | Suspensao | Suspensa |
| 51 | Diferimento | Diferido |
| 60 | Cobrado anteriormente por ST | Ja pagou ST |
| 70 | Reducao + ST | Ambos |
| 90 | Outras | Outros casos |

### CST PIS/COFINS
| CST | Descricao |
|-----|-----------|
| 01 | Aliquota basica |
| 02 | Aliquota diferenciada |
| 04 | Monofasica revenda zero |
| 06 | Aliquota zero |
| 07 | Isenta |
| 08 | Sem incidencia |
| 09 | Suspensao |
| 49 | Outras saidas |
| 50-56 | Com direito credito |
| 70-75 | Sem direito credito |

### CST IPI
| CST | Descricao |
|-----|-----------|
| 00-05 | Entradas |
| 49 | Outras entradas |
| 50-55 | Saidas |
| 99 | Outras saidas |

---

## PADROES DE IMPLEMENTACAO

### Estrutura de Configuracao no Script

```python
MODELOS_CONHECIDOS = {
    'nome_modelo': {
        'modelo_odoo': 'nome.modelo.odoo',
        'modelo_linha': 'nome.modelo.linha',  # se aplicavel
        'subtipos': {
            'subtipo1': {'filtro': ('campo', '=', 'valor')},
            'subtipo2': {'filtro': ('campo', '=', 'valor')},
        },
        'campos_principais': [
            'id',
            'campo1',
            'campo2',
        ],
        'campos_opcionais': [
            # Campos extras para --detalhes ou --fiscais
        ],
        'campo_busca': 'campo_principal_busca',
        'campo_data': 'campo_data_principal',
    }
}
```

### Padrao de Funcao de Consulta

```python
def consultar_MODELO(args) -> Dict[str, Any]:
    """
    Consulta MODELO no Odoo
    """
    from app.odoo.utils.connection import get_odoo_connection

    config = MODELOS_CONHECIDOS['modelo']
    resultado = {
        'sucesso': False,
        'tipo': 'modelo',
        'subtipo': args.subtipo,
        'total': 0,
        'registros': [],
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            resultado['erro'] = 'Falha na autenticacao'
            return resultado

        # Montar filtros
        filtros = []
        # ... adicionar filtros baseado nos args

        # Buscar registros
        registros = odoo.search_read(
            config['modelo_odoo'],
            filtros,
            fields=config['campos_principais'],
            limit=args.limit or 100
        )

        resultado['sucesso'] = True
        resultado['total'] = len(registros)
        resultado['registros'] = registros

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado
```

---

## CONEXAO COM ODOO

```python
from app.odoo.utils.connection import get_odoo_connection

# Autenticacao
odoo = get_odoo_connection()
if not odoo.authenticate():
    raise Exception("Falha na autenticacao")

# Operacoes disponiveis
odoo.search_read(modelo, filtros, fields, limit)
odoo.read(modelo, ids, fields)
odoo.write(modelo, ids, valores)
odoo.execute_kw(modelo, metodo, args, kwargs)
```

---

## NOTAS IMPORTANTES

1. **CNPJ do Emitente:** Armazenado COM pontuacao (XX.XXX.XXX/XXXX-XX)
2. **CNPJ do Destinatario:** Armazenado SEM pontuacao
3. **Status DFE '04':** Documento pronto para lancamento
4. **Filtro active:** Sempre incluir `'|', ('active', '=', True), ('active', '=', False)` para ver todos
5. **Campos inexistentes:** `nfe_infnfe_dest_xnome` NAO existe - usar partner_dest_id
6. **CST vs CSOSN:** Empresas Simples Nacional usam CSOSN

---

## ATUALIZACOES DESTE DOCUMENTO

| Data | Alteracao |
|------|-----------|
| 02/12/2025 | Criacao do documento |
| 02/12/2025 | Mapeamento completo DFE com campos fiscais |
| 02/12/2025 | Mapeamento parcial account.move.line (via doc contas receber) |
| 02/12/2025 | Roadmap de implementacao definido |
| 02/12/2025 | Fase 1 concluida: filtros avancados (NCM, CFOP, ICMS-ST, IPI, valor) e pagamentos |
| 02/12/2025 | Fase 2 concluida: nova skill consultando-odoo-cadastros (res.partner, delivery.carrier) |
| 02/12/2025 | Fase 3 concluida: nova skill consultando-odoo-financeiro (account.move, account.move.line) |
| 02/12/2025 | Fase 4 concluida: nova skill consultando-odoo-compras (purchase.order, purchase.order.line) |

---

## PROXIMOS PASSOS SUGERIDOS

1. ✅ ~~Validar mapeamento res.partner~~ - Concluido (316 campos)
2. ✅ ~~Implementar Fase 1~~ - Filtros avancados no DFE
3. ✅ ~~Criar reference/PARTNER.md~~ - Documentacao criada
4. ✅ ~~Implementar --tipo partner~~ - Nova skill consultando-odoo-cadastros
5. ✅ ~~Fase 3: Financeiro~~ - Nova skill consultando-odoo-financeiro (691 campos)
6. ✅ ~~Fase 4: Compras~~ - Nova skill consultando-odoo-compras (366 campos)
7. ✅ ~~Fase 5: Produtos~~ - Nova skill consultando-odoo-produtos (425 campos)

**ROADMAP COMPLETO!** Todas as fases de implementacao foram concluidas.
As proximas evolucoes podem incluir:
- Consultas de vendas (sale.order)
- Consultas de estoque (stock.move, stock.picking)
- Consultas de pagamentos (account.payment)

---

## PADRAO PARA CRIACAO DE NOVAS SKILLS (Anthropic Guidelines)

### Estrategia de Separacao por Dominio

Cada dominio significativo deve ter **skill separada** para melhor match do Agent SDK:

```
.claude/skills/
├── consultando-odoo-dfe/           # DFE/Documentos fiscais (IMPLEMENTADO)
├── descobrindo-odoo-estrutura/     # Descoberta de campos/modelos (IMPLEMENTADO)
├── consultando-odoo-cadastros/     # Parceiros/Transportadoras (IMPLEMENTADO)
├── consultando-odoo-financeiro/    # Contas a pagar/receber (IMPLEMENTADO)
├── consultando-odoo-compras/       # Pedidos de Compra (IMPLEMENTADO)
└── consultando-odoo-produtos/      # Catalogo de Produtos (IMPLEMENTADO)
```

### Template para Nova Skill

**Estrutura de diretorio:**
```
consultando-odoo-{dominio}/
├── SKILL.md                    # Frontmatter + documentacao
├── scripts/
│   └── consulta.py             # Script de consulta
└── reference/
    └── {MODELO}.md             # Documentacao de campos
```

**Frontmatter SKILL.md (description eh CRITICO):**
```yaml
---
name: consultando-odoo-{dominio}
description: "{O QUE FAZ}. {KEYWORDS de busca}. Use para: {CASOS DE USO especificos}."
---
```

### Checklist para Description Efetiva

A description deve:
1. **Comecar com acao** - "Busca...", "Consulta...", "Localiza..."
2. **Listar keywords** - Termos que o usuario pode usar
3. **Explicar casos de uso** - "Use para: X, Y, Z"
4. **Ser especifica** - Evitar termos genericos como "dados", "informacoes"
5. **Ter menos de 300 caracteres** - Concisa e direta

### Exemplos de Descriptions por Dominio

**consultando-odoo-dfe (ATUAL):**
```yaml
description: "Busca documentos fiscais (DFE) no Odoo: devolucoes, CTe de frete,
notas de entrada, tributos (ICMS, PIS, COFINS, IPI, ST). Use para: NF de devolucao,
CTe de transportadora, nota de fornecedor, impostos de nota fiscal, localizar
documento por chave, CNPJ, nome, numero NF, produto ou periodo."
```

**consultando-odoo-financeiro (FUTURO):**
```yaml
description: "Consulta contas a pagar e receber no Odoo. Busca parcelas, vencimentos,
faturas, titulos em aberto. Use para: parcelas vencidas, contas a pagar de fornecedor,
vencimentos da semana, saldo devedor por parceiro, relatorio de inadimplencia."
```

**consultando-odoo-cadastros (IMPLEMENTADO):**
```yaml
description: "Busca fornecedores, clientes e transportadoras no Odoo (res.partner, delivery.carrier).
Use para: localizar fornecedor por CNPJ, dados de transportadora, endereco de cliente,
inscricao estadual, cadastro de parceiro, consultar ranking cliente/fornecedor."
```

**consultando-odoo-compras (FUTURO):**
```yaml
description: "Consulta pedidos de compra no Odoo (purchase.order). Busca POs por
fornecedor, status, periodo. Use para: pedidos pendentes, compras do mes, PO vinculado
a nota, historico de compras de fornecedor."
```

### Quando Criar Nova Skill vs Expandir Existente

**CRIAR NOVA SKILL quando:**
- Dominio tem > 10 campos especificos
- Casos de uso sao distintos do dominio atual
- Description ficaria > 300 caracteres se combinada
- Keywords nao se sobrepoe significativamente

**EXPANDIR SKILL EXISTENTE quando:**
- Funcionalidade eh extensao natural (ex: mais filtros no DFE)
- Compartilha mesmos casos de uso
- Reutiliza mesma estrutura de consulta

### Migracao Gradual

1. ✅ **Fase 1 concluida:** consultando-odoo-dfe cobre DFE, CTe, pagamentos
2. ✅ **Fase 2 concluida:** consultando-odoo-cadastros cobre parceiros e transportadoras
3. ✅ **Fase 3 concluida:** consultando-odoo-financeiro cobre contas a pagar/receber
4. ✅ **Fase 4 concluida:** consultando-odoo-compras cobre pedidos de compra
5. ✅ **Fase 5 concluida:** consultando-odoo-produtos cobre catalogo de produtos
6. **ROADMAP COMPLETO:** Todas as fases foram implementadas! Este documento permanece como referencia unica

---

## REFERENCIAS ANTHROPIC

- Skills sao **model-invoked** - Claude decide quando usar baseado na description
- Description eh o **unico criterio** para selecao automatica
- Multiplas skills especializadas > Uma skill generica
- allowed-tools no frontmatter controla quais ferramentas a skill pode usar
