# 📊 Estratégia de Projeção de ENTRADAS de Estoque

**Data**: 01/11/2025
**Objetivo**: Definir ÚNICA fonte da verdade para projetar entradas sem duplicação

---

## 🎯 PROBLEMA

Temos 3 tabelas relacionadas:
1. **RequisicaoCompras** - O que precisamos comprar
2. **PedidoCompras** - De quem vamos comprar
3. **RequisicaoCompraAlocacao** - Quem atende o quê (N:N)

**RISCO**: Projetar entrada 3 vezes para o mesmo material!

---

## ⚠️ CENÁRIOS DE DUPLICAÇÃO

### Cenário 1: Requisição sem Pedido
```
RequisicaoCompras
- Produto A: 100 un
- Status: Aprovada
- SEM alocação ainda

❌ SE projetar por Requisição: +100
❌ SE projetar por Pedido: +0
✅ TOTAL CORRETO: +100 (ainda vai ser comprado)
```

### Cenário 2: Requisição COM Pedido (1:1)
```
RequisicaoCompras
- Produto A: 100 un

PedidoCompras
- Produto A: 100 un
- Fornecedor X

RequisicaoCompraAlocacao
- Requisição → Pedido
- Qtd alocada: 100

❌ SE projetar por Requisição: +100
❌ SE projetar por Pedido: +100
❌ SE projetar por Alocação: +100
❌ TOTAL ERRADO: +300 (TRIPLICADO!)

✅ TOTAL CORRETO: +100 (vai entrar só 1 vez)
```

### Cenário 3: Requisição atendida por MÚLTIPLOS Pedidos
```
RequisicaoCompras
- Produto A: 1000 un

PedidoCompras 1
- Produto A: 600 un
- Fornecedor X

PedidoCompras 2
- Produto A: 400 un
- Fornecedor Y

RequisicaoCompraAlocacao 1
- Requisição → Pedido1: 600 un

RequisicaoCompraAlocacao 2
- Requisição → Pedido2: 400 un

❌ SE projetar por Requisição: +1000
❌ SE projetar por Pedido1 + Pedido2: +600 +400 = +1000
✅ SE projetar por Alocação: +600 +400 = +1000

✅ TOTAL CORRETO: +1000
```

### Cenário 4: MÚLTIPLAS Requisições em 1 Pedido (Consolidação)
```
RequisicaoCompras 1
- Produto A: 50 un

RequisicaoCompras 2
- Produto A: 30 un

PedidoCompras (CONSOLIDADO)
- Produto A: 80 un
- Fornecedor Z

RequisicaoCompraAlocacao 1
- Requisição1 → Pedido: 50 un

RequisicaoCompraAlocacao 2
- Requisição2 → Pedido: 30 un

❌ SE projetar por Requisição1 + Requisição2: +50 +30 = +80
❌ SE projetar por Pedido: +80
✅ SE projetar por Alocação: +50 +30 = +80

✅ TOTAL CORRETO: +80
```

---

## ✅ SOLUÇÃO: ÚNICA FONTE DA VERDADE

### 🎯 REGRA DE OURO:

**SEMPRE projetar entradas por `PedidoCompras`**

```sql
-- ÚNICA QUERY para projetar entradas:
SELECT
    cod_produto,
    SUM(qtd_produto_pedido) as qtd_entrada_prevista,
    MIN(data_pedido_previsao) as data_entrada_prevista
FROM pedido_compras
WHERE importado_odoo = TRUE
  AND confirmacao_pedido = TRUE  -- Só pedidos confirmados
GROUP BY cod_produto
```

**POR QUÊ?**
1. ✅ Pedido = Compra EFETIVA com fornecedor
2. ✅ Pedido tem quantidade REAL que vai chegar
3. ✅ Pedido tem data REAL de previsão
4. ✅ Pedido NUNCA duplica (1 linha = 1 produto de 1 fornecedor)
5. ✅ RequisicaoCompraAlocacao já garante vínculo (não precisa consultar)

---

## 📋 COMPARAÇÃO: REQUISIÇÃO vs PEDIDO

| Aspecto | Requisição | Pedido |
|---------|------------|--------|
| **Representa** | Necessidade interna | Compra efetiva |
| **Pode mudar?** | ✅ Sim (cancelar, ajustar) | ❌ Raramente (já confirmado) |
| **Tem fornecedor?** | ❌ Não | ✅ Sim |
| **Tem preço?** | ❌ Não | ✅ Sim |
| **Tem data entrega?** | ⚠️ Estimada | ✅ Real do fornecedor |
| **Pode ser consolidada?** | ✅ Sim (N requisições → 1 pedido) | ❌ Não |
| **Pode ser dividida?** | ✅ Sim (1 requisição → N pedidos) | ❌ Não |
| **ÚNICA para projeção?** | ❌ NÃO | ✅ **SIM** |

