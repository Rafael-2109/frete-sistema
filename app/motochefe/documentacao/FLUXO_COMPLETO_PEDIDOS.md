# 📋 FLUXO COMPLETO: Emissão de Pedidos - Sistema MotoChefe

**Data**: 14/10/2025
**Objetivo**: Documentar TODO o fluxo desde a criação do pedido até pagamentos

---

## 🎯 PRÓXIMAS FASES DA CARGA INICIAL

Após **Fase 3** (Produtos e Clientes), temos:

### **FASE 4: Pedidos e Vendas**
```
Tabelas:
├── pedido_venda_moto (cabeçalho do pedido)
├── pedido_venda_moto_item (itens - motos vendidas)
└── pedido_venda_auditoria (histórico de alterações)
```

### **FASE 5: Financeiro**
```
Tabelas:
├── titulo_financeiro (a receber - do cliente)
├── comissao_vendedor (comissões calculadas)
└── titulo_a_pagar (a pagar - transportadora/montador)
```

### **FASE 6: Logística**
```
Tabelas:
├── embarque_moto (embarques agrupados)
├── embarque_pedido (pedidos no embarque)
└── movimentacao_financeira (fluxo de caixa)
```

---

## 🔄 FLUXO COMPLETO: CRIAÇÃO DE PEDIDO

### **1️⃣ CRIAR PEDIDO** (`pedido_service.criar_pedido_completo()`)

#### **Input:**
```python
dados_pedido = {
    'numero_pedido': 'PED-2025-001',
    'cliente_id': 5,
    'vendedor_id': 3,
    'equipe_vendas_id': 1,
    'data_pedido': date(2025, 10, 15),
    'data_expedicao': date(2025, 10, 20),
    'valor_total_pedido': Decimal('15600.00'),
    'forma_pagamento': 'BOLETO',
    'condicao_pagamento': '2x',
    'numero_parcelas': 2,
    'parcelas': [
        {'numero': 1, 'valor': 7800, 'prazo_dias': 28},
        {'numero': 2, 'valor': 7800, 'prazo_dias': 35}
    ],
    'transportadora_id': 2,
    'tipo_frete': 'CIF',
    'observacoes': 'Entregar em horário comercial'
}

itens_json = [
    {
        'modelo_id': 3,  # S8-12
        'cor': 'PRETA',
        'quantidade': 2,
        'preco_venda': Decimal('7800.00'),
        'montagem': True,
        'valor_montagem': Decimal('150.00'),
        'fornecedor_montagem': 'NACOM'
    }
]
```

#### **O que acontece:**

##### ✅ **1.1. Criar Registro de Pedido**
```python
# Tabela: pedido_venda_moto
PedidoVendaMoto(
    numero_pedido='PED-2025-001',
    cliente_id=5,
    vendedor_id=3,
    ativo=False,              # 🔴 PENDENTE até aprovação
    status='PENDENTE',        # Aguardando aprovação
    faturado=False
)
```

##### ✅ **1.2. Alocar Motos (FIFO)**
```python
# Busca motos DISPONÍVEIS, ordenadas por data_entrada
motos = Moto.query.filter_by(
    modelo_id=3,
    cor='PRETA',
    status='DISPONIVEL',
    reservado=False
).order_by(Moto.data_entrada.asc()).limit(2).all()

# Para cada moto:
for moto in motos:
    # Criar item do pedido
    PedidoVendaMotoItem(
        pedido_id=pedido.id,
        numero_chassi=moto.numero_chassi,
        preco_venda=Decimal('7800.00'),
        montagem_contratada=True,
        valor_montagem=Decimal('150.00')
    )

    # Reservar moto
    moto.status = 'RESERVADA'  # 🔴 ALTERA STATUS DA MOTO!
    moto.reservado = True
```

**⚠️ IMPORTANTE**: Status da moto muda de `DISPONIVEL` → `RESERVADA`

