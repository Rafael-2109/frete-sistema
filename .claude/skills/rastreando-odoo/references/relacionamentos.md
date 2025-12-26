# Mapeamento de Relacionamentos Odoo

## Glossario de Modelos

| Modelo Odoo | Nome Amigavel | Descricao |
|-------------|---------------|-----------|
| `l10n_br_ciel_it_account.dfe` | DFE | Documento Fiscal Eletronico (NF-e, CT-e) |
| `purchase.order` | PO | Pedido de Compra |
| `purchase.requisition` | Requisicao | Requisicao de Compra |
| `sale.order` | SO | Pedido de Venda |
| `account.move` | Fatura/Invoice | Fatura (compra ou venda) |
| `account.move.line` | Linha Fatura | Linha de fatura ou titulo |
| `stock.picking` | Picking | Transferencia de estoque |
| `res.partner` | Parceiro | Cliente ou Fornecedor |
| `account.full.reconcile` | Conciliacao | Conciliacao total de titulos |
| `account.partial.reconcile` | Conc. Parcial | Conciliacao parcial |
| `account.bank.statement.line` | Extrato | Linha de extrato bancario |

## Modelos e Campos-Chave

### Fluxo de Compra

| Modelo | Campo | Tipo | Relaciona com | Descrição |
|--------|-------|------|---------------|-----------|
| `purchase.requisition` | `purchase_ids` | one2many | `purchase.order` | POs da requisição |
| `purchase.order` | `requisition_id` | many2one | `purchase.requisition` | Requisição vinculada |
| `purchase.order` | `invoice_ids` | many2many | `account.move` | Faturas do PO |
| `l10n_br_ciel_it_account.dfe` | `purchase_id` | many2one | `purchase.order` | PO vinculado ao DFE |
| `l10n_br_ciel_it_account.dfe` | `invoice_ids` | one2many | `account.move` | Faturas do DFE |

### Fluxo de Venda

| Modelo | Campo | Tipo | Relaciona com | Descrição |
|--------|-------|------|---------------|-----------|
| `sale.order` | `picking_ids` | one2many | `stock.picking` | Transferências |
| `sale.order` | `invoice_ids` | many2many | `account.move` | Faturas |
| `stock.picking` | `sale_id` | many2one | `sale.order` | Pedido de venda |
| `account.move` | `invoice_origin` | char | - | Origem ("SO00123", "PO00456") |
| `account.move` | `picking_ids` | many2many | `stock.picking` | Pickings vinculados |

### Fluxo Financeiro

| Modelo | Campo | Tipo | Relaciona com | Descrição |
|--------|-------|------|---------------|-----------|
| `account.move` | `line_ids` | one2many | `account.move.line` | Linhas do diário |
| `account.move` | `invoice_line_ids` | one2many | `account.move.line` | Linhas da fatura |
| `account.move` | `statement_line_ids` | one2many | `account.bank.statement.line` | Extrato |
| `account.move` | `l10n_br_chave_nf` | char | - | Chave NF-e 44 dígitos |
| `account.move.line` | `full_reconcile_id` | many2one | `account.full.reconcile` | Conciliação |
| `account.move.line` | `statement_line_id` | many2one | `account.bank.statement.line` | Linha extrato |
| `account.move.line` | `reconciled` | boolean | - | Se está conciliado |
| `account.full.reconcile` | `reconciled_line_ids` | one2many | `account.move.line` | Linhas conciliadas |
| `account.bank.statement.line` | `move_id` | many2one | `account.move` | Lançamento vinculado |

### Fluxo de Devolução

| Modelo | Campo | Tipo | Relaciona com | Descrição |
|--------|-------|------|---------------|-----------|
| `l10n_br_ciel_it_account.dfe` | `nfe_infnfe_ide_finnfe` | char | - | Finalidade (4=devolução) |
| `account.move` | `reversed_entry_id` | many2one | `account.move` | Fatura revertida |
| `account.move` | `referencia_ids` | one2many | - | NF-e de referência |

### Parceiros

