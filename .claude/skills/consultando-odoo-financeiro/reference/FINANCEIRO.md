# Campos dos Modelos Financeiros

**Modelos Odoo:** `account.move` e `account.move.line`
**Descricao:** Faturas, contas a pagar/receber, parcelas e vencimentos
**Total de Campos:** 376 (move) + 315 (line) = 691

---

## account.move - Faturas/Documentos

### Campos de Identificacao

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID interno | PK |
| `name` | char | Numero do documento | Ex: INV/2025/0001 |
| `ref` | char | Referencia | Referencia externa |
| `partner_id` | many2one | Parceiro | Cliente ou Fornecedor |
| `commercial_partner_id` | many2one | Parceiro comercial | Empresa pai |
| `company_id` | many2one | Empresa | Empresa do sistema |
| `journal_id` | many2one | Diario | Diario contabil |

---

### Campos de Tipo e Status

| Campo | Tipo | Valores | Descricao |
|-------|------|---------|-----------|
| `move_type` | selection | out_invoice, in_invoice, out_refund, in_refund, entry | Tipo documento |
| `state` | selection | draft, posted, cancel | Status documento |
| `payment_state` | selection | not_paid, partial, paid, in_payment, reversed | Status pagamento |

**Valores move_type:**
- `out_invoice` = Fatura cliente (a receber)
- `out_refund` = Nota credito cliente
- `in_invoice` = Fatura fornecedor (a pagar)
- `in_refund` = Nota credito fornecedor
- `entry` = Lancamento contabil

**Valores state:**
- `draft` = Rascunho
- `posted` = Lancado/Confirmado
- `cancel` = Cancelado

**Valores payment_state:**
- `not_paid` = Nao pago
- `partial` = Parcialmente pago
- `paid` = Totalmente pago
- `in_payment` = Em processamento
- `reversed` = Estornado

---

### Campos de Datas

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `date` | date | Data contabil | 2025-12-02 |
| `invoice_date` | date | Data da fatura | 2025-12-01 |
| `invoice_date_due` | date | **Data vencimento** | 2025-12-31 |
| `create_date` | datetime | Data criacao | Auto |
| `write_date` | datetime | Ultima atualizacao | Auto |

> **IMPORTANTE:** `invoice_date_due` eh o campo principal para filtrar vencimentos no account.move

---

### Campos de Valores

| Campo | Tipo | Descricao | Formato |
|-------|------|-----------|---------|
| `amount_total` | monetary | **Valor total** | R$ 1.000,00 |
| `amount_untaxed` | monetary | Valor sem impostos | R$ 900,00 |
| `amount_tax` | monetary | Total impostos | R$ 100,00 |
| `amount_residual` | monetary | **Valor em aberto** | R$ 500,00 |
| `amount_paid` | monetary | Valor pago | R$ 500,00 |
| `amount_total_signed` | monetary | Total com sinal | Negativo se a pagar |
| `amount_residual_signed` | monetary | Em aberto com sinal | Negativo se a pagar |

> **IMPORTANTE:**
> - `amount_residual` = valor ainda nao pago
> - `amount_residual > 0` = documento em aberto
> - `amount_residual = 0` = documento quitado

---

### Campos de Parceiro

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_id` | many2one | Parceiro (res.partner) |
| `commercial_partner_id` | many2one | Parceiro comercial |
| `partner_bank_id` | many2one | Banco do parceiro |
| `partner_credit` | monetary | Credito do parceiro |
| `partner_shipping_id` | many2one | Endereco entrega |
| `partner_invoice_id` | many2one | Endereco cobranca |

---

### Campos de Pagamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `payment_id` | many2one | Pagamento vinculado |
| `payment_ids` | one2many | Pagamentos |
| `payment_reference` | char | Referencia pagamento |
| `payment_state` | selection | Status pagamento |
| `invoice_payment_term_id` | many2one | Prazo pagamento |

---

### Campos Brasileiros (l10n_br_*)

#### Identificacao Fiscal
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_cnpj` | char | CNPJ do parceiro |
| `l10n_br_chave_nf` | char | Chave da NF-e (44 digitos) |
| `l10n_br_serie_nf` | char | Serie da NF |
| `l10n_br_situacao_nf` | selection | Situacao da NF-e |
| `l10n_br_cstat_nf` | char | Codigo status NF |
| `l10n_br_xmotivo_nf` | char | Mensagem status NF |

