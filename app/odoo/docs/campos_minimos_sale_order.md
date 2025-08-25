# Campos Mínimos para Criar uma Cotação de Venda (sale.order) no Odoo

## 📋 Campos Obrigatórios Mínimos

Para criar uma cotação de venda no Odoo via API, você precisa fornecer apenas alguns campos essenciais:

### 1. **partner_id** (Obrigatório)
- **Tipo**: Integer (ID do parceiro/cliente)
- **Descrição**: ID do cliente (res.partner) para quem a cotação será criada
- **Exemplo**: `partner_id: 42`

### 2. **Linhas de Produtos** (Opcional mas necessário para cotação útil)
- Embora tecnicamente você possa criar uma cotação vazia, normalmente você precisa adicionar linhas de produtos

## 📦 Exemplo Mínimo de Criação

```python
from app.odoo.utils.connection import get_odoo_connection

# Conectar ao Odoo
odoo = get_odoo_connection()

# 1. EXEMPLO MAIS SIMPLES - Apenas cliente
cotacao_minima = odoo.execute_kw(
    'sale.order',
    'create',
    [{
        'partner_id': 123,  # ID do cliente (obrigatório)
    }]
)
print(f"Cotação criada com ID: {cotacao_minima}")
```

## 📋 Exemplo com Campos Recomendados

```python
# 2. EXEMPLO RECOMENDADO - Com mais detalhes
cotacao_completa = odoo.execute_kw(
    'sale.order',
    'create',
    [{
        # CAMPOS ESSENCIAIS
        'partner_id': 123,              # ID do cliente (obrigatório)
        
        # CAMPOS RECOMENDADOS (mas opcionais)
        'partner_shipping_id': 124,     # ID do endereço de entrega (se diferente)
        'date_order': '2025-01-20',     # Data da cotação (padrão: hoje)
        'validity_date': '2025-02-20',  # Data de validade da cotação
        'payment_term_id': 1,           # ID das condições de pagamento
        'pricelist_id': 1,              # ID da lista de preços
        'user_id': 2,                   # ID do vendedor/usuário responsável
        'team_id': 1,                   # ID da equipe de vendas
        
        # LINHAS DE PRODUTOS (order_line)
        'order_line': [
            (0, 0, {  # (0, 0, {...}) é a sintaxe para criar nova linha
                'product_id': 456,           # ID do produto
                'product_uom_qty': 10.0,     # Quantidade
                'price_unit': 100.00,        # Preço unitário (opcional - pega do produto)
                'name': 'Descrição do Produto',  # Descrição (opcional - pega do produto)
                'product_uom': 1,            # Unidade de medida (opcional - pega do produto)
            }),
            (0, 0, {  # Segunda linha
                'product_id': 789,
                'product_uom_qty': 5.0,
            })
        ]
    }]
)
```

## 🏷️ Campos Importantes e Seus Valores Padrão

| Campo | Obrigatório | Tipo | Padrão | Descrição |
|-------|-------------|------|---------|-----------|
| **partner_id** | ✅ Sim | Integer | - | ID do cliente |
| partner_shipping_id | Não | Integer | = partner_id | Endereço de entrega |
| partner_invoice_id | Não | Integer | = partner_id | Endereço de faturamento |
| date_order | Não | Date | Hoje | Data da cotação |
| validity_date | Não | Date | - | Validade da cotação |
| state | Não | String | 'draft' | Status (draft, sent, sale, done, cancel) |
| payment_term_id | Não | Integer | Do cliente | Condições de pagamento |
| pricelist_id | Não | Integer | Do cliente | Lista de preços |
| currency_id | Não | Integer | Da empresa | Moeda |
| user_id | Não | Integer | Usuário atual | Vendedor responsável |
| team_id | Não | Integer | Do vendedor | Equipe de vendas |
| company_id | Não | Integer | Empresa atual | Empresa |
| warehouse_id | Não | Integer | Padrão | Armazém |

## 📝 Campos para Linhas de Produtos (sale.order.line)

| Campo | Obrigatório | Tipo | Descrição |
|-------|-------------|------|-----------|
| **product_id** | ✅ Sim* | Integer | ID do produto |
| **name** | ✅ Sim* | String | Descrição da linha |
| product_uom_qty | Não | Float | Quantidade (padrão: 1.0) |
| price_unit | Não | Float | Preço unitário (padrão: do produto) |
| product_uom | Não | Integer | Unidade de medida (padrão: do produto) |
| discount | Não | Float | Desconto em % |
| tax_id | Não | [(6,0,[ids])] | IDs dos impostos |

