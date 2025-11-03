# 📋 Mapeamento Completo - RequisicaoCompraAlocacao

**Data**: 01/11/2025
**Modelo**: `RequisicaoCompraAlocacao` ([app/manufatura/models.py](../../../app/manufatura/models.py))
**Modelo Odoo**: `purchase.request.allocation`

---

## 🎯 OBJETIVO

Mapear a tabela intermediária N:N que relaciona:
- **Requisições de Compra** (purchase.request.line) ↔ **Pedidos de Compra** (purchase.order.line)

Permite rastrear:
1. ✅ Qual requisição gerou qual pedido de compra
2. ✅ Quantidades alocadas vs abertas
3. ✅ Status de atendimento de requisições
4. ✅ Relacionamento com movimentos de estoque

---

## 📊 ESTRUTURA DO MODELO ODOO

### Modelo: `purchase.request.allocation`

| Campo | Tipo | Relaciona Com | Obrigatório |
|-------|------|---------------|-------------|
| `id` | integer | - | ✅ PK |
| `purchase_request_line_id` | many2one | purchase.request.line | ✅ Sim |
| `purchase_line_id` | many2one | purchase.order.line | ❌ Não |
| `product_id` | many2one | product.product | ❌ Não |
| `product_uom_id` | many2one | uom.uom | ✅ Sim |
| `allocated_product_qty` | float | - | ❌ Não |
| `requested_product_uom_qty` | float | - | ❌ Não |
| `open_product_qty` | float | - | ❌ Não |
| `purchase_state` | selection | - | ❌ Não |
| `stock_move_id` | many2one | stock.move | ❌ Não |
| `company_id` | many2one | res.company | ❌ Não |
| `create_date` | datetime | - | ❌ Não |
| `write_date` | datetime | - | ❌ Não |
| `create_uid` | many2one | res.users | ❌ Não |
| `write_uid` | many2one | res.users | ❌ Não |

---

## 🗺️ MAPEAMENTO DE CAMPOS

### Campo 1: `id` → `odoo_allocation_id`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `VARCHAR(50)` UNIQUE |
| **Tipo Odoo** | `integer` |
| **Origem Odoo** | `purchase.request.allocation.id` |
| **Processamento** | Converter para string |
| **Uso** | Identificador único da alocação no Odoo |

```python
odoo_allocation_id = str(alocacao_odoo['id'])  # "574"
```

---

### Campo 2: `purchase_request_line_id` → `purchase_request_line_odoo_id` + FK

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `VARCHAR(50)` NOT NULL + FK para `requisicao_compras` |
| **Tipo Odoo** | `many2one` → `purchase.request.line` |
| **Origem Odoo** | `alocacao['purchase_request_line_id'][0]` |
| **Processamento** | Extrair ID e buscar registro local |
| **Obrigatório** | ✅ Sim |

```python
# Odoo retorna: [853, "[800000001] SERVICO DE INFORMATICA\nAnálise..."]
purchase_request_line_odoo_id = str(alocacao['purchase_request_line_id'][0])  # "853"

# Buscar FK local
requisicao = RequisicaoCompras.query.filter_by(
    odoo_id=purchase_request_line_odoo_id
).first()

requisicao_compra_id = requisicao.id if requisicao else None
```

---

### Campo 3: `purchase_line_id` → `purchase_order_line_odoo_id` + FK

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `VARCHAR(50)` NULLABLE + FK para `pedido_compras` |
| **Tipo Odoo** | `many2one` → `purchase.order.line` |
| **Origem Odoo** | `alocacao['purchase_line_id'][0]` ou `False` |
| **Processamento** | Extrair ID e buscar registro local (se existir) |
| **Obrigatório** | ❌ Não (pode não ter pedido ainda) |

```python
# Odoo retorna: [2528, "[800000001] SERVICO..."] ou False
purchase_line_id_tuple = alocacao.get('purchase_line_id')

if purchase_line_id_tuple and purchase_line_id_tuple != False:
    purchase_order_line_odoo_id = str(purchase_line_id_tuple[0])  # "2528"

    # Buscar FK local
    pedido = PedidoCompras.query.filter_by(
        odoo_id=purchase_order_line_odoo_id
    ).first()

    pedido_compra_id = pedido.id if pedido else None
else:
    purchase_order_line_odoo_id = None
    pedido_compra_id = None
```

---

### Campo 4: `product_id` → `cod_produto` + `nome_produto`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `VARCHAR(50)` NOT NULL |
| **Tipo Odoo** | `many2one` → `product.product` |
| **Origem Odoo** | `alocacao['product_id'][0]` |
| **Processamento** | Buscar `default_code` no `product.product` |
| **Obrigatório** | ✅ Sim |

```python
# Odoo retorna: [30122, "[800000001] SERVICO DE INFORMATICA"]
product_id_odoo = alocacao['product_id'][0]  # 30122

# Query adicional (pode usar cache de produtos)
produto = conn.read('product.product', [product_id_odoo], ['default_code', 'name'])[0]

cod_produto = produto['default_code']  # "800000001"
nome_produto = produto['name']  # "SERVICO DE INFORMATICA"
```

