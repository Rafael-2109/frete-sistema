# TABELAS DO ODOO - CONTAS A RECEBER
## Documentação Consolidada com Explicação de Cada Campo

**Data:** 2025-11-28
**Gerado por:** Investigação automática via XML-RPC

---

## RESUMO DAS TABELAS

| Tabela | Total Campos | Função |
|--------|-------------|--------|
| `account.move.line` | 315 | Linhas contábeis - **ONDE ESTÃO AS PARCELAS/TÍTULOS** |
| `account.move` | 376 | Documentos fiscais (faturas, notas de crédito) |
| `account.payment` | 437 | Pagamentos e recebimentos |
| `account.partial.reconcile` | 18 | **VINCULA DÉBITO COM CRÉDITO** (mecanismo de baixa) |
| `account.full.reconcile` | 9 | Reconciliação completa (saldo = 0) |

---

## DIAGRAMA DE RELACIONAMENTOS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUXO DE BAIXA NO ODOO                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│   account.move       │     │   account.payment    │
│  (Documento Fiscal)  │     │    (Pagamento)       │
│                      │     │                      │
│  move_type:          │     │  payment_type:       │
│  - out_invoice (NF)  │     │  - inbound (receb.)  │
│  - out_refund (NC)   │     │  - outbound (pag.)   │
│  - entry (ajuste)    │     │                      │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           │ line_ids                   │ move_id
           ▼                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         account.move.line                                     │
│                    (Linhas de movimento contábil)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LINHA DE DÉBITO (título a receber)        LINHA DE CRÉDITO (pagamento)      │
│  ├── debit > 0                             ├── credit > 0                    │
│  ├── account_type = 'asset_receivable'     ├── account_type = 'asset_recv.'  │
│  ├── balance = valor do título             ├── balance = valor negativo      │
│  └── amount_residual = saldo restante      └── matched_debit_ids             │
│                                                                              │
│  ▲                                         ▲                                 │
│  │ matched_credit_ids                      │ matched_debit_ids               │
│  │                                         │                                 │
└──┼─────────────────────────────────────────┼─────────────────────────────────┘
   │                                         │
   └─────────────────┬───────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     account.partial.reconcile                                 │
│                   (VINCULA DÉBITO COM CRÉDITO)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  debit_move_id  → Linha de DÉBITO (título original)                          │
│  credit_move_id → Linha de CRÉDITO (pagamento/abatimento)                    │
│  amount         → Valor reconciliado                                         │
│  full_reconcile_id → Se saldo = 0, aponta para full_reconcile               │
└──────────────────────────────────────────────────────────────────────────────┘
                     │
                     │ Se soma(amount) = balance original
                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     account.full.reconcile                                    │
│                   (RECONCILIAÇÃO COMPLETA)                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  partial_reconcile_ids → Lista de reconciliações parciais                    │
│  reconciled_line_ids   → Todas as linhas envolvidas                          │
│                                                                              │
│  Quando existe: o título está 100% QUITADO                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 1. ACCOUNT.MOVE.LINE (315 campos)

## Descrição
Esta é a tabela PRINCIPAL onde estão as **parcelas/títulos a receber**. Cada linha representa um lançamento contábil. Para contas a receber, filtramos por `account_type = 'asset_receivable'`.

## Campos CRÍTICOS para Contas a Receber

### 🔴 IDENTIFICAÇÃO DO TÍTULO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | integer | ID único da linha | 2636115 |
| `x_studio_nf_e` | char | **NF-e** (campo customizado) | "141787" |
| `l10n_br_cobranca_parcela` | integer | **Número da Parcela** | 1, 2, 3... |
| `name` | char | Label da linha | "VND/2025/05103 parcela nº1" |
| `move_id` | many2one → account.move | Documento fiscal pai | [404387, 'NF-e: 141787...'] |
| `move_name` | char | Número do documento | "VND/2025/05103" |