---

## 🔧 IMPLEMENTAÇÃO

### Opção 1: Projeção Simples (Apenas Pedidos)

```python
from app.manufatura.models import PedidoCompras
from sqlalchemy import func
from datetime import date, timedelta

def projetar_entradas_estoque(cod_produto: str, dias_futuro: int = 30):
    """
    Projeta entradas de estoque baseado APENAS em pedidos confirmados

    Args:
        cod_produto: Código do produto
        dias_futuro: Quantos dias no futuro projetar

    Returns:
        Dict com projeção de entradas
    """
    data_limite = date.today() + timedelta(days=dias_futuro)

    # ÚNICA QUERY - Apenas pedidos
    entradas = db.session.query(
        PedidoCompras.data_pedido_previsao.label('data_entrada'),
        func.sum(PedidoCompras.qtd_produto_pedido).label('qtd_entrada')
    ).filter(
        PedidoCompras.cod_produto == cod_produto,
        PedidoCompras.importado_odoo == True,
        PedidoCompras.data_pedido_previsao.isnot(None),
        PedidoCompras.data_pedido_previsao <= data_limite
    ).group_by(
        PedidoCompras.data_pedido_previsao
    ).order_by(
        PedidoCompras.data_pedido_previsao
    ).all()

    return {
        'produto': cod_produto,
        'entradas': [
            {
                'data': entrada.data_entrada,
                'quantidade': float(entrada.qtd_entrada),
                'origem': 'pedido_compra'
            }
            for entrada in entradas
        ]
    }
```

---

### Opção 2: Projeção Detalhada (Com Rastreamento)

```python
def projetar_entradas_detalhadas(cod_produto: str, dias_futuro: int = 30):
    """
    Projeta entradas COM rastreamento de requisições via alocações

    Retorna pedidos + quais requisições eles atendem
    """
    from app.manufatura.models import (
        PedidoCompras,
        RequisicaoCompraAlocacao,
        RequisicaoCompras
    )

    data_limite = date.today() + timedelta(days=dias_futuro)

    # Query com LEFT JOIN para pegar alocações (se existirem)
    pedidos_com_alocacoes = db.session.query(
        PedidoCompras,
        RequisicaoCompraAlocacao,
        RequisicaoCompras
    ).outerjoin(
        RequisicaoCompraAlocacao,
        RequisicaoCompraAlocacao.pedido_compra_id == PedidoCompras.id
    ).outerjoin(
        RequisicaoCompras,
        RequisicaoCompras.id == RequisicaoCompraAlocacao.requisicao_compra_id
    ).filter(
        PedidoCompras.cod_produto == cod_produto,
        PedidoCompras.importado_odoo == True,
        PedidoCompras.data_pedido_previsao.isnot(None),
        PedidoCompras.data_pedido_previsao <= data_limite
    ).all()

    # Agrupar por pedido
    entradas = {}
    for pedido, alocacao, requisicao in pedidos_com_alocacoes:
        pedido_key = pedido.id

        if pedido_key not in entradas:
            entradas[pedido_key] = {
                'data_entrada': pedido.data_pedido_previsao,
                'quantidade': float(pedido.qtd_produto_pedido),
                'fornecedor': pedido.raz_social,
                'num_pedido': pedido.num_pedido,
                'preco_unitario': float(pedido.preco_produto_pedido) if pedido.preco_produto_pedido else 0,
                'requisicoes_atendidas': []
            }

        # Adicionar requisição se houver alocação
        if alocacao and requisicao:
            entradas[pedido_key]['requisicoes_atendidas'].append({
                'num_requisicao': requisicao.num_requisicao,
                'qtd_alocada': float(alocacao.qtd_alocada),
                'status': requisicao.status
            })

    return {
        'produto': cod_produto,
        'entradas': sorted(
            entradas.values(),
            key=lambda x: x['data_entrada']
        )
    }
```

---

## 🚨 REGRAS CRÍTICAS

### ✅ FAZER:

1. **Projetar APENAS por `PedidoCompras`**
   - É a única fonte confiável
   - Nunca duplica
   - Tem dados reais (fornecedor, preço, data)

2. **Usar `RequisicaoCompraAlocacao` APENAS para rastreamento**
   - Mostrar "Este pedido atende qual requisição?"
   - NÃO usar para projetar quantidades

3. **Filtrar pedidos confirmados**
   ```python
   PedidoCompras.query.filter_by(
       importado_odoo=True,
       confirmacao_pedido=True  # Importante!
   )
   ```

