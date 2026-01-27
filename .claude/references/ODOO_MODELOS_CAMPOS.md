# Modelos Odoo - Campos e Relacionamentos

**Ultima verificacao:** Janeiro/2026

---

## MODELOS INEXISTENTES (NAO USAR)

**ATENCAO**: Os seguintes modelos NAO EXISTEM nesta instalacao do Odoo. Sao comuns em outras implementacoes de localizacao brasileira mas NAO estao disponiveis aqui.

| Modelo INEXISTENTE | Modelo CORRETO | Observacao |
|--------------------|----------------|------------|
| `l10n_br_fiscal.document` | `l10n_br_ciel_it_account.dfe` | DFe/NFe |
| `l10n_br_fiscal.document.line` | `l10n_br_ciel_it_account.dfe.line` | Linhas do DFe |
| `l10n_br_fiscal.cfop` | Campo `det_prod_cfop` (char) | CFOP eh campo texto |

### Mapeamento de Campos (l10n_br_fiscal.document → l10n_br_ciel_it_account.dfe)

| Campo ERRADO | Campo CORRETO |
|--------------|---------------|
| `document_type_id.code` | `nfe_infnfe_ide_finnfe` |
| `state_edoc` | `l10n_br_status` |
| `date` | `nfe_infnfe_ide_dhemi` |
| `number` | `nfe_infnfe_ide_nnf` |
| `document_serie` | `nfe_infnfe_ide_serie` |
| `document_key` | `protnfe_infnfe_chnfe` |
| `partner_cnpj_cpf` | `nfe_infnfe_emit_cnpj` |
| `fiscal_additional_data` | `nfe_infnfe_infadic_infcpl` |
| `amount_total` | `nfe_infnfe_total_icmstot_vnf` |

### Mapeamento de Campos (l10n_br_fiscal.document.line → l10n_br_ciel_it_account.dfe.line)

| Campo ERRADO | Campo CORRETO |
|--------------|---------------|
| `document_id` | `dfe_id` |
| `cfop_id` (many2one) | `det_prod_cfop` (char) |
| `quantity` | `det_prod_qcom` |
| `product_id` | `product_id` (mesmo) |

---

## Documentos Fiscais Eletronicos (DFe)

### l10n_br_ciel_it_account.dfe

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID do registro |
| name | char | Nome/numero do documento |
| l10n_br_status | selection | Status do DFe (01-07) |
| l10n_br_tipo_pedido | selection | compra, venda, transferencia |
| protnfe_infnfe_chnfe | char | Chave de acesso NFe/CTe |
| nfe_infnfe_ide_nnf | char | Numero da nota |
| nfe_infnfe_emit_cnpj | char | CNPJ emitente |
| nfe_infnfe_dest_cnpj | char | CNPJ destinatario |
| is_cte | boolean | Se eh CTe |
| purchase_id | many2one | → purchase.order (PO vinculado) |
| purchase_fiscal_id | many2one | → purchase.order (PO escrituracao) |
| partner_id | many2one | → res.partner |

#### Status DFe (l10n_br_status)

| Codigo | Nome | Significado | Acao |
|--------|------|-------------|------|
| 01 | Rascunho | Recem-importado | Aguardar |
| 02 | Sincronizado | Sincronizado SEFAZ | Aguardar |
| 03 | Ciencia | Ciencia confirmada | Aguardar |
| **04** | **PO Vinculado** | **ALVO DE VALIDACAO** | **Processar** |
| 05 | Rateio | Em rateio | Aguardar |
| 06 | Concluido | Finalizado | Ignorar |
| 07 | Rejeitado | Documento rejeitado | Ignorar |

### l10n_br_ciel_it_account.dfe.line

| Campo | Tipo | Descricao |
|-------|------|-----------|
| dfe_id | many2one | → dfe |
| product_id | many2one | → product.product |
| det_prod_cprod | char | Codigo produto fornecedor |
| det_prod_xprod | char | Nome produto NF |
| det_prod_qcom | float | Quantidade comercial |
| det_prod_ucom | char | Unidade medida |
| det_prod_vuncom | float | Valor unitario |

