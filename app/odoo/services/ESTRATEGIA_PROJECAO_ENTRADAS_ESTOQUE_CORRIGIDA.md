# 📊 Estratégia CORRETA de Projeção de ENTRADAS de Estoque

**Data**: 01/11/2025
**Objetivo**: Projetar entradas SEM DUPLICAÇÃO considerando Pedidos + Saldo de Requisições

---

## 🎯 REGRA DE OURO

### ✅ PROJEÇÃO CORRETA = PEDIDOS + SALDO NÃO ATENDIDO

```
Entradas Projetadas =
    1. Pedidos de Compra confirmados (qtd garantida)
    +
    2. Saldo não atendido das Requisições (qtd prevista)
```

---

## 📐 FÓRMULA DO SALDO

Para cada Requisição:

```
Saldo NÃO Atendido = qtd_requisitada - SUM(qtd_alocada)

Onde:
  qtd_requisitada = RequisicaoCompras.qtd_produto_requisicao
  qtd_alocada = SUM de RequisicaoCompraAlocacao.qtd_alocada
                para aquela requisição
```

---

## 📊 EXEMPLO PRÁTICO

### Cenário:

```
RequisicaoCompras REQ/FB/001
- Produto: 210639522
- Qtd requisitada: 1000 un
- Data necessidade: 2025-11-20
- Status: Aprovada

PedidoCompras PO/FB/001
- Produto: 210639522
- Qtd pedido: 300 un
- Data previsão: 2025-11-10
- Fornecedor: Fornecedor X

PedidoCompras PO/FB/002
- Produto: 210639522
- Qtd pedido: 200 un
- Data previsão: 2025-11-15
- Fornecedor: Fornecedor Y

RequisicaoCompraAlocacao 1
- Requisição: REQ/FB/001
- Pedido: PO/FB/001
- Qtd alocada: 300 un

RequisicaoCompraAlocacao 2
- Requisição: REQ/FB/001
- Pedido: PO/FB/002
- Qtd alocada: 200 un
```

### Cálculo do Saldo:

```python
qtd_requisitada = 1000
qtd_alocada_total = 300 + 200 = 500

Saldo NÃO Atendido = 1000 - 500 = 500 un
```

### ✅ PROJEÇÃO CORRETA:

| Data | Origem | Quantidade | Observação |
|------|--------|------------|------------|
| 2025-11-10 | Pedido PO/FB/001 | 300 un | Confirmado (Fornecedor X) |
| 2025-11-15 | Pedido PO/FB/002 | 200 un | Confirmado (Fornecedor Y) |
| 2025-11-20 | Saldo REQ/FB/001 | 500 un | Previsto (ainda será comprado) |
| **TOTAL** | | **1000 un** | ✅ **SEM DUPLICAÇÃO** |

---

## 🔧 IMPLEMENTAÇÃO EM SQL

### Query Completa:

```sql
WITH pedidos_confirmados AS (
    -- PARTE 1: Pedidos confirmados (entradas garantidas)
    SELECT
        p.cod_produto,
        p.data_pedido_previsao as data_entrada,
        p.qtd_produto_pedido as qtd_entrada,
        'PEDIDO' as tipo_entrada,
        p.num_pedido as origem,
        p.raz_social as fornecedor,
        p.preco_produto_pedido as preco_unitario,
        NULL as num_requisicao
    FROM pedido_compras p
    WHERE p.importado_odoo = TRUE
      AND p.data_pedido_previsao IS NOT NULL
      AND p.cod_produto = :cod_produto
),

saldos_requisicoes AS (
    -- PARTE 2: Saldos não atendidos (entradas previstas)
    SELECT
        r.cod_produto,
        r.data_necessidade as data_entrada,
        (r.qtd_produto_requisicao - COALESCE(SUM(a.qtd_alocada), 0)) as qtd_entrada,
        'SALDO_REQUISICAO' as tipo_entrada,
        r.num_requisicao as origem,
        NULL as fornecedor,
        NULL as preco_unitario,
        r.num_requisicao as num_requisicao
    FROM requisicao_compras r
    LEFT JOIN requisicao_compra_alocacao a
        ON a.requisicao_compra_id = r.id
    WHERE r.importado_odoo = TRUE
      AND r.data_necessidade IS NOT NULL
      AND r.cod_produto = :cod_produto
      AND r.status IN ('Aprovada', 'Aguardando Aprovação')  -- Apenas requisições ativas
    GROUP BY r.id, r.cod_produto, r.data_necessidade, r.num_requisicao, r.qtd_produto_requisicao
    HAVING (r.qtd_produto_requisicao - COALESCE(SUM(a.qtd_alocada), 0)) > 0  -- Apenas se houver saldo
)

-- UNIÃO das duas fontes
SELECT * FROM pedidos_confirmados
UNION ALL
SELECT * FROM saldos_requisicoes
ORDER BY data_entrada;
```

