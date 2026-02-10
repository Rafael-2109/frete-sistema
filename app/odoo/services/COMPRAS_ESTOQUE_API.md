# 📦 API de Integração Odoo - Compras e Controle de Estoque de Componentes

**Data**: 31/10/2025
**Objetivo**: Controle de estoque de componentes (produto_comprado=True) para produção/revenda

---

## 🎯 ESCOPO DO PROJETO

### Funcionalidades Planejadas:

1. **Entradas Previstas**: Requisições e pedidos de compras importados do Odoo
2. **Saídas Previstas**: Programação de produção explodida pela estrutura (ListaMateriais)
3. **Baixas Efetivas**: Explosão de estrutura das MovimentacaoEstoque tipo PRODUCAO
4. **Projeção de Estoque**: 60 dias para produtos com produto_comprado=True

---

## 📊 MODELOS LOCAIS EXISTENTES

### 1. [app/estoque/models.py](../../../app/estoque/models.py)

#### MovimentacaoEstoque (linhas 26-96)
**Objetivo**: Controle de entradas/saídas efetivas

```python
# CAMPOS CRÍTICOS:
cod_produto = db.Column(db.String(50), nullable=False, index=True)
data_movimentacao = db.Column(db.Date, nullable=False, index=True)
tipo_movimentacao = db.Column(db.String(50), nullable=False, index=True)
# Valores: ENTRADA, SAIDA, AJUSTE, PRODUCAO

local_movimentacao = db.Column(db.String(50), nullable=False)
# Valores: COMPRA, VENDA, PRODUCAO, AJUSTE, DEVOLUCAO

qtd_movimentacao = db.Column(db.Numeric(15, 3), nullable=False)
numero_nf = db.Column(db.String(20), nullable=True, index=True)
```

**Uso**: Baixas efetivas quando produtos são consumidos na produção.

---

### 2. [app/producao/models.py](../../../app/producao/models.py)

#### CadastroPalletizacao (linhas 60-136)
**CAMPO CRÍTICO**: `produto_comprado` (linha 90)

```python
produto_comprado = db.Column(db.Boolean, nullable=False, default=False)
produto_produzido = db.Column(db.Boolean, nullable=False, default=False)
produto_vendido = db.Column(db.Boolean, nullable=False, default=True)
lead_time = db.Column(db.Integer, nullable=True)  # Renomeado de lead_time_mto
lote_minimo_compra = db.Column(db.Integer, nullable=True)  # Novo campo
```

**Uso**: Identificar quais produtos devem ter controle de estoque de compras (produto_comprado=True).

#### ProgramacaoProducao (linhas 4-56)
```python
data_programacao = db.Column(db.Date, nullable=False, index=True)
cod_produto = db.Column(db.String(50), nullable=False, index=True)
qtd_programada = db.Column(db.Float, nullable=False)
linha_producao = db.Column(db.String(50), nullable=True)
```

**Uso**: Base para calcular saídas previstas (explodindo ListaMateriais).

---

### 3. [app/manufatura/models.py](../../../app/manufatura/models.py)

#### RequisicaoCompras (linhas 176-203)
**Status**: JÁ EXISTE

```python
# CAMPOS PRINCIPAIS:
num_requisicao = db.Column(db.String(30), unique=True, nullable=False, index=True)
data_requisicao_criacao = db.Column(db.Date, nullable=False)
cod_produto = db.Column(db.String(50), nullable=False, index=True)
qtd_produto_requisicao = db.Column(db.Numeric(15, 3), nullable=False)
data_requisicao_solicitada = db.Column(db.Date)
data_necessidade = db.Column(db.Date)
status = db.Column(db.String(20), default='Pendente', index=True)

# CAMPOS ODOO (JÁ IMPLEMENTADOS):
importado_odoo = db.Column(db.Boolean, default=False)
odoo_id = db.Column(db.String(50))
requisicao_odoo_id = db.Column(db.String(50), index=True)
status_requisicao = db.Column(db.String(20), default='rascunho')
# Valores: 'rascunho', 'enviada_odoo', 'confirmada'
data_envio_odoo = db.Column(db.DateTime)
data_confirmacao_odoo = db.Column(db.DateTime)
```

**Uso**: Entradas previstas - requisições criadas internamente ou importadas do Odoo.

---

#### PedidoCompras (linhas 205-234)
**Status**: JÁ EXISTE

