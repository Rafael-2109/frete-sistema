# Campos dos Modelos de Compra

**Modelos Odoo:** `purchase.order` e `purchase.order.line`
**Descricao:** Pedidos de compra, itens e tributos
**Total de Campos:** 165 (order) + 201 (line) = 366

---

## purchase.order - Pedido de Compra

### Campos de Identificacao

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID interno | PK |
| `name` | char | Numero do PO | Ex: PO00123 |
| `partner_ref` | char | Referencia do fornecedor | Numero pedido fornecedor |
| `origin` | char | Documento origem | Ex: SO0001 |
| `company_id` | many2one | Empresa | Empresa do sistema |

---

### Campos de Status

| Campo | Tipo | Valores | Descricao |
|-------|------|---------|-----------|
| `state` | selection | draft, sent, to approve, purchase, done, cancel | Status do pedido |
| `invoice_status` | selection | no, to invoice, invoiced | Status faturamento |
| `receipt_status` | selection | pending, partial, full | Status recebimento |

**Valores state:**
- `draft` = Rascunho/Cotacao
- `sent` = Cotacao Enviada
- `to approve` = Aguardando Aprovacao
- `purchase` = Pedido Confirmado
- `done` = Concluido
- `cancel` = Cancelado

**Valores invoice_status:**
- `no` = Nada a Faturar
- `to invoice` = Aguardando Faturamento
- `invoiced` = Totalmente Faturado

**Valores receipt_status:**
- `pending` = Aguardando
- `partial` = Parcialmente Recebido
- `full` = Totalmente Recebido

---

### Campos de Datas

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `date_order` | datetime | Data do pedido | 2025-12-02 10:30:00 |
| `date_planned` | datetime | Data prevista entrega | 2025-12-10 |
| `date_approve` | datetime | Data aprovacao | Auto |
| `effective_date` | datetime | Data efetiva entrega | Auto |
| `create_date` | datetime | Data criacao | Auto |
| `write_date` | datetime | Ultima atualizacao | Auto |

> **IMPORTANTE:** `date_order` eh o campo principal para filtrar pedidos por periodo

---

### Campos de Valores

| Campo | Tipo | Descricao | Formato |
|-------|------|-----------|---------|
| `amount_total` | monetary | **Valor total** | R$ 10.000,00 |
| `amount_untaxed` | monetary | Valor sem impostos | R$ 9.000,00 |
| `amount_tax` | monetary | Total impostos | R$ 1.000,00 |
| `currency_id` | many2one | Moeda | BRL |

---

### Campos de Parceiro/Fornecedor

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_id` | many2one | Fornecedor (res.partner) |
| `partner_contact_id` | many2one | Contato |
| `dest_address_id` | many2one | Endereco entrega (dropship) |
| `user_id` | many2one | Comprador responsavel |
| `team_id` | many2one | Equipe de compras |

---

### Campos de Logistica

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `picking_type_id` | many2one | Tipo de operacao |
| `picking_ids` | many2many | Recebimentos vinculados |
| `incoming_picking_count` | integer | Contagem recebimentos |
| `incoterm_id` | many2one | Tipo de Frete (Incoterm) |
| `incoterm_location` | char | Local Incoterm |

---

### Campos Brasileiros (l10n_br_*)

#### Totalizadores Fiscais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_total_nfe` | float | Total da NF-e |
| `l10n_br_prod_valor` | float | Total produtos |
| `l10n_br_frete` | float | Total frete |
| `l10n_br_seguro` | float | Total seguro |
| `l10n_br_desc_valor` | float | Total desconto |
| `l10n_br_despesas_acessorias` | float | Despesas acessorias |
| `l10n_br_total_tributos` | float | Total tributos |

#### Impostos Totalizados
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icms_base` | float | Base ICMS |
| `l10n_br_icms_valor` | float | Total ICMS |
| `l10n_br_icmsst_base` | float | Base ICMS-ST |
| `l10n_br_icmsst_valor` | float | Total ICMS-ST |
| `l10n_br_ipi_valor` | float | Total IPI |
| `l10n_br_pis_valor` | float | Total PIS |
| `l10n_br_cofins_valor` | float | Total COFINS |
| `l10n_br_ii_valor` | float | Total II (Importacao) |

#### Retencoes
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_pis_ret_valor` | float | PIS Retido |
| `l10n_br_cofins_ret_valor` | float | COFINS Retido |
| `l10n_br_csll_ret_valor` | float | CSLL Retido |
| `l10n_br_irpj_ret_valor` | float | IRPJ Retido |
| `l10n_br_inss_ret_valor` | float | INSS Retido |