---

## 🐍 IMPLEMENTAÇÃO EM PYTHON

```python
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompras,
    RequisicaoCompraAlocacao
)
from sqlalchemy import func, case
from datetime import date, timedelta
from decimal import Decimal

def projetar_entradas_completas(cod_produto: str, dias_futuro: int = 30):
    """
    Projeta entradas de estoque SEM DUPLICAÇÃO

    Combina:
    1. Pedidos confirmados (entradas garantidas)
    2. Saldos não atendidos de requisições (entradas previstas)

    Args:
        cod_produto: Código do produto
        dias_futuro: Dias no futuro para projetar

    Returns:
        Lista de entradas projetadas ordenadas por data
    """
    data_limite = date.today() + timedelta(days=dias_futuro)
    entradas = []

    # ==========================================
    # PARTE 1: PEDIDOS CONFIRMADOS
    # ==========================================

    pedidos = PedidoCompras.query.filter(
        PedidoCompras.cod_produto == cod_produto,
        PedidoCompras.importado_odoo == True,
        PedidoCompras.data_pedido_previsao.isnot(None),
        PedidoCompras.data_pedido_previsao <= data_limite
    ).all()

    for pedido in pedidos:
        entradas.append({
            'data_entrada': pedido.data_pedido_previsao,
            'quantidade': float(pedido.qtd_produto_pedido),
            'tipo': 'PEDIDO',
            'origem': pedido.num_pedido,
            'fornecedor': pedido.raz_social,
            'preco_unitario': float(pedido.preco_produto_pedido) if pedido.preco_produto_pedido else None,
            'num_requisicao': None,
            'cor': 'success',  # Verde (confirmado)
            'icone': '✅'
        })

    # ==========================================
    # PARTE 2: SALDOS NÃO ATENDIDOS
    # ==========================================

    # Buscar requisições ativas
    requisicoes = RequisicaoCompras.query.filter(
        RequisicaoCompras.cod_produto == cod_produto,
        RequisicaoCompras.importado_odoo == True,
        RequisicaoCompras.data_necessidade.isnot(None),
        RequisicaoCompras.data_necessidade <= data_limite,
        RequisicaoCompras.status.in_(['Aprovada', 'Aguardando Aprovação'])
    ).all()

    for requisicao in requisicoes:
        # Calcular saldo não atendido
        qtd_alocada_total = db.session.query(
            func.sum(RequisicaoCompraAlocacao.qtd_alocada)
        ).filter(
            RequisicaoCompraAlocacao.requisicao_compra_id == requisicao.id
        ).scalar() or Decimal('0')

        saldo = requisicao.qtd_produto_requisicao - qtd_alocada_total

        # Só adicionar se houver saldo > 0
        if saldo > 0:
            entradas.append({
                'data_entrada': requisicao.data_necessidade,
                'quantidade': float(saldo),
                'tipo': 'SALDO_REQUISICAO',
                'origem': requisicao.num_requisicao,
                'fornecedor': None,
                'preco_unitario': None,
                'num_requisicao': requisicao.num_requisicao,
                'cor': 'warning',  # Amarelo (previsto)
                'icone': '⏳',
                'observacao': f'Saldo não atendido de {requisicao.num_requisicao}'
            })

    # Ordenar por data
    entradas_ordenadas = sorted(entradas, key=lambda x: x['data_entrada'])

    # Calcular total
    total = sum(e['quantidade'] for e in entradas_ordenadas)

    return {
        'cod_produto': cod_produto,
        'total_entradas': total,
        'qtd_entradas': len(entradas_ordenadas),
        'entradas': entradas_ordenadas
    }
```

---

## 📊 EXEMPLO DE SAÍDA