```python
# CAMPOS PRINCIPAIS:
num_pedido = db.Column(db.String(30), unique=True, nullable=False, index=True)
num_requisicao = db.Column(db.String(30), db.ForeignKey('requisicao_compras.num_requisicao'))
cnpj_fornecedor = db.Column(db.String(20), index=True)
raz_social = db.Column(db.String(255))
numero_nf = db.Column(db.String(20))
data_pedido_criacao = db.Column(db.Date)
data_pedido_previsao = db.Column(db.Date)
data_pedido_entrega = db.Column(db.Date)
cod_produto = db.Column(db.String(50), nullable=False, index=True)
qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
preco_produto_pedido = db.Column(db.Numeric(15, 4))
confirmacao_pedido = db.Column(db.Boolean, default=False)

# CAMPOS ODOO (JÁ IMPLEMENTADOS):
importado_odoo = db.Column(db.Boolean, default=False)
odoo_id = db.Column(db.String(50))
```

**Uso**: Entradas previstas - pedidos confirmados aguardando recebimento.

---

#### ListaMateriais (linhas 254-300)
**Estrutura de produtos (BOM)**

```python
cod_produto_produzido = db.Column(db.String(50), nullable=False, index=True)
cod_produto_componente = db.Column(db.String(50), nullable=False, index=True)
qtd_utilizada = db.Column(db.Numeric(15, 6), nullable=False)
status = db.Column(db.String(10), default='ativo', index=True)
versao = db.Column(db.String(100), default='v1')
```

**Uso**: Explodir programação de produção para calcular necessidade de componentes (saídas previstas).

---

## 🔗 MODELOS ODOO - CAMPOS NECESSÁRIOS

### 1. purchase.requisition (Requisição de Compras)

**Modelo Odoo**: `purchase.requisition`
**Objetivo**: Importar requisições confirmadas

#### Campos Obrigatórios:
```python
CAMPOS_REQUISICAO_ODOO = [
    'id',                    # ID único no Odoo
    'name',                  # Número da requisição (ex: REQ/2025/0001)
    'state',                 # Estado: draft, in_progress, open, done, cancel
    'create_date',           # Data de criação
    'ordering_date',         # Data de solicitação
    'schedule_date',         # Data de necessidade/previsão
    'user_id',               # Usuário criador (ID, name)

    # Linhas da requisição (purchase.requisition.line):
    'line_ids',              # IDs das linhas
    'line_ids/product_id',   # Produto (ID, default_code, name)
    'line_ids/product_qty',  # Quantidade solicitada
    'line_ids/product_uom_id', # Unidade de medida
    'line_ids/price_unit',   # Preço unitário (se disponível)
]
```

#### Filtros de Importação:
```python
FILTRO = [
    ['state', 'in', ['in_progress', 'open', 'done']],  # Requisições ativas
]
```

---

### 2. purchase.order + purchase.order.line (Pedido de Compras)

**Modelos Odoo**: `purchase.order` + `purchase.order.line`
**Objetivo**: Importar pedidos confirmados com previsão de entrega

#### Campos Obrigatórios - purchase.order:
```python
CAMPOS_PEDIDO_COMPRA_ODOO = [
    'id',                    # ID único no Odoo
    'name',                  # Número do pedido (ex: PO00123)
    'state',                 # Estado: draft, sent, purchase, done, cancel
    'date_order',            # Data de criação
    'date_approve',          # Data de confirmação
    'date_planned',          # Data prevista de entrega
    'partner_id',            # Fornecedor (ID, name, l10n_br_cnpj)
    'user_id',               # Usuário comprador (ID, name)
    'origin',                # Documento origem (pode ser requisição)
    'invoice_ids',           # IDs das faturas (para pegar número NF)
    'picking_ids',           # IDs dos recebimentos vinculados

    # Campos calculados/úteis:
    'amount_total',          # Valor total do pedido
    'currency_id',           # Moeda
]
```

#### Campos Obrigatórios - purchase.order.line:
```python
CAMPOS_LINHA_PEDIDO_ODOO = [
    'id',                    # ID da linha
    'order_id',              # ID do pedido pai
    'product_id',            # Produto (ID, default_code, name)
    'product_qty',           # Quantidade
    'qty_received',          # Quantidade recebida
    'qty_invoiced',          # Quantidade faturada
    'price_unit',            # Preço unitário
    'price_subtotal',        # Subtotal
    'price_tax',             # Valor impostos (ICMS, PIS, COFINS)
    'taxes_id',              # IDs dos impostos aplicados
    'product_uom',           # Unidade de medida
    'date_planned',          # Data prevista linha
]
```

#### Filtros de Importação:
```python
FILTRO = [
    ['state', 'in', ['purchase', 'done']],  # Pedidos confirmados
    ['date_planned', '>=', data_inicio],    # Data prevista >= hoje
]
```

---

### 3. stock.picking + stock.move (Recebimento de Materiais)

**Modelos Odoo**: `stock.picking` + `stock.move`
**Objetivo**: Importar entradas efetivas de materiais comprados