---

### Campo 5: `allocated_product_qty` → `qtd_alocada`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `NUMERIC(15, 3)` NOT NULL |
| **Tipo Odoo** | `float` |
| **Origem Odoo** | `alocacao['allocated_product_qty']` |
| **Processamento** | Converter para Decimal |
| **Obrigatório** | ✅ Sim |

```python
from decimal import Decimal

# Odoo retorna: 1.0
qtd_alocada = Decimal(str(alocacao['allocated_product_qty']))  # Decimal('1.0')
```

---

### Campo 6: `requested_product_uom_qty` → `qtd_requisitada`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `NUMERIC(15, 3)` NOT NULL |
| **Tipo Odoo** | `float` |
| **Origem Odoo** | `alocacao['requested_product_uom_qty']` |
| **Processamento** | Converter para Decimal |
| **Obrigatório** | ✅ Sim |

```python
# Odoo retorna: 1.0
qtd_requisitada = Decimal(str(alocacao['requested_product_uom_qty']))  # Decimal('1.0')
```

---

### Campo 7: `open_product_qty` → `qtd_aberta`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `NUMERIC(15, 3)` DEFAULT 0 |
| **Tipo Odoo** | `float` |
| **Origem Odoo** | `alocacao['open_product_qty']` |
| **Processamento** | Converter para Decimal |
| **Obrigatório** | ❌ Não |

```python
# Odoo retorna: 0.0
qtd_aberta = Decimal(str(alocacao.get('open_product_qty', 0)))  # Decimal('0.0')
```

---

### Campo 8: `purchase_state` → `purchase_state`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `VARCHAR(20)` |
| **Tipo Odoo** | `selection` |
| **Origem Odoo** | `alocacao['purchase_state']` |
| **Valores** | 'draft', 'sent', 'purchase', 'done', 'cancel' |
| **Obrigatório** | ❌ Não |

```python
# Odoo retorna: 'purchase'
purchase_state = alocacao.get('purchase_state')  # 'purchase'
```

---

### Campo 9: `stock_move_id` → `stock_move_odoo_id`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `VARCHAR(50)` |
| **Tipo Odoo** | `many2one` → `stock.move` |
| **Origem Odoo** | `alocacao['stock_move_id'][0]` ou `False` |
| **Processamento** | Extrair ID se existir |
| **Obrigatório** | ❌ Não |

```python
# Odoo retorna: False (sem movimento) ou [12345, "Move..."]
stock_move = alocacao.get('stock_move_id')

if stock_move and stock_move != False:
    stock_move_odoo_id = str(stock_move[0])  # "12345"
else:
    stock_move_odoo_id = None
```

---

### Campo 10: `create_date` → `create_date_odoo`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `TIMESTAMP` |
| **Tipo Odoo** | `datetime` |
| **Origem Odoo** | `alocacao['create_date']` |
| **Processamento** | Converter string para datetime |
| **Obrigatório** | ❌ Não |

```python
from datetime import datetime

# Odoo retorna: "2024-07-22 11:31:43"
create_date_str = alocacao.get('create_date')
create_date_odoo = datetime.strptime(create_date_str, '%Y-%m-%d %H:%M:%S') if create_date_str else None
```

---

### Campo 11: `write_date` → `write_date_odoo`

| Propriedade | Valor |
|-------------|-------|
| **Tipo Local** | `TIMESTAMP` |
| **Tipo Odoo** | `datetime` |
| **Origem Odoo** | `alocacao['write_date']` |
| **Processamento** | Converter string para datetime |
| **Obrigatório** | ❌ Não |

```python
# Odoo retorna: "2024-07-22 12:19:05"
write_date_str = alocacao.get('write_date')
write_date_odoo = datetime.strptime(write_date_str, '%Y-%m-%d %H:%M:%S') if write_date_str else None
```

---

## 🔧 PSEUDOCÓDIGO COMPLETO DE IMPORTAÇÃO