### 🔴 VALORES FINANCEIROS

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `balance` | monetary | **Valor original do título** (positivo = débito) | 840.76 |
| `debit` | monetary | Valor de débito | 840.76 |
| `credit` | monetary | Valor de crédito (para pagamentos) | 0.0 |
| `amount_currency` | monetary | Valor na moeda da transação | 840.76 |
| `amount_residual` | monetary | **SALDO RESTANTE** (0 = pago) | 0.0 |
| `amount_residual_currency` | monetary | Saldo na moeda original | 0.0 |

### 🔴 DESCONTO CONCEDIDO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `desconto_concedido` | float | **Valor do desconto após emissão** | 50.00 |
| `desconto_concedido_percentual` | float | **Percentual do desconto** | 5.0 |
| `discount` | float | Desconto padrão Odoo (%) | 0.0 |

### 🔴 STATUS DE PAGAMENTO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `l10n_br_paga` | boolean | **PARCELA PAGA?** (campo principal BR) | True/False |
| `reconciled` | boolean | Totalmente reconciliado? | True/False |
| `x_studio_status_de_pagamento` | selection | Status customizado | "paid", "partial", "not_paid" |
| `parent_state` | selection | Status do documento pai | "posted", "draft", "cancel" |

**Valores de x_studio_status_de_pagamento:**
- `not_paid` = Não Pago
- `in_payment` = Em Pagamento
- `paid` = Pago
- `partial` = Parcialmente Pago
- `reversed` = Revertido
- `invoicing_legacy` = Legacy

### 🔴 RECONCILIAÇÃO (MECANISMO DE BAIXA)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `matched_credit_ids` | one2many → account.partial.reconcile | **Créditos que baixaram este débito** | [202, 305, ...] |
| `matched_debit_ids` | one2many → account.partial.reconcile | Débitos que foram baixados (para créditos) | [] |
| `full_reconcile_id` | many2one → account.full.reconcile | **Reconciliação completa** (se saldo = 0) | [133, '...'] |
| `matching_number` | char | Número do match ('P' = parcial) | "P" ou "X123" |

### 🔴 DATAS

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `date` | date | Data do lançamento | "2025-11-13" |
| `date_maturity` | date | **Data de vencimento** | "2025-12-13" |
| `invoice_date` | date | Data da fatura | "2025-11-13" |
| `create_date` | datetime | Criação do registro | "2025-11-13 10:30:00" |
| `write_date` | datetime | Última atualização | "2025-11-28 14:00:00" |

### 🔴 CLIENTE E EMPRESA

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `partner_id` | many2one → res.partner | **Cliente** | [12345, 'EMPRESA ABC'] |
| `company_id` | many2one → res.company | Empresa (FB, SC, CD) | [1, 'NACOM GOYA - FB'] |
| `account_id` | many2one → account.account | Conta contábil | [24801, '1120100001 CLIENTES'] |

### 🔴 VÍNCULO COM PAGAMENTO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `payment_id` | many2one → account.payment | Pagamento que gerou esta linha | [17734, 'PAG/2025/001'] |
| `statement_line_id` | many2one → account.bank.statement.line | Linha de extrato bancário | False |

### 🟡 CAMPOS BRASILEIROS (l10n_br)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `l10n_br_cobranca_nossonumero` | char | Nosso Número (boleto) |
| `l10n_br_cobranca_situacao` | selection | Situação da cobrança (EMITIDO, PENDENTE, FALHA...) |
| `l10n_br_cobranca_protocolo` | char | Protocolo da cobrança |
| `l10n_br_meio` | selection | Meio de pagamento (01=Dinheiro, 15=Boleto, 17=PIX...) |
| `l10n_br_pedido_compra` | char | Pedido de Compra do Cliente |

---

# 2. ACCOUNT.MOVE (376 campos)

## Descrição
Documento fiscal principal - faturas, notas de crédito, lançamentos contábeis manuais.

## Campos CRÍTICOS

### 🔴 IDENTIFICAÇÃO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | integer | ID único | 404387 |
| `name` | char | Número do documento | "NF-e: 141787 Série: 1" |
| `ref` | char | Referência externa | "PED-12345" |
| `move_type` | selection | **TIPO DO DOCUMENTO** | "out_invoice" |

