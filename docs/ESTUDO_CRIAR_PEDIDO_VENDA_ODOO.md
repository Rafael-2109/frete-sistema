# Estudo: Criação de Pedido de Venda no Odoo 17

**Data**: 04/12/2025
**Versão Odoo**: 17 Enterprise
**Localização**: CIEL IT (l10n_br)

---

## 1. Resumo dos Campos Identificados

### Campos para Criar Pedido via API

#### sale.order (Cabeçalho)

| Campo | Tipo | Obrigatório | Descrição | Valor Exemplo |
|-------|------|-------------|-----------|---------------|
| `partner_id` | int | ✅ SIM | ID do cliente (res.partner) | `88500` |
| `company_id` | int | ✅ SIM | ID da empresa emissora | `4` (NACOM GOYA - CD) |
| `l10n_br_compra_indcom` | selection | ✅ CRÍTICO | Destinação de Uso | `'com'` (Comercialização) |
| `incoterm` | int | ✅ SIM | Tipo de Frete | `6` (CIF) |
| `l10n_br_pedido_compra` | char | Opcional | Pedido de compra do cliente | `'12321'` |
| `l10n_br_imposto_auto` | boolean | Recomendado | Calcular impostos automaticamente | `True` |
| `note` | text | Opcional | Observações | `'Pedido teste'` |

**Campos preenchidos automaticamente pelo sistema:**
- `pricelist_id` - Lista de preços (vem do cliente)
- `payment_term_id` - Prazo de pagamento (vem do cliente)
- `user_id` - Vendedor
- `team_id` - Equipe de vendas
- `partner_shipping_id` - Endereço de entrega

#### sale.order.line (Linhas)

| Campo | Tipo | Obrigatório | Descrição | Valor Exemplo |
|-------|------|-------------|-----------|---------------|
| `product_id` | int | ✅ SIM | ID do produto | `29741` |
| `product_uom_qty` | float | ✅ SIM | Quantidade | `10.0` |
| `price_unit` | float | ✅ SIM | Preço unitário | `121.00` |
| `l10n_br_compra_indcom` | selection | ✅ CRÍTICO | Destinação de Uso (na linha) | `'com'` |
| `discount` | float | Opcional | Desconto em % | `0.0` |

**Campos preenchidos automaticamente após cálculo de impostos:**
- `l10n_br_operacao_id` - Operação fiscal
- `l10n_br_cfop_id` - CFOP
- `l10n_br_cfop_codigo` - Código CFOP (ex: 5101, 6101)

---

## 2. Valores de Referência

### Incoterms (Tipo de Frete)

| ID | Código | Nome |
|----|--------|------|
| 4 | FOB | FREE ON BOARD |
| 6 | CIF | COST, INSURANCE AND FREIGHT |
| 16 | RED | REDESPACHO |
| 17 | SFT | FRETE CIF |

### Destinação de Uso (l10n_br_compra_indcom)

| Valor | Descrição |
|-------|-----------|
| `'uso'` | Uso e Consumo |
| `'uso-prestacao'` | Uso na Prestação de Serviço |
| `'ind'` | Industrialização |
| `'com'` | **Comercialização** (mais comum) |
| `'ativo'` | Ativo |
| `'garantia'` | Garantia |
| `'out'` | Outros |

### Empresas

| ID | Nome |
|----|------|
| 4 | NACOM GOYA - CD |

---

## 3. Fluxo de Criação do Pedido

### Passo 1: Criar o Pedido

```python
order_data = {
    'partner_id': CLIENTE_ID,
    'company_id': 4,  # NACOM GOYA - CD
    'l10n_br_compra_indcom': 'com',  # CRÍTICO!
    'incoterm': 6,  # CIF
    'l10n_br_pedido_compra': 'PC-12345',
    'l10n_br_imposto_auto': True,
    'order_line': [
        (0, 0, {
            'product_id': PRODUTO_ID,
            'product_uom_qty': 10.0,
            'price_unit': 121.00,
            'l10n_br_compra_indcom': 'com',  # Na linha também!
        }),
    ]
}

order_id = models.execute_kw(db, uid, api_key, 'sale.order', 'create', [order_data])
```

### Passo 2: Calcular Impostos (Preenche CFOP e Operação)

```python
try:
    models.execute_kw(db, uid, api_key,
        'sale.order',
        'onchange_l10n_br_calcular_imposto',
        [[order_id]]
    )
except Exception as e:
    # Erro "cannot marshal None" é esperado
    if "cannot marshal None" not in str(e):
        raise
```

### Passo 3: Confirmar o Pedido (Opcional)

```python
models.execute_kw(db, uid, api_key,
    'sale.order',
    'action_confirm',
    [[order_id]]
)
```

---

## 4. Descobertas Importantes

### Campo Crítico: `l10n_br_compra_indcom`

O campo **Destinação de Uso** (`l10n_br_compra_indcom`) é **CRÍTICO** para o cálculo correto de impostos:

- Deve ser definido tanto no **cabeçalho** quanto nas **linhas**
- Valor mais comum: `'com'` (Comercialização)
- Sem este campo, a **Operação Fiscal** e o **CFOP** não são preenchidos corretamente

### Operação Fiscal e CFOP

