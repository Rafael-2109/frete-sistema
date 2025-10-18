# 🔍 ANÁLISE DE CAMPOS DOS MODELOS PARA IMPORTAÇÃO HISTÓRICA

**Data:** 16/10/2025
**Objetivo:** Validar se todos os campos necessários existem nos modelos para suportar importação de FRETE, MONTAGEM e MOVIMENTAÇÃO

---

## ✅ RESUMO EXECUTIVO

| Fase | Modelo | Status | Ação Necessária |
|------|--------|--------|-----------------|
| **FASE 6: MONTAGEM** | ✅ Todos OK | ✅ PRONTO | Nenhuma |
| **FASE 7: MOVIMENTAÇÃO** | ✅ Todos OK | ✅ PRONTO | Nenhuma |
| **FASE 8: FRETE** | ⚠️ Falta implementar | ❌ CRIAR | Implementar service |

**CONCLUSÃO:** Os modelos estão 100% preparados! Apenas falta criar o código da FASE 8.

---

## 📋 ANÁLISE POR FASE

### **FASE 6: IMPORTAÇÃO DE MONTAGENS HISTÓRICAS**

#### ✅ **Tabela: TituloFinanceiro** (A RECEBER do cliente)

| Campo Necessário | Existe? | Tipo | Nullable | Observação |
|------------------|---------|------|----------|------------|
| `id` | ✅ | Integer | PK | Auto-increment |
| `pedido_id` | ✅ | Integer | NOT NULL | FK pedido_venda_moto.id |
| `numero_chassi` | ✅ | String(30) | NOT NULL | FK moto.numero_chassi |
| `tipo_titulo` | ✅ | String(20) | NOT NULL | Valor: **'MONTAGEM'** |
| `ordem_pagamento` | ✅ | Integer | NOT NULL | Valor: **2** |
| `numero_parcela` | ✅ | Integer | NOT NULL | Default: 1 |
| `total_parcelas` | ✅ | Integer | NOT NULL | Default: 1 |
| `valor_parcela` | ✅ | Numeric(15,2) | NOT NULL | 0 se sem parcelamento |
| `valor_original` | ✅ | Numeric(15,2) | NOT NULL | Valor cobrado do cliente |
| `valor_saldo` | ✅ | Numeric(15,2) | NOT NULL | 0 se PAGO, valor se ABERTO |
| `valor_pago_total` | ✅ | Numeric(15,2) | Default 0 | Total pago |
| `empresa_recebedora_id` | ✅ | Integer | NULLABLE | FK empresa_venda_moto.id |
| `data_emissao` | ✅ | Date | Default today | Data importação |
| `prazo_dias` | ✅ | Integer | NULLABLE | Dias até vencimento |
| `data_vencimento` | ✅ | Date | NULLABLE | Calculado ou NULL |
| `data_ultimo_pagamento` | ✅ | Date | NULLABLE | Data recebimento |
| `status` | ✅ | String(20) | NOT NULL | **'PAGO'** ou **'ABERTO'** |
| `criado_em` | ✅ | DateTime | Default utcnow | Auto |
| `criado_por` | ✅ | String(100) | NULLABLE | 'IMPORTACAO_HISTORICO' |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

---

#### ✅ **Tabela: TituloAPagar** (A PAGAR para fornecedor)

| Campo Necessário | Existe? | Tipo | Nullable | Observação |
|------------------|---------|------|----------|------------|
| `id` | ✅ | Integer | PK | Auto-increment |
| `tipo` | ✅ | String(20) | NOT NULL | Valor: **'MONTAGEM'** |
| `titulo_financeiro_id` | ✅ | Integer | NOT NULL | FK titulo_financeiro.id |
| `pedido_id` | ✅ | Integer | NOT NULL | FK pedido_venda_moto.id |
| `numero_chassi` | ✅ | String(30) | NOT NULL | FK moto.numero_chassi |
| `fornecedor_montagem` | ✅ | String(100) | NULLABLE | Nome fornecedor |
| `empresa_destino_id` | ✅ | Integer | NULLABLE | NULL para montagem |
| `valor_original` | ✅ | Numeric(15,2) | NOT NULL | Custo real montagem |
| `valor_pago` | ✅ | Numeric(15,2) | Default 0 | Valor pago |
| `valor_saldo` | ✅ | Numeric(15,2) | NOT NULL | Saldo devedor |
| `data_criacao` | ✅ | Date | Default today | Data importação |
| `data_liberacao` | ✅ | Date | NULLABLE | Quando liberado |
| `data_vencimento` | ✅ | Date | NULLABLE | Vencimento |
| `data_pagamento` | ✅ | Date | NULLABLE | Data pagamento |
| `status` | ✅ | String(20) | NOT NULL | **'PENDENTE'**, **'ABERTO'** ou **'PAGO'** |
| `criado_em` | ✅ | DateTime | Default utcnow | Auto |
| `criado_por` | ✅ | String(100) | NULLABLE | 'IMPORTACAO_HISTORICO' |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

