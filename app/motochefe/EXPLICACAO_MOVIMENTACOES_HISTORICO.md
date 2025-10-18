# 📊 EXPLICAÇÃO DETALHADA: IMPORTAÇÃO DE MOVIMENTAÇÕES HISTÓRICAS

**Data:** 16/10/2025
**Objetivo:** Explicar como funciona a importação de movimentações (TituloFinanceiro + TituloAPagar)

---

## ⚠️ IMPORTANTE: O que é "MOVIMENTAÇÃO"?

### **NÃO CONFUNDIR:**

| Termo | O que é | Tabela |
|-------|---------|--------|
| **MOVIMENTAÇÃO** (título) | Custo de movimentação entre CD's (R$ 50 por moto) | `TituloFinanceiro` + `TituloAPagar` |
| **MovimentacaoFinanceira** | Registro de fluxo de caixa (entrada/saída de dinheiro) | `movimentacao_financeira` |

**Neste documento:** Falamos de **MOVIMENTAÇÃO** (título de R$ 50).

---

## 🎯 O QUE É MOVIMENTAÇÃO?

### **Conceito de Negócio:**

Quando uma moto precisa ser movida entre CD's (ex: CD Matriz → CD Filial), há um custo de R$ 50 por moto que é pago para **MargemSogima**.

### **Quem paga:**

- **OPÇÃO 1:** Cliente paga R$ 50 (incluído no valor total)
- **OPÇÃO 2:** Empresa absorve o custo (cliente paga R$ 0)

**Independente da opção, empresa SEMPRE paga R$ 50 para MargemSogima!**

---

## 📋 ESTRUTURA DO EXCEL - ABA "MOVIMENTACOES"

### **Colunas do Template:**

```excel
| numero_pedido | numero_chassi | valor_cliente | valor_custo | status_recebimento | data_recebimento | empresa_recebedora | status_pagamento | data_pagamento | empresa_pagadora |
|---------------|---------------|---------------|-------------|--------------------|-----------------|--------------------|------------------|----------------|------------------|
| MC-001        | ABC123XYZ456  | 50.00         | 50.00       | PAGO               | 2024-01-10      | Sogima LTDA        | PAGO             | 2024-01-15     | Sogima LTDA      |
| MC-002        | DEF789GHI012  | 0.00          | 50.00       | PAGO               | 2024-01-12      | Sogima LTDA        | PAGO             | 2024-01-15     | Sogima LTDA      |
```

### **Explicação das Colunas:**

| Coluna | Obrigatório | Tipo | Descrição | Exemplo |
|--------|-------------|------|-----------|---------|
| `numero_pedido` | ✅ SIM | String | Número do pedido existente | "MC-001" |
| `numero_chassi` | ✅ SIM | String | Chassi da moto | "ABC123XYZ456" |
| `valor_cliente` | ✅ SIM | Decimal | Quanto CLIENTE pagou (pode ser R$ 0) | 50.00 ou 0.00 |
| `valor_custo` | ✅ SIM | Decimal | Quanto EMPRESA pagou MargemSogima (sempre > 0) | 50.00 |
| `status_recebimento` | ✅ SIM | Enum | Se recebeu do cliente | "PAGO" ou "PENDENTE" |
| `data_recebimento` | ⚠️ Condicional | Date | Data que recebeu (obrigatório se PAGO) | "2024-01-10" |
| `empresa_recebedora` | ⚠️ Condicional | String | Empresa que recebeu (obrigatório se PAGO) | "Sogima LTDA" |
| `status_pagamento` | ✅ SIM | Enum | Se pagou MargemSogima | "PAGO" ou "PENDENTE" |
| `data_pagamento` | ⚠️ Condicional | Date | Data que pagou (obrigatório se PAGO) | "2024-01-15" |
| `empresa_pagadora` | ⚠️ Condicional | String | Empresa que pagou (obrigatório se PAGO) | "Sogima LTDA" |

---

## 🔄 FLUXO COMPLETO DE IMPORTAÇÃO

### **Exemplo 1: Cliente PAGOU movimentação**

**Excel:**
```
numero_pedido: MC-001
numero_chassi: ABC123XYZ456
valor_cliente: 50.00
valor_custo: 50.00
status_recebimento: PAGO
data_recebimento: 2024-01-10
empresa_recebedora: Sogima LTDA
status_pagamento: PAGO
data_pagamento: 2024-01-15
empresa_pagadora: Sogima LTDA
```

