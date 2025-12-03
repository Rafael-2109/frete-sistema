# Referencia de Campos - Produtos Odoo

**Modelos:** product.product, product.template
**Total de campos:** product.product (229) + product.template (196) = 425 campos
**Data mapeamento:** 02/12/2025

---

## Modelo Principal: product.product

Este modelo representa a variante de produto. Herda campos de product.template.

---

## Campos de Identificacao

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `id` | integer | ID interno | 12345 |
| `name` | char | Nome do produto | 'Pupunha em Conserva 300g' |
| `display_name` | char | Nome de exibicao | '[PROD001] Pupunha em Conserva 300g' |
| `default_code` | char | Codigo interno (SKU) | 'PROD001' |
| `barcode` | char | Codigo de barras EAN | '7891234567890' |
| `barcode_nacom` | char | Codigo de barras Nacom | '12345678' |
| `code` | char | Referencia (calculado) | 'PROD001' |

---

## Campos de Classificacao

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `categ_id` | many2one | Categoria do produto | (1, 'Conservas') |
| `detailed_type` | selection | Tipo detalhado | 'product', 'consu', 'service' |
| `type` | selection | Tipo basico | 'product', 'consu', 'service' |
| `product_tmpl_id` | many2one | Template do produto | (100, 'Pupunha') |
| `product_tag_ids` | many2many | Tags do produto | [(1, 'Promocao'), (2, 'Novo')] |

### Valores de detailed_type

| Valor | Descricao |
|-------|-----------|
| `product` | Produto Estocavel (controla estoque) |
| `consu` | Consumivel (nao controla estoque) |
| `service` | Servico |

---

## Campos de Preco

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `list_price` | float | Preco de venda | 15.90 |
| `lst_price` | float | Preco de venda (delegado) | 15.90 |
| `standard_price` | float | Custo | 8.50 |
| `avg_cost` | monetary | Custo medio | 8.45 |
| `price_extra` | float | Extra por variante | 2.00 |
| `total_value` | monetary | Valor total em estoque | 850.00 |

---

## Campos de Unidade de Medida

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `uom_id` | many2one | Unidade de medida | (1, 'Unidade(s)') |
| `uom_name` | char | Nome da unidade | 'Unidade(s)' |
| `uom_po_id` | many2one | Unidade de compra | (2, 'Caixa') |

---

## Campos de Estoque

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `qty_available` | float | Em estoque (on hand) | 100.0 |
| `virtual_available` | float | Previsto (forecast) | 150.0 |
| `incoming_qty` | float | Entrando | 50.0 |
| `outgoing_qty` | float | Saindo | 0.0 |
| `free_qty` | float | Disponivel (livre) | 100.0 |
| `tracking` | selection | Rastreabilidade | 'none', 'lot', 'serial' |
| `valuation` | selection | Valorizacao | 'manual_periodic', 'real_time' |
| `cost_method` | selection | Metodo de custo | 'standard', 'average', 'fifo' |

### Valores de tracking

| Valor | Descricao |
|-------|-----------|
| `none` | Sem rastreio |
| `lot` | Por lote |
| `serial` | Por numero de serie |

### Valores de cost_method

| Valor | Descricao |
|-------|-----------|
| `standard` | Custo Padrao |
| `average` | Custo Medio |
| `fifo` | PEPS (Primeiro que Entra, Primeiro que Sai) |

---

## Campos de Peso e Dimensoes

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `weight` | float | Peso liquido (kg) | 0.300 |
| `gross_weight` | float | Peso bruto (kg) | 0.350 |
| `volume` | float | Volume (m3) | 0.001 |
| `weight_uom_name` | char | Unidade de peso | 'kg' |
| `volume_uom_name` | char | Unidade de volume | 'm3' |

---

## Campos de Status

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `active` | boolean | Ativo | True |
| `sale_ok` | boolean | Pode ser vendido | True |
| `purchase_ok` | boolean | Pode ser comprado | True |
| `priority` | selection | Favorito | '0', '1' |

---

## Campos de Descricao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `description` | html | Descricao geral |
| `description_sale` | text | Descricao de venda (para cliente) |
| `description_purchase` | text | Descricao de compra (para fornecedor) |
| `description_picking` | text | Descricao no picking |
| `description_pickingin` | text | Descricao no recebimento |
| `description_pickingout` | text | Descricao na expedicao |

---

## Campos Brasileiros (l10n_br_*)

### NCM e Origem