| Modelo | Campo | Tipo | Descrição |
|--------|-------|------|-----------|
| `res.partner` | `l10n_br_cnpj` | char | CNPJ |
| `res.partner` | `name` | char | Nome/Razão Social |

## Tipos de Documento (move_type)

| Código | Descrição | Fluxo |
|--------|-----------|-------|
| `out_invoice` | Fatura Cliente | Venda |
| `out_refund` | Nota Crédito Cliente | Devolução Venda |
| `in_invoice` | Fatura Fornecedor | Compra |
| `in_refund` | Nota Crédito Fornecedor | Devolução Compra |
| `entry` | Lançamento Contábil | - |

## Tipos de DFE (finnfe)

| Código | Descrição |
|--------|-----------|
| `1` | Normal |
| `2` | Complementar |
| `3` | Ajuste |
| `4` | Devolução |

## Estratégias de Navegação

### A partir de NF de Compra (DFE)
```
DFE → purchase_id → purchase.order
DFE → invoice_ids → account.move
account.move → line_ids (account_type=payable) → títulos
account.move.line → full_reconcile_id → conciliação
```

### A partir de NF de Venda
```
account.move (out_invoice) → invoice_origin → sale.order
sale.order → picking_ids → stock.picking
account.move → line_ids (account_type=receivable) → títulos
account.move.line → full_reconcile_id → conciliação
```

### A partir de Devolução
```
DFE (finnfe=4) → invoice_ids → account.move (refund)
account.move → reversed_entry_id → NF original
account.move → referencia_ids → chaves NF originais
NF original → invoice_origin → sale.order/purchase.order
```

### A partir de Título
```
account.move.line → move_id → account.move (fatura)
account.move → invoice_origin → sale.order/purchase.order
account.move.line → full_reconcile_id → account.full.reconcile
account.full.reconcile → reconciled_line_ids → outras linhas conciliadas
```

### A partir de Fatura (busca inversa para DFE)
```
# Buscar DFE vinculado a uma Invoice pelo campo invoice_ids
account.move (invoice_id) → DFE.invoice_ids (contains invoice_id) → l10n_br_ciel_it_account.dfe
```

**Exemplo Python:**
```python
# Dado invoice_id = 426987, encontrar o DFE
dfes = odoo.search_read('l10n_br_ciel_it_account.dfe',
    [('invoice_ids', 'in', [426987])],
    fields=['id', 'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf',
            'nfe_infnfe_total_icmstot_vnf'])
```

## Campos de Impostos (DFE)

| Campo | Descricao | Uso |
|-------|-----------|-----|
| `nfe_infnfe_total_icmstot_vnf` | Valor Total NF | Valor total do documento |
| `nfe_infnfe_total_icmstot_vicms` | Valor ICMS | Imposto estadual |
| `nfe_infnfe_total_icmstot_vbcicms` | Base ICMS | Base de calculo ICMS |
| `nfe_infnfe_total_icmstot_vpis` | Valor PIS | Imposto federal PIS |
| `nfe_infnfe_total_icmstot_vcofins` | Valor COFINS | Imposto federal COFINS |
| `nfe_infnfe_total_icmstot_vprod` | Valor Produtos | Valor dos produtos/servicos |

---

## Fluxo de Conciliacao Bancaria

### Visao Geral

O pagamento a fornecedor no Odoo envolve uma conciliacao em DUAS etapas:

```
EXTRATO ←→ PAYMENT ←→ TÍTULO
   (A)         (B)
```

### Modelos Envolvidos na Conciliacao

| Modelo | Papel | Conta Contabil |
|--------|-------|----------------|
| `account.bank.statement.line` | Linha do extrato bancario | BANCO (ativo) |
| `account.payment` | Pagamento (elo de ligacao) | PENDENTES + FORNECEDORES |
| `account.move.line` | Titulo a pagar (da fatura) | FORNECEDORES (passivo) |
| `account.full.reconcile` | Conciliacao completa | - |

### Contas Contabeis