##### ✅ **1.3. Gerar Títulos Financeiros (A RECEBER)**
```python
# Service: titulo_service.gerar_titulos_com_fifo_parcelas()

# Para cada moto, cria títulos conforme parcelas
# Exemplo com 2 motos e 2 parcelas = 4 títulos mínimo:

# Moto 1 - Parcela 1
TituloFinanceiro(
    pedido_id=pedido.id,
    numero_chassi='ABC123',
    tipo_titulo='VENDA_MOTO',
    valor=Decimal('3900.00'),  # 7800 / 2 parcelas
    numero_parcela=1,
    total_parcelas=2,
    prazo_dias=28,
    data_vencimento=data_expedicao + timedelta(days=28)
)

# Moto 1 - Montagem - Parcela 1
TituloFinanceiro(
    tipo_titulo='MONTAGEM',
    valor=Decimal('75.00'),  # 150 / 2 parcelas
    numero_parcela=1,
    prazo_dias=28
)

# Moto 1 - Movimentação - Parcela 1
TituloFinanceiro(
    tipo_titulo='MOVIMENTACAO',
    valor=Decimal('?'),  # Valor que CLIENTE paga
    numero_parcela=1,
    prazo_dias=28
)

# ... Repete para Moto 2 e Parcela 2
```

**⚠️ IMPORTANTE**: `data_vencimento` calculada AQUI, não no faturamento!

##### ✅ **1.4. Gerar Títulos a Pagar (PENDENTES)**
```python
# Service: titulo_a_pagar_service.criar_titulo_a_pagar_*()

# Para cada título de MOVIMENTACAO:
TituloAPagar(
    titulo_financeiro_id=titulo.id,
    tipo='MOVIMENTACAO',
    favorecido='NACOM',  # equipe.responsavel_movimentacao
    valor=equipe.custo_movimentacao,  # 🔴 CUSTO REAL, não o que cliente paga
    status='PENDENTE',
    data_vencimento=None  # Será preenchido quando pagar
)

# Para cada título de MONTAGEM:
TituloAPagar(
    tipo='MONTAGEM',
    favorecido='NACOM',  # fornecedor_montagem
    valor=Decimal('150.00'),  # valor_montagem do item
    status='PENDENTE'
)
```

**⚠️ IMPORTANTE**: Títulos criados como `PENDENTE`, sem data_vencimento

##### ✅ **1.5. Resultado**
```python
{
    'pedido': PedidoVendaMoto,
    'itens': [PedidoVendaMotoItem, PedidoVendaMotoItem],
    'titulos_financeiros': [TituloFinanceiro x6],  # 2 motos x 3 tipos x 2 parcelas
    'titulos_a_pagar': [TituloAPagar x4]  # 2 motos x (movimentação + montagem) x 2 parcelas
}
```

---

### **2️⃣ APROVAR PEDIDO**

```python
# Ação manual ou automática
pedido.ativo = True
pedido.status = 'APROVADO'
```

**O que libera:**
- ✅ Pedido aparece nas listagens
- ✅ Pode ser faturado
- ✅ Pode entrar em embarque

---

### **3️⃣ FATURAR PEDIDO** (`pedido_service.faturar_pedido_completo()`)

#### **Input:**
```python
faturar_pedido_completo(
    pedido=pedido,
    empresa_id=1,  # Empresa que emite NF
    numero_nf='NF-12345',
    data_nf=date(2025, 10, 20),
    numero_nf_importada='NF-IMP-6789'  # Opcional
)
```

#### **O que acontece:**

##### ✅ **3.1. Validações**
```python
if pedido.faturado:
    raise Exception('Pedido já foi faturado')

if pedido.status != 'APROVADO':
    raise Exception('Apenas pedidos aprovados podem ser faturados')
```

##### ✅ **3.2. Atualizar Pedido**
```python
pedido.faturado = True
pedido.numero_nf = 'NF-12345'
pedido.numero_nf_importada = 'NF-IMP-6789'
pedido.data_nf = date(2025, 10, 20)
pedido.empresa_venda_id = 1
```

##### ✅ **3.3. Atualizar Motos**
```python
for item in pedido.itens:
    item.moto.status = 'VENDIDA'  # 🔴 ALTERA STATUS!
```

**⚠️ IMPORTANTE**: Status da moto muda de `RESERVADA` → `VENDIDA`

##### ✅ **3.4. Vencimentos dos Títulos**
```python
# ✅ JÁ FORAM CALCULADOS na criação do pedido!
# Não precisa recalcular aqui
```

---

### **4️⃣ EMBARQUE** (Opcional - Logística)

```python
# Agrupar pedidos para transporte
EmbarqueMoto(
    numero=1,
    data_embarque=date(2025, 10, 21),
    transportadora_id=2,
    tipo_carga='FRACIONADA'
)

EmbarquePedido(
    embarque_id=1,
    pedido_id=pedido.id
)
```

---

