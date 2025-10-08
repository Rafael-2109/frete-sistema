# 📋 FLUXO DE PARCELAMENTO COM FIFO - SISTEMA MOTOCHEFE

**Data:** 07/10/2025
**Implementado em:** `app/motochefe/services/titulo_service.py`
**Status:** ✅ IMPLEMENTADO

---

## 🎯 VISÃO GERAL

Sistema de parcelamento que:
1. ✅ Aplica **FIFO** na criação de títulos entre parcelas
2. ✅ Permite **splitting automático** de títulos no pagamento parcial
3. ✅ Faz **renumeração automática** de parcelas quando necessário
4. ✅ Mantém **prazo_dias e data_vencimento** inalterados na renumeração

---

## 📊 EXEMPLO COMPLETO

### **ENTRADA (Criação do Pedido)**

```python
dados_pedido = {
    'numero_pedido': 'PED-001',
    'valor_total_pedido': 15600,
    'numero_parcelas': 2,
    'parcelas': [
        {'numero': 1, 'valor': 7800, 'prazo_dias': 28},
        {'numero': 2, 'valor': 7800, 'prazo_dias': 35}
    ],
    'data_expedicao': date(2025, 10, 15)
}

itens_json = [
    {'modelo_id': 1, 'cor': 'Preta', 'quantidade': 3, 'preco_venda': 5000, 'montagem': True, 'valor_montagem': 100}
]
```

### **SAÍDA (Títulos Criados com FIFO)**

#### **Parcela 1 (R$ 7.800, prazo 28 dias, vencimento: 15/11/2025)**
```
P1 - Movimentacao Moto 1: R$ 100
P1 - Montagem Moto 1:      R$ 50
P1 - Frete Moto 1:         R$ 50
P1 - Venda Moto 1:         R$ 5.000
P1 - Movimentacao Moto 2:  R$ 100
P1 - Montagem Moto 2:      R$ 50
P1 - Frete Moto 2:         R$ 50
P1 - Venda Moto 2:         R$ 2.400  ← SPLIT (R$ 5.000 / R$ 7.800 = R$ 2.400)

TOTAL: R$ 7.800
```

#### **Parcela 2 (R$ 7.800, prazo 35 dias, vencimento: 19/11/2025)**
```
P2 - Venda Moto 2 (cont):  R$ 2.600  ← SPLIT (R$ 5.000 - R$ 2.400)
P2 - Movimentacao Moto 3:  R$ 100
P2 - Montagem Moto 3:      R$ 50
P2 - Frete Moto 3:         R$ 50
P2 - Venda Moto 3:         R$ 5.000

TOTAL: R$ 7.800
```

---

## 💰 FLUXO DE PAGAMENTO PARCIAL

### **Cliente paga R$ 5.000**

#### **ANTES (Parcela 1 - 8 títulos)**
```
P1 - Movimentacao 1: R$ 100    (ABERTO)
P1 - Montagem 1:     R$ 50     (ABERTO)
P1 - Frete 1:        R$ 50     (ABERTO)
P1 - Venda 1:        R$ 5.000  (ABERTO)
P1 - Movimentacao 2: R$ 100    (ABERTO)
P1 - Montagem 2:     R$ 50     (ABERTO)
P1 - Frete 2:        R$ 50     (ABERTO)
P1 - Venda 2:        R$ 2.400  (ABERTO)

TOTAL: R$ 7.800
```

#### **PROCESSAMENTO FIFO**
```python
processar_pagamento_fifo(pedido, 5000, empresa, usuario)

# 1. Paga R$ 100 → Título 1 (Movimentacao 1) = PAGO
# 2. Paga R$ 50  → Título 2 (Montagem 1) = PAGO
# 3. Paga R$ 50  → Título 3 (Frete 1) = PAGO
# 4. Paga R$ 4.800 de R$ 5.000 → Título 4 (Venda 1) = SPLIT
#    - Cria título PAGO: R$ 4.800 (parcela 1)
#    - Cria título RESTANTE: R$ 200 (parcela 1, ABERTO)
#    - Inativa título original (status CANCELADO)
#    - RENUMERA parcelas >= 1 (exceto título restante)
```

#### **DEPOIS (3 parcelas)**

