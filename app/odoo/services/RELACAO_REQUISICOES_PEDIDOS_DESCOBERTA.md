# 🔍 DESCOBERTA: Relacionamento Real Requisições ↔ Pedidos

**Data**: 01/11/2025  
**Método**: Análise empírica (banco local + API Odoo)  
**Status**: ✅ Relacionamento descoberto e documentado

---

## 📊 DADOS COLETADOS

### 1. Banco Local
- ✅ **Requisições**: 3.490 linhas (2.880 requisições únicas)
- ❌ **Pedidos**: 0 (ainda não importados)

### 2. Odoo (API)
- ✅ **purchase.request** + **purchase.request.line**
- ✅ **purchase.order** + **purchase.order.line**

---

## 🔗 RELACIONAMENTO DESCOBERTO

### ✅ purchase.request.line → purchase.order.line

**Campo encontrado**: `purchase_lines`

```json
{
  "requisicao": "REQ/FB/06618",
  "linha_id": 20448,
  "produto": "[800000012] SERVICO DE PROMOCAO DE VENDA",
  "quantidade": 1.0,
  "purchase_lines": [85772]  ← Lista de IDs de linhas de pedidos
}
```

**Conclusão**:
- ✅ Requisição CONHECE os pedidos que a atendem
- ✅ Relação **1:N** (1 linha de requisição → N linhas de pedido)
- ✅ Campo existe e está populado

---

### ❌ purchase.order.line → purchase.request.line

**Campo tentado**: `request_line_id`

**Erro retornado**:
```
ValueError: Invalid field 'request_line_id' on model 'purchase.order.line'
```

**Conclusão**:
- ❌ Pedido NÃO CONHECE qual requisição o originou
- ❌ Campo `request_line_id` NÃO EXISTE no seu Odoo
- ❌ Relacionamento reverso IMPOSSÍVEL via API

---

## 📐 ARQUITETURA REAL

```
┌────────────────────────────┐
│ purchase.request           │
│ - name: "REQ/FB/06611"     │
│ - line_ids: [20448, 20449] │
└─────────┬──────────────────┘
          │ One2Many
          ↓
┌────────────────────────────┐
│ purchase.request.line      │  ✅ CONHECE OS PEDIDOS
│ - id: 20448                │
│ - product_qty: 100         │
│ - purchase_lines: [85772]  │ ← ÚNICO VÍNCULO!
└─────────┬──────────────────┘
          │ Referência (SEM FK reversa)
          ↓
┌────────────────────────────┐
│ purchase.order.line        │  ❌ NÃO CONHECE A REQUISIÇÃO
│ - id: 85772                │
│ - product_qty: 60          │
│ - request_line_id: ❌      │ ← NÃO EXISTE
└─────────┬──────────────────┘
          │ Many2One
          ↓
┌────────────────────────────┐
│ purchase.order             │
│ - name: "C2511687"         │
│ - partner_id: Fornecedor X │
└────────────────────────────┘
```

---

## 💡 CENÁRIOS REAIS

### Cenário 1: Atendimento Total
```
Requisição: REQ/001
└─ Linha: 100 un
   └─ purchase_lines: [PO_LINE_001]

Pedido PO_LINE_001: 100 un → Atende 100%
```

### Cenário 2: Atendimento Parcial
```
Requisição: REQ/002
└─ Linha: 1000 un
   └─ purchase_lines: [PO_LINE_002, PO_LINE_003]

Pedido PO_LINE_002: 600 un → Atende 60%
Pedido PO_LINE_003: 400 un → Atende 40%
```

### Cenário 3: Sem Requisição
```
Pedido PO/004: 50 un
(Compra direta, sem requisição)
```

---

## 🎯 RECOMENDAÇÃO FINAL

### ✅ Manter Arquitetura Atual

**Estrutura**:
- `RequisicaoCompras` (tabela independente)
- `PedidoCompras` (tabela independente)
- `PedidoCompras.num_requisicao` (campo informativo SEM FK)

**Justificativa**:
1. Odoo não tem FK reversa
2. Relacionamento é unidirecional
3. Pedidos podem existir sem requisição
4. Vínculo é opcional

---

## 📝 CAMPOS SUGERIDOS

### RequisicaoCompras

```python
class RequisicaoCompras(db.Model):
    # Campos atuais mantidos
    qtd_produto_requisicao = db.Column(db.Numeric(15, 3))

    # ✅ NOVOS: Campos calculados (@property)
    @property
    def qtd_com_pedido(self):
        """Quantidade já com pedidos vinculados"""
        return db.session.query(
            func.coalesce(func.sum(PedidoCompras.qtd_produto_pedido), 0)
        ).filter(
            PedidoCompras.num_requisicao == self.num_requisicao,
            PedidoCompras.cod_produto == self.cod_produto
        ).scalar()

    @property
    def qtd_sem_pedido(self):
        """Quantidade ainda sem pedido"""
        return self.qtd_produto_requisicao - self.qtd_com_pedido

    @property
    def percentual_atendimento(self):
        """% atendido"""
        if self.qtd_produto_requisicao == 0:
            return 0
        return (self.qtd_com_pedido / self.qtd_produto_requisicao) * 100
```

### PedidoCompras

```python
class PedidoCompras(db.Model):
    # MANTER como está
    num_requisicao = db.Column(db.String(30), index=True)  # SEM FK
```

---

## 📋 CONCLUSÕES

### ✅ SABEMOS:
1. Requisições podem ter N pedidos (via `purchase_lines`)
2. Pedidos NÃO conhecem requisição (campo não existe no Odoo)
3. Relacionamento é unidirecional
4. Pedidos podem existir sem requisição

### ❌ NÃO PODEMOS:
1. Importar vínculo pedido→requisição do Odoo
2. Criar FK formal entre modelos
3. Garantir rastreabilidade 100% automática

### ✅ SOLUÇÃO:
**Manter separado + campos calculados**
- Usar `@property` para mostrar `qtd_com_pedido`
- Calcular sob demanda via query
- Evitar tabela de vínculo (não temos dados para popular)

---

**Status**: ✅ ANÁLISE CONCLUÍDA  
**Decisão**: Arquitetura atual está correta  
**Ação**: Adicionar @property em RequisicaoCompras