| Campo | Tipo | Descricao | Exemplo |
|-------|------|-----------|---------|
| `l10n_br_ncm_id` | many2one | NCM | (123, '2008.99.00 - Outros frutos') |
| `l10n_br_origem` | selection | Origem do produto | '0' (Nacional) |
| `l10n_br_tipo_produto` | selection | Tipo do produto BR | Usa da categoria se vazio |
| `l10n_br_fci` | char | Ficha de Conteudo Importacao | '12345678-ABCD-...' |
| `l10n_br_cnpj_fabricante` | char | CNPJ do fabricante | '12.345.678/0001-99' |
| `l10n_br_grupo_id` | many2one | Grupo | (1, 'Alimentos') |
| `l10n_br_indescala` | boolean | Indicador de Escala Relevante | False |

### Valores de l10n_br_origem

| Valor | Descricao |
|-------|-----------|
| `0` | Nacional, exceto indicados nos codigos 3, 4, 5 e 8 |
| `1` | Estrangeira - Importacao direta, exceto codigo 6 |
| `2` | Estrangeira - Adquirida no mercado interno, exceto codigo 7 |
| `3` | Nacional - Conteudo de importacao superior a 40% e igual ou inferior a 70% |
| `4` | Nacional - Producao conforme processos produtivos basicos |
| `5` | Nacional - Conteudo de importacao igual ou inferior a 40% |
| `6` | Estrangeira - Importacao direta, sem similar nacional |
| `7` | Estrangeira - Adquirida no mercado interno, sem similar nacional |
| `8` | Nacional - Conteudo de importacao superior a 70% |

### ICMS-ST Retido

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_icmsst_retido_aliquota` | float | Aliquota suportada pelo Consumidor Final (%) |
| `l10n_br_icmsst_retido_base` | float | Valor da Base de Calculo do ICMSST Retido |
| `l10n_br_icmsst_retido_valor` | float | Valor do ICMSST Retido |
| `l10n_br_icmsst_substituto_valor` | float | Valor do ICMS proprio do Substituto |

### PIS/COFINS

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_nat_bc_cred` | selection | Natureza do Credito de PIS/COFINS |

### Servicos (ISS)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_codigo_servico` | char | Codigo Servico (LC 116) |
| `l10n_br_codigo_tributacao_servico` | char | Codigo Tributacao Servico |
| `l10n_br_exigibilidade_iss` | selection | Exigibilidade ISS |
| `l10n_br_natureza_iss` | selection | Natureza da tributacao do Servico |
| `l10n_br_material_aplicado_servico` | boolean | Material Aplicado c/ Deducao ISS |

### ANVISA (Farmaceuticos)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_farmaceutico` | boolean | Eh medicamento/farmaceutico |
| `l10n_br_registro_anvisa` | char | Registro ANVISA |
| `l10n_br_processo_anvisa` | char | Processo ANVISA |
| `l10n_br_preco_maximo_anvisa` | float | Preco Maximo ANVISA |
| `l10n_br_validade_processo_anvisa` | date | Validade do Registro |

### ANP (Combustiveis)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_registro_anp` | boolean | Tem Registro ANP |
| `l10n_br_produto_anp` | char | Codigo de produto da ANP |