#### Campos Obrigatórios - stock.picking:
```python
CAMPOS_RECEBIMENTO_ODOO = [
    'id',                    # ID único
    'name',                  # Número do recebimento (ex: WH/IN/00123)
    'picking_type_id',       # Tipo (code='incoming' para recebimentos)
    'state',                 # Estado: draft, waiting, confirmed, assigned, done, cancel
    'scheduled_date',        # Data programada
    'date_done',             # Data efetiva do recebimento
    'origin',                # Documento origem (pedido de compra)
    'partner_id',            # Fornecedor (ID, name, l10n_br_cnpj)
    'purchase_id',           # ID do pedido de compra vinculado
    'location_dest_id',      # Localização destino (ID, name)
]
```

#### Campos Obrigatórios - stock.move:
```python
CAMPOS_MOVIMENTO_ESTOQUE_ODOO = [
    'id',                    # ID único
    'picking_id',            # ID do recebimento pai
    'product_id',            # Produto (ID, default_code, name)
    'product_uom_qty',       # Quantidade programada
    'quantity',              # Quantidade efetiva movimentada (quando done)
    'product_uom',           # Unidade de medida
    'date',                  # Data do movimento
    'date_expected',         # Data esperada
    'state',                 # Estado: draft, confirmed, assigned, done, cancel
    'origin',                # Origem
    'purchase_line_id',      # ID da linha de pedido origem
]
```

#### Filtros de Importação:
```python
FILTRO_RECEBIMENTO = [
    ['picking_type_id.code', '=', 'incoming'],  # Apenas recebimentos
    ['state', '=', 'done'],                     # Apenas concluídos
    ['date_done', '>=', data_inicio],           # Recebimentos recentes
]
```

---

## 🔄 FLUXO DE INTEGRAÇÃO PROPOSTO

### 1. Entradas Previstas (Requisições)
```
Odoo: purchase.requisition (state=in_progress/open/done)
   ↓
Sistema: RequisicaoCompras (importado_odoo=True)
   ↓
Filtro: CadastroPalletizacao.produto_comprado=True
   ↓
Projeção: Entrada prevista em data_necessidade
```

### 2. Entradas Previstas (Pedidos Confirmados)
```
Odoo: purchase.order (state=purchase) + purchase.order.line
   ↓
Sistema: PedidoCompras (importado_odoo=True)
   ↓
Filtro: CadastroPalletizacao.produto_comprado=True
   ↓
Projeção: Entrada prevista em data_pedido_previsao
```

### 3. Entradas Efetivas (Recebimentos)
```
Odoo: stock.picking (type=incoming, state=done) + stock.move
   ↓
Sistema: MovimentacaoEstoque (tipo_movimentacao=ENTRADA, local_movimentacao=COMPRA)
   ↓
Filtro: CadastroPalletizacao.produto_comprado=True
   ↓
Atualização: Estoque físico atualizado
```

### 4. Saídas Previstas (Programação Explodida)
```
Sistema: ProgramacaoProducao (data_programacao)
   ↓
Explosão: ListaMateriais.explode(cod_produto_produzido)
   ↓
Filtro: CadastroPalletizacao.produto_comprado=True (componentes)
   ↓
Projeção: Saída prevista em data_programacao
```

### 5. Saídas Efetivas (Produção Realizada)
```
Sistema: MovimentacaoEstoque (tipo_movimentacao=SAIDA, local_movimentacao=PRODUCAO)
   ↓
Explosão: ListaMateriais.explode(cod_produto_produzido)
   ↓
Filtro: CadastroPalletizacao.produto_comprado=True (componentes)
   ↓
Baixa: Consumo real de componentes
```

---

## 📋 QUERIES DE EXEMPLO

### Buscar Requisições no Odoo
```python
odoo.execute_kw(
    'purchase.requisition',
    'search_read',
    [[['state', 'in', ['in_progress', 'open', 'done']]]],
    {
        'fields': [
            'id', 'name', 'state', 'create_date', 'ordering_date',
            'schedule_date', 'user_id', 'line_ids'
        ]
    }
)
```

### Buscar Pedidos de Compras no Odoo
```python
odoo.execute_kw(
    'purchase.order',
    'search_read',
    [[['state', 'in', ['purchase', 'done']]]],
    {
        'fields': [
            'id', 'name', 'state', 'date_order', 'date_approve',
            'date_planned', 'partner_id', 'user_id', 'origin',
            'picking_ids', 'invoice_ids'
        ]
    }
)

# Depois buscar linhas:
odoo.execute_kw(
    'purchase.order.line',
    'search_read',
    [[['order_id', 'in', [pedido_ids]]]],
    {
        'fields': [
            'id', 'order_id', 'product_id', 'product_qty',
            'qty_received', 'price_unit', 'price_tax', 'date_planned'
        ]
    }
)
```