#### Totalizadores
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_total_nfe` | float | Total da NF |
| `l10n_br_prod_valor` | float | Total produtos |
| `l10n_br_frete` | float | Total frete |
| `l10n_br_seguro` | float | Total seguro |
| `l10n_br_desc_valor` | float | Total desconto |
| `l10n_br_despesas_acessorias` | float | Despesas acessorias |
| `l10n_br_total_tributos` | float | Total tributos |

#### Impostos Totalizados
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icms_valor` | float | Total ICMS |
| `l10n_br_icms_st_valor` | float | Total ICMS-ST |
| `l10n_br_ipi_valor` | float | Total IPI |
| `l10n_br_pis_valor` | float | Total PIS |
| `l10n_br_cofins_valor` | float | Total COFINS |

#### Retencoes
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_pis_ret_valor` | float | PIS Retido |
| `l10n_br_cofins_ret_valor` | float | COFINS Retido |
| `l10n_br_csll_ret_valor` | float | CSLL Retido |
| `l10n_br_irpj_ret_valor` | float | IRPJ Retido |
| `l10n_br_inss_ret_valor` | float | INSS Retido |
| `l10n_br_iss_ret_valor` | float | ISS Retido |

#### Configuracoes
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_tipo_documento` | selection | Tipo doc fiscal |
| `l10n_br_tipo_pedido` | selection | Tipo pedido (saida) |
| `l10n_br_tipo_pedido_entrada` | selection | Tipo pedido (entrada) |
| `l10n_br_cfop_id` | many2one | CFOP padrao |
| `l10n_br_carrier_id` | many2one | Transportadora |

---

## account.move.line - Parcelas/Itens

### Campos de Identificacao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `id` | integer | ID interno |
| `name` | char | Descricao da linha |
| `move_id` | many2one | **Documento pai** |
| `partner_id` | many2one | Parceiro |
| `account_id` | many2one | Conta contabil |
| `account_type` | selection | Tipo da conta |

---

### Campos de Valores

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `debit` | monetary | Valor debito | Entrada |
| `credit` | monetary | Valor credito | Saida |
| `balance` | monetary | Saldo (debit-credit) | Calculado |
| `amount_currency` | monetary | Valor moeda estrangeira | Multi-moeda |
| `amount_residual` | monetary | **Valor em aberto** | Parcela pendente |
| `amount_residual_currency` | monetary | Em aberto (moeda estr) | Multi-moeda |

---

### Campos de Vencimento

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `date` | date | Data contabil | 2025-12-02 |
| `date_maturity` | date | **Data vencimento** | 2025-12-31 |

> **IMPORTANTE:** `date_maturity` eh o campo principal para filtrar parcelas vencidas/a vencer

---

### Campos de Produto (para linhas de itens)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `product_id` | many2one | Produto |
| `product_uom_id` | many2one | Unidade medida |
| `quantity` | float | Quantidade |
| `price_unit` | float | Preco unitario |
| `price_subtotal` | monetary | Subtotal |
| `price_total` | monetary | Total com impostos |

---