**O que acontece no sistema:**

#### **PASSO 1: Criar TituloFinanceiro (A RECEBER)**
```python
TituloFinanceiro(
    tipo_titulo='MOVIMENTACAO',
    ordem_pagamento=1,
    valor_original=50.00,          # Valor que cliente pagou
    valor_saldo=0.00,              # 0 porque já foi pago
    valor_pago_total=50.00,
    status='PAGO',
    empresa_recebedora_id=Sogima.id,
    data_ultimo_pagamento='2024-01-10'
)
```

#### **PASSO 2: Deduzir do TituloFinanceiro VENDA**
```python
titulo_venda = TituloFinanceiro.query.filter_by(
    pedido_id=MC-001,
    numero_chassi=ABC123XYZ456,
    tipo_titulo='VENDA'
).first()

titulo_venda.valor_original -= 50.00  # Era 15.000, vira 14.950
titulo_venda.valor_saldo -= 50.00
```

**Motivo:** Cliente pagou R$ 15.000 TOTAL. Se R$ 50 é movimentação, então VENDA = R$ 14.950.

#### **PASSO 3: Criar TituloAPagar (A PAGAR para MargemSogima)**
```python
TituloAPagar(
    tipo='MOVIMENTACAO',
    empresa_destino_id=MargemSogima.id,
    valor_original=50.00,          # Custo real
    valor_saldo=0.00,              # 0 porque já foi pago
    valor_pago=50.00,
    status='PAGO',
    data_pagamento='2024-01-15'
)
```

#### **PASSO 4: Criar MovimentacaoFinanceira RECEBIMENTO**
```python
MovimentacaoFinanceira(
    tipo='RECEBIMENTO',
    categoria='Título Movimentação',
    valor=50.00,
    data_movimentacao='2024-01-10',
    origem_tipo='Cliente',
    empresa_destino_id=Sogima.id,
    descricao='Recebimento Histórico Movimentação - Pedido MC-001'
)
```

#### **PASSO 5: Atualizar Saldo da Empresa Recebedora**
```python
Sogima.saldo += 50.00
```

#### **PASSO 6: Criar MovimentacaoFinanceira PAGAMENTO**
```python
MovimentacaoFinanceira(
    tipo='PAGAMENTO',
    categoria='Movimentação',
    valor=50.00,
    data_movimentacao='2024-01-15',
    empresa_origem_id=Sogima.id,
    empresa_destino_id=MargemSogima.id,
    descricao='Pagamento Histórico Movimentação - Pedido MC-001'
)
```

#### **PASSO 7: Atualizar Saldo da Empresa Pagadora**
```python
Sogima.saldo -= 50.00
```

**RESULTADO FINAL:**
- ✅ Cliente pagou R$ 50 → recebido
- ✅ Empresa pagou R$ 50 para MargemSogima → pago
- ✅ Título VENDA deduzido em R$ 50
- ✅ Saldo da Sogima: +50 -50 = 0 (entrada e saída)
- ✅ Saldo da MargemSogima: +50

---

### **Exemplo 2: Empresa ABSORVEU custo (cliente não pagou)**

**Excel:**
```
numero_pedido: MC-002
numero_chassi: DEF789GHI012
valor_cliente: 0.00              ← Cliente NÃO pagou
valor_custo: 50.00               ← Empresa PAGOU MargemSogima
status_recebimento: PAGO         ← Título R$ 0 fica PAGO automaticamente
data_recebimento: 2024-01-12
empresa_recebedora: Sogima LTDA
status_pagamento: PAGO
data_pagamento: 2024-01-15
empresa_pagadora: Sogima LTDA
```

**O que acontece no sistema:**

#### **PASSO 1: Criar TituloFinanceiro (A RECEBER) - R$ 0**
```python
TituloFinanceiro(
    tipo_titulo='MOVIMENTACAO',
    valor_original=0.00,           # Cliente NÃO pagou
    valor_saldo=0.00,
    valor_pago_total=0.00,
    status='PAGO'                  # PAGO automaticamente (nada a receber)
)
```

#### **PASSO 2: Deduzir do TituloFinanceiro VENDA - R$ 0**
```python
titulo_venda.valor_original -= 0.00  # Não muda nada
titulo_venda.valor_saldo -= 0.00
```