*Nota: É necessário fornecer `product_id` OU `name`. Se fornecer `product_id`, o `name` é preenchido automaticamente.

## 🔍 Como Descobrir IDs Necessários

```python
# Buscar ID de um cliente por CNPJ
cliente = odoo.search_read(
    'res.partner',
    [('l10n_br_cnpj', '=', '12.345.678/0001-90')],
    ['id', 'name'],
    limit=1
)
partner_id = cliente[0]['id'] if cliente else None

# Buscar ID de um produto por código
produto = odoo.search_read(
    'product.product',
    [('default_code', '=', 'PROD001')],
    ['id', 'name', 'list_price'],
    limit=1
)
product_id = produto[0]['id'] if produto else None

# Buscar condições de pagamento
payment_terms = odoo.search_read(
    'account.payment.term',
    [],
    ['id', 'name']
)

# Buscar lista de preços
pricelists = odoo.search_read(
    'product.pricelist',
    [],
    ['id', 'name', 'currency_id']
)
```

## ⚡ Exemplo Completo Funcional

```python
from app.odoo.utils.connection import get_odoo_connection
from datetime import datetime, timedelta

def criar_cotacao_minima(cnpj_cliente, produtos):
    """
    Cria uma cotação com campos mínimos necessários
    
    Args:
        cnpj_cliente: CNPJ do cliente
        produtos: Lista de dicts com 'codigo' e 'quantidade'
    
    Returns:
        ID da cotação criada ou None se erro
    """
    try:
        odoo = get_odoo_connection()
        
        # 1. Buscar cliente
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_cliente)],
            ['id'],
            limit=1
        )
        
        if not cliente:
            print(f"Cliente com CNPJ {cnpj_cliente} não encontrado")
            return None
        
        partner_id = cliente[0]['id']
        
        # 2. Preparar linhas de produtos
        order_lines = []
        for prod in produtos:
            # Buscar produto
            produto = odoo.search_read(
                'product.product',
                [('default_code', '=', prod['codigo'])],
                ['id'],
                limit=1
            )
            
            if produto:
                order_lines.append((0, 0, {
                    'product_id': produto[0]['id'],
                    'product_uom_qty': prod['quantidade']
                }))
        
        # 3. Criar cotação com CAMPOS MÍNIMOS
        cotacao_data = {
            'partner_id': partner_id,  # ÚNICO CAMPO REALMENTE OBRIGATÓRIO
        }
        
        # Adicionar linhas se houver
        if order_lines:
            cotacao_data['order_line'] = order_lines
        
        # 4. Criar cotação
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data]
        )
        
        print(f"✅ Cotação criada com sucesso! ID: {cotacao_id}")
        
        # 5. Buscar número da cotação criada
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'state', 'amount_total']
        )
        
        if cotacao:
            print(f"   Número: {cotacao[0]['name']}")
            print(f"   Status: {cotacao[0]['state']}")
            print(f"   Total: R$ {cotacao[0]['amount_total']}")
        
        return cotacao_id
        
    except Exception as e:
        print(f"❌ Erro ao criar cotação: {e}")
        return None

# Exemplo de uso
if __name__ == "__main__":
    # Criar cotação com campos mínimos
    produtos_exemplo = [
        {'codigo': 'PROD001', 'quantidade': 10},
        {'codigo': 'PROD002', 'quantidade': 5}
    ]
    
    cotacao_id = criar_cotacao_minima(
        cnpj_cliente='12.345.678/0001-90',
        produtos=produtos_exemplo
    )
```

## 🚨 Observações Importantes

1. **Campo Absolutamente Mínimo**: Tecnicamente, apenas `partner_id` é obrigatório para criar uma cotação
2. **Validações do Odoo**: O Odoo pode ter validações adicionais configuradas que exigem outros campos
3. **Campos Calculados**: Muitos campos são calculados automaticamente (total, impostos, etc.)
4. **Workflow**: Após criar como 'draft', você pode:
   - Enviar por email: `action_quotation_send`
   - Confirmar venda: `action_confirm`
   - Cancelar: `action_cancel`

## 📚 Referências Úteis

- [Documentação Oficial Odoo - Sale Order](https://www.odoo.com/documentation/16.0/developer/reference/backend/orm.html)
- Modelo: `sale.order` (Cotações/Pedidos de Venda)
- Modelo de Linhas: `sale.order.line` (Itens da Cotação)
- Cliente: `res.partner` (Parceiros/Clientes)
- Produtos: `product.product` (Produtos)