### Campos de Cobranca Brasileiros

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_cobranca_nossonumero` | char | **Nosso Numero** (boleto) |
| `l10n_br_cobranca_situacao` | selection | Situacao cobranca |
| `l10n_br_cobranca_situacao_mensagem` | char | Mensagem situacao |
| `l10n_br_cobranca_parcela` | integer | Numero da parcela |
| `l10n_br_cobranca_protocolo` | char | Protocolo registro |
| `l10n_br_cobranca_idintegracao` | char | ID integracao banco |
| `l10n_br_cobranca_arquivo_remessa` | char | Arquivo remessa |
| `l10n_br_paga` | boolean | **Parcela paga?** |
| `l10n_br_pdf_boleto` | binary | PDF do boleto |
| `l10n_br_pdf_boleto_fname` | char | Nome arquivo boleto |

**Valores l10n_br_cobranca_situacao:**
- Registrado, Baixado, Pago, Protestado, etc.

---

### Campos de Tributos por Linha

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icms_base` | float | Base ICMS |
| `l10n_br_icms_aliquota` | float | Aliquota ICMS |
| `l10n_br_icms_valor` | float | Valor ICMS |
| `l10n_br_icms_cst` | selection | CST ICMS |
| `l10n_br_pis_base` | float | Base PIS |
| `l10n_br_pis_aliquota` | float | Aliquota PIS |
| `l10n_br_pis_valor` | float | Valor PIS |
| `l10n_br_cofins_base` | float | Base COFINS |
| `l10n_br_cofins_aliquota` | float | Aliquota COFINS |
| `l10n_br_cofins_valor` | float | Valor COFINS |
| `l10n_br_ipi_base` | float | Base IPI |
| `l10n_br_ipi_aliquota` | float | Aliquota IPI |
| `l10n_br_ipi_valor` | float | Valor IPI |

---

## Filtros Uteis

### account.move

```python
# Faturas de fornecedor (a pagar)
[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]

# Faturas de cliente (a receber)
[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]

# Em aberto (nao totalmente pago)
[('payment_state', 'in', ['not_paid', 'partial'])]

# Vencidas
[('invoice_date_due', '<', '2025-12-02'), ('payment_state', '!=', 'paid')]

# Por parceiro
[('partner_id.name', 'ilike', 'atacadao')]

# Por CNPJ
[('l10n_br_cnpj', 'ilike', '18467441')]

# Por valor minimo
[('amount_residual', '>=', 1000)]

# Vencendo na semana
[('invoice_date_due', '>=', '2025-12-02'), ('invoice_date_due', '<=', '2025-12-08')]
```

### account.move.line

```python
# Parcelas em aberto
[('amount_residual', '>', 0)]

# Parcelas vencidas
[('date_maturity', '<', '2025-12-02'), ('amount_residual', '>', 0)]

# Por nosso numero
[('l10n_br_cobranca_nossonumero', '=', '00001234')]

# Parcelas pagas
[('l10n_br_paga', '=', True)]

# Com boleto gerado
[('l10n_br_pdf_boleto', '!=', False)]
```

---

## Relacionamento entre Modelos

```
account.move (Fatura/Documento)
    │
    ├── partner_id → res.partner
    │   └── Cliente ou Fornecedor
    │
    ├── invoice_line_ids → account.move.line
    │   └── Itens da fatura (produtos/servicos)
    │
    ├── line_ids → account.move.line
    │   └── Lancamentos contabeis (debito/credito)
    │
    ├── payment_ids → account.payment
    │   └── Pagamentos vinculados
    │
    └── journal_id → account.journal
        └── Diario contabil
```

---

## Consultas Comuns

### Contas a Pagar em Aberto

```python
domain = [
    ('move_type', '=', 'in_invoice'),
    ('state', '=', 'posted'),
    ('payment_state', 'in', ['not_paid', 'partial'])
]
fields = ['id', 'name', 'partner_id', 'invoice_date_due', 'amount_total', 'amount_residual']
```

### Contas a Receber Vencidas

```python
from datetime import date
hoje = date.today().isoformat()

domain = [
    ('move_type', '=', 'out_invoice'),
    ('state', '=', 'posted'),
    ('payment_state', 'in', ['not_paid', 'partial']),
    ('invoice_date_due', '<', hoje)
]
```

### Parcelas Vencendo Hoje

```python
from datetime import date
hoje = date.today().isoformat()

domain = [
    ('date_maturity', '=', hoje),
    ('amount_residual', '>', 0)
]
```

---

## Atualizacoes

| Data | Alteracao |
|------|-----------|
| 02/12/2025 | Documento criado com mapeamento completo |