**Valores de move_type:**
- `entry` = Lançamento Manual (ajustes, write-offs)
- `out_invoice` = **Fatura de Cliente (NF de venda)**
- `out_refund` = **Nota de Crédito de Cliente (devolução/abatimento)**
- `in_invoice` = Fatura de Fornecedor
- `in_refund` = Nota de Crédito de Fornecedor
- `out_receipt` = Recibo de Venda
- `in_receipt` = Recibo de Compra

### 🔴 STATUS

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `state` | selection | Status do documento | "posted", "draft", "cancel" |
| `payment_state` | selection | Status de pagamento | "paid", "partial", "not_paid" |

**Valores de payment_state:**
- `not_paid` = Não pago
- `in_payment` = Em pagamento
- `paid` = Pago
- `partial` = Parcialmente pago
- `reversed` = Revertido

### 🔴 VALORES

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `amount_total` | monetary | Valor total do documento | 5068.30 |
| `amount_residual` | monetary | Saldo restante | 0.0 |
| `amount_untaxed` | monetary | Valor sem impostos | 4500.00 |
| `amount_tax` | monetary | Total de impostos | 568.30 |

### 🔴 RELACIONAMENTOS

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `line_ids` | one2many → account.move.line | Linhas do documento |
| `partner_id` | many2one → res.partner | Cliente/Fornecedor |
| `payment_id` | many2one → account.payment | Pagamento vinculado |
| `reversed_entry_id` | many2one → account.move | Documento revertido |
| `reversal_move_id` | one2many → account.move | Documentos de reversão |

---

# 3. ACCOUNT.PAYMENT (437 campos)

## Descrição
Registro de pagamentos e recebimentos. Quando um pagamento é registrado, ele cria automaticamente um `account.move` com linhas de crédito.

## Campos CRÍTICOS

### 🔴 IDENTIFICAÇÃO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | integer | ID único | 17734 |
| `name` | char | Número do pagamento | "PAG/2025/00123" |
| `ref` | char | Referência | "Ref. NF 141787" |

### 🔴 TIPO E DIREÇÃO

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `payment_type` | selection | Direção do pagamento | "inbound" ou "outbound" |
| `partner_type` | selection | Tipo de parceiro | "customer" ou "supplier" |

**Valores de payment_type:**
- `inbound` = **RECEBIMENTO** (dinheiro entra - cliente paga)
- `outbound` = **PAGAMENTO** (dinheiro sai - pagamos fornecedor)

### 🔴 VALORES

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `amount` | monetary | **Valor do pagamento** | 5068.30 |
| `currency_id` | many2one → res.currency | Moeda | [6, 'BRL'] |

### 🔴 DATAS E STATUS

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `date` | date | **Data do pagamento** | "2025-11-28" |
| `state` | selection | Status | "posted", "draft", "cancel" |

**Valores de state:**
- `draft` = Rascunho
- `posted` = Confirmado
- `cancel` = Cancelado

### 🔴 RELACIONAMENTOS

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `move_id` | many2one → account.move | Documento contábil gerado |
| `partner_id` | many2one → res.partner | Cliente/Fornecedor |
| `journal_id` | many2one → account.journal | Diário (banco, caixa) |
| `reconciled_invoice_ids` | many2many → account.move | **Faturas reconciliadas** |
| `reconciled_invoices_count` | integer | Quantidade de faturas |

### 🟡 MÉTODO DE PAGAMENTO

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `payment_method_line_id` | many2one | Método de pagamento |
| `payment_method_code` | char | Código do método |

---

# 4. ACCOUNT.PARTIAL.RECONCILE (18 campos)

## Descrição
**TABELA CHAVE DO MECANISMO DE BAIXA**. Cada registro representa uma "ligação" entre uma linha de DÉBITO (título) e uma linha de CRÉDITO (pagamento/abatimento).