### Energia/Gas

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_consumo_energia_gas` | selection | Consumo de Energia ou Gas |
| `l10n_br_tipo_ligacao` | selection | Codigo de tipo de Ligacao |
| `l10n_br_grupo_tensao` | selection | Grupo de Tensao |

### Outros Campos Brasileiros

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `l10n_br_informacao_adicional` | text | Informacoes Adicionais |
| `l10n_br_fator_utrib` | float | Fator Unidade Tributavel |
| `l10n_br_reinf_01` | many2one | REINF - Natureza do Rendimento |
| `l10n_br_reinf_06` | selection | REINF - Tipo de Servico |

---

## Campos de Fornecedores

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `seller_ids` | one2many | Fornecedores (product.supplierinfo) |
| `variant_seller_ids` | one2many | Fornecedores da variante |

### Modelo product.supplierinfo (seller_ids)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `partner_id` | many2one | Fornecedor (res.partner) |
| `product_tmpl_id` | many2one | Template do produto |
| `product_id` | many2one | Variante especifica |
| `price` | float | Preco de compra |
| `min_qty` | float | Quantidade minima |
| `delay` | integer | Prazo de entrega (dias) |
| `currency_id` | many2one | Moeda |
| `date_start` | date | Validade inicio |
| `date_end` | date | Validade fim |

---

## Campos de Contas Contabeis

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `property_account_income_id` | many2one | Conta de Receita |
| `property_account_expense_id` | many2one | Conta de Despesa |
| `property_account_creditor_price_difference` | many2one | Conta Diferenca de Preco |
| `property_stock_inventory` | many2one | Localizacao Inventario |
| `property_stock_production` | many2one | Localizacao Producao |

---

## Campos de Impostos

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `taxes_id` | many2many | Impostos de Venda |
| `supplier_taxes_id` | many2many | Impostos de Compra |
| `fiscal_tag_ids` | many2many | Marcadores Fiscais |
| `fiscal_country_codes` | char | Codigos de Pais Fiscais |
| `account_tag_ids` | many2many | Tags Contabeis |

---

## Campos de Empresa

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `company_id` | many2one | Empresa |
| `company_ids` | many2many | Empresas permitidas |
| `responsible_id` | many2one | Responsavel (logistica) |

---

## Campos de Controle de Datas

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `create_date` | datetime | Data de criacao |
| `create_uid` | many2one | Criado por |
| `write_date` | datetime | Ultima atualizacao |
| `write_uid` | many2one | Atualizado por |

---

## Campos de Validade/Expiracao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `use_expiration_date` | boolean | Usa data de validade |
| `expiration_time` | integer | Dias para expiracao (apos recebimento) |
| `use_time` | integer | Dias para "melhor antes" |
| `removal_time` | integer | Dias para remocao do estoque |
| `alert_time` | integer | Dias antes do alerta |

---

## Campos de Variantes

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `product_variant_count` | integer | Numero de variantes |
| `product_variant_ids` | one2many | Variantes do template |
| `product_variant_id` | many2one | Variante unica |
| `is_product_variant` | boolean | Eh variante de produto |
| `attribute_line_ids` | one2many | Linhas de atributos |
| `product_template_attribute_value_ids` | many2many | Valores de atributos |
| `has_configurable_attributes` | boolean | Tem atributos configuraveis |
| `combination_indices` | char | Indices de combinacao |

---

## Campos de Rotas e Regras de Reabastecimento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `route_ids` | many2many | Rotas |
| `route_from_categ_ids` | many2many | Rotas da categoria |
| `has_available_route_ids` | boolean | Tem rotas disponiveis |
| `orderpoint_ids` | one2many | Regras de reabastecimento |
| `nbr_reordering_rules` | integer | Numero de regras |
| `reordering_min_qty` | float | Quantidade minima |
| `reordering_max_qty` | float | Quantidade maxima |

---

## Campos de Embalagem

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `packaging_ids` | one2many | Embalagens do produto |

---

## Campos de Compras

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `purchase_order_line_ids` | one2many | Linhas de PO |
| `purchased_product_qty` | float | Quantidade comprada |
| `purchase_line_warn` | selection | Aviso em linha de PO |
| `purchase_line_warn_msg` | text | Mensagem de aviso |
| `purchase_method` | selection | Politica de controle |
| `purchase_request` | boolean | Gerar Requisicao de Compra |

---

## Campos de Vendas

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `sales_count` | float | Quantidade vendida |
| `sale_line_warn` | selection | Aviso em linha de venda |
| `sale_line_warn_msg` | text | Mensagem de aviso |
| `sale_delay` | integer | Lead time do cliente (dias) |
| `invoice_policy` | selection | Politica de faturamento |
| `optional_product_ids` | many2many | Produtos opcionais (cross-sell) |

---

## Campos de Movimentos de Estoque

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `stock_move_ids` | one2many | Movimentos de estoque |
| `stock_quant_ids` | one2many | Quantidades em estoque |
| `stock_valuation_layer_ids` | one2many | Camadas de valorizacao |
| `nbr_moves_in` | integer | Movimentos de entrada (12m) |
| `nbr_moves_out` | integer | Movimentos de saida (12m) |

---

## Campos de Producao (MRP)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `bom_ids` | one2many | Listas de materiais |
| `bom_count` | integer | Numero de BOMs |
| `bom_line_ids` | one2many | Componentes em BOMs |
| `variant_bom_ids` | one2many | BOMs da variante |
| `used_in_bom_count` | integer | Usado em quantas BOMs |
| `mrp_product_qty` | float | Quantidade manufaturada |
| `is_kits` | boolean | Eh kit |

---

## Campos de Qualidade

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `quality_control_point_qty` | integer | Pontos de controle |
| `quality_pass_qty` | integer | Aprovados |
| `quality_fail_qty` | integer | Reprovados |

---

## Campos de Servicos/Projetos

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `service_type` | selection | Tipo de servico |
| `service_tracking` | selection | Criar ao confirmar pedido |
| `service_policy` | selection | Politica de faturamento servico |
| `service_to_purchase` | boolean | Subcontratar servico |
| `project_id` | many2one | Projeto |
| `project_template_id` | many2one | Template de projeto |
| `expense_policy` | selection | Politica de reembolso |

---

## Campos de Atividades

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `activity_ids` | one2many | Atividades |
| `activity_state` | selection | Estado da atividade |
| `activity_date_deadline` | date | Prazo da proxima atividade |
| `activity_summary` | char | Resumo da proxima atividade |
| `activity_type_id` | many2one | Tipo da proxima atividade |
| `activity_user_id` | many2one | Responsavel da atividade |

---

## Campos de Imagens

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `image_1920` | binary | Imagem principal (1920px) |
| `image_1024` | binary | Imagem (1024px) |
| `image_512` | binary | Imagem (512px) |
| `image_256` | binary | Imagem (256px) |
| `image_128` | binary | Imagem miniatura (128px) |
| `image_variant_1920` | binary | Imagem da variante (1920px) |
| `image_variant_1024` | binary | Imagem da variante (1024px) |
| `image_variant_512` | binary | Imagem da variante (512px) |
| `image_variant_256` | binary | Imagem da variante (256px) |
| `image_variant_128` | binary | Imagem da variante (128px) |
| `can_image_1024_be_zoomed` | boolean | Imagem pode dar zoom |

---

## Campos de Documentos

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `product_document_ids` | one2many | Documentos do produto |
| `product_document_count` | integer | Numero de documentos |
| `modelo_laudo` | binary | Modelo de laudo |
| `modelo_laudo_filename` | char | Nome do arquivo de laudo |

---

## Campos de Custo Landed

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `landed_cost_ok` | boolean | Eh custo landed |
| `split_method_landed_cost` | selection | Metodo de rateio |

---

## Campos de Faturamento

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `invoices_count` | float | Total faturado |

---

## Filtros Uteis

```python
# Produtos ativos para venda
[('active', '=', True), ('sale_ok', '=', True)]