4. **Agrupar por data de previsão**
   ```python
   GROUP BY data_pedido_previsao
   ```

---

### ❌ NUNCA FAZER:

1. **❌ Somar Requisição + Pedido**
   - Vai duplicar tudo!

2. **❌ Projetar por Alocação**
   - Alocação é apenas mapeamento N:N
   - Não adiciona quantidade nova

3. **❌ Contar Requisição sem Pedido como entrada garantida**
   - Requisição = intenção
   - Pedido = compra efetiva

4. **❌ Usar `qtd_alocada` da alocação para projeção**
   - Use `qtd_produto_pedido` do pedido

---

## 📊 QUERY FINAL RECOMENDADA

```sql
-- Projeção de entradas dos próximos 30 dias
SELECT
    p.cod_produto,
    p.data_pedido_previsao as data_entrada,
    SUM(p.qtd_produto_pedido) as qtd_total_entrada,
    COUNT(DISTINCT p.num_pedido) as num_pedidos,
    STRING_AGG(DISTINCT p.raz_social, ', ') as fornecedores,

    -- Opcional: Rastrear requisições
    COUNT(DISTINCT a.requisicao_compra_id) as num_requisicoes_atendidas

FROM pedido_compras p
LEFT JOIN requisicao_compra_alocacao a
    ON a.pedido_compra_id = p.id

WHERE p.importado_odoo = TRUE
  AND p.confirmacao_pedido = TRUE
  AND p.data_pedido_previsao IS NOT NULL
  AND p.data_pedido_previsao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
  AND p.cod_produto = :cod_produto

GROUP BY p.cod_produto, p.data_pedido_previsao
ORDER BY p.data_pedido_previsao;
```

---

## 🎯 EXEMPLO PRÁTICO

### Produto: "210639522"

**DADOS:**
```
RequisicaoCompras 1: 500 un (sem pedido ainda)
RequisicaoCompras 2: 1000 un

PedidoCompras 1: 600 un (Fornecedor X) - Data: 10/11
PedidoCompras 2: 400 un (Fornecedor Y) - Data: 15/11

Alocação 1: Req2 → Ped1 (600 un)
Alocação 2: Req2 → Ped2 (400 un)
```

**PROJEÇÃO CORRETA:**
```python
{
    "produto": "210639522",
    "entradas": [
        {
            "data_entrada": "2025-11-10",
            "quantidade": 600,
            "fornecedor": "Fornecedor X",
            "num_pedido": "PO/FB/001",
            "requisicoes_atendidas": [
                {"num_requisicao": "REQ/FB/002", "qtd": 600}
            ]
        },
        {
            "data_entrada": "2025-11-15",
            "quantidade": 400,
            "fornecedor": "Fornecedor Y",
            "num_pedido": "PO/FB/002",
            "requisicoes_atendidas": [
                {"num_requisicao": "REQ/FB/002", "qtd": 400}
            ]
        }
    ],
    "total_entradas": 1000
}
```

**OBSERVAÇÕES:**
- ✅ Requisição 1 (500 un) NÃO aparece (sem pedido ainda)
- ✅ Requisição 2 (1000 un) está TOTALMENTE atendida por 2 pedidos
- ✅ Total de entradas = 1000 (correto!)
- ✅ SEM DUPLICAÇÃO

---

## ✅ CHECKLIST DE VALIDAÇÃO

Antes de projetar entradas, verificar:

- [ ] Está usando APENAS `PedidoCompras` como fonte?
- [ ] Filtrou por `importado_odoo = True`?
- [ ] Filtrou por `confirmacao_pedido = True`?
- [ ] Agrupou por `data_pedido_previsao`?
- [ ] NÃO está somando com requisições?
- [ ] NÃO está usando `qtd_alocada` para projeção?
- [ ] LEFT JOIN em alocações (não INNER JOIN)?

---

## 📝 CONCLUSÃO

### ✅ ÚNICA FONTE DA VERDADE PARA ENTRADAS:

**`PedidoCompras`** = Compra efetiva que VAI ENTRAR

### ✅ USO DAS OUTRAS TABELAS:

- **`RequisicaoCompras`** = Rastrear ORIGEM da necessidade
- **`RequisicaoCompraAlocacao`** = Rastrear VÍNCULO (qual pedido atende qual requisição)

### ❌ NUNCA:

- Projetar somando Requisição + Pedido
- Usar Alocação para calcular quantidade
- Contar mesmo produto 2x ou 3x

---

**Status**: ✅ ESTRATÉGIA DEFINIDA
**Próximo passo**: Implementar tela de Pedidos de Compra com projeção correta