## Campos COMPLETOS (são apenas 18!)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | integer | ID único | 202 |
| `amount` | monetary | **Valor reconciliado** (sempre positivo) | 5068.30 |
| `debit_move_id` | many2one → account.move.line | **Linha de DÉBITO (título)** | [106615, 'parcela nº1'] |
| `credit_move_id` | many2one → account.move.line | **Linha de CRÉDITO (pagamento)** | [68956, 'Pagamento...'] |
| `debit_amount_currency` | monetary | Valor do débito na moeda | 5068.30 |
| `credit_amount_currency` | monetary | Valor do crédito na moeda | 5068.30 |
| `debit_currency_id` | many2one → res.currency | Moeda do débito | [6, 'BRL'] |
| `credit_currency_id` | many2one → res.currency | Moeda do crédito | [6, 'BRL'] |
| `full_reconcile_id` | many2one → account.full.reconcile | **Reconciliação completa** (se existir) | [133, '...'] |
| `exchange_move_id` | many2one → account.move | Ajuste de câmbio | False |
| `max_date` | date | Data máxima das linhas | "2024-07-18" |
| `company_id` | many2one → res.company | Empresa | [1, 'NACOM GOYA - FB'] |
| `company_currency_id` | many2one → res.currency | Moeda da empresa | [6, 'BRL'] |
| `create_date` | datetime | Data de criação | "2024-08-01 21:03:09" |
| `create_uid` | many2one → res.users | Criado por | [20, 'Vanderleia...'] |
| `write_date` | datetime | Última atualização | "2024-08-01 21:03:09" |
| `write_uid` | many2one → res.users | Atualizado por | [20, 'Vanderleia...'] |
| `display_name` | char | Nome de exibição | "account.partial.reconcile,202" |

## Como funciona a reconciliação:

```
Exemplo: Título de R$ 1.000,00 pago em 2 parcelas

TÍTULO (account.move.line)
├── id: 100
├── debit: 1000.00
├── balance: 1000.00
├── amount_residual: 0.00 (após baixa completa)
└── matched_credit_ids: [50, 51]

PAGAMENTO 1 (account.move.line via account.payment)
├── id: 200
├── credit: 600.00
└── matched_debit_ids: [50]

PAGAMENTO 2 (account.move.line via account.payment)
├── id: 201
├── credit: 400.00
└── matched_debit_ids: [51]

RECONCILIAÇÃO 1 (account.partial.reconcile)
├── id: 50
├── debit_move_id: 100 (título)
├── credit_move_id: 200 (pagamento 1)
├── amount: 600.00
└── full_reconcile_id: 25

RECONCILIAÇÃO 2 (account.partial.reconcile)
├── id: 51
├── debit_move_id: 100 (título)
├── credit_move_id: 201 (pagamento 2)
├── amount: 400.00
└── full_reconcile_id: 25

RECONCILIAÇÃO COMPLETA (account.full.reconcile)
├── id: 25
├── partial_reconcile_ids: [50, 51]
└── reconciled_line_ids: [100, 200, 201]
```

---

# 5. ACCOUNT.FULL.RECONCILE (9 campos)

## Descrição
Criado AUTOMATICAMENTE quando a soma de todas as reconciliações parciais iguala o valor do título (saldo = 0).

## Campos COMPLETOS (são apenas 9!)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | integer | ID único | 133 |
| `display_name` | char | Nome de exibição | "account.full.reconcile,133" |
| `partial_reconcile_ids` | one2many → account.partial.reconcile | **Reconciliações parciais** | [50, 51] |
| `reconciled_line_ids` | one2many → account.move.line | **Todas as linhas envolvidas** | [100, 200, 201] |
| `exchange_move_id` | many2one → account.move | Ajuste de câmbio | False |
| `create_date` | datetime | Data de criação | "2024-08-01 21:03:09" |
| `create_uid` | many2one → res.users | Criado por | [6, 'Suporte...'] |
| `write_date` | datetime | Última atualização | "2024-08-01 21:03:09" |
| `write_uid` | many2one → res.users | Atualizado por | [6, 'Suporte...'] |

---

