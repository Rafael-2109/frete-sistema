# MAPEAMENTO DIRETO: Sistema ← Excel ← Odoo

## 🎯 OBJETIVO
Casar diretamente **Campos sistema** com **Campos Odoo** através do **Campos Excel** para integração manual.

**REGRA GLOBAL: NUNCA SINCRONIZAR ODOO COM SISTEMA**

---

## 📋 CARTEIRA DE PEDIDOS

### Campos Obrigatórios
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `num_pedido` | `Referência do pedido/Referência do pedido` | `order_id/name` |
| `cod_produto` | `Produto/Referência interna` | `product_id/default_code` |
| `nome_produto` | `Produto/Nome` | `product_id/name` |
| `qtd_produto_pedido` | `Quantidade` | `product_uom_qty` |
| `cnpj_cpf` | `Referência do pedido/Cliente/CNPJ` | `order_id/partner_id/l10n_br_cnpj` |

### Dados do Pedido
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `pedido_cliente` | `Referência do pedido/Pedido de Compra do Cliente` | `order_id/l10n_br_pedido_compra` |
| `data_pedido` | `Referência do pedido/Data de criação` | `order_id/create_date` |
| `data_atual_pedido` | `Referência do pedido/Data do pedido` | `order_id/date_order` |
| `status_pedido` | `Referência do pedido/Status` | `order_id/state` |

### Dados do Cliente
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `cnpj_cpf` | `Referência do pedido/Cliente/CNPJ` | `order_id/partner_id/l10n_br_cnpj` |
| `raz_social` | `Referência do pedido/Cliente/Razão Social` | `order_id/partner_id/l10n_br_razao_social` |
| `raz_social_red` | `Referência do pedido/Cliente/Nome` | `order_id/partner_id/name` |
| `municipio` | `Referência do pedido/Cliente/Município/Nome do Município` | `order_id/partner_id/l10n_br_municipio_id/name` |
| `estado` | `Referência do pedido/Cliente/Estado/Código do estado` | `order_id/partner_id/state_id/code` |
| `vendedor` | `Referência do pedido/Vendedor` | `order_id/user_id` |
| `equipe_vendas` | `Referência do pedido/Equipe de vendas` | `order_id/team_id` |

### Dados do Produto
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `cod_produto` | `Produto/Referência interna` | `product_id/default_code` |
| `nome_produto` | `Produto/Nome` | `product_id/name` |
| `unid_medida_produto` | `Produto/Unidade de medida` | `product_id/uom_id` |
| `embalagem_produto` | `Produto/Categoria de produtos/Nome` | `product_id/categ_id/name` |
| `materia_prima_produto` | `Produto/Categoria de produtos/Categoria primária/Nome` | `product_id/categ_id/parent_id/name` |
| `categoria_produto` | `Produto/Categoria de produtos/Categoria primária/Categoria primária/Nome` | `product_id/categ_id/parent_id/parent_id/name` |

### Quantidades e Valores
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `qtd_produto_pedido` | `Quantidade` | `product_uom_qty` |
| `qtd_saldo_produto_pedido` | `Saldo` | `qty_saldo` |
| `qtd_cancelada_produto_pedido` | `Cancelado` | `qty_cancelado` |
| `qtd_produto_faturado` | `Quantidade faturada` | `qty_invoiced` |
| `preco_produto_pedido` | `Preço unitário` | `price_unit` |
| `valor_produto_pedido` | `Valor do Produto` | `l10n_br_prod_valor` |
| `valor_total_item` | `Valor do Item do Pedido` | `l10n_br_total_nfe` |
| `qtd_entregue` | `Quantidade entregue` | `qty_delivered` |

### Condições Comerciais
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `cond_pgto_pedido` | `Referência do pedido/Condições de pagamento` | `order_id/payment_term_id` |
| `forma_pgto_pedido` | `Referência do pedido/Forma de Pagamento` | `order_id/payment_provider_id` |
| `observ_ped_1` | `Referência do pedido/Notas para Expedição` | `order_id/picking_note` |
| `incoterm` | `Referência do pedido/Incoterm` | `order_id/incoterm` |
| `metodo_entrega_pedido` | `Referência do pedido/Método de entrega` | `order_id/carrier_id` |
| `data_entrega_pedido` | `Referência do pedido/Data de entrega` | `order_id/commitment_date` |
| `cliente_nec_agendamento` | `Referência do pedido/Cliente/Agendamento` | `order_id/partner_id/agendamento` |

### Endereço de Entrega
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `cnpj_endereco_ent` | `Referência do pedido/Endereço de entrega/CNPJ` | `order_id/partner_shipping_id/l10n_br_cnpj` |
| `empresa_endereco_ent` | `Referência do pedido/Endereço de entrega/O próprio` | `order_id/partner_shipping_id/self` |
| `cep_endereco_ent` | `Referência do pedido/Endereço de entrega/CEP` | `order_id/partner_shipping_id/zip` |
| `nome_cidade` | `Referência do pedido/Endereço de entrega/Município` | `order_id/partner_shipping_id/l10n_br_municipio_id` |
| `cod_uf` | `Referência do pedido/Endereço de entrega/Estado` | `order_id/partner_shipping_id/state_id` |
| `bairro_endereco_ent` | `Referência do pedido/Endereço de entrega/Bairro` | `order_id/partner_shipping_id/l10n_br_endereco_bairro` |
| `rua_endereco_ent` | `Referência do pedido/Endereço de entrega/Endereço` | `order_id/partner_shipping_id/street` |
| `endereco_ent` | `Referência do pedido/Endereço de entrega/Número` | `order_id/partner_shipping_id/l10n_br_endereco_numero` |
| `telefone_endereco_ent` | `Referência do pedido/Endereço de entrega/Telefone` | `order_id/partner_shipping_id/phone` |

