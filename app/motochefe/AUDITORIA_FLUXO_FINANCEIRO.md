# 🔍 AUDITORIA COMPLETA - FLUXO FINANCEIRO MOTOCHEFE

**Data:** 07/10/2025
**Objetivo:** Verificar integridade de TODOS os fluxos financeiros
**Status:** 🔄 EM ANDAMENTO

---

## 📊 MAPEAMENTO COMPLETO

### **1. TÍTULOS A RECEBER (TituloFinanceiro)**

**Arquivo:** [app/motochefe/models/financeiro.py:10-128](app/motochefe/models/financeiro.py#L10)

#### **Tipos de Títulos:**
| Tipo | Ordem | Valor | Criado Quando |
|------|-------|-------|---------------|
| MOVIMENTACAO | 1 | `equipe.custo_movimentacao` | Se `equipe.incluir_custo_movimentacao=True` |
| MONTAGEM | 2 | `item.valor_montagem` | Se `item.montagem_contratada=True` |
| FRETE | 3 | `pedido.valor_frete_cliente / total_motos` ✅ | SEMPRE (rateio por moto) |
| VENDA | 4 | `item.preco_venda` | SEMPRE |

**Evidência:** [titulo_service.py:47-53](app/motochefe/services/titulo_service.py#L47)

```python
tipos_titulo = [
    ('MOVIMENTACAO', 1, valores['movimentacao']),
    ('MONTAGEM', 2, valores['montagem']),
    ('FRETE', 3, valores['frete']),  # ← Sempre R$ 0
    ('VENDA', 4, valores['venda'])
]
```

#### **✅ FRETE IMPLEMENTADO (08/01/2025)**

**Evidência:** [titulo_service.py:201-206](app/motochefe/services/titulo_service.py#L201)

```python
# FRETE: Rateio do frete do pedido entre motos
valor_frete = Decimal('0')
if pedido and pedido.valor_frete_cliente and total_motos > 0:
    valor_frete = Decimal(str(pedido.valor_frete_cliente)) / total_motos
    valor_frete = valor_frete.quantize(Decimal('0.01'))
```

**Status:** ✅ FRETE cobrado do cliente (TituloFinanceiro)
- Rateio proporcional por moto
- Arredondamento para 2 casas decimais
- Gera MovimentacaoFinanceira quando pago

**IMPORTANTE:** Existem DOIS tipos de frete:
1. **Frete Cliente** (`PedidoVendaMoto.valor_frete_cliente`): Cobrado do cliente via TituloFinanceiro
2. **Frete Embarque** (`EmbarqueMoto.valor_frete_contratado`): Pago à transportadora (veja seção 4 abaixo)

---

### **2. TÍTULOS A PAGAR (TituloAPagar)**

**Arquivo:** [app/motochefe/models/financeiro.py:291-389](app/motochefe/models/financeiro.py#L291)

#### **Tipos de Títulos:**
| Tipo | Beneficiário | Valor | Criado Quando |
|------|-------------|-------|---------------|
| MOVIMENTACAO | MargemSogima (`empresa_destino_id`) | Mesmo do TituloFinanceiro | Quando título MOVIMENTACAO é criado |
| MONTAGEM | `fornecedor_montagem` | `CustosOperacionais.custo_montagem` ⚠️ | Se `item.montagem_contratada=True` |

**Evidência:** [pedido_service.py:141-154](app/motochefe/services/pedido_service.py#L141)

```python
for titulo in titulos_financeiros_criados:
    if titulo.tipo_titulo == 'MOVIMENTACAO':
        titulo_pagar = criar_titulo_a_pagar_movimentacao(titulo)  # ✅

    elif titulo.tipo_titulo == 'MONTAGEM':
        titulo_pagar = criar_titulo_a_pagar_montagem(titulo, item)  # ✅
```

#### **✅ CONFIRMADO: Não cria TituloAPagar para FRETE e VENDA**

**Razão:** Documentação diz "Usado para: Movimentação e Montagem" (linha 296)

#### **🔴 PROBLEMA IDENTIFICADO: VALOR DA MONTAGEM**

**Cliente paga:** `item.valor_montagem` (ex: R$ 150)
**Sistema paga:** `CustosOperacionais.custo_montagem` (ex: R$ 100)
**Margem:** R$ 50 fica para quem?

**Evidência:** [titulo_a_pagar_service.py:72-77](app/motochefe/services/titulo_a_pagar_service.py#L72)

```python
# Buscar custo REAL da montagem
custos = CustosOperacionais.get_custos_vigentes()
valor_custo_real = custos.custo_montagem  # ← CUSTO, não valor cobrado
```

**Status:** ⚠️ Diferença entre valor cobrado e valor pago - CONFIRMAR se é intencional

---

### **3. MOVIMENTAÇÕES FINANCEIRAS**

**Arquivo:** [app/motochefe/models/financeiro.py:187-289](app/motochefe/models/financeiro.py#L187)

#### **Tipos de Movimentações (RECEBIMENTOS):**
| Categoria | Quando | Valor | Empresa Destino |
|-----------|--------|-------|-----------------|
| Título Movimentação | Recebimento TituloFinanceiro MOVIMENTACAO | Valor recebido | `empresa_recebedora` |
| Título Montagem | Recebimento TituloFinanceiro MONTAGEM | Valor recebido | `empresa_recebedora` |
| Título Frete | Recebimento TituloFinanceiro FRETE | Valor recebido | `empresa_recebedora` |
| Título Venda | Recebimento TituloFinanceiro VENDA | Valor recebido | `empresa_recebedora` |

**Evidência:** [movimentacao_service.py:10-53](app/motochefe/services/movimentacao_service.py#L10)

```python
def registrar_recebimento_titulo(titulo, valor_recebido, empresa_recebedora, usuario=None):
    movimentacao = MovimentacaoFinanceira(
        tipo='RECEBIMENTO',
        categoria=f'Título {titulo.tipo_titulo}',  # ← Dinâmico
        valor=valor_recebido,
        empresa_destino_id=empresa_recebedora.id,  # ✅
        titulo_financeiro_id=titulo.id,  # ✅
        # ...
    )
```

#### **Tipos de Movimentações (PAGAMENTOS):**
| Categoria | Quando | Valor | Empresa Origem |
|-----------|--------|-------|----------------|
| Movimentação | Pagar TituloAPagar MOVIMENTACAO | Valor pago | `empresa_pagadora` |
| Montagem | Pagar TituloAPagar MONTAGEM | Valor pago | `empresa_pagadora` |
| Comissão | Gerar comissão vendedor | `comissao.valor_rateado` | `empresa_pagadora` |
| Custo Moto | Pagar fornecedor moto | Valor pago | `empresa_pagadora` |

**Evidência:** [movimentacao_service.py:56-113](app/motochefe/services/movimentacao_service.py#L56)

---

## 🔄 FLUXO 1: CRIAÇÃO DE PEDIDO

### **Passo a Passo (com evidências):**

#### **1. Criar Pedido**
[pedido_service.py:63-84](app/motochefe/services/pedido_service.py#L63)
```python
pedido = PedidoVendaMoto(...)
db.session.add(pedido)
db.session.flush()
```

#### **2. Alocar Motos (FIFO)**
[pedido_service.py:99-131](app/motochefe/services/pedido_service.py#L99)
```python
motos_disponiveis = Moto.query.filter_by(
    modelo_id=modelo_id,
    cor=cor,
    status='DISPONIVEL',
    reservado=False,
    ativo=True
).order_by(Moto.data_entrada.asc()).limit(quantidade).all()  # ← FIFO

for moto in motos_disponiveis:
    item = PedidoVendaMotoItem(...)
    moto.status = 'RESERVADA'  # ✅
    moto.reservado = True  # ✅
```

#### **3. Gerar Títulos Financeiros (FIFO entre parcelas)**
[pedido_service.py:133-139](app/motochefe/services/pedido_service.py#L133)
```python
parcelas_config = dados_pedido.get('parcelas', [])
titulos_financeiros_criados = gerar_titulos_com_fifo_parcelas(
    pedido,
    itens_criados,
    parcelas_config  # ← Pode ser [] se sem parcelamento
)
```

**Resultado:** Para cada moto:
- ✅ 1 título MOVIMENTACAO (se `equipe.incluir_custo_movimentacao`)
- ✅ 1 título MONTAGEM (se `item.montagem_contratada`)
- ⚠️ 1 título FRETE (sempre R$ 0)
- ✅ 1 título VENDA (sempre)

**Total:** 3-4 títulos por moto (dependendo de montagem e movimentação)

#### **4. Criar Títulos A Pagar (PENDENTES)**
[pedido_service.py:141-154](app/motochefe/services/pedido_service.py#L141)
```python
for titulo in titulos_financeiros_criados:
    if titulo.tipo_titulo == 'MOVIMENTACAO':
        titulo_pagar = criar_titulo_a_pagar_movimentacao(titulo)  # ✅

    elif titulo.tipo_titulo == 'MONTAGEM':
        titulo_pagar = criar_titulo_a_pagar_montagem(titulo, item)  # ✅
```

**Resultado:** Para cada moto:
- ✅ 1 TituloAPagar MOVIMENTACAO (status PENDENTE)
- ✅ 1 TituloAPagar MONTAGEM (se montagem, status PENDENTE)

**❌ MovimentacaoFinanceira:** NENHUMA criada nesta etapa

---

## 🔄 FLUXO 2: RECEBIMENTO DE TÍTULO

### **Passo a Passo (com evidências):**

#### **Opção A: Recebimento com FIFO (NOVO)**
[titulo_service.py:213-365](app/motochefe/services/titulo_service.py#L213)

```python
def processar_pagamento_fifo(pedido, valor_pago, empresa_recebedora, usuario=None):
    # 1. Buscar títulos ABERTOS (FIFO)
    titulos_abertos = TituloFinanceiro.query.filter_by(
        pedido_id=pedido.id,
        status='ABERTO'
    ).order_by(
        TituloFinanceiro.numero_parcela,  # ← Parcela
        TituloFinanceiro.numero_chassi,   # ← Moto
        TituloFinanceiro.ordem_pagamento  # ← Tipo (1=MOV, 2=MONT, 3=FRETE, 4=VENDA)
    ).all()

    # 2. Consumir títulos até esgotar valor
    for titulo in titulos_abertos:
        if valor_restante >= titulo.valor_saldo:
            # PAGA COMPLETO
            mov = registrar_recebimento_titulo(titulo, ...)  # ✅ CRIA MovimentacaoFinanceira
            titulo.status = 'PAGO'

            # TRIGGERS:
            liberar_titulo_a_pagar(titulo.id)  # ✅ PENDENTE → ABERTO

            if empresa_recebedora.baixa_compra_auto:
                processar_baixa_automatica_motos(...)  # ✅ CRIA MovimentacaoFinanceira (pagamento moto)

            if titulo.tipo_titulo == 'VENDA':
                gerar_comissao_moto(titulo)  # ✅ CRIA ComissaoVendedor

        else:
            # PAGA PARCIAL → SPLIT
            titulo_pago = TituloFinanceiro(valor=valor_restante, status='PAGO')
            titulo_restante = TituloFinanceiro(valor=saldo, status='ABERTO')
            titulo_original.status = 'CANCELADO'

            registrar_recebimento_titulo(titulo_pago, ...)  # ✅ CRIA MovimentacaoFinanceira
            renumerar_parcelas_nao_pagas(...)  # ✅ +1 em todas parcelas não pagas
```

**MovimentacaoFinanceira criada:**
- ✅ 1 por título pago (RECEBIMENTO)
- ✅ 1+ por baixa automática de motos (PAGAMENTO) - se `baixa_compra_auto=True`

#### **Opção B: Recebimento Individual (COMPATIBILIDADE)**
[titulo_service.py:402-484](app/motochefe/services/titulo_service.py#L402)

```python
def receber_titulo(titulo, valor_recebido, empresa_recebedora, usuario=None):
    # MESMO FLUXO mas sem FIFO
    movimentacao = registrar_recebimento_titulo(...)  # ✅
    atualizar_saldo(empresa_recebedora.id, valor_recebido, 'SOMAR')  # ✅

    if titulo.valor_saldo <= 0:
        titulo.status = 'PAGO'
        liberar_titulo_a_pagar(titulo.id)  # ✅

        if empresa_recebedora.baixa_compra_auto:
            processar_baixa_automatica_motos(...)  # ✅

        if titulo.tipo_titulo == 'VENDA':
            gerar_comissao_moto(titulo)  # ✅
```

**✅ CONFIRMADO:** TODO recebimento cria MovimentacaoFinanceira

---

## 🔄 FLUXO 3: PAGAMENTO DE TÍTULO A PAGAR

### **Passo a Passo (com evidências):**

[titulo_a_pagar_service.py:131-189](app/motochefe/services/titulo_a_pagar_service.py#L131)

```python
def pagar_titulo_a_pagar(titulo_pagar, valor_pago, empresa_pagadora, usuario=None):
    # 1. REGISTRAR MOVIMENTAÇÃO
    movimentacao = registrar_pagamento_titulo_a_pagar(
        titulo_pagar,
        valor_pago,
        empresa_pagadora,
        usuario
    )  # ✅ CRIA MovimentacaoFinanceira (PAGAMENTO)

    # 2. ATUALIZAR SALDOS
    atualizar_saldo(empresa_pagadora.id, valor_pago, 'SUBTRAIR')  # ✅

    if titulo_pagar.tipo == 'MOVIMENTACAO' and titulo_pagar.empresa_destino_id:
        atualizar_saldo(titulo_pagar.empresa_destino_id, valor_pago, 'SOMAR')  # ✅

    # 3. ATUALIZAR TÍTULO
    titulo_pagar.valor_pago += valor_pago
    titulo_pagar.valor_saldo -= valor_pago

    if titulo_pagar.valor_saldo <= 0:
        titulo_pagar.status = 'PAGO'
    else:
        titulo_pagar.status = 'PARCIAL'
```

**MovimentacaoFinanceira criada:**
- ✅ MOVIMENTACAO: PAGAMENTO de `empresa_pagadora` para `MargemSogima`
- ✅ MONTAGEM: PAGAMENTO de `empresa_pagadora` para `fornecedor_montagem` (externo)

**✅ CONFIRMADO:** TODO pagamento cria MovimentacaoFinanceira

---

## 🔄 FLUXO 4: COMISSÃO DE VENDEDOR

### **Onde é gerada:**
[titulo_service.py:279-281](app/motochefe/services/titulo_service.py#L279)
[titulo_service.py:473-475](app/motochefe/services/titulo_service.py#L473)

```python
if titulo.tipo_titulo == 'VENDA':
    gerar_comissao_moto(titulo)  # ✅ Chamado quando VENDA é PAGO
```

### **Como é paga:**
[movimentacao_service.py:159-193](app/motochefe/services/movimentacao_service.py#L159)

```python
def registrar_pagamento_comissao(comissao, empresa_pagadora, usuario=None):
    movimentacao = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Comissão',
        valor=comissao.valor_rateado,
        empresa_origem_id=empresa_pagadora.id,  # ✅
        destino_tipo='Vendedor',
        destino_identificacao=comissao.vendedor.vendedor,
        comissao_vendedor_id=comissao.id,  # ✅
        # ...
    )
```

**MovimentacaoFinanceira criada:**
- ✅ 1 por comissão paga (PAGAMENTO)

**✅ CONFIRMADO:** Pagamento de comissão cria MovimentacaoFinanceira

---

## 🔄 FLUXO 5: BAIXA AUTOMÁTICA DE MOTOS

### **Quando ocorre:**
[titulo_service.py:276-277](app/motochefe/services/titulo_service.py#L276)

```python
if empresa_recebedora.baixa_compra_auto:
    processar_baixa_automatica_motos(empresa_recebedora, valor_recebido, mov.id, usuario)
```

### **O que faz:**
[baixa_automatica_service.py](app/motochefe/services/baixa_automatica_service.py)

Paga motos mais antigas primeiro (FIFO) até esgotar valor recebido.

**MovimentacaoFinanceira criada:**
- ✅ 1 por moto paga (PAGAMENTO via `registrar_pagamento_custo_moto`)

---

## ✅ CHECKLIST DE INTEGRIDADE

### **Títulos A RECEBER (TituloFinanceiro):**
| Tipo | Criado? | Valor Correto? | Status |
|------|---------|----------------|--------|
| MOVIMENTACAO | ✅ | ✅ | OK |
| MONTAGEM | ✅ | ✅ | OK |
| FRETE | ✅ | ❌ Sempre R$ 0 | ⚠️ TODO |
| VENDA | ✅ | ✅ | OK |

### **Títulos A PAGAR (TituloAPagar):**
| Tipo | Criado? | Beneficiário Correto? | Status |
|------|---------|----------------------|--------|
| MOVIMENTACAO | ✅ | ✅ MargemSogima | OK |
| MONTAGEM | ✅ | ✅ Fornecedor | ⚠️ Diferença de valor |
| FRETE | ❌ | N/A | OK (não precisa) |
| VENDA | ❌ | N/A | OK (não precisa) |

### **MovimentacaoFinanceira:**
| Origem | Cria MovimentacaoFinanceira? | Status |
|--------|----------------------------|--------|
| Recebimento Título | ✅ | OK |
| Pagamento Título A Pagar | ✅ | OK |
| Pagamento Comissão | ✅ | OK |
| Baixa Automática Moto | ✅ | OK |
| Splitting de Título | ✅ | OK |
| Pagamento DespesaMensal | ✅ | OK (implementado 08/01) |
| **Pagamento Frete Embarque** | ✅ | **OK (implementado 08/01)** |

---

## 🚛 FRETE DE EMBARQUE (EmbarqueMoto) - IMPLEMENTADO 08/01/2025

### **Modelo:**
**Arquivo:** [app/motochefe/models/logistica.py:10-68](app/motochefe/models/logistica.py#L10)

#### **Campos de Pagamento:**
```python
valor_frete_contratado = db.Column(db.Numeric(15, 2), nullable=False)    # Valor acordado
valor_frete_pago = db.Column(db.Numeric(15, 2), nullable=True)           # Pago efetivamente
data_pagamento_frete = db.Column(db.Date, nullable=True)                  # Data pagamento
status_pagamento_frete = db.Column(db.String(20), default='PENDENTE')     # PENDENTE/PAGO
empresa_pagadora_id = db.Column(db.Integer, FK, nullable=True, index=True) # ✅ NOVO
```

### **Fluxo de Pagamento:**

#### **1. Registrar Movimentação**
**Arquivo:** [movimentacao_service.py:262-295](app/motochefe/services/movimentacao_service.py#L262)

```python
def registrar_pagamento_frete_embarque(embarque, valor_pago, empresa_pagadora, usuario=None):
    movimentacao = MovimentacaoFinanceira(
        tipo='PAGAMENTO',
        categoria='Frete Embarque',
        valor=valor_pago,

        empresa_origem_id=empresa_pagadora.id,
        destino_tipo='Transportadora',
        destino_identificacao=embarque.transportadora.transportadora,

        embarque_moto_id=embarque.id,  # ✅ Relacionamento
        descricao=f'Pagamento Frete Embarque #{embarque.numero_embarque}',
        criado_por=usuario
    )
```

#### **2. Atualizar Saldo**
Usa mesma função de empresa_service: `atualizar_saldo(empresa_id, valor, 'SUBTRAIR')`

#### **3. Atualizar EmbarqueMoto**
**Arquivo:** [financeiro.py:245-276](app/motochefe/routes/financeiro.py#L245)

```python
embarque.valor_frete_pago = valor_pago
embarque.data_pagamento_frete = data_pag
embarque.empresa_pagadora_id = empresa_pagadora.id  # ✅ NOVO
embarque.status_pagamento_frete = 'PAGO'
```

### **Migration SQL:**
**Arquivo:** [add_empresa_pagadora_embarque.sql](app/motochefe/scripts/add_empresa_pagadora_embarque.sql)

### **Status Final:**
✅ **COMPLETO** - Frete de embarque agora:
- Cria MovimentacaoFinanceira
- Atualiza saldo da empresa pagadora
- Rastreia qual empresa pagou (empresa_pagadora_id)
- Consistente com DespesaMensal

---

## 🔴 PROBLEMAS IDENTIFICADOS

### **1. ✅ FRETE Cliente - RESOLVIDO (08/01/2025)**
**Status:** ✅ IMPLEMENTADO rateio por moto
- TituloFinanceiro tipo FRETE agora recebe `pedido.valor_frete_cliente / total_motos`
- Gera MovimentacaoFinanceira quando cliente paga

### **2. ✅ FRETE Embarque - RESOLVIDO (08/01/2025)**
**Status:** ✅ IMPLEMENTADO pagamento completo
- Adiciona empresa_pagadora_id ao EmbarqueMoto
- Cria MovimentacaoFinanceira quando empresa paga transportadora
- Atualiza saldo da empresa

### **3. ✅ MONTAGEM: Diferença de valor É INTENCIONAL**
**Cobrado do cliente:** `item.valor_montagem` (ex: R$ 150)
**Pago ao fornecedor:** `CustosOperacionais.custo_montagem` (ex: R$ 100)
**Diferença:** R$ 50 → **MARGEM DA EMPRESA** ✅

**Status:** Confirmado pelo usuário como intencional

---

## 📝 PRÓXIMAS AÇÕES

1. ✅ **CONCLUÍDO:** FRETE Cliente - rateio implementado
2. ✅ **CONCLUÍDO:** FRETE Embarque - pagamento completo implementado
3. ✅ **CONCLUÍDO:** DespesaMensal - MovimentacaoFinanceira implementada
4. ✅ **CONFIRMADO:** MONTAGEM - diferença é margem da empresa
5. 🔄 **Continuar auditoria:** Verificar outros fluxos financeiros se necessário

---

## ✅ RESUMO FINAL DA AUDITORIA

### **Implementações Realizadas (08/01/2025):**

1. **Frete Cliente (TituloFinanceiro):**
   - ✅ Rateio por moto implementado
   - ✅ MovimentacaoFinanceira criada no pagamento

2. **Frete Embarque (EmbarqueMoto):**
   - ✅ Campo empresa_pagadora_id adicionado
   - ✅ Função registrar_pagamento_frete_embarque() criada
   - ✅ MovimentacaoFinanceira criada no pagamento
   - ✅ Saldo da empresa atualizado
   - ✅ Migration SQL criada

3. **DespesaMensal:**
   - ✅ Campo empresa_pagadora_id já existia
   - ✅ MovimentacaoFinanceira implementada anteriormente

### **Integridade Verificada:**
✅ Todos os recebimentos geram MovimentacaoFinanceira
✅ Todos os pagamentos geram MovimentacaoFinanceira
✅ Todos os saldos são atualizados corretamente
✅ Rastreabilidade completa de origem e destino