# Produtos estocaveis
[('detailed_type', '=', 'product')]

# Por codigo interno
[('default_code', 'ilike', 'PROD001')]

# Por categoria
[('categ_id.name', 'ilike', 'conservas')]

# Por NCM
[('l10n_br_ncm_id.codigo', 'ilike', '2008.99')]

# Com estoque
[('qty_available', '>', 0)]

# Sem estoque
[('qty_available', '<=', 0)]

# Por barcode
['|', ('barcode', 'ilike', '789'), ('barcode_nacom', 'ilike', '789')]

# Por fornecedor (via supplierinfo)
# Primeiro buscar em product.supplierinfo, depois usar product_tmpl_id
```

---

## Relacionamentos Principais

```
product.product
    │
    ├── product_tmpl_id ──► product.template
    │
    ├── categ_id ──► product.category
    │
    ├── uom_id ──► uom.uom
    │
    ├── seller_ids ──► product.supplierinfo
    │       │
    │       └── partner_id ──► res.partner (Fornecedor)
    │
    ├── taxes_id ──► account.tax (Impostos de venda)
    │
    ├── supplier_taxes_id ──► account.tax (Impostos de compra)
    │
    ├── l10n_br_ncm_id ──► l10n_br_ncm.ncm (NCM)
    │
    └── stock_quant_ids ──► stock.quant (Estoque)
```

---

## Notas Importantes

1. **product.product vs product.template**: product.product representa variantes. Para produtos sem variantes, ha uma relacao 1:1 com product.template.

2. **Campos herdados**: Muitos campos em product.product sao delegados de product.template.

3. **NCM**: Armazenado como many2one para l10n_br_ncm.ncm. O codigo esta no campo `codigo` do NCM.

4. **Estoque**: Os campos `qty_available`, `virtual_available`, etc. sao calculados em tempo real baseado na localizacao/warehouse do contexto.

5. **Fornecedores**: Para buscar por fornecedor, use product.supplierinfo e depois filtre por product_tmpl_id.

6. **Preco de custo**: O campo `standard_price` pode ser atualizado automaticamente dependendo do `cost_method`.