# RESUMO: COMO SABER SE UM TÍTULO FOI PAGO

## Método 1: Verificar campo l10n_br_paga (mais simples)
```python
if titulo.l10n_br_paga == True:
    print("Título pago!")
```

## Método 2: Verificar amount_residual (mais preciso)
```python
if titulo.amount_residual == 0:
    print("Título quitado!")
elif titulo.amount_residual < titulo.balance:
    print("Título parcialmente pago!")
else:
    print("Título em aberto!")
```

## Método 3: Verificar reconciliação completa
```python
if titulo.full_reconcile_id:
    print("Título com reconciliação completa!")
```

## Método 4: Verificar reconciliações parciais
```python
if titulo.matched_credit_ids:
    print(f"Título tem {len(titulo.matched_credit_ids)} créditos vinculados")
```

---

# TIPOS DE ABATIMENTOS E ONDE FICAM

## 1. DESCONTO CONTRATUAL (na emissão)
- **Onde:** Campo `desconto_concedido` em `account.move.line`
- **Como:** Valor já reduzido na emissão
- **Não gera:** Documento separado

## 2. NOTA DE CRÉDITO (devolução/bonificação)
- **Onde:** `account.move` com `move_type = 'out_refund'`
- **Como:** Documento fiscal separado
- **Gera:** Linha de crédito em contas a receber
- **Reconciliação:** Vinculada via `account.partial.reconcile`

## 3. PAGAMENTO (baixa normal)
- **Onde:** `account.payment` com `payment_type = 'inbound'`
- **Como:** Registro de recebimento
- **Gera:** Linha de crédito via `account.move`
- **Reconciliação:** Vinculada via `account.partial.reconcile`

## 4. WRITE-OFF (ajuste/diferença)
- **Onde:** `account.move` com `move_type = 'entry'`
- **Como:** Lançamento contábil manual
- **Gera:** Linha de crédito em contas a receber
- **Reconciliação:** Vinculada via `account.partial.reconcile`

---

# CAMPOS PARA SINCRONIZAR DO ODOO → SISTEMA LOCAL

## Tabela ContasAReceber (já existente)
```
ODOO (account.move.line)          → LOCAL (ContasAReceber)
─────────────────────────────────────────────────────────
x_studio_nf_e                     → titulo_nf
l10n_br_cobranca_parcela          → parcela
partner_id.cnpj                   → cnpj
partner_id.name                   → raz_social
partner_id.trade_name             → raz_social_red
date                              → emissao
date_maturity                     → vencimento
balance                           → valor_original (calculado)
desconto_concedido                → desconto
desconto_concedido_percentual/100 → desconto_percentual
l10n_br_paga                      → parcela_paga
x_studio_status_de_pagamento      → status_pagamento_odoo
amount_residual                   → (para cálculo de valor_titulo)
write_date                        → odoo_write_date
```

## NOVA Tabela: ContasAReceberBaixa (sugestão)
```
ODOO (account.partial.reconcile)  → LOCAL (ContasAReceberBaixa)
─────────────────────────────────────────────────────────
id                                → odoo_reconcile_id
debit_move_id                     → conta_a_receber_id (FK)
credit_move_id                    → odoo_credit_line_id
amount                            → valor_baixa
create_date                       → data_baixa
payment_id (via credit_move)      → odoo_payment_id
move_type (via credit_move)       → tipo_baixa (pagamento/NC/ajuste)
```

---

# CONCLUSÃO

O mecanismo de baixa do Odoo é baseado em **RECONCILIAÇÃO CONTÁBIL**:

1. **Título** = Linha de DÉBITO em `account.move.line`
2. **Pagamento/Abatimento** = Linha de CRÉDITO em `account.move.line`
3. **Baixa** = Registro em `account.partial.reconcile` vinculando débito e crédito
4. **Quitação** = Quando `amount_residual = 0`, cria `account.full.reconcile`

O campo `l10n_br_paga` é um campo **CALCULADO** baseado na reconciliação, não é um flag que alguém marca manualmente.