#### Configuracoes Fiscais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_cfop_id` | many2one | CFOP padrao |
| `l10n_br_tipo_pedido` | selection | Tipo do pedido |
| `l10n_br_compra_indcom` | selection | Destinacao de uso |
| `l10n_br_operacao_id` | many2one | Operacao fiscal |
| `l10n_br_operacao_consumidor` | selection | Operacao consumidor final |
| `l10n_br_calcular_imposto` | boolean | Calcular impostos |
| `l10n_br_imposto_auto` | boolean | Impostos automaticos |

#### Informacoes Complementares
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_informacao_complementar` | text | Info complementar |
| `l10n_br_informacao_fiscal` | text | Info fiscal |

---

### Campos de Relacionamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `order_line` | one2many | Linhas do pedido |
| `invoice_ids` | many2many | Faturas vinculadas |
| `invoice_count` | integer | Contagem faturas |
| `dfe_id` | many2one | Documento fiscal (DFE) |
| `requisition_id` | many2one | Contrato guarda-chuva |
| `request_id` | many2one | Solicitacao de compra |

---

## purchase.order.line - Linha do Pedido

### Campos de Identificacao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID interno |
| `name` | text | Descricao |
| `order_id` | many2one | **Pedido pai** |
| `product_id` | many2one | Produto |
| `partner_id` | many2one | Fornecedor |

---

### Campos de Quantidade

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `product_qty` | float | **Quantidade pedida** | Principal |
| `qty_received` | float | Quantidade recebida | Recebimento |
| `qty_invoiced` | float | Quantidade faturada | Faturamento |
| `qty_to_invoice` | float | Quantidade a faturar | Calculado |
| `product_uom` | many2one | Unidade de medida | UN, KG, CX |
| `product_uom_qty` | float | Quantidade total | Calculado |

---

### Campos de Valores

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `price_unit` | float | **Preco unitario** | Principal |
| `price_subtotal` | monetary | Subtotal | Sem impostos |
| `price_total` | monetary | Total | Com impostos |
| `price_tax` | float | Valor impostos | Calculado |
| `discount` | float | Desconto (%) | Percentual |

---

### Campos de Datas

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `date_planned` | datetime | Data prevista entrega |
| `date_order` | datetime | Data do pedido (pai) |
| `date_approve` | datetime | Data aprovacao (pai) |

---

### Campos Fiscais Brasileiros (l10n_br_*)

#### CFOP e Origem
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_cfop_id` | many2one | CFOP |
| `l10n_br_cfop_codigo` | char | Codigo CFOP |
| `l10n_br_origem` | selection | Origem do produto |
| `l10n_br_compra_indcom` | selection | Destinacao de uso |

#### Valores
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_prod_valor` | float | Valor do produto |
| `l10n_br_total_nfe` | float | Valor total item |
| `l10n_br_unit_nfe` | float | Valor unitario NF |
| `l10n_br_frete` | float | Frete |
| `l10n_br_seguro` | float | Seguro |
| `l10n_br_desc_valor` | float | Desconto |
| `l10n_br_despesas_acessorias` | float | Despesas acessorias |
| `l10n_br_total_tributos` | float | Total tributos |

#### ICMS
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icms_cst` | selection | CST ICMS |
| `l10n_br_icms_base` | float | Base ICMS |
| `l10n_br_icms_aliquota` | float | Aliquota ICMS (%) |
| `l10n_br_icms_valor` | float | Valor ICMS |
| `l10n_br_icms_modalidade_base` | selection | Modalidade BC |
| `l10n_br_icms_reducao_base` | float | Reducao BC (%) |
| `l10n_br_icms_valor_isento` | float | ICMS Isento |
| `l10n_br_icms_valor_outros` | float | ICMS Outros |
| `l10n_br_icms_valor_desonerado` | float | ICMS Desonerado |

#### ICMS-ST
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icmsst_base` | float | Base ICMS-ST |
| `l10n_br_icmsst_aliquota` | float | Aliquota ICMS-ST (%) |
| `l10n_br_icmsst_valor` | float | Valor ICMS-ST |
| `l10n_br_icmsst_mva` | float | MVA (%) |
| `l10n_br_icmsst_reducao_base` | float | Reducao BC ST (%) |
| `l10n_br_icmsst_retido_base` | float | Base ST Retido |
| `l10n_br_icmsst_retido_valor` | float | Valor ST Retido |

#### ICMS Partilha (UF Destino)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icms_dest_base` | float | Base ICMS Destino |
| `l10n_br_icms_dest_aliquota` | float | Aliquota Destino (%) |
| `l10n_br_icms_dest_valor` | float | Valor ICMS Destino |
| `l10n_br_icms_remet_valor` | float | Valor ICMS Remetente |
| `l10n_br_fcp_dest_valor` | float | Valor FCP |

