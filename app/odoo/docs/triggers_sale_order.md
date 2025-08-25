# Triggers e Métodos do Odoo ao Criar Sale.Order

## 🔄 Principais Triggers/Métodos Executados

### 1. **Onchange Methods** (Triggers de Mudança de Campo)
Estes são executados automaticamente na interface do Odoo mas NÃO via API:

#### `@api.onchange('partner_id')`
- **Quando**: Ao selecionar um cliente
- **O que faz**:
  - Define `partner_invoice_id` (endereço de faturamento)
  - Define `partner_shipping_id` (endereço de entrega)
  - Define `pricelist_id` (lista de preços do cliente)
  - Define `payment_term_id` (condições de pagamento)
  - Define `fiscal_position_id` (posição fiscal)
  - Define `user_id` (vendedor responsável)
  - Define `team_id` (equipe de vendas)

#### `@api.onchange('partner_shipping_id')`
- **Quando**: Ao mudar endereço de entrega
- **O que faz**:
  - Atualiza `fiscal_position_id` baseado no endereço

#### `@api.onchange('pricelist_id')`
- **Quando**: Ao mudar lista de preços
- **O que faz**:
  - Recalcula preços de todos os produtos nas linhas

#### `@api.onchange('fiscal_position_id')`
- **Quando**: Ao mudar posição fiscal
- **O que faz**:
  - Recalcula impostos de todas as linhas

### 2. **Computed Fields** (Campos Calculados)
Estes SÃO executados via API automaticamente:

#### `amount_untaxed` (Subtotal)
- **Tipo**: `@api.depends('order_line.price_subtotal')`
- **Calculado**: Sempre que as linhas mudam

#### `amount_tax` (Impostos)
- **Tipo**: `@api.depends('order_line.price_tax')`
- **Calculado**: Sempre que os impostos das linhas mudam

#### `amount_total` (Total)
- **Tipo**: `@api.depends('amount_untaxed', 'amount_tax')`
- **Calculado**: Sempre que subtotal ou impostos mudam

### 3. **Sale Order Line Triggers**

#### `@api.onchange('product_id')`
- **Quando**: Ao selecionar um produto
- **O que faz**:
  - Define `name` (descrição do produto)
  - Define `price_unit` (preço baseado na pricelist)
  - Define `product_uom` (unidade de medida)
  - Define `tax_id` (impostos do produto com mapeamento fiscal)
  - Define `discount` (desconto se houver)

#### `@api.onchange('product_uom_qty', 'product_uom')`
- **Quando**: Ao mudar quantidade ou unidade
- **O que faz**:
  - Recalcula `price_unit` (pode haver preços por quantidade)
  - Recalcula descontos por volume

#### Campos Calculados da Linha:
- `price_subtotal` = qty × price_unit × (1 - discount/100)
- `price_tax` = cálculo dos impostos
- `price_total` = price_subtotal + price_tax

### 4. **Métodos de API Disponíveis**

#### `create()` 
- Cria o pedido mas NÃO executa onchange

#### `write()` 
- Atualiza o pedido mas NÃO executa onchange

#### `_onchange_partner_id()`
- Pode ser chamado manualmente via API
- Retorna dict com valores calculados

#### `_compute_tax_id()`
- Recalcula impostos de todas as linhas
- Executado automaticamente em campos computed

#### `action_confirm()`
- Confirma a cotação transformando em pedido de venda
- Executa validações e atualiza status

## 🎯 Como Acionar Triggers via API

### Método 1: Usar Default Values
```python
# Buscar valores padrão para o partner
defaults = odoo.execute_kw(
    'sale.order',
    'default_get',
    [['partner_id', 'pricelist_id', 'payment_term_id']],
    {'context': {'default_partner_id': partner_id}}
)
```