### Buscar Recebimentos no Odoo
```python
odoo.execute_kw(
    'stock.picking',
    'search_read',
    [[
        ['picking_type_id.code', '=', 'incoming'],
        ['state', '=', 'done'],
        ['date_done', '>=', data_inicio]
    ]],
    {
        'fields': [
            'id', 'name', 'state', 'scheduled_date', 'date_done',
            'origin', 'partner_id', 'purchase_id', 'move_ids_without_package'
        ]
    }
)

# Depois buscar movimentos:
odoo.execute_kw(
    'stock.move',
    'search_read',
    [[['picking_id', 'in', [picking_ids]]]],
    {
        'fields': [
            'id', 'picking_id', 'product_id', 'product_uom_qty',
            'quantity', 'date', 'state', 'purchase_line_id'
        ]
    }
)
```

---

## ⚠️ VALIDAÇÕES CRÍTICAS

### 1. Produto Deve Ser Controlado
```python
# ANTES de importar, verificar:
produto = CadastroPalletizacao.query.filter_by(
    cod_produto=cod_produto_odoo,
    produto_comprado=True  # ← CRÍTICO
).first()

if not produto:
    # NÃO importar - produto não é comprado
    logger.warning(f"Produto {cod_produto_odoo} não está marcado como produto_comprado")
    continue
```

### 2. Evitar Duplicação
```python
# ANTES de criar RequisicaoCompras:
existe = RequisicaoCompras.query.filter_by(
    odoo_id=str(requisicao_odoo['id'])
).first()

if existe:
    # Atualizar ao invés de criar
    existe.qtd_produto_requisicao = nova_quantidade
    db.session.commit()
```

### 3. Sincronizar Estado
```python
# Mapear estados Odoo → Sistema:
MAPA_STATUS_REQUISICAO = {
    'draft': 'Pendente',
    'in_progress': 'Em Andamento',
    'open': 'Aberta',
    'done': 'Concluída',
    'cancel': 'Cancelada'
}

MAPA_STATUS_PEDIDO = {
    'draft': 'Rascunho',
    'sent': 'Enviado',
    'purchase': 'Confirmado',
    'done': 'Recebido',
    'cancel': 'Cancelado'
}
```

---

## 🚀 PRÓXIMOS PASSOS

### Fase 1 - Importação de Requisições
1. ✅ Modelos já existem ([RequisicaoCompras](../../../app/manufatura/models.py:176-203))
2. ⏳ Criar serviço de importação em [manufatura_service.py](manufatura_service.py:39)
3. ⏳ Testar com dados reais do Odoo
4. ⏳ Validar filtro produto_comprado=True

### Fase 2 - Importação de Pedidos
1. ✅ Modelos já existem ([PedidoCompras](../../../app/manufatura/models.py:205-234))
2. ⏳ Criar serviço de importação (similar a requisições)
3. ⏳ Vincular com requisições (num_requisicao FK)
4. ⏳ Validar previsão de entrega

### Fase 3 - Importação de Recebimentos
1. ⏳ Analisar se precisa novo modelo ou usa MovimentacaoEstoque
2. ⏳ Criar serviço de importação de stock.picking
3. ⏳ Criar baixa automática em MovimentacaoEstoque
4. ⏳ Validar integração com número_nf

### Fase 4 - Explosão de Programação
1. ✅ ListaMateriais já existe ([ListaMateriais](../../../app/manufatura/models.py:254-300))
2. ⏳ Criar serviço de explosão (ProgramacaoProducao → Componentes)
3. ⏳ Filtrar apenas produto_comprado=True
4. ⏳ Calcular necessidade líquida

### Fase 5 - Projeção de Estoque 60 dias
1. ⏳ Criar serviço de projeção consolidado
2. ⏳ Agregar: Entradas previstas + Saídas previstas
3. ⏳ Calcular saldo projetado dia a dia
4. ⏳ Alertar produtos em ruptura

---

## 📝 OBSERVAÇÕES IMPORTANTES

1. **Serviço Existente**: [manufatura_service.py](manufatura_service.py) já tem estrutura para importação (linha 39)
2. **Mapper Existente**: [manufatura_mapper.py](../utils/manufatura_mapper.py) já tem mapeamentos hardcoded
3. **Conexão Odoo**: Usar [connection.py](../utils/connection.py) - `get_odoo_connection()`
4. **Não Assumir**: Sempre verificar campos no Odoo real antes de implementar
5. **Filtro Crítico**: SEMPRE filtrar por `produto_comprado=True` para evitar controlar produtos errados

---

**Status**: DOCUMENTAÇÃO INICIAL - AGUARDANDO VALIDAÇÃO
**Autor**: Sistema de Fretes
**Revisão**: Necessária antes de implementação