#### IPI
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_ipi_cst` | selection | CST IPI |
| `l10n_br_ipi_base` | float | Base IPI |
| `l10n_br_ipi_aliquota` | float | Aliquota IPI (%) |
| `l10n_br_ipi_valor` | float | Valor IPI |
| `l10n_br_ipi_enq` | char | Enquadramento |
| `l10n_br_ipi_valor_isento` | float | IPI Isento |
| `l10n_br_ipi_valor_outros` | float | IPI Outros |

#### PIS
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_pis_cst` | selection | CST PIS |
| `l10n_br_pis_base` | float | Base PIS |
| `l10n_br_pis_aliquota` | float | Aliquota PIS (%) |
| `l10n_br_pis_valor` | float | Valor PIS |
| `l10n_br_pis_ret_valor` | float | PIS Retido |

#### COFINS
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_cofins_cst` | selection | CST COFINS |
| `l10n_br_cofins_base` | float | Base COFINS |
| `l10n_br_cofins_aliquota` | float | Aliquota COFINS (%) |
| `l10n_br_cofins_valor` | float | Valor COFINS |
| `l10n_br_cofins_ret_valor` | float | COFINS Retido |

#### II (Importacao)
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_ii_base` | float | Base II |
| `l10n_br_ii_aliquota` | float | Aliquota II (%) |
| `l10n_br_ii_valor` | float | Valor II |
| `l10n_br_ii_valor_aduaneira` | float | Valor Aduaneira |
| `l10n_br_ii_valor_afrmm` | float | Valor AFRMM |

#### Custo de Estoque
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_custo_estoque` | float | Custo unitario estoque |
| `l10n_br_custo_estoque_fator` | float | Fator custo |
| `l10n_br_custo_estoque_total` | float | Custo total estoque |

---

### Campos de Estoque

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `qty_available` | float | Quantidade em estoque |
| `virtual_available` | float | Quantidade projetada |
| `move_ids` | one2many | Movimentos estoque |
| `move_dest_ids` | many2many | Movimentos destino |

---

### Campos de Relacionamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `invoice_lines` | one2many | Linhas de fatura |
| `sale_line_id` | many2one | Linha venda origem |
| `sale_order_id` | many2one | Pedido venda origem |
| `dfe_line_id` | many2one | Linha DFE |

---

## Filtros Uteis

### purchase.order

```python
# Pedidos pendentes de aprovacao
[('state', 'in', ['draft', 'sent', 'to approve'])]

# Pedidos confirmados
[('state', '=', 'purchase')]

# Pedidos aguardando faturamento
[('invoice_status', '=', 'to invoice')]

# Por fornecedor
[('partner_id.name', 'ilike', 'vale sul')]

# Por CNPJ
[('partner_id.vat', 'ilike', '32451351')]

# Por periodo
[('date_order', '>=', '2025-11-01'), ('date_order', '<=', '2025-11-30')]

# Por valor minimo
[('amount_total', '>=', 10000)]

# Por origem (pedido de venda)
[('origin', 'ilike', 'SO0001')]
```

### purchase.order.line

```python
# Linhas de um PO
[('order_id', '=', po_id)]

# Linhas com recebimento pendente
[('qty_received', '<', 'product_qty')]

# Por produto
[('product_id.name', 'ilike', 'pupunha')]

# Com ICMS-ST
[('l10n_br_icmsst_valor', '>', 0)]

# Por CFOP
[('l10n_br_cfop_codigo', '=', '5102')]
```

---

## Relacionamento entre Modelos

```
purchase.order (Pedido de Compra)
    │
    ├── partner_id → res.partner
    │   └── Fornecedor (dados cadastrais, CNPJ)
    │
    ├── order_line → purchase.order.line
    │   └── Itens do pedido (produtos, qtd, precos)
    │
    ├── invoice_ids → account.move
    │   └── Faturas/Contas a pagar
    │
    ├── picking_ids → stock.picking
    │   └── Recebimentos de mercadoria
    │
    ├── dfe_id → l10n_br_ciel_it_account.dfe
    │   └── Documento fiscal (NF-e de entrada)
    │
    └── user_id → res.users
        └── Comprador responsavel
```

---

## Atualizacoes

| Data | Alteracao |
|------|-----------|
| 02/12/2025 | Documento criado com mapeamento completo |