| ID | Codigo | Nome | Uso |
|----|--------|------|-----|
| 22199 | 1110100003 | TRANSITORIA DE VALORES | Conta temporaria do extrato |
| 26868 | 1110100004 | PAGAMENTOS/RECEBIMENTOS PENDENTES | Conta para conciliacao |
| Varia | 2111100001 | FORNECEDORES | Conta de passivo |

### Campos-Chave para Conciliacao

#### account.bank.statement.line (Extrato)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | int | ID da linha de extrato |
| `move_id` | many2one | Lancamento contabil do extrato |
| `is_reconciled` | boolean | Se esta totalmente conciliado |
| `amount_residual` | float | Valor restante (suporta 1:N) |
| `partner_id` | many2one | Parceiro (pode estar vazio) |
| `journal_id` | many2one | Diario/Conta bancaria |

#### account.move.line (Titulo)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | int | ID do titulo |
| `move_id` | many2one | Fatura (account.move) |
| `account_type` | char | `liability_payable` = a pagar |
| `date_maturity` | date | Vencimento |
| `credit` | float | Valor a pagar |
| `amount_residual` | float | Saldo em aberto |
| `reconciled` | boolean | Se esta conciliado |
| `full_reconcile_id` | many2one | Conciliacao completa |
| `l10n_br_cobranca_parcela` | int | Numero da parcela (1, 2, 3...) |
| `statement_line_id` | many2one | Extrato direto (raro) |

#### account.payment (Pagamento)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | int | ID do pagamento |
| `name` | char | Numero (PSIC/2025/00156) |
| `move_id` | many2one | Lancamento do pagamento |
| `amount` | float | Valor |
| `payment_type` | char | `outbound` = pagamento |
| `partner_type` | char | `supplier` = fornecedor |
| `partner_id` | many2one | Parceiro |
| `journal_id` | many2one | Diario/Conta bancaria |

#### account.move (Fatura)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_chave_nf` | char | Chave NF-e 44 digitos |
| `l10n_br_numero_nota_fiscal` | char | Numero da NF |
| `reversed_entry_id` | many2one | Fatura estornada (se NC) |

### Estrategia de Navegacao: Extrato → Titulo

```
1. account.bank.statement.line (extrato)
   └── move_id → account.move (lancamento do extrato)
       └── line_ids → account.move.line (linhas do extrato)
           └── full_reconcile_id → account.full.reconcile (Conciliacao A)

2. account.full.reconcile (Conciliacao A)
   └── reconciled_line_ids → account.move.line (todas as linhas)
       └── Filtrar: linha do account.payment (move_id != extrato)

3. account.payment
   └── move_id → account.move (lancamento do payment)
       └── line_ids (debit > 0, account_type=liability_payable)
           └── full_reconcile_id → account.full.reconcile (Conciliacao B)

4. account.full.reconcile (Conciliacao B)
   └── reconciled_line_ids → account.move.line (titulo da fatura)
       └── move_id → account.move (FATURA!)
```

### Regras de Validacao do Odoo

| Regra | Modelo | Condicao |
|-------|--------|----------|
| Saldo zerado | account.move.line | `reconciled=True` quando `amount_residual=0` |
| Conciliacao completa | account.full.reconcile | Soma debitos = soma creditos |
| Parceiro obrigatorio | account.payment | Partner igual ao da fatura |
| Conta compativel | account.move.line | So concilia mesma conta contabil |
| Mesmo parceiro | account.move.line | Linhas conciliadas devem ter mesmo `partner_id` |
| Estado posted | account.move | So concilia lancamentos `state='posted'` |

### Mapeamento de Vinculos (5 Visoes Cruzadas)

Para identificar registros "soltos" (sem vinculo), extrair:

1. **EXTRATOS** → titulo_ids, fatura_ids, nc_ids, payment_ids
2. **TITULOS** → extrato_ids, fatura_id, nc_ids, payment_ids
3. **FATURAS** → titulo_ids, extrato_ids, nc_ids
4. **NOTAS CREDITO** → fatura_origem_id, titulo_ids, extrato_ids
5. **PAGAMENTOS** → extrato_ids, titulo_ids

Script: `scripts/mapeamento_vinculos_completo.py`