**Parcela 1 (pagos, prazo 28 dias):**
```
P1 - Movimentacao 1: R$ 100    (PAGO)
P1 - Montagem 1:     R$ 50     (PAGO)
P1 - Frete 1:        R$ 50     (PAGO)
P1 - Venda 1 (pago): R$ 4.800  (PAGO)

TOTAL PAGO: R$ 5.000
```

**Parcela 1 (restante, prazo 28 dias, MANTÉM vencimento):**
```
P1 - Venda 1 (saldo): R$ 200   (ABERTO, prazo 28, venc: 15/11)
```

**Parcela 2 (renumerados +1, prazo 28 dias, MANTÉM vencimento):**
```
P2 - Movimentacao 2: R$ 100    (ABERTO, prazo 28, venc: 15/11)
P2 - Montagem 2:     R$ 50     (ABERTO, prazo 28, venc: 15/11)
P2 - Frete 2:        R$ 50     (ABERTO, prazo 28, venc: 15/11)
P2 - Venda 2:        R$ 2.400  (ABERTO, prazo 28, venc: 15/11)

TOTAL: R$ 2.600
```

**Parcela 3 (eram P2, prazo 35 dias, MANTÉM vencimento):**
```
P3 - Venda 2 (cont): R$ 2.600  (ABERTO, prazo 35, venc: 19/11)
P3 - Movimentacao 3: R$ 100    (ABERTO, prazo 35, venc: 19/11)
P3 - Montagem 3:     R$ 50     (ABERTO, prazo 35, venc: 19/11)
P3 - Frete 3:        R$ 50     (ABERTO, prazo 35, venc: 19/11)
P3 - Venda 3:        R$ 5.000  (ABERTO, prazo 35, venc: 19/11)

TOTAL: R$ 7.800
```

---

## 🔧 FUNÇÕES IMPLEMENTADAS