### **5️⃣ RECEBER DO CLIENTE**

#### **5.1. Baixar Título Financeiro (A RECEBER)**
```python
# Quando cliente paga uma parcela
titulo = TituloFinanceiro.query.get(id)

titulo.status = 'PAGO'
titulo.data_baixa = date(2025, 11, 17)  # Data real do pagamento
titulo.valor_pago = titulo.valor
titulo.empresa_destino_id = 1  # Empresa que recebeu

# Criar movimentação financeira
MovimentacaoFinanceira(
    tipo='RECEBIMENTO',
    titulo_financeiro_id=titulo.id,
    valor=titulo.valor,
    data_movimentacao=date(2025, 11, 17),
    empresa_destino_id=1
)

# ✅ Se empresa tem baixa_compra_auto=True
# → Roda service de baixa automática
# → Paga custos de motos usando FIFO
```

#### **5.2. Baixa Automática** (`baixa_automatica_service.py`)

Se `empresa.baixa_compra_auto = True`:

```python
# Busca motos VENDIDAS com custo PENDENTE (FIFO)
motos_pendentes = Moto.query.filter_by(
    status_pagamento_custo='PENDENTE'
).order_by(Moto.data_entrada.asc()).all()

saldo_disponivel = empresa.saldo

for moto in motos_pendentes:
    if saldo_disponivel >= moto.custo_aquisicao:
        # Pagar custo da moto
        moto.custo_pago = moto.custo_aquisicao
        moto.status_pagamento_custo = 'PAGO'
        moto.data_pagamento_custo = date.today()
        moto.empresa_pagadora_id = empresa.id

        saldo_disponivel -= moto.custo_aquisicao

        # Criar movimentação
        MovimentacaoFinanceira(
            tipo='PAGAMENTO',
            valor=moto.custo_aquisicao,
            empresa_origem_id=empresa.id,
            descricao=f'Pagamento custo moto {moto.numero_chassi}'
        )
```

**⚠️ IMPORTANTE**: Motos são pagas em ordem FIFO (mais antigas primeiro)

---

### **6️⃣ PAGAR FORNECEDORES/TRANSPORTADORA**

#### **6.1. Pagar Título a Pagar**
```python
# Quando paga montagem ou movimentação
titulo_pagar = TituloAPagar.query.get(id)

titulo_pagar.status = 'PAGO'
titulo_pagar.data_baixa = date(2025, 11, 18)
titulo_pagar.valor_pago = titulo_pagar.valor
titulo_pagar.empresa_pagadora_id = 1

# Criar movimentação financeira
MovimentacaoFinanceira(
    tipo='PAGAMENTO',
    titulo_a_pagar_id=titulo_pagar.id,
    valor=titulo_pagar.valor,
    empresa_origem_id=1,
    descricao=f'Pagamento {titulo_pagar.tipo} para {titulo_pagar.favorecido}'
)
```

---

## 📊 RESUMO DO FLUXO COMPLETO

```
1. CRIAR PEDIDO (status=PENDENTE, ativo=False)
   ├── Aloca motos FIFO
   ├── Moto: DISPONIVEL → RESERVADA ✅
   ├── Cria itens do pedido
   ├── Gera títulos financeiros (A RECEBER) com vencimentos
   └── Gera títulos a pagar (PENDENTES)

2. APROVAR PEDIDO (status=APROVADO, ativo=True)
   └── Libera para faturamento

3. FATURAR PEDIDO (faturado=True)
   ├── Registra NF
   ├── Moto: RESERVADA → VENDIDA ✅
   └── Vencimentos já calculados (não recalcula)

4. EMBARCAR (opcional)
   └── Agrupa pedidos para transporte

5. RECEBER DO CLIENTE
   ├── Baixa título financeiro
   ├── Cria movimentação (RECEBIMENTO)
   ├── Atualiza saldo empresa
   └── Se baixa_compra_auto=True:
       ├── Busca motos PENDENTES (FIFO)
       ├── Paga custos das motos
       └── Moto: status_pagamento_custo = PAGO ✅

6. PAGAR FORNECEDORES
   ├── Baixa título a pagar
   ├── Cria movimentação (PAGAMENTO)
   └── Atualiza saldo empresa
```

---

## ⚠️ CAMPOS QUE MUDAM AUTOMATICAMENTE

### **Moto (produto.py)**