**Motivo:** Cliente pagou R$ 15.000 TOTAL e não pagou movimentação. Logo, VENDA = R$ 15.000 (sem dedução).

#### **PASSO 3: Criar TituloAPagar (A PAGAR) - R$ 50**
```python
TituloAPagar(
    tipo='MOVIMENTACAO',
    empresa_destino_id=MargemSogima.id,
    valor_original=50.00,          # Empresa SEMPRE paga
    valor_saldo=0.00,
    valor_pago=50.00,
    status='PAGO'
)
```

#### **PASSO 4: NÃO cria MovimentacaoFinanceira RECEBIMENTO**
```python
# if valor_cliente > 0:  ← FALSE, pula
#     criar_movimentacao_recebimento()
```

**Motivo:** Não houve recebimento do cliente (R$ 0).

#### **PASSO 5: Atualizar Saldo - NÃO altera**
```python
# Sogima.saldo += 0.00  ← Não executa
```

#### **PASSO 6: Criar MovimentacaoFinanceira PAGAMENTO - R$ 50**
```python
MovimentacaoFinanceira(
    tipo='PAGAMENTO',
    categoria='Movimentação',
    valor=50.00,
    empresa_origem_id=Sogima.id,
    empresa_destino_id=MargemSogima.id
)
```

#### **PASSO 7: Atualizar Saldo da Empresa Pagadora**
```python
Sogima.saldo -= 50.00
```

**RESULTADO FINAL:**
- ✅ Cliente pagou R$ 0 → sem recebimento
- ✅ Empresa pagou R$ 50 para MargemSogima → pago
- ✅ Título VENDA NÃO deduzido (cliente pagou valor cheio)
- ✅ Saldo da Sogima: -50 (apenas saída)
- ✅ Saldo da MargemSogima: +50

---

## 🔍 DIFERENÇA ENTRE MOVIMENTAÇÃO E MONTAGEM

| Aspecto | MOVIMENTAÇÃO | MONTAGEM |
|---------|--------------|----------|
| **Beneficiário** | MargemSogima (empresa fixa) | Fornecedor terceirizado (variável) |
| **Campo TituloAPagar** | `empresa_destino_id` | `fornecedor_montagem` |
| **Valor pode ser R$ 0?** | ✅ SIM (cliente) / ❌ NÃO (custo) | ✅ SIM (ambos) |
| **Tipo** | `tipo='MOVIMENTACAO'` | `tipo='MONTAGEM'` |
| **Ordem** | `ordem_pagamento=1` | `ordem_pagamento=2` |
| **Controle em Item?** | ❌ NÃO (sempre criado) | ✅ SIM (`montagem_contratada=True`) |

---

## ❓ PERGUNTAS FREQUENTES

### **Q1: Por que criar título de R$ 0?**
**A:** Para rastreabilidade. Mesmo que cliente não pague, o sistema registra que movimentação existiu (custo para empresa).

### **Q2: O que acontece se `valor_cliente > valor_custo`?**
**A:** É permitido. Cliente pode pagar R$ 60 e empresa pagar R$ 50 (lucro de R$ 10).

### **Q3: O que acontece se `valor_cliente < valor_custo`?**
**A:** É permitido. Cliente pode pagar R$ 30 e empresa pagar R$ 50 (prejuízo de R$ 20).

### **Q4: Posso ter `status_recebimento=PAGO` e `status_pagamento=PENDENTE`?**
**A:** ✅ SIM! Recebeu do cliente mas ainda não pagou fornecedor.

### **Q5: Posso ter `status_recebimento=PENDENTE` e `status_pagamento=PAGO`?**
**A:** ⚠️ TECNICAMENTE SIM, mas é estranho. Pagou fornecedor antes de receber do cliente.

### **Q6: Se `valor_cliente=0`, preciso preencher `status_recebimento`?**
**A:** ✅ SIM, use `status_recebimento=PAGO` (nada a receber = já "pago").

### **Q7: Como saber se MargemSogima existe no sistema?**
**A:** O código chama `garantir_margem_sogima()` que cria automaticamente se não existir.

### **Q8: O que acontece se título VENDA não existir?**
**A:** Gera AVISO mas continua importação. Título movimentação é criado mas dedução não é feita.

### **Q9: Pode deduzir mais do que o valor VENDA?**
**A:** ❌ NÃO deveria, mas o código atual PERMITE (bug potencial). Recomendo validar antes.

### **Q10: Como gerar o template Excel?**
**A:** Execute:
```bash
python app/motochefe/scripts/gerar_template_historico.py
```
Arquivo criado em: `/tmp/template_historico_motochefe.xlsx`

---

## ⚠️ VALIDAÇÕES CRÍTICAS

### **Antes de importar, verifique:**

1. ✅ Pedido existe no sistema
2. ✅ Chassi existe no pedido
3. ✅ Título VENDA existe (se não existir, haverá aviso)
4. ✅ `valor_cliente >= 0`
5. ✅ `valor_custo > 0` (empresa SEMPRE paga)
6. ✅ Se `status_recebimento=PAGO`: `data_recebimento` e `empresa_recebedora` preenchidos
7. ✅ Se `status_pagamento=PAGO`: `data_pagamento` e `empresa_pagadora` preenchidos
8. ✅ Empresas existem no sistema
9. ✅ `titulo_venda.valor_original >= valor_cliente` (evitar valores negativos)

---

## 📊 EXEMPLO COMPLETO COM MÚLTIPLAS LINHAS

**Excel:**
```excel
numero_pedido | numero_chassi | valor_cliente | valor_custo | status_recebimento | data_recebimento | empresa_recebedora | status_pagamento | data_pagamento | empresa_pagadora
MC-001        | ABC123        | 50.00         | 50.00       | PAGO               | 2024-01-10       | Sogima LTDA        | PAGO             | 2024-01-15     | Sogima LTDA
MC-001        | DEF456        | 50.00         | 50.00       | PAGO               | 2024-01-10       | Sogima LTDA        | PAGO             | 2024-01-15     | Sogima LTDA
MC-002        | GHI789        | 0.00          | 50.00       | PAGO               | 2024-01-12       | Sogima LTDA        | PENDENTE         |                |
MC-003        | JKL012        | 50.00         | 50.00       | PENDENTE           |                  |                    | PENDENTE         |                |
```

**Resultado:**
- **Linha 1:** Cliente pagou R$ 50, empresa pagou R$ 50 (TUDO PAGO)
- **Linha 2:** Mesmo pedido, segunda moto (TUDO PAGO)
- **Linha 3:** Cliente não pagou (R$ 0), empresa ainda não pagou MargemSogima (PENDENTE)
- **Linha 4:** Nada foi pago ainda (TUDO PENDENTE)

**Impacto em MC-001:**
```
Título VENDA original: R$ 30.000 (2 motos × R$ 15.000)
Dedução: 50 + 50 = R$ 100
Título VENDA final: R$ 29.900
```

---

## 🎯 RESUMO VISUAL

```
┌─────────────────────────────────────────────────────────────┐
│                    IMPORTAÇÃO MOVIMENTAÇÃO                  │
└─────────────────────────────────────────────────────────────┘

EXCEL (1 linha)
    ↓
┌───────────────────────────────────────────────────────────┐
│ 1. TituloFinanceiro (A RECEBER)                           │
│    tipo='MOVIMENTACAO', valor=valor_cliente              │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 2. DEDUZIR TituloFinanceiro VENDA                         │
│    titulo_venda.valor_original -= valor_cliente          │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 3. TituloAPagar (A PAGAR para MargemSogima)               │
│    tipo='MOVIMENTACAO', valor=valor_custo                │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 4. SE valor_cliente > 0 E status_recebimento=PAGO:        │
│    - MovimentacaoFinanceira RECEBIMENTO                   │
│    - Atualizar saldo empresa (+)                          │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 5. SE status_pagamento=PAGO:                              │
│    - MovimentacaoFinanceira PAGAMENTO                     │
│    - Atualizar saldo empresa (-)                          │
└───────────────────────────────────────────────────────────┘
```

---

## 📁 ARQUIVOS RELACIONADOS

- **Template:** `app/motochefe/scripts/gerar_template_historico.py`
- **Importação:** `app/motochefe/services/importacao_historico_service.py:613`
- **Execução:** `app/motochefe/scripts/importar_historico_completo.py`
- **Model TituloFinanceiro:** `app/motochefe/models/financeiro.py:10`
- **Model TituloAPagar:** `app/motochefe/models/financeiro.py:304`
- **Model MovimentacaoFinanceira:** `app/motochefe/models/financeiro.py:200`

---

**Data:** 16/10/2025
**Autor:** Claude AI (Precision Engineer Mode)
**Status:** ✅ Documentação Completa