---

## Compras

### purchase.order

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Numero do PO (ex: PO00123) |
| partner_id | many2one | → res.partner (fornecedor) |
| state | selection | draft, sent, purchase, done, cancel |
| dfe_id | many2one | → dfe (DFe vinculado) |
| l10n_br_operacao_id | many2one | Operacao fiscal |
| company_id | many2one | → res.company |
| picking_type_id | many2one | → stock.picking.type |
| partner_ref | char | Referencia fornecedor |
| order_line | one2many | → purchase.order.line |
| picking_ids | one2many | → stock.picking |
| invoice_ids | many2many | → account.move |

### purchase.order.line

| Campo | Tipo | Descricao |
|-------|------|-----------|
| order_id | many2one | → purchase.order |
| product_id | many2one | → product.product |
| product_qty | float | Quantidade pedida |
| price_unit | float | Preco unitario |
| qty_received | float | Quantidade recebida |
| l10n_br_operacao_id | many2one | Operacao fiscal linha |

---

## Vendas

### sale.order

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Numero do pedido |
| partner_id | many2one | → res.partner |
| state | selection | draft, sent, sale, done, cancel |
| commitment_date | datetime | Data compromisso entrega |
| tag_ids | many2many | → crm.tag |
| order_line | one2many | → sale.order.line |

### sale.order.line

| Campo | Tipo | Descricao |
|-------|------|-----------|
| order_id | many2one | → sale.order |
| product_id | many2one | → product.product |
| product_uom_qty | float | Quantidade |
| price_unit | float | Preco unitario |
| qty_delivered | float | Quantidade entregue |
| qty_invoiced | float | Quantidade faturada |

### crm.tag

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Nome da tag |
| color | int | Cor (1-11) |

---

## Estoque e Movimentacoes

### stock.picking

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Nome (ex: WH/IN/00123) |
| state | selection | draft, waiting, confirmed, assigned, done, cancel |
| purchase_id | many2one | → purchase.order |
| location_id | many2one | Origem |
| location_dest_id | many2one | Destino |
| picking_type_id | many2one | Tipo operacao |
| move_ids | one2many | → stock.move |
| move_line_ids | one2many | → stock.move.line |

### stock.move

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| picking_id | many2one | → stock.picking |
| product_id | many2one | → product.product |
| product_uom_qty | float | Quantidade demandada |
| quantity | float | Quantidade feita |
| state | selection | draft, waiting, confirmed, assigned, done, cancel |
| move_line_ids | one2many | → stock.move.line |

### stock.move.line

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| picking_id | many2one | → stock.picking |
| move_id | many2one | → stock.move |
| product_id | many2one | → product.product |
| lot_id | many2one | → stock.lot (lote existente) |
| lot_name | char | Nome lote (criar novo) |
| **quantity** | float | **Quantidade reservada** |
| **qty_done** | float | **Quantidade realizada** |
| location_id | many2one | Origem |
| location_dest_id | many2one | Destino |

> **ATENCAO:** `reserved_uom_qty` NAO EXISTE! Usar `quantity` para reservado.

### stock.lot

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Nome do lote (UNIQUE com product_id + company_id) |
| product_id | many2one | → product.product |
| company_id | many2one | → res.company (OBRIGATORIO no create) |
| expiration_date | datetime | Data de validade (formato: '2026-06-15 00:00:00') |

> **IMPORTANTE:** Para produtos com `use_expiration_date=True`, e necessario criar o stock.lot MANUALMENTE via `create()` antes de usar `lot_id` no stock.move.line. O `lot_name` NAO propaga a data de validade.

---

## Qualidade

### quality.check

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| picking_id | many2one | → stock.picking |
| product_id | many2one | → product.product |
| test_type | selection | passfail, measure |
| quality_state | selection | none, pass, fail |
| measure | float | Valor medido (para test_type=measure) |

**Metodos:**
- `do_pass()` - Aprovar check tipo passfail
- `do_fail()` - Reprovar check tipo passfail
- `do_measure()` - Finalizar check tipo measure (apos write no campo measure)