| Campo | Estado Inicial | Após Criar Pedido | Após Faturar | Após Pagar Custo |
|-------|----------------|-------------------|--------------|------------------|
| `status` | `DISPONIVEL` | `RESERVADA` | `VENDIDA` | - |
| `reservado` | `False` | `True` | `True` | - |
| `status_pagamento_custo` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PAGO` |
| `empresa_pagadora_id` | `NULL` | `NULL` | `NULL` | `empresa.id` |
| `custo_pago` | `0` | `0` | `0` | `custo_aquisicao` |
| `data_pagamento_custo` | `NULL` | `NULL` | `NULL` | `date.today()` |

### **Pedido (vendas.py)**

| Campo | Ao Criar | Após Aprovar | Após Faturar |
|-------|----------|--------------|--------------|
| `ativo` | `False` | `True` | `True` |
| `status` | `PENDENTE` | `APROVADO` | `APROVADO` |
| `faturado` | `False` | `False` | `True` |
| `numero_nf` | `NULL` | `NULL` | `'NF-12345'` |
| `data_nf` | `NULL` | `NULL` | `date(2025, 10, 20)` |

### **Títulos Financeiros**

| Campo | Ao Criar | Após Receber |
|-------|----------|--------------|
| `status` | `ABERTO` | `PAGO` |
| `data_vencimento` | **calculado** | - |
| `data_baixa` | `NULL` | `date.today()` |
| `valor_pago` | `NULL` | `valor` |

---

## 🎯 ORDEM CORRETA DAS FASES

### **Fase 3 → Fase 4 → Fase 5 → Fase 6**

```
FASE 3: Produtos e Clientes
├── Clientes
└── Motos (status=DISPONIVEL, status_pagamento_custo=PENDENTE)

↓

FASE 4: Pedidos e Vendas
├── Pedidos (status=PENDENTE ou APROVADO)
├── Itens (chassi vinculados)
└── Auditoria
    └── Motos ficam RESERVADAS ou VENDIDAS

↓

FASE 5: Financeiro
├── Títulos Financeiros (A RECEBER - com vencimentos)
├── Comissões (calculadas)
└── Títulos a Pagar (PENDENTES)

↓

FASE 6: Logística + Pagamentos
├── Embarques (agrupamento)
├── Movimentações Financeiras (recebimentos/pagamentos)
└── Motos ficam PAGAS (status_pagamento_custo=PAGO)
```

---

## ✅ CHECKLIST PARA IMPORTAÇÃO DE PEDIDOS HISTÓRICOS

Ao importar **Fase 4 (Pedidos)**:

1. ✅ Garantir que motos existem e estão `DISPONIVEL`
2. ✅ Setar `status='APROVADO'` e `ativo=True` (pedidos históricos já aprovados)
3. ✅ Setar `faturado=True` se já foi faturado
4. ✅ Preencher `numero_nf` e `data_nf` se faturado
5. ✅ Atualizar `moto.status`:
   - `RESERVADA` se pedido não faturado
   - `VENDIDA` se pedido faturado

Ao importar **Fase 5 (Financeiro)**:

1. ✅ Criar títulos com `data_vencimento` já calculada
2. ✅ Marcar títulos pagos como `status='PAGO'`
3. ✅ Preencher `data_baixa` e `valor_pago`
4. ✅ Títulos a pagar também com status correto

Ao importar **Fase 6 (Movimentações)**:

1. ✅ Criar movimentações de recebimento/pagamento
2. ✅ Atualizar saldos das empresas
3. ✅ Marcar motos como pagas (`status_pagamento_custo='PAGO'`)
4. ✅ Preencher `empresa_pagadora_id`, `custo_pago`, `data_pagamento_custo`

---

## 🔧 SERVICES ENVOLVIDOS

| Service | Responsabilidade |
|---------|------------------|
| `pedido_service.py` | Criar e faturar pedidos |
| `titulo_service.py` | Gerar títulos financeiros (A RECEBER) |
| `titulo_a_pagar_service.py` | Gerar títulos a pagar (PENDENTES) |
| `baixa_automatica_service.py` | Pagar custos de motos automaticamente (FIFO) |
| `lote_pagamento_service.py` | Pagar custos de motos em lote |
| `comissao_service.py` | Calcular comissões de vendedores |
| `movimentacao_service.py` | Registrar movimentações financeiras |
| `empresa_service.py` | Atualizar saldos de empresas |

---

**Data de Criação**: 14/10/2025
**Última Atualização**: 14/10/2025