```python
def importar_alocacao(alocacao_odoo, conn, produtos_cache):
    """
    Importa uma alocação do Odoo

    Args:
        alocacao_odoo: dict com dados de purchase.request.allocation
        conn: Conexão Odoo
        produtos_cache: Cache de produtos já carregados
    """
    from decimal import Decimal
    from datetime import datetime

    # ========================================
    # PASSO 1: EXTRAIR IDS DO ODOO
    # ========================================

    odoo_allocation_id = str(alocacao_odoo['id'])

    # Linha de requisição (OBRIGATÓRIO)
    purchase_request_line_odoo_id = str(alocacao_odoo['purchase_request_line_id'][0])

    # Linha de pedido (OPCIONAL)
    purchase_line_tuple = alocacao_odoo.get('purchase_line_id')
    purchase_order_line_odoo_id = str(purchase_line_tuple[0]) if purchase_line_tuple and purchase_line_tuple != False else None

    # ========================================
    # PASSO 2: BUSCAR FKs LOCAIS
    # ========================================

    # Buscar requisição local
    requisicao = RequisicaoCompras.query.filter_by(
        odoo_id=purchase_request_line_odoo_id
    ).first()

    if not requisicao:
        logger.warning(f"Requisição {purchase_request_line_odoo_id} não encontrada - IGNORANDO alocação")
        return None

    # Buscar pedido local (se existir)
    pedido_compra_id = None
    if purchase_order_line_odoo_id:
        pedido = PedidoCompras.query.filter_by(
            odoo_id=purchase_order_line_odoo_id
        ).first()
        pedido_compra_id = pedido.id if pedido else None

    # ========================================
    # PASSO 3: BUSCAR PRODUTO
    # ========================================

    product_id_odoo = alocacao_odoo['product_id'][0]

    # Usar cache se disponível
    if product_id_odoo in produtos_cache:
        produto = produtos_cache[product_id_odoo]
    else:
        produto = conn.read('product.product', [product_id_odoo], ['default_code', 'name'])[0]

    cod_produto = produto.get('default_code')
    nome_produto = produto.get('name')

    # ========================================
    # PASSO 4: CONVERTER QUANTIDADES
    # ========================================

    qtd_alocada = Decimal(str(alocacao_odoo.get('allocated_product_qty', 0)))
    qtd_requisitada = Decimal(str(alocacao_odoo.get('requested_product_uom_qty', 0)))
    qtd_aberta = Decimal(str(alocacao_odoo.get('open_product_qty', 0)))

    # ========================================
    # PASSO 5: EXTRAIR STATUS E MOVIMENTO
    # ========================================

    purchase_state = alocacao_odoo.get('purchase_state')

    stock_move = alocacao_odoo.get('stock_move_id')
    stock_move_odoo_id = str(stock_move[0]) if stock_move and stock_move != False else None

    # ========================================
    # PASSO 6: CONVERTER DATAS
    # ========================================

    create_date_str = alocacao_odoo.get('create_date')
    create_date_odoo = datetime.strptime(create_date_str, '%Y-%m-%d %H:%M:%S') if create_date_str else None

    write_date_str = alocacao_odoo.get('write_date')
    write_date_odoo = datetime.strptime(write_date_str, '%Y-%m-%d %H:%M:%S') if write_date_str else None

    # ========================================
    # PASSO 7: CRIAR OBJETO
    # ========================================

    alocacao = RequisicaoCompraAlocacao(
        # FKs
        requisicao_compra_id=requisicao.id,
        pedido_compra_id=pedido_compra_id,

        # IDs Odoo
        odoo_allocation_id=odoo_allocation_id,
        purchase_request_line_odoo_id=purchase_request_line_odoo_id,
        purchase_order_line_odoo_id=purchase_order_line_odoo_id,

        # Produto
        cod_produto=cod_produto,
        nome_produto=nome_produto,

        # Quantidades
        qtd_alocada=qtd_alocada,
        qtd_requisitada=qtd_requisitada,
        qtd_aberta=qtd_aberta,

        # Status
        purchase_state=purchase_state,
        stock_move_odoo_id=stock_move_odoo_id,

        # Controle
        importado_odoo=True,

        # Datas Odoo
        create_date_odoo=create_date_odoo,
        write_date_odoo=write_date_odoo
    )

    return alocacao
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [ ] **Requisição existe**: Verificar se `requisicao_compra_id` é válido
- [ ] **Produto existe**: Verificar se `cod_produto` foi encontrado
- [ ] **Quantidades válidas**: `qtd_alocada` <= `qtd_requisitada`
- [ ] **Converter Decimals**: Usar `Decimal(str(valor))` para precisão
- [ ] **Tratar False do Odoo**: Converter `False` para `None`
- [ ] **Evitar duplicação**: Verificar por `odoo_allocation_id` antes de inserir
- [ ] **Pedido opcional**: `pedido_compra_id` pode ser NULL

---

## 📈 QUERIES ÚTEIS

### Query 1: Ver alocações de uma requisição
```python
requisicao = RequisicaoCompras.query.get(id)
alocacoes = requisicao.alocacoes  # via backref
```

### Query 2: % de atendimento de uma requisição
```python
from sqlalchemy import func

total_alocado = db.session.query(
    func.sum(RequisicaoCompraAlocacao.qtd_alocada)
).filter(
    RequisicaoCompraAlocacao.requisicao_compra_id == requisicao_id
).scalar() or 0

percentual = (total_alocado / requisicao.qtd_produto_requisicao) * 100
```

### Query 3: Requisições sem alocação
```python
requisicoes_sem_alocacao = db.session.query(RequisicaoCompras)\
    .outerjoin(RequisicaoCompraAlocacao)\
    .filter(RequisicaoCompraAlocacao.id == None)\
    .all()
```

---

**Status**: ✅ MAPEAMENTO COMPLETO
**Total de Campos**: 16 campos mapeados
**Pronto para**: Implementação do serviço de importação
