# Campos do Modelo res.partner

**Modelo Odoo:** `res.partner`
**Descricao:** Parceiros (clientes, fornecedores, transportadoras)
**Total de Campos:** 316

---

## Campos de Identificacao

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID interno | PK |
| `name` | char | Nome/Razao Social | Identificacao principal |
| `display_name` | char | Nome de exibicao | Nome formatado |
| `ref` | char | Referencia | Codigo interno |
| `vat` | char | CNPJ/CPF | **SEM formatacao** |
| `l10n_br_cnpj` | char | CNPJ | Com formatacao |
| `l10n_br_cpf` | char | CPF | Com formatacao |
| `l10n_br_razao_social` | char | Razao Social | Nome legal completo |
| `company_registry` | char | Company ID | Registro comercial |

---

## Campos de Tipo/Classificacao

| Campo | Tipo | Valores | Uso |
|-------|------|---------|-----|
| `is_company` | boolean | True/False | Empresa ou pessoa |
| `company_type` | selection | company, person | Tipo |
| `customer_rank` | integer | 0+ | **>0 = Cliente** |
| `supplier_rank` | integer | 0+ | **>0 = Fornecedor** |
| `active` | boolean | True/False | Ativo/Inativo |

> **IMPORTANTE:**
> - Para filtrar fornecedores: `('supplier_rank', '>', 0)`
> - Para filtrar clientes: `('customer_rank', '>', 0)`

---

## Campos de Contato

| Campo | Tipo | Descricao | Formato |
|-------|------|-----------|---------|
| `email` | char | Email | email@domain.com |
| `email_normalized` | char | Email normalizado | Busca |
| `phone` | char | Telefone | +55... |
| `mobile` | char | Celular | +55... |
| `website` | char | Website | URL |
| `function` | char | Cargo | Texto |

---

## Campos de Endereco

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `street` | char | Logradouro | Rua das Flores |
| `l10n_br_endereco_numero` | char | Numero | 123 |
| `street2` | char | Complemento | Sala 101 |
| `l10n_br_endereco_bairro` | char | Bairro | Centro |
| `city` | char | Cidade | Sao Paulo |
| `state_id` | many2one | Estado | (35, 'Sao Paulo') |
| `zip` | char | CEP | 01310-100 |
| `country_id` | many2one | Pais | (31, 'Brazil') |
| `l10n_br_municipio_id` | many2one | Municipio IBGE | (3550308, 'Sao Paulo') |

> **Nota:** Campos many2one retornam tupla `[id, nome]`

---

## Campos Fiscais Brasileiros

### Inscricoes e Registros
| Campo | Tipo | Valores/Descricao |
|-------|------|-------------------|
| `l10n_br_ie` | char | Inscricao Estadual |
| `l10n_br_im` | char | Inscricao Municipal |
| `l10n_br_is` | char | Inscricao Suframa |
| `l10n_br_indicador_ie` | selection | 1=Contribuinte, 2=Isento, 9=Nao contribuinte |
| `l10n_br_regime_tributario` | selection | 1=SN, 2=SN Exc, 3=Lucro Presumido/Real |
| `l10n_br_situacao_cadastral` | selection | Situacao do cadastro |
| `l10n_br_crc` | char | CRC (Conselho Regional Contabilidade) |
| `l10n_br_nire` | char | NIRE (Numero Identificacao Registro Empresas) |
| `l10n_br_id_estrangeiro` | char | Identificacao de Estrangeiro |

### Retencoes de Impostos
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_pis_ret_valor` | float | Valor Minimo do PIS Retido |
| `l10n_br_cofins_ret_valor` | float | Valor Minimo do COFINS Retido |
| `l10n_br_csll_ret_valor` | float | Valor Minimo do CSLL Retido |
| `l10n_br_irpj_ret_valor` | float | Valor Minimo do IRPJ Retido |
| `l10n_br_inss_cprb` | selection | Contribuinte INSS Receita Bruta (CPRB) |

### Credito ICMS Simples Nacional
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icms_credito_aliquota` | float | Aliquota de calculo do credito (Simples Nacional) |

### Mensagens e Observacoes Fiscais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_mensagem_fiscal_01_id` | many2one | Observacao Fiscal 1 |
| `l10n_br_mensagem_fiscal_02_id` | many2one | Observacao Fiscal 2 |
| `l10n_br_mensagem_fiscal_03_id` | many2one | Observacao Fiscal 3 |
| `l10n_br_mensagem_fiscal_04_id` | many2one | Observacao Fiscal 4 |
| `l10n_br_mensagem_fiscal_05_id` | many2one | Observacao Fiscal 5 |

