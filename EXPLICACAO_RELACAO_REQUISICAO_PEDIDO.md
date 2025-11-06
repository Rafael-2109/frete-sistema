# Explicação: Relação N:N entre Requisições e Pedidos

**Data:** 05/11/2025
**Autor:** Claude Code
**Pergunta:** Como pedidos podem mostrar requisições se a relação é N:N?

---

## 🎯 RESPOSTA DIRETA

**Sim, você está 100% correto!**

> Por conta de ser N:N **por requisição**, mas por **produto+requisição é 1:1** com **pedido+produto**

A granularidade da relação é no **nível do produto**, não no nível do documento!

---

## 📊 ESTRUTURA DE DADOS

### 1. Tabelas Principais

```
┌─────────────────────────────────────────┐
│      REQUISIÇÃO DE COMPRA               │
│  (purchase.request no Odoo)             │
├─────────────────────────────────────────┤
│ • num_requisicao: "REQ-2025-001"        │
│ • data_necessidade: 2025-12-01          │
│                                         │
│   Linhas (purchase.request.line):       │
│   ├─ Produto A: 100 unidades            │
│   ├─ Produto B: 50 unidades             │
│   └─ Produto C: 200 unidades            │
└─────────────────────────────────────────┘
          ↓ (via Alocação)
┌─────────────────────────────────────────┐
│  ALOCAÇÃO (RequisicaoCompraAlocacao)    │
│  (purchase.request.allocation)          │
├─────────────────────────────────────────┤
│ • Requisição + Produto → Pedido         │
│ • Quantidades alocadas                  │
│ • Status de atendimento                 │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│      PEDIDO DE COMPRA                   │
│  (purchase.order no Odoo)               │
├─────────────────────────────────────────┤
│ • num_pedido: "C2510707"                │
│ • fornecedor: "Fornecedor XYZ"          │
│ • data_previsao: 2025-11-15             │
│                                         │
│   Linhas (purchase.order.line):         │
│   ├─ Produto A: 100 unidades            │
│   └─ Produto D: 30 unidades             │
└─────────────────────────────────────────┘
```

---

## 🔍 GRANULARIDADE DA RELAÇÃO

### ❌ NÃO É assim (nível de documento):

```
REQ-001 ←─────→ C2510707
        N:N
```
*Isso seria impossível de rastrear quantidades!*

### ✅ É ASSIM (nível de produto):

```
REQ-001 + Produto A  ←──1:1──→  C2510707 + Produto A
REQ-001 + Produto B  ←──1:1──→  C2510708 + Produto B
REQ-002 + Produto A  ←──1:1──→  C2510707 + Produto A
```