---

## 📊 FATURAMENTO

### Faturamento Consolidado (RelatorioFaturamentoImportado)
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `numero_nf` | `Linhas da fatura/NF-e` | `invoice_line_ids/x_studio_nf_e` |
| `cnpj_cliente` | `Linhas da fatura/Parceiro/CNPJ` | `invoice_line_ids/partner_id/l10n_br_cnpj` |
| `nome_cliente` | `Linhas da fatura/Parceiro` | `invoice_line_ids/partner_id` |
| `municipio` | `Linhas da fatura/Parceiro/Município` | `invoice_line_ids/partner_id/l10n_br_municipio_id` |
| `origem` | `Linhas da fatura/Origem` | `invoice_line_ids/invoice_origin` |
| `data_fatura` | `Linhas da fatura/Data` | `invoice_line_ids/date` |
| `incoterm` | `Incoterm` | `invoice_incoterm_id` |
| `vendedor` | `Vendedor` | `invoice_user_id` |

### Faturamento por Produto (FaturamentoProduto)
| Campo Sistema | Campo Excel | Campo Odoo |
|---------------|-------------|------------|
| `numero_nf` | `Linhas da fatura/NF-e` | `invoice_line_ids/x_studio_nf_e` |
| `cnpj_cliente` | `Linhas da fatura/Parceiro/CNPJ` | `invoice_line_ids/partner_id/l10n_br_cnpj` |
| `nome_cliente` | `Linhas da fatura/Parceiro` | `invoice_line_ids/partner_id` |
| `municipio` | `Linhas da fatura/Parceiro/Município` | `invoice_line_ids/partner_id/l10n_br_municipio_id` |
| `origem` | `Linhas da fatura/Origem` | `invoice_line_ids/invoice_origin` |
| `status_nf` | `Status` | `state` |
| `cod_produto` | `Linhas da fatura/Produto/Referência` | `invoice_line_ids/product_id/code` |
| `nome_produto` | `Linhas da fatura/Produto/Nome` | `invoice_line_ids/product_id/name` |
| `qtd_produto_faturado` | `Linhas da fatura/Quantidade` | `invoice_line_ids/quantity` |
| `valor_produto_faturado` | `Linhas da fatura/Valor Total do Item da NF` | `invoice_line_ids/l10n_br_total_nfe` |
| `data_fatura` | `Linhas da fatura/Data` | `invoice_line_ids/date` |
| `incoterm` | `Incoterm` | `invoice_incoterm_id` |
| `vendedor` | `Vendedor` | `invoice_user_id` |
| `peso_total` | `*** Campo não existe no modelo ***` | `invoice_line_ids/product_id/gross_weight` |

---

## 🔧 IMPLEMENTAÇÃO MANUAL

### 1. Preparação dos Dados Odoo
```python
# Consulta ao Odoo para Carteira
search_fields = [
    'order_id/name',
    'order_id/partner_id/l10n_br_cnpj', 
    'product_id/default_code',
    'product_id/name',
    'product_uom_qty',
    # ... todos os campos conforme mapeamento
]

# Consulta ao Odoo para Faturamento
search_fields = [
    'invoice_line_ids/x_studio_nf_e',
    'invoice_line_ids/partner_id/l10n_br_cnpj',
    'invoice_line_ids/product_id/code',
    # ... todos os campos conforme mapeamento
]
```

### 2. Transformação dos Dados
```python
# Carteira: Odoo → Sistema
def transform_carteira_odoo_to_system(odoo_data):
    return {
        'num_pedido': odoo_data['order_id/name'],
        'cod_produto': odoo_data['product_id/default_code'],
        'nome_produto': odoo_data['product_id/name'],
        'qtd_produto_pedido': odoo_data['product_uom_qty'],
        'cnpj_cpf': odoo_data['order_id/partner_id/l10n_br_cnpj'],
        # ... todos os campos conforme mapeamento
    }

# Faturamento: Odoo → Sistema  
def transform_faturamento_odoo_to_system(odoo_data):
    return {
        'numero_nf': odoo_data['invoice_line_ids/x_studio_nf_e'],
        'cnpj_cliente': odoo_data['invoice_line_ids/partner_id/l10n_br_cnpj'],
        'nome_cliente': odoo_data['invoice_line_ids/partner_id'],
        'cod_produto': odoo_data['invoice_line_ids/product_id/code'],
        'qtd_produto_faturado': odoo_data['invoice_line_ids/quantity'],
        # ... todos os campos conforme mapeamento
    }
```

### 3. Importação Manual
```python
# Usar as rotas existentes do sistema
# Carteira: POST /carteira/importar
# Faturamento: POST /faturamento/importar-relatorio
# Faturamento Produto: POST /faturamento/produtos/importar

# Formato dos dados: seguir os campos do sistema
# Validação: usar os mesmos critérios dos imports Excel
```

---

## 🎯 PRÓXIMOS PASSOS

1. **Manual**: Criar scripts Python para buscar dados do Odoo
2. **Transformação**: Aplicar mapeamento direto dos campos
3. **Importação**: Usar rotas existentes do sistema
4. **Validação**: Verificar dados importados
5. **Automação**: Posteriormente criar jobs automáticos

 
 