### Posicao e Marcadores Fiscais
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `property_account_position_id` | many2one | Posicao Fiscal (determina impostos/contas) |
| `fiscal_tag_ids` | many2many | Marcadores Fiscais |
| `fiscal_country_codes` | char | Codigos de Pais Fiscais |

### Configuracoes de Compra
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_compra_indcom` | selection | Destinacao de Uso |
| `l10n_br_orgao_publico` | selection | Orgao Publico |

### Preferencias de Documentos
| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_receber_nfe` | boolean | Receber NF-e |
| `l10n_br_receber_boleto` | boolean | Receber Boleto (endereco diferente) |
| `l10n_br_consultar_cep` | boolean | Consultar CEP automaticamente |
| `l10n_br_consultar_cnpj` | boolean | Consultar CNPJ automaticamente |

---

## Campos Financeiros

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `credit` | monetary | Total a receber |
| `debit` | monetary | Total a pagar |
| `credit_limit` | float | Limite de credito |
| `total_due` | monetary | Total vencido |
| `total_overdue` | monetary | Total em atraso |
| `property_payment_term_id` | many2one | Prazo pagamento cliente |
| `property_supplier_payment_term_id` | many2one | Prazo pagamento fornecedor |
| `property_account_receivable_id` | many2one | Conta a receber |
| `property_account_payable_id` | many2one | Conta a pagar |

---

## Campos de Logistica

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `property_delivery_carrier_id` | many2one | Transportadora padrao |
| `property_stock_customer` | many2one | Local estoque cliente |
| `property_stock_supplier` | many2one | Local estoque fornecedor |
| `on_time_rate` | float | Taxa de entrega no prazo |

---

## Campos Customizados (Goya/Nacom)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `carga_compartilhada` | boolean | Aceita carga compartilhada? |
| `exige_laudo` | boolean | Exige laudo? |
| `agendamento` | selection | Tipo de agendamento |
| `adiantamento` | boolean | Exige adiantamento? |
| `representante` | boolean | Eh representante? |
| `representante_id` | many2one | Representante vinculado |
| `x_studio_agendamento` | selection | Agendamento (Studio) |
| `x_studio_desconto` | float | Desconto |
| `x_studio_desconto_contratual` | boolean | Desconto contratual? |

---

## Campos de Datas

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `create_date` | datetime | Data de criacao |
| `write_date` | datetime | Ultima atualizacao |
| `date` | date | Data do parceiro |
| `l10n_br_data_nascimento` | date | Data de nascimento |

---

## Campos de Relacionamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `parent_id` | many2one | Empresa pai |
| `child_ids` | one2many | Contatos filhos |
| `user_id` | many2one | Vendedor responsavel |
| `team_id` | many2one | Equipe de vendas |
| `company_id` | many2one | Empresa |
| `invoice_ids` | one2many | Faturas |
| `sale_order_ids` | one2many | Pedidos de venda |
| `purchase_line_ids` | one2many | Linhas de compra |

---

## Filtros Uteis

```python
# Fornecedores ativos
[('supplier_rank', '>', 0), ('active', '=', True)]

# Clientes ativos
[('customer_rank', '>', 0), ('active', '=', True)]

# Por CNPJ (sem formatacao)
[('vat', 'ilike', '18467441')]

# Por CNPJ (com formatacao)
[('l10n_br_cnpj', 'ilike', '18.467.441')]

# Por UF
[('state_id.code', '=', 'SP')]

# Por cidade
[('city', 'ilike', 'Sao Paulo')]

# Fornecedores de SP
[('supplier_rank', '>', 0), ('state_id.code', '=', 'SP')]

# Com limite de credito
[('credit_limit', '>', 0)]

# Incluir inativos
['|', ('active', '=', True), ('active', '=', False)]
```

---

## Campos NAO Existentes (Evitar)

Os seguintes campos **NAO existem** no res.partner padrao:
- `is_transportadora` - Usar delivery.carrier
- `tipo_parceiro` - Usar customer_rank/supplier_rank
- `razao_social` - Usar `l10n_br_razao_social`
- `inscricao_estadual` - Usar `l10n_br_ie`

---

## Relacionamento com Outros Modelos

```
res.partner
    │
    ├── delivery.carrier (l10n_br_partner_id)
    │   └── Transportadoras vinculadas ao parceiro
    │
    ├── account.move (partner_id)
    │   └── Faturas do parceiro
    │
    ├── sale.order (partner_id)
    │   └── Pedidos de venda
    │
    ├── purchase.order (partner_id)
    │   └── Pedidos de compra
    │
    └── l10n_br_ciel_it_account.dfe (partner_id, partner_dest_id)
        └── Documentos fiscais
```

---

## Atualizacoes

| Data | Alteracao |
|------|-----------|
| 02/12/2025 | Documento criado com mapeamento completo |
