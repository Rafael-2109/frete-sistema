# Campos para Criar Pedido de Venda no Odoo

**Instruções**: Preencha os valores de exemplo nos campos marcados com `_____`

---

## CABEÇALHO (sale.order)

### Campos Obrigatórios

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `partner_id` | ID do cliente | ATACADAO 183 (não sei o ID) |
| `company_id` | ID da empresa emissora | 4 (NACOM GOYA - CD) |
| `pricelist_id` | ID da lista de preços | 11 (TABELA PADRÃO BRL) | Preenche sozinho
| `l10n_br_operacao_id` | ID da operação fiscal | Não encontrei esse campo |

### Campos Recomendados

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `payment_term_id` | ID do prazo de pagamento | acho que 0 (60 DDL) | Preenche sozinho
| `user_id` | ID do vendedor | Não sei o ID (6 JOAO YASUAKI YAMAMOTO) | Preenche sozinho
| `team_id` | ID da equipe de vendas | Não sei o ID (VENDA EXTERNA ATACADÃO) | Preenche sozinho

### Campos Opcionais

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `client_order_ref` | Referência do cliente | deixar vazio |
| `l10n_br_pedido_compra` | Pedido de compra do cliente | 12321 |
| `partner_shipping_id` | ID do endereço de entrega (se diferente do cliente) | (ATACADAO 183) | Preenche sozinho
| `carrier_id` | ID do método de entrega/transportadora | deixar vazio |
| `commitment_date` | Data de entrega prometida (formato: YYYY-MM-DD HH:MM:SS) | deixar vazio |
| `note` | Observações do pedido | Pedido teste |

---

## LINHAS DO PEDIDO (sale.order.line)

### Campos Obrigatórios (por linha)

| Campo | Descrição | Exemplo Linha 1 |
|-------|-----------|-----------------|
| `product_id` | ID do produto | _____ |
| `product_uom_qty` | Quantidade | 10 |
| `price_unit` | Preço unitário | 121 |

### Campos Opcionais (por linha)

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `discount` | Desconto em % | _____ |
| `name` | Descrição customizada (se vazio, usa do produto) | [4320162] AZEITONA VERDE FATIADA - BD 6X2 KG - CAMPO BELO |

---

## CONTROLE DE IMPOSTOS

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `l10n_br_imposto_auto` | Calcular impostos automaticamente? (True/False) | Execute esse calculo automatico |

---

## CAMPOS ADICIONAIS QUE VOCÊS USAM?

Liste aqui outros campos que são utilizados no processo de criação de pedidos:

1. _____
2. _____
3. _____

---

## OBSERVAÇÕES

- Algum campo tem valor padrão que sempre é usado?
- Há campos que dependem de outros (ex: operação fiscal depende do tipo de cliente)?
- Existem validações específicas antes de criar o pedido?

