# 💰 CONTAS FINANCEIRAS - SISTEMA MOTOCHEFE

**Data**: 2025-01-04
**Status**: ✅ **BACKEND COMPLETO** | ⏳ **TEMPLATES PENDENTES**

---

## 📋 RESUMO

Sistema consolidado de **Contas a Pagar** e **Contas a Receber** com:
- ✅ Visão única de todas as contas
- ✅ Pagamento/recebimento em lote
- ✅ Agrupamentos inteligentes
- ✅ 5 tipos de contas a pagar
- ✅ 1 tipo de contas a receber

---

## 💸 CONTAS A PAGAR (5 tipos)

### 1. **MOTOS** - Custo de Aquisição
**Modelo**: `Moto`
**Campos Novos** (adicionados):
```python
custo_pago = db.Column(db.Numeric(15, 2), nullable=True)
data_pagamento_custo = db.Column(db.Date, nullable=True)
status_pagamento_custo = db.Column(db.String(20), default='PENDENTE')
```

**Agrupamento**: Por NF de entrada
**Permite**: Pagar NF inteira OU chassi individual

---

### 2. **FRETES** - Embarques
**Modelo**: `EmbarqueMoto`
**Campos Existentes**:
```python
valor_frete_contratado  # Valor a pagar
valor_frete_pago        # Valor pago
data_pagamento_frete
status_pagamento_frete  # PENDENTE, PAGO
```

**Agrupamento**: Por transportadora
**Exemplo**: "Pagar todos os fretes da JadLog na sexta-feira"

---

### 3. **COMISSÕES** - Vendedores
**Modelo**: `ComissaoVendedor`
**Campos Existentes**:
```python
valor_rateado       # Valor a pagar
data_pagamento
status              # PENDENTE, PAGO
```

**Agrupamento**: Por vendedor

---

### 4. **MONTAGENS** - Motos Vendidas
**Modelo**: `PedidoVendaMotoItem`
**Campos Novos** (adicionados):
```python
fornecedor_montagem = db.Column(db.String(100), nullable=True)
montagem_paga = db.Column(db.Boolean, default=False)
data_pagamento_montagem = db.Column(db.Date, nullable=True)
```

**Agrupamento**: Por fornecedor de montagem
**Preparado para**: Múltiplas equipes terceirizadas

---

### 5. **DESPESAS** - Mensais
**Modelo**: `DespesaMensal`
**Campos Existentes**:
```python
valor
valor_pago
data_pagamento
status  # PENDENTE, PAGO
```

**Agrupamento**: Por tipo (salário, aluguel, etc)

---

## 💵 CONTAS A RECEBER (1 tipo)

### 1. **TÍTULOS** - Parcelas de Vendas
**Modelo**: `TituloFinanceiro`
**Campos Existentes**:
```python
valor_parcela
valor_recebido
data_vencimento
data_recebimento
status  # ABERTO, PAGO
```

**Agrupamento**: Por situação (vencidos, hoje, a vencer)
**Trigger**: Ao pagar último título → Gera comissão

---

## 🗺️ ROTAS CRIADAS

| Rota | Método | Função |
|------|--------|--------|
| `/contas-a-pagar` | GET | Tela consolidada |
| `/contas-a-pagar/pagar-lote` | POST | Pagamento múltiplo |
| `/contas-a-receber` | GET | Tela consolidada |
| `/contas-a-receber/receber-lote` | POST | Recebimento múltiplo |

**Arquivo**: [financeiro.py](app/motochefe/routes/financeiro.py) - 350 linhas

---

## 📊 LAYOUT DAS TELAS

### CONTAS A PAGAR - Estrutura

```
┌─────────────────────────────────────┐
│ RESUMO GERAL                        │
│ Total a Pagar: R$ 150.000,00        │
│ Vencidos: R$ 10.000 | Hoje: R$ 5k  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ [1] MOTOS (Custo Aquisição)         │
│     R$ 50.000 pendente              │
│                                     │
│ Agrupado por: [NF ▼]                │
│                                     │
│ ☐ [NF 1234] Honda - 5 motos        │
│    R$ 50.000                        │
│    ☐ Chassi ABC | R$ 10.000        │
│    ☐ Chassi DEF | R$ 10.000        │
│    [Expandir]                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ [2] FRETES DE EMBARQUES             │
│     R$ 8.000 pendente               │
│                                     │
│ Agrupado por: [Transportadora ▼]   │
│                                     │
│ ☐ [JadLog] 3 embarques             │
│    R$ 5.000                         │
│    ☐ EMB-001 | Venc: 10/01 | R$ 1k│
│    ☐ EMB-003 | Venc: 12/01 | R$ 2k│
│    [Expandir]                       │
└─────────────────────────────────────┘

SELECIONADOS: 5 itens | R$ 8.500
[Pagar Selecionados] [Exportar]
```

### CONTAS A RECEBER - Estrutura

```
┌─────────────────────────────────────┐
│ RESUMO GERAL                        │
│ Total a Receber: R$ 80.000,00       │
│ Vencidos: R$ 10.000 | Hoje: R$ 2k  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ VENCIDOS (10 títulos)               │
│ Total: R$ 10.000                    │
│                                     │
│ ☐ Título #001 | Ped P-123 | R$ 1k  │
│ ☐ Título #002 | Ped P-124 | R$ 2k  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ VENCENDO HOJE (3 títulos)           │
│ Total: R$ 2.000                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ A VENCER (20 títulos)               │
│ Total: R$ 68.000                    │
└─────────────────────────────────────┘

SELECIONADOS: 3 títulos | R$ 3.000
[Receber Selecionados] [Exportar]
```

---

## 🔧 MIGRAÇÃO SQL

**Arquivo**: [add_campos_pagamento.sql](app/motochefe/scripts/add_campos_pagamento.sql)

```sql
-- Adicionar em moto:
ALTER TABLE moto
ADD COLUMN custo_pago NUMERIC(15, 2),
ADD COLUMN data_pagamento_custo DATE,
ADD COLUMN status_pagamento_custo VARCHAR(20) DEFAULT 'PENDENTE';

-- Adicionar em pedido_venda_moto_item:
ALTER TABLE pedido_venda_moto_item
ADD COLUMN fornecedor_montagem VARCHAR(100),
ADD COLUMN montagem_paga BOOLEAN DEFAULT FALSE,
ADD COLUMN data_pagamento_montagem DATE;
```

**⚠️ EXECUTAR** antes de usar as telas!

---

## 💡 FLUXOS DE USO

### Fluxo 1: Pagar Fretes Semanalmente
```
1. Sexta-feira → Acessar /contas-a-pagar
2. Expandir seção "FRETES DE EMBARQUES"
3. Expandir "JadLog"
4. Selecionar todos os embarques (checkbox pai)
5. Clicar "Pagar Selecionados"
6. Informar data: 06/01/2025
7. Confirmar → 5 embarques pagos!
```

### Fluxo 2: Pagar NF de Motos
```
1. Acessar /contas-a-pagar
2. Seção "MOTOS"
3. Selecionar NF 1234 inteira (5 motos)
4. OU selecionar chassi individual
5. Pagar Selecionados
6. Status → PAGO
```

### Fluxo 3: Baixar Títulos Vencidos
```
1. Acessar /contas-a-receber
2. Seção "VENCIDOS"
3. Selecionar todos (checkbox)
4. Receber Selecionados
5. Data recebimento
6. Confirmar → Se for último título do pedido: GERA COMISSÃO!
```

---

## ⚠️ PENDÊNCIAS

### ❌ TEMPLATES HTML NÃO CRIADOS

Devido ao tamanho, os templates precisam ser criados separadamente:

1. **contas_a_pagar.html** (~500 linhas)
   - Cards expansíveis para cada tipo
   - Checkboxes aninhados (pai/filho)
   - Modal de pagamento
   - JavaScript para seleção

2. **contas_a_receber.html** (~300 linhas)
   - Cards por situação
   - Checkboxes simples
   - Modal de recebimento
   - JavaScript

**Status**: Backend 100% pronto, aguardando templates

---

## 📁 ARQUIVOS CRIADOS/MODIFICADOS

### CRIADOS:
1. ✅ `routes/financeiro.py` (350 linhas)
2. ✅ `scripts/add_campos_pagamento.sql`
3. ✅ `CONTAS_FINANCEIRAS.md` (este arquivo)

### MODIFICADOS:
4. ✅ `models/produto.py` - Moto (3 campos)
5. ✅ `models/vendas.py` - PedidoVendaMotoItem (3 campos)
6. ✅ `routes/__init__.py` - Import financeiro

### PENDENTES:
7. ⏳ `templates/motochefe/financeiro/contas_a_pagar.html`
8. ⏳ `templates/motochefe/financeiro/contas_a_receber.html`
9. ⏳ Adicionar links no navbar/dashboard

---

## ✅ PRÓXIMOS PASSOS

1. **EXECUTAR MIGRAÇÃO SQL**:
   ```bash
   psql -f app/motochefe/scripts/add_campos_pagamento.sql
   ```

2. **CRIAR TEMPLATES** (usar estrutura do layout acima)

3. **ADICIONAR LINKS**:
   - Navbar → Dropdown "Financeiro"
   - Dashboard → Card "Financeiro"

4. **REINICIAR** servidor Flask

5. **TESTAR** fluxos de pagamento/recebimento

---

## 🎯 BENEFÍCIOS

- ✅ **Visão única** de todas as contas
- ✅ **Pagamento em lote** (economiza tempo)
- ✅ **Agrupamentos inteligentes** (por fornecedor, transportadora, etc)
- ✅ **Flexibilidade** (pagar individual OU em grupo)
- ✅ **Controle** (status de cada item)
- ✅ **Auditoria** (data de cada pagamento)

---

**Última atualização**: 04/01/2025
**Versão**: 1.0.0 (Backend completo)