### 1. **gerar_titulos_com_fifo_parcelas()**
[titulo_service.py:12](app/motochefe/services/titulo_service.py#L12)

```python
def gerar_titulos_com_fifo_parcelas(pedido, itens_pedido, parcelas_config):
    """
    Gera títulos aplicando FIFO entre parcelas

    Args:
        pedido: PedidoVendaMoto
        itens_pedido: list de PedidoVendaMotoItem
        parcelas_config: [
            {'numero': 1, 'valor': 7800, 'prazo_dias': 28},
            {'numero': 2, 'valor': 7800, 'prazo_dias': 35}
        ]

    Algoritmo:
    1. Gera lista de títulos (MOVIMENTACAO, MONTAGEM, FRETE, VENDA) por moto
    2. Consome títulos sequencialmente distribuindo entre parcelas
    3. Se título excede parcela: SPLIT em 2 títulos (parte1 + parte2)
    4. Cada título recebe prazo_dias da parcela correspondente
    """
```

### 2. **processar_pagamento_fifo()**
[titulo_service.py:213](app/motochefe/services/titulo_service.py#L213)

```python
def processar_pagamento_fifo(pedido, valor_pago, empresa_recebedora, usuario=None):
    """
    Processa pagamento aplicando FIFO nos títulos

    Fluxo:
    1. Busca títulos ABERTOS ordenados (parcela, chassi, ordem)
    2. Consome títulos até esgotar valor_pago
    3. Se valor insuficiente para último título:
       - Cria título PAGO com valor recebido (mantém parcela original)
       - Cria título RESTANTE com saldo (mantém parcela original)
       - Inativa título original (status CANCELADO)
       - RENUMERA títulos não pagos +1 (exceto restante)
    4. Registra movimentações
    5. Triggers automáticos (liberar título a pagar, baixa auto, comissão)
    """
```

### 3. **renumerar_parcelas_nao_pagas()**
[titulo_service.py:368](app/motochefe/services/titulo_service.py#L368)

```python
def renumerar_parcelas_nao_pagas(pedido_id, a_partir_de_parcela, exceto_ids=None):
    """
    Renumera títulos ABERTOS somando +1
    MANTÉM prazo_dias e data_vencimento inalterados

    Args:
        pedido_id: int
        a_partir_de_parcela: int (renumera >= esta parcela)
        exceto_ids: list de IDs para não renumerar (ex: título restante do split)

    Resultado:
    - numero_parcela += 1
    - prazo_dias: SEM ALTERAÇÃO
    - data_vencimento: SEM ALTERAÇÃO
    """
```

---

## 📋 ESTRUTURA DE DADOS

### **TituloFinanceiro (Campos Chave)**
```python
numero_parcela = db.Column(db.Integer, nullable=False, index=True)
prazo_dias = db.Column(db.Integer, nullable=True)
data_vencimento = db.Column(db.Date, nullable=True)

# Splitting
titulo_pai_id = db.Column(db.Integer, db.ForeignKey('titulo_financeiro.id'))
eh_titulo_dividido = db.Column(db.Boolean, default=False)
historico_divisao = db.Column(db.Text, nullable=True)  # JSON
```

### **PedidoVendaMoto (Campos Chave)**
```python
prazo_dias = db.Column(db.Integer, default=0, nullable=False)
numero_parcelas = db.Column(db.Integer, default=1, nullable=False)
```

---

## ✅ REGRAS DE NEGÓCIO

1. **Criação de Títulos:**
   - FIFO: Títulos distribuídos sequencialmente entre parcelas
   - Splitting automático quando título excede valor da parcela
   - Cada título recebe `prazo_dias` da parcela correspondente

2. **Pagamento:**
   - FIFO: Consome títulos na ordem (parcela, chassi, ordem_pagamento)
   - Splitting quando valor insuficiente
   - Título splitado MANTÉM `numero_parcela` original
   - Renumeração +1 em TODOS não pagos (exceto restante do split)

3. **Renumeração:**
   - SOMA +1 em `numero_parcela`
   - MANTÉM `prazo_dias` e `data_vencimento`
   - Não altera títulos pagos ou cancelados
   - Exclui título restante do split

4. **Vencimento:**
   ```python
   data_vencimento = data_expedicao + timedelta(days=prazo_dias)
   ```
   - Calculado no faturamento
   - Baseado em `prazo_dias` do título (não do pedido)
   - Nunca recalculado na renumeração

---

## 🚀 USO NO CÓDIGO

### **Criar Pedido com Parcelas**
```python
from app.motochefe.services.pedido_service import criar_pedido_completo

resultado = criar_pedido_completo(
    dados_pedido={
        'numero_pedido': 'PED-001',
        'cliente_id': 1,
        'vendedor_id': 1,
        'data_expedicao': date(2025, 10, 15),
        'valor_total_pedido': 15600,
        'numero_parcelas': 2,
        'parcelas': [
            {'numero': 1, 'valor': 7800, 'prazo_dias': 28},
            {'numero': 2, 'valor': 7800, 'prazo_dias': 35}
        ]
    },
    itens_json=[
        {'modelo_id': 1, 'cor': 'Preta', 'quantidade': 3, 'preco_venda': 5000}
    ]
)

# resultado['titulos_financeiros'] contém títulos com FIFO aplicado
```

### **Processar Pagamento**
```python
from app.motochefe.services.titulo_service import processar_pagamento_fifo

resultado = processar_pagamento_fifo(
    pedido=pedido,
    valor_pago=Decimal('5000'),
    empresa_recebedora=empresa,
    usuario='João'
)

# resultado['titulos_pagos'] = títulos pagos
# resultado['titulo_splitado'] = título original (se houve split)
# resultado['titulo_restante'] = novo título com saldo (se houve split)
# resultado['renumeracao_executada'] = True/False
```

---

## ⚠️ IMPORTANTE

### **MovimentacaoFinanceira Preservada**
- Todas as movimentações continuam usando `titulo_financeiro_id`
- Títulos splitados criam novos IDs (titulo_pago e titulo_restante)
- Título original vira CANCELADO (não aparece em consultas)
- Rastreabilidade via `titulo_pai_id` e `historico_divisao`

### **Tabelas Removidas**
- ❌ ParcelaPedido (removida)
- ❌ ParcelaTitulo (removida)
- ✅ TituloFinanceiro.numero_parcela é a única fonte de verdade

---

## 📝 CHANGELOG

**07/10/2025:**
- ✅ Implementado FIFO na criação de títulos
- ✅ Implementado splitting no pagamento
- ✅ Implementado renumeração automática
- ✅ Removido ParcelaPedido e ParcelaTitulo
- ✅ Integrado em pedido_service.py
- ✅ Documentação completa criada
