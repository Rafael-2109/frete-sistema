# Mapeamento de Relacionamentos Odoo

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