### Método 2: Criar com Campos Mínimos e Atualizar
```python
# 1. Criar pedido básico
order_id = odoo.execute_kw('sale.order', 'create', [{
    'partner_id': partner_id
}])

# 2. Ler pedido criado (triggers computed fields)
order = odoo.execute_kw('sale.order', 'read', 
    [[order_id]], 
    {'fields': ['partner_invoice_id', 'pricelist_id', 'fiscal_position_id']}
)

# 3. Adicionar linhas (que vão calcular impostos)
```

### Método 3: Usar Métodos Preparatórios
```python
# Para produtos com impostos corretos
product_vals = odoo.execute_kw(
    'sale.order.line',
    '_prepare_add_missing_fields',
    [values],
    {'context': {
        'partner_id': partner_id,
        'fiscal_position_id': fiscal_position_id
    }}
)
```

### Método 4: Forçar Recálculo Após Criação
```python
# Criar pedido
order_id = odoo.execute_kw('sale.order', 'create', [vals])

# Forçar recálculo escrevendo campo vazio
odoo.execute_kw('sale.order', 'write', [[order_id], {
    'note': 'Forçando recálculo'
}])

# Ou chamar método específico se disponível
odoo.execute_kw('sale.order', '_compute_amounts', [[order_id]])
```

## 🔍 Impostos no Brasil (Localização l10n_br)

### Campos Específicos Brasileiros:
- `l10n_br_icms_tax_id` - ICMS
- `l10n_br_ipi_tax_id` - IPI  
- `l10n_br_pis_tax_id` - PIS
- `l10n_br_cofins_tax_id` - COFINS
- `l10n_br_issqn_tax_id` - ISS (serviços)

### Posição Fiscal (fiscal_position_id):
- Mapeia impostos do produto para impostos do cliente
- Considera origem/destino da operação
- Define CST/CFOP corretos

## ⚡ Solução Recomendada para API

### Abordagem Completa:
```python
# 1. Buscar dados do cliente com impostos
cliente = odoo.search_read('res.partner', 
    [('id', '=', partner_id)],
    ['property_account_position_id', 'property_product_pricelist']
)

fiscal_position_id = cliente[0]['property_account_position_id'][0]
pricelist_id = cliente[0]['property_product_pricelist'][0]

# 2. Para cada produto, buscar impostos mapeados
for produto in produtos:
    # Buscar produto com impostos
    prod = odoo.search_read('product.product',
        [('id', '=', product_id)],
        ['taxes_id', 'supplier_taxes_id']
    )
    
    # Se houver posição fiscal, mapear impostos
    if fiscal_position_id:
        impostos_mapeados = odoo.execute_kw(
            'account.fiscal.position',
            'map_tax',
            [fiscal_position_id, prod[0]['taxes_id']]
        )
    else:
        impostos_mapeados = prod[0]['taxes_id']

# 3. Criar pedido com todos os campos
order_vals = {
    'partner_id': partner_id,
    'fiscal_position_id': fiscal_position_id,
    'pricelist_id': pricelist_id,
    'order_line': [
        (0, 0, {
            'product_id': product_id,
            'product_uom_qty': qty,
            'price_unit': price,
            'tax_id': [(6, 0, impostos_mapeados)]  # Impostos mapeados
        })
    ]
}

order_id = odoo.execute_kw('sale.order', 'create', [order_vals])

# 4. Forçar recálculo se necessário
odoo.execute_kw('sale.order', 'write', [[order_id], {}])
```

## 📝 Observações Importantes

1. **Onchange NÃO funciona via XML-RPC** na maioria das versões do Odoo
2. **Computed fields** SÃO calculados automaticamente
3. **Impostos** precisam ser mapeados pela posição fiscal
4. **Preços** devem considerar a pricelist do cliente
5. **Validações** são executadas no create/write

## 🛠️ Métodos Úteis para Debugging

```python
# Ver todos os campos de um modelo
fields = odoo.execute_kw('sale.order', 'fields_get', [], 
    {'attributes': ['string', 'type', 'required', 'readonly', 'compute']})

# Ver métodos disponíveis
import xmlrpc.client
server = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')
methods = server.execute_kw(db, uid, password, 
    'sale.order', 'get_metadata', [])
```