---

#### ✅ **Tabela: PedidoVendaMotoItem** (Controle de contratação)

| Campo Necessário | Existe? | Tipo | Nullable | Observação |
|------------------|---------|------|----------|------------|
| `montagem_contratada` | ✅ | Boolean | NOT NULL | Default: False |
| `valor_montagem` | ✅ | Numeric(15,2) | Default 0 | Valor cobrado cliente |
| `fornecedor_montagem` | ✅ | String(100) | NULLABLE | Nome fornecedor |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

**OBSERVAÇÃO IMPORTANTE:** Ao importar montagem, SEMPRE atualizar:
```python
item.montagem_contratada = True
item.valor_montagem = valor_cliente
item.fornecedor_montagem = fornecedor
```

---

### **FASE 7: IMPORTAÇÃO DE MOVIMENTAÇÕES HISTÓRICAS**

#### ✅ **Tabela: TituloFinanceiro** (A RECEBER do cliente)

| Campo Necessário | Existe? | Observação |
|------------------|---------|------------|
| Mesmos campos da MONTAGEM | ✅ | `tipo_titulo='MOVIMENTACAO'`, `ordem_pagamento=1` |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

**IMPORTANTE:**
- `valor_original` **pode ser R$ 0** (empresa absorveu custo)
- Mesmo com R$ 0, o título é criado para rastreabilidade

---

#### ✅ **Tabela: TituloAPagar** (A PAGAR para MargemSogima)

| Campo Necessário | Existe? | Observação |
|------------------|---------|------------|
| `empresa_destino_id` | ✅ | FK para MargemSogima (EmpresaVendaMoto) |
| `fornecedor_montagem` | ✅ | NULL para movimentação |
| Demais campos | ✅ | `tipo='MOVIMENTACAO'` |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

**OBSERVAÇÃO CRÍTICA:**
- `valor_original` do TituloAPagar **SEMPRE > 0** (empresa paga MargemSogima)
- Mesmo que cliente não pague (TituloFinanceiro R$ 0), empresa SEMPRE paga

---

### **FASE 8: IMPORTAÇÃO DE FRETES HISTÓRICOS** ⚠️

#### ✅ **Tabela: TituloFinanceiro** (A RECEBER do cliente)

| Campo Necessário | Existe? | Observação |
|------------------|---------|------------|
| Mesmos campos das outras fases | ✅ | `tipo_titulo='FRETE'`, `ordem_pagamento=3` |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

**OBSERVAÇÃO:**
- `valor_original` = `pedido.valor_frete_cliente / total_motos` (rateado)
- Um título FRETE por moto

---

#### ✅ **Tabela: PedidoVendaMoto** (Valor total frete)

| Campo Necessário | Existe? | Tipo | Observação |
|------------------|---------|------|------------|
| `valor_frete_cliente` | ✅ | Numeric(15,2) | Default 0, valor TOTAL cobrado |

**STATUS:** ✅ **CAMPO EXISTE**

---

#### ✅ **Tabela: EmbarqueMoto** (Custo do frete para transportadora)

| Campo Necessário | Existe? | Tipo | Observação |
|------------------|---------|------|------------|
| `numero_embarque` | ✅ | String(50) | Número único |
| `transportadora_id` | ✅ | Integer | FK transportadora_moto.id |
| `data_embarque` | ✅ | Date | Data embarque |
| `valor_frete_contratado` | ✅ | Numeric(15,2) | **Custo real** do frete |
| `valor_frete_pago` | ✅ | Numeric(15,2) | Valor pago |
| `valor_frete_saldo` | ✅ | Numeric(15,2) | Saldo devedor |
| `data_pagamento_frete` | ✅ | Date | Data pagamento |
| `status_pagamento_frete` | ✅ | String(20) | PENDENTE/PAGO |
| `empresa_pagadora_id` | ✅ | Integer | Empresa que pagou |
| `criado_em` | ✅ | DateTime | Auto |
| `criado_por` | ✅ | String(100) | 'IMPORTACAO_HISTORICO' |

**STATUS:** ✅ **TODOS OS CAMPOS EXISTEM**

**OBSERVAÇÃO CRÍTICA:**
- **NÃO EXISTE** `TituloAPagar` para frete!
- Frete usa `EmbarqueMoto` para controlar pagamento à transportadora
- Diferente de MONTAGEM e MOVIMENTAÇÃO

---

## 🔄 RELAÇÃO ENTRE TABELAS