---

## Financeiro

### account.move

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Numero documento |
| state | selection | draft, posted, cancel |
| move_type | selection | entry, out_invoice, in_invoice, etc |
| invoice_date | date | Data fatura |
| l10n_br_numero_nota_fiscal | char | Numero NF |
| payment_reference | char | Referencia pagamento |
| partner_id | many2one | → res.partner |
| line_ids | one2many | → account.move.line |

### account.move.line

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| move_id | many2one | → account.move |
| account_id | many2one | → account.account |
| debit | float | Debito |
| credit | float | Credito |
| balance | float | Saldo (debit - credit) |
| partner_id | many2one | → res.partner |
| reconciled | boolean | Se esta conciliado |
| amount_residual | float | Saldo em aberto (nao pago/reconciliado) |
| l10n_br_cobranca_parcela | int | Numero da parcela (1, 2, 3...) |

### account.payment

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Nome |
| amount | float | Valor |
| journal_id | many2one | → account.journal |
| partner_id | many2one | → res.partner |
| state | selection | draft, posted, cancel |
| payment_type | selection | inbound, outbound |

### account.journal

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Nome |
| type | selection | sale, purchase, bank, cash, general |
| company_id | many2one | → res.company |

### account.bank.statement.line (Extrato Bancario)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| date | date | Data da transacao |
| amount | float | Valor (+ credito, - debito) |
| amount_residual | float | Saldo nao reconciliado (suporta conciliacao 1:N) |
| payment_ref | char | Referencia (contem CNPJ, nome - usar regex) |
| partner_id | many2one | → res.partner (pode ser False) |
| partner_name | char | Nome do parceiro do extrato |
| journal_id | many2one | → account.journal |
| move_id | many2one | → account.move (lancamento contabil) |
| is_reconciled | boolean | Se esta totalmente conciliado |

---

## Cadastros

### res.partner

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| name | char | Nome/Razao Social |
| l10n_br_cnpj | char | CNPJ (formatado) |
| l10n_br_cpf | char | CPF |
| state_id | many2one | → res.country.state |
| l10n_br_municipio_id | many2one | Municipio |
| email | char | Email |
| phone | char | Telefone |

### product.product

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| default_code | char | Codigo interno |
| name | char | Nome |
| uom_id | many2one | → uom.uom |
| categ_id | many2one | Categoria |
| tracking | selection | none, lot, serial |
| type | selection | consu, product, service |
| use_expiration_date | boolean | Se produto usa data de validade (impacta criacao de lotes) |

### product.supplierinfo (De-Para Fornecedor)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | int | ID |
| partner_id | many2one | → res.partner (fornecedor) |
| product_tmpl_id | many2one | → product.template |
| product_code | char | Codigo do fornecedor |
| min_qty | float | Quantidade minima |
| price | float | Preco |

---

## Diagrama de Relacionamentos

```
                        ┌──────────────────┐
                        │  l10n_br_ciel_   │
                        │  it_account.dfe  │
                        └────────┬─────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │ purchase_id        │ purchase_fiscal_id │
            ▼                    │                    ▼
    ┌───────────────┐            │            ┌───────────────┐
    │ purchase.order│◄───────────┘            │ purchase.order│
    │   (Compra)    │                         │ (Escrituracao)│
    └───────┬───────┘                         └───────────────┘
            │
    ┌───────┼───────────────────┐
    │       │ picking_ids       │ invoice_ids
    ▼       ▼                   ▼
┌────────┐ ┌─────────────┐ ┌─────────────┐
│  PO    │ │stock.picking│ │account.move │
│ .line  │ └──────┬──────┘ └──────┬──────┘
└────────┘        │               │
                  │ move_line_ids │ line_ids
                  ▼               ▼
           ┌─────────────┐ ┌─────────────┐
           │stock.move   │ │account.move │
           │   .line     │ │   .line     │
           └──────┬──────┘ └─────────────┘
                  │ lot_id
                  ▼
           ┌─────────────┐
           │ stock.lot   │
           └─────────────┘
```