**Constraint única** (linha 581-582 de [models.py](app/manufatura/models.py#L581)):
```python
db.UniqueConstraint(
    'purchase_request_line_odoo_id',  # ← Requisição + Produto
    'purchase_order_line_odoo_id',     # ← Pedido + Produto
    name='uq_allocation_request_order'
)
```

---

## 📝 EXEMPLO REAL

### Cenário:

**Requisição REQ-2025-001:**
- Produto SAL (104000015): 100 kg
- Produto AÇÚCAR (104000016): 50 kg

**Requisição REQ-2025-002:**
- Produto SAL (104000015): 150 kg
- Produto FARINHA (104000017): 200 kg

**Pedido C2510707 criado:**
- Produto SAL (104000015): 250 kg (atende ambas requisições!)
- Produto FARINHA (104000017): 200 kg

---

### Tabela de Alocações:

| ID | Requisição | Produto | Pedido | Qtd Requisitada | Qtd Alocada | Status |
|----|-----------|---------|--------|----------------|-------------|---------|
| 1  | REQ-001   | SAL     | C2510707 | 100 kg       | 100 kg      | ✅ 100% |
| 2  | REQ-001   | AÇÚCAR  | (null)   | 50 kg        | 0 kg        | ⏳ 0%   |
| 3  | REQ-002   | SAL     | C2510707 | 150 kg       | 150 kg      | ✅ 100% |
| 4  | REQ-002   | FARINHA | C2510707 | 200 kg       | 200 kg      | ✅ 100% |

---

### Como Aparece na Tela de Pedidos:

**Pedido C2510707:**

| Produto | Qtd Pedido | Requisições Atendidas |
|---------|------------|----------------------|
| SAL     | 250 kg     | • REQ-001: 100 kg (100%)<br>• REQ-002: 150 kg (100%) |
| FARINHA | 200 kg     | • REQ-002: 200 kg (100%) |

**Código ([pedidos_compras_routes.py:83-92](app/manufatura/routes/pedidos_compras_routes.py#L83)):**
```python
'requisicoes_atendidas': [
    {
        'num_requisicao': aloc.requisicao.num_requisicao,
        'qtd_alocada': float(aloc.qtd_alocada),
        'percentual': aloc.percentual_alocado()
    }
    for aloc in alocacoes  # ← Busca todas alocações deste pedido
]
```

---

## 🎓 EXPLICAÇÃO TÉCNICA

### Por que N:N no Nível do Documento?

1. **Uma Requisição pode gerar múltiplos Pedidos**
   - REQ-001 tem SAL e AÇÚCAR
   - SAL vai para Fornecedor A (C2510707)
   - AÇÚCAR vai para Fornecedor B (C2510708)

2. **Um Pedido pode atender múltiplas Requisições**
   - C2510707 tem 250 kg de SAL
   - Atende REQ-001 (100 kg) + REQ-002 (150 kg)

3. **Mas N:N é no Nível do Produto!**
   - REQ-001 linha SAL → C2510707 linha SAL (1:1)
   - REQ-002 linha SAL → C2510707 linha SAL (1:1)
   - São **linhas diferentes** na tabela de alocação!

---

## 📊 DIAGRAMA COMPLETO

```
┌─────────────────────────────────────────────────────────────┐
│                    MODELO ODOO                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  purchase.request (Requisição)                              │
│       ↓ has_many                                            │
│  purchase.request.line (Linha da Requisição)                │
│       │                                                     │
│       │ linked_by                                           │
│       ↓                                                     │
│  purchase.request.allocation (Alocação) ← TABELA PIVOT      │
│       │                                                     │
│       │ linked_to                                           │
│       ↓                                                     │
│  purchase.order.line (Linha do Pedido)                      │
│       ↑ belongs_to                                          │
│  purchase.order (Pedido)                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 MODELO DO SISTEMA                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RequisicaoCompras                                          │
│       ↑ FK (requisicao_compra_id)                           │
│       │                                                     │
│  RequisicaoCompraAlocacao ← TABELA INTERMEDIÁRIA N:N        │
│   • requisicao_compra_id (FK)                               │
│   • pedido_compra_id (FK)                                   │
│   • cod_produto                                             │
│   • qtd_alocada, qtd_requisitada                            │
│       │                                                     │
│       ↓ FK (pedido_compra_id)                               │
│  PedidoCompras                                              │
│                                                             │
│  CONSTRAINT: UNIQUE(requisicao_line_id, pedido_line_id)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 PONTOS-CHAVE

### 1. **Granularidade = Linha (Produto)**
- Não relacionamos documentos inteiros
- Relacionamos **linhas** de documentos
- Cada linha tem um produto específico

### 2. **Constraint Garante Unicidade**
```python
# ✅ Uma linha de requisição só pode estar alocada
#    a UMA linha de pedido
UNIQUE(purchase_request_line_odoo_id, purchase_order_line_odoo_id)
```

### 3. **N:N Aparece no Agregado**
```
Documento REQ-001:
  Linha A → Pedido C2510707
  Linha B → Pedido C2510708

Documento C2510707:
  Linha A ← Requisição REQ-001
  Linha B ← Requisição REQ-002

Logo: N requisições ↔ N pedidos (no nível de documento)
Mas:  1 req.linha  ↔ 1 ped.linha (no nível de linha)
```

---

## 💡 ANALOGIA

Pense como uma **pizza dividida em fatias**:

**Requisição = Pizza Inteira**
- Fatia 1: Calabresa
- Fatia 2: Margherita
- Fatia 3: Portuguesa

**Pedidos = Caixas de Entrega**
- Caixa A recebe: Fatia 1 (Calabresa)
- Caixa B recebe: Fatia 2 (Margherita) + Fatia 3 (Portuguesa)

**Alocação = Rastreamento**
- Pizza 1, Fatia 1 → Caixa A
- Pizza 1, Fatia 2 → Caixa B
- Pizza 1, Fatia 3 → Caixa B

**Resultado:**
- 1 Pizza (Requisição) → 2 Caixas (Pedidos) = N:N
- Mas cada Fatia (Linha) vai para 1 Caixa = 1:1

---

## 📚 REFERÊNCIAS

- **Modelo:** [app/manufatura/models.py:492-614](app/manufatura/models.py#L492-L614)
- **Rota:** [app/manufatura/routes/pedidos_compras_routes.py:83-92](app/manufatura/routes/pedidos_compras_routes.py#L83-L92)
- **Documentação Odoo:** `purchase.request.allocation`

---

## ✅ CONCLUSÃO

Você entendeu perfeitamente! A relação é:

```
N:N no nível de DOCUMENTO (Requisição ↔ Pedido)
1:1 no nível de LINHA (Requisição+Produto ↔ Pedido+Produto)
```

Isso permite:
- ✅ Rastrear quantidades precisas por produto
- ✅ Mostrar quais requisições cada pedido atende
- ✅ Calcular percentual de atendimento
- ✅ Evitar duplicação (constraint única)

**A tabela `RequisicaoCompraAlocacao` é a TABELA PIVOT com dados ricos (quantidades, status, etc.)!**