```json
{
  "cod_produto": "210639522",
  "total_entradas": 1000,
  "qtd_entradas": 3,
  "entradas": [
    {
      "data_entrada": "2025-11-10",
      "quantidade": 300,
      "tipo": "PEDIDO",
      "origem": "PO/FB/001",
      "fornecedor": "Fornecedor X",
      "preco_unitario": 10.50,
      "num_requisicao": null,
      "cor": "success",
      "icone": "✅"
    },
    {
      "data_entrada": "2025-11-15",
      "quantidade": 200,
      "tipo": "PEDIDO",
      "origem": "PO/FB/002",
      "fornecedor": "Fornecedor Y",
      "preco_unitario": 10.80,
      "num_requisicao": null,
      "cor": "success",
      "icone": "✅"
    },
    {
      "data_entrada": "2025-11-20",
      "quantidade": 500,
      "tipo": "SALDO_REQUISICAO",
      "origem": "REQ/FB/001",
      "fornecedor": null,
      "preco_unitario": null,
      "num_requisicao": "REQ/FB/001",
      "cor": "warning",
      "icone": "⏳",
      "observacao": "Saldo não atendido de REQ/FB/001"
    }
  ]
}
```

---

## ✅ VALIDAÇÃO - SEM DUPLICAÇÃO

### Checklist:

- [x] Pedidos contam quantidade do `PedidoCompras.qtd_produto_pedido`
- [x] Saldo calcula `qtd_requisitada - SUM(qtd_alocada)`
- [x] Pedido e Saldo são fontes INDEPENDENTES
- [x] Não há soma dupla de quantidade
- [x] TOTAL = Pedidos + Saldos (correto!)

### Teste de Duplicação:

```python
def testar_duplicacao(cod_produto):
    """Testa se há duplicação na projeção"""

    resultado = projetar_entradas_completas(cod_produto)

    # Somar TODAS as entradas
    total_projetado = sum(e['quantidade'] for e in resultado['entradas'])

    # Somar TODAS as requisições ativas
    total_requisitado = db.session.query(
        func.sum(RequisicaoCompras.qtd_produto_requisicao)
    ).filter(
        RequisicaoCompras.cod_produto == cod_produto,
        RequisicaoCompras.status.in_(['Aprovada', 'Aguardando Aprovação'])
    ).scalar() or 0

    print(f"Total Projetado: {total_projetado}")
    print(f"Total Requisitado: {total_requisitado}")

    # DEVEM SER IGUAIS!
    if abs(total_projetado - total_requisitado) < 0.01:
        print("✅ SEM DUPLICAÇÃO - Valores coincidem!")
    else:
        print(f"❌ DUPLICAÇÃO DETECTADA - Diferença: {abs(total_projetado - total_requisitado)}")
```

---

## 🎨 VISUALIZAÇÃO NA TELA

### Exemplo de como exibir:

```html
<table class="table">
  <thead>
    <tr>
      <th>Data</th>
      <th>Tipo</th>
      <th>Origem</th>
      <th>Quantidade</th>
      <th>Fornecedor</th>
      <th>Preço</th>
    </tr>
  </thead>
  <tbody>
    <tr class="table-success">
      <td>10/11/2025</td>
      <td><span class="badge bg-success">✅ Pedido Confirmado</span></td>
      <td>PO/FB/001</td>
      <td>300 un</td>
      <td>Fornecedor X</td>
      <td>R$ 10,50</td>
    </tr>
    <tr class="table-success">
      <td>15/11/2025</td>
      <td><span class="badge bg-success">✅ Pedido Confirmado</span></td>
      <td>PO/FB/002</td>
      <td>200 un</td>
      <td>Fornecedor Y</td>
      <td>R$ 10,80</td>
    </tr>
    <tr class="table-warning">
      <td>20/11/2025</td>
      <td><span class="badge bg-warning">⏳ Saldo Previsto</span></td>
      <td>REQ/FB/001</td>
      <td>500 un</td>
      <td>-</td>
      <td>-</td>
    </tr>
  </tbody>
  <tfoot>
    <tr class="table-info">
      <th colspan="3">TOTAL</th>
      <th>1000 un</th>
      <th colspan="2"></th>
    </tr>
  </tfoot>
</table>
```

---

## 📝 CONCLUSÃO

### ✅ ESTRATÉGIA CORRETA:

**Entradas = Pedidos + Saldos**

1. **Pedidos** = Quantidade que VAI CHEGAR (confirmado)
2. **Saldos** = Quantidade que AINDA VAI SER COMPRADA (previsto)

### ✅ SEM DUPLICAÇÃO porque:

- Pedido conta qtd do pedido (não da requisição)
- Saldo conta APENAS o que NÃO foi alocado
- Alocação serve APENAS para calcular saldo
- Não há soma dupla

### ✅ TOTAL CORRETO:

```
Total Projetado = Total Requisitado (quando tudo estiver atendido)
```

---

**Status**: ✅ ESTRATÉGIA CORRIGIDA E VALIDADA
**Próximo passo**: Implementar tela de Pedidos com projeção correta