### **MONTAGEM:**
```
PedidoVendaMotoItem.montagem_contratada = True
    ↓
TituloFinanceiro (A RECEBER)
    tipo='MONTAGEM', valor=valor_cliente
    ↓
TituloAPagar (A PAGAR)
    tipo='MONTAGEM', fornecedor=fornecedor_montagem, valor=custo_real
```

### **MOVIMENTAÇÃO:**
```
TituloFinanceiro (A RECEBER)
    tipo='MOVIMENTACAO', valor=valor_cliente (pode ser 0)
    ↓
TituloAPagar (A PAGAR)
    tipo='MOVIMENTACAO', empresa_destino=MargemSogima, valor=custo_fixo
```

### **FRETE:**
```
PedidoVendaMoto.valor_frete_cliente = TOTAL
    ↓
TituloFinanceiro (A RECEBER) - UM POR MOTO
    tipo='FRETE', valor=total/qtd_motos (rateado)
    ↓
EmbarqueMoto (A PAGAR) - UM POR EMBARQUE
    valor_frete_contratado=custo_real_transportadora
```

---

## ⚠️ CAMPOS IMPORTANTES QUE **NÃO EXISTEM** (e não são necessários)

### **PedidoVendaMotoItem**
- ❌ `frete_contratado` - Não existe (frete é no nível do pedido, não do item)
- ❌ `valor_frete` - Não existe (usa `pedido.valor_frete_cliente` rateado)
- ❌ `movimentacao_contratada` - Não existe (movimentação é sempre criada)
- ❌ `valor_movimentacao` - Não existe (vem da equipe)

**MOTIVO:** Esses controles não são necessários porque:
1. **FRETE:** É controlado por `PedidoVendaMoto.valor_frete_cliente` (rateado entre motos)
2. **MOVIMENTAÇÃO:** É SEMPRE criada (baseado na equipe, não é opcional por item)

---

## ✅ VALIDAÇÕES CRÍTICAS ANTES DA IMPORTAÇÃO

### **1. MONTAGEM:**
- [ ] `PedidoVendaMotoItem` existe para o chassi
- [ ] `valor_cliente >= 0`
- [ ] `valor_custo > 0`
- [ ] `fornecedor_montagem` preenchido
- [ ] Título VENDA existe para dedução
- [ ] `titulo_venda.valor_original >= valor_cliente` (não pode deduzir mais que existe)

### **2. MOVIMENTAÇÃO:**
- [ ] `PedidoVendaMotoItem` existe para o chassi
- [ ] `valor_cliente >= 0` (pode ser 0!)
- [ ] `valor_custo > 0` (SEMPRE!)
- [ ] MargemSogima existe no cadastro de empresas
- [ ] Título VENDA existe para dedução
- [ ] `titulo_venda.valor_original >= valor_cliente`

### **3. FRETE:**
- [ ] `PedidoVendaMoto` existe
- [ ] `valor_frete_cliente >= 0` (pode ser 0 se CIF)
- [ ] `valor_frete_custo > 0` (custo real)
- [ ] `Transportadora` existe (se informada)
- [ ] Para CADA MOTO:
  - [ ] Título VENDA existe
  - [ ] `titulo_venda.valor_original >= (valor_frete_cliente / total_motos)`

---

## 🎯 CAMPOS A PREENCHER EM CADA FASE

### **FASE 6: MONTAGEM**

#### **TituloFinanceiro (A RECEBER):**
```python
tipo_titulo = 'MONTAGEM'
ordem_pagamento = 2
numero_parcela = 1
total_parcelas = 1
valor_parcela = 0
valor_original = valor_cliente
valor_saldo = 0 if status_recebimento == 'PAGO' else valor_cliente
valor_pago_total = valor_cliente if status_recebimento == 'PAGO' else 0
empresa_recebedora_id = empresa_id if status == 'PAGO' else NULL
data_emissao = data_recebimento ou date.today()
data_ultimo_pagamento = data_recebimento if PAGO else NULL
status = 'PAGO' ou 'ABERTO'
criado_por = 'IMPORTACAO_HISTORICO'
```

#### **TituloAPagar (A PAGAR):**
```python
tipo = 'MONTAGEM'
fornecedor_montagem = fornecedor
empresa_destino_id = NULL
valor_original = valor_custo
valor_pago = valor_custo if status_pagamento == 'PAGO' else 0
valor_saldo = 0 if status == 'PAGO' else valor_custo
data_liberacao = data_recebimento if titulo_financeiro PAGO else NULL
data_pagamento = data_pagamento if PAGO else NULL
status = 'PAGO' ou 'ABERTO' ou 'PENDENTE'
criado_por = 'IMPORTACAO_HISTORICO'
```

#### **PedidoVendaMotoItem:**
```python
montagem_contratada = True
valor_montagem = valor_cliente
fornecedor_montagem = fornecedor
```

#### **Dedução do VENDA:**
```python
titulo_venda.valor_original -= valor_cliente
titulo_venda.valor_saldo -= valor_cliente
```

---

### **FASE 7: MOVIMENTAÇÃO**

#### **TituloFinanceiro (A RECEBER):**
```python
tipo_titulo = 'MOVIMENTACAO'
ordem_pagamento = 1
valor_original = valor_cliente  # PODE SER 0!
# Demais campos iguais à MONTAGEM
```

#### **TituloAPagar (A PAGAR):**
```python
tipo = 'MOVIMENTACAO'
empresa_destino_id = margem_sogima.id
fornecedor_montagem = NULL
valor_original = valor_custo  # SEMPRE > 0
# Demais campos iguais à MONTAGEM
```

#### **Dedução do VENDA:**
```python
titulo_venda.valor_original -= valor_cliente
titulo_venda.valor_saldo -= valor_cliente
```

---

### **FASE 8: FRETE** (A IMPLEMENTAR)

#### **PedidoVendaMoto:**
```python
valor_frete_cliente = valor_total_frete
```

#### **TituloFinanceiro (A RECEBER) - PARA CADA MOTO:**
```python
tipo_titulo = 'FRETE'
ordem_pagamento = 3
valor_original = pedido.valor_frete_cliente / total_motos
valor_saldo = 0 if status == 'PAGO' else valor_original
# Demais campos iguais às outras fases
```

#### **EmbarqueMoto (A PAGAR):**
```python
numero_embarque = gerar_numero_unico()
transportadora_id = transportadora.id
data_embarque = data_embarque
valor_frete_contratado = valor_custo
valor_frete_pago = valor_custo if PAGO else 0
valor_frete_saldo = 0 if PAGO else valor_custo
data_pagamento_frete = data_pagamento if PAGO else NULL
status_pagamento_frete = 'PAGO' ou 'PENDENTE'
empresa_pagadora_id = empresa_id if PAGO else NULL
criado_por = 'IMPORTACAO_HISTORICO'
```

#### **EmbarquePedido (Relação N:N):**
```python
embarque_id = embarque.id
pedido_id = pedido.id
qtd_motos_pedido = total_motos
valor_frete_rateado = valor_custo / total_motos (por moto)
```

#### **Dedução do VENDA - PARA CADA MOTO:**
```python
valor_rateado = pedido.valor_frete_cliente / total_motos
titulo_venda.valor_original -= valor_rateado
titulo_venda.valor_saldo -= valor_rateado
```

---

## 📊 RESUMO DE STATUS

### ✅ **O QUE ESTÁ PRONTO:**

1. ✅ **Modelos 100% completos** - Todos os campos existem
2. ✅ **FASE 6: Importação Montagens** - Código implementado
3. ✅ **FASE 7: Importação Movimentações** - Código implementado

### ❌ **O QUE FALTA:**

1. ❌ **FASE 8: Importação Fretes** - Precisa criar service (seguir padrão fases 6 e 7)

---

## 🔧 RECOMENDAÇÕES

### **Para FASE 8 (FRETE):**

1. Criar `importar_fretes_historico()` em `importacao_historico_service.py`
2. Seguir EXATAMENTE o padrão das FASES 6 e 7
3. Criar template Excel com colunas:
   - `numero_pedido` (obrigatório)
   - `valor_frete_cliente` (cobrado do cliente, pode ser 0)
   - `valor_frete_custo` (custo real, obrigatório)
   - `transportadora` (nome, opcional)
   - `status_recebimento` (PAGO/ABERTO)
   - `status_pagamento` (PAGO/PENDENTE)
   - `empresa_recebedora` (se PAGO)
   - `empresa_pagadora` (se PAGO)
   - `data_recebimento` (se PAGO)
   - `data_pagamento` (se PAGO)
   - `data_embarque` (data do embarque)

4. Lógica especial:
   - Um registro no Excel = TODOS os fretes do pedido
   - Criar N títulos (um por moto) com valor RATEADO
   - Criar 1 EmbarqueMoto para o custo

---

## 📞 CONCLUSÃO

**✅ TODOS OS CAMPOS NECESSÁRIOS EXISTEM NOS MODELOS!**

Não é necessário criar/alterar NENHUMA tabela ou campo. O sistema está 100% preparado estruturalmente.

A única ação necessária é **implementar o código da FASE 8** seguindo o padrão existente das FASES 6 e 7.

---

**Data de Análise:** 16/10/2025
**Analista:** Claude AI (Precision Engineer Mode)
**Status Final:** ✅ APROVADO - Estrutura de dados completa