- A **Operação Fiscal** (`l10n_br_operacao_id`) é determinada automaticamente pelo sistema
- O **CFOP** (`l10n_br_cfop_id`) é preenchido automaticamente após chamar `onchange_l10n_br_calcular_imposto`
- O sistema considera:
  - UF do cliente vs UF da empresa (interno/interestadual)
  - Tipo de produto (produção própria vs revenda)
  - Configurações fiscais do cliente

### Campos Somente Leitura no Cabeçalho

Alguns campos no cabeçalho são **calculados** e não podem ser escritos diretamente:
- `l10n_br_operacao_id` (cabeçalho) - readonly, store=False
- `l10n_br_cfop_id` (cabeçalho) - readonly, store=False

Estes campos são derivados das linhas do pedido.

---

## 5. DE-PARA: CarteiraPrincipal → sale.order

### Campos do Odoo a preencher

#### sale.order (Cabeçalho)

| Campo Odoo | Tipo | Descrição | DE (CarteiraPrincipal) |
|------------|------|-----------|------------------------|
| `partner_id` | int | ID do cliente | Pesquisado através do `cnpj_cpf` |
| `company_id` | int | ID da empresa (fixo: 4) | Não existe - Fixo |
| `l10n_br_compra_indcom` | selection | Destinação de Uso (fixo: 'com') | Não existe - Fixo |
| `incoterm` | int | Tipo de Frete (fixo: 6 = CIF) | `incoterm` |
| `l10n_br_pedido_compra` | char | Pedido de compra do cliente | `pedido_cliente` |
| `l10n_br_imposto_auto` | boolean | Calcular impostos auto (fixo: True) | Sempre calcular |
| `note` | text | Observações do pedido | `observ_ped_1` |

#### sale.order.line (Linhas)

| Campo Odoo | Tipo | Descrição | DE (CarteiraPrincipal) |
|------------|------|-----------|------------------------|
| `product_id` | int | ID do produto | Pesquisado através do `cod_produto`  |
| `product_uom_qty` | float | Quantidade | `qtd_produto_pedido` |
| `price_unit` | float | Preço unitário | `preco_produto_pedido` |
| `l10n_br_compra_indcom` | selection | Destinação de Uso (fixo: 'com') | Não existe - Fixo |
| `discount` | float | Desconto em % | Não há necessidade |

#### Campos que precisam de busca prévia

| Campo Odoo | Buscar por | Modelo Odoo |
|------------|------------|-------------|
| `partner_id` | `cnpj_cpf` | `res.partner` (campo `vat`) |
| `product_id` | `cod_produto`  | `product.product` (campo `default_code`) |

---

## 6. Método de Cálculo de Impostos

### Método
```python
onchange_l10n_br_calcular_imposto()
```

### Comportamento
1. Calcula todos os impostos brasileiros (ICMS, PIS, COFINS, IPI, etc.)
2. Determina a **Operação Fiscal** correta baseada nas regras configuradas
3. Preenche o **CFOP** automaticamente
4. Retorna `None` (causa erro XML-RPC, mas funciona)

### Ação do Servidor na Interface
- **ID**: 863
- **Nome**: "Atualizar Impostos"
- **Código**: `records.onchange_l10n_br_calcular_imposto()`

---

## 7. Campos de Impostos Calculados

### Cabeçalho (sale.order)

| Campo | Descrição |
|-------|-----------|
| `amount_untaxed` | Subtotal (sem impostos) |
| `amount_tax` | Total de impostos |
| `amount_total` | Total geral |
| `l10n_br_icms_valor` | Total ICMS |
| `l10n_br_pis_valor` | Total PIS |
| `l10n_br_cofins_valor` | Total COFINS |
| `l10n_br_total_tributos` | Total de tributos |

### Linha (sale.order.line)

| Campo | Descrição |
|-------|-----------|
| `l10n_br_cfop_codigo` | Código CFOP (ex: 5101) |
| `l10n_br_icms_valor` | Valor ICMS da linha |
| `l10n_br_icms_aliquota` | Alíquota ICMS (%) |
| `l10n_br_pis_valor` | Valor PIS |
| `l10n_br_cofins_valor` | Valor COFINS |
| `l10n_br_total_nfe` | Valor total da linha |

---

## 8. Referências

### Arquivos do Sistema
- [odoo_integration.py](../app/utils/odoo_integration.py) - Cliente XML-RPC base
- [carteira_service.py](../app/odoo/services/carteira_service.py) - Serviço de carteira

### Modelos Odoo
- `sale.order` - Pedido de venda
- `sale.order.line` - Linha do pedido
- `res.partner` - Cliente
- `product.product` - Produto
- `account.incoterms` - Incoterms
- `l10n_br_ciel_it_account.operacao` - Operação fiscal

---

## 9. Observações Finais

1. **Sempre definir `l10n_br_compra_indcom`** - Sem este campo, os impostos não são calculados corretamente

2. **Sempre chamar `onchange_l10n_br_calcular_imposto`** - É este método que preenche CFOP e Operação Fiscal

3. **Incoterm CIF (ID 6)** - Padrão para vendas com frete incluso

4. **Pedidos travados** - Use `action_unlock` antes de editar pedidos confirmados

5. **Erro "cannot marshal None"** - É esperado, o método funciona mesmo assim
