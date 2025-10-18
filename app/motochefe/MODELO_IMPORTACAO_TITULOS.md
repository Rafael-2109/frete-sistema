# 📋 MODELO DE IMPORTAÇÃO HISTÓRICA DE TÍTULOS - MotoChefe

**Data:** 16/10/2025
**Objetivo:** Documentar o modelo correto para importação histórica de títulos de FRETE, MONTAGEM e MOVIMENTAÇÃO

---

## 🎯 ENTENDIMENTO CRÍTICO

### **Diferença entre Modo Operacional vs Importação Histórica**

| Aspecto | Modo Operacional (Normal) | Importação Histórica |
|---------|---------------------------|----------------------|
| **Quando usar** | Pedidos novos do sistema | Dados antigos (antes do sistema) |
| **Criação de títulos** | Automática via `gerar_titulos_com_fifo_parcelas()` | Manual via scripts de importação |
| **Tipos criados** | MOVIMENTACAO, MONTAGEM, FRETE, VENDA | APENAS tipos contratados historicamente |
| **Valor total** | Soma todos os serviços | Deduz serviços do valor VENDA |
| **Status inicial** | ABERTO (aguardando pagamento) | PAGO (se já foi pago) ou ABERTO |

---

## 🔄 FLUXO COMPLETO - MODO OPERACIONAL

### **Passo 1: Criar Pedido** (via `criar_pedido_completo()`)
```python
# Local: app/motochefe/services/pedido_service.py:16

def criar_pedido_completo(dados_pedido, itens_json):
    # 1. Criar PedidoVendaMoto
    # 2. Criar PedidoVendaMotoItem para cada moto
    # 3. Gerar TituloFinanceiro via gerar_titulos_com_fifo_parcelas()
    # 4. Gerar TituloAPagar para MOVIMENTACAO, MONTAGEM (se contratados)
```

### **Passo 2: Gerar Títulos Financeiros** (TituloFinanceiro - A RECEBER)
```python
# Local: app/motochefe/services/titulo_service.py:12

def gerar_titulos_com_fifo_parcelas(pedido, itens_pedido, parcelas_config, tipos_permitidos=None):
    """
    CRIA 4 TIPOS DE TÍTULOS PARA CADA MOTO:
    1. MOVIMENTACAO (ordem=1) - Sempre cria (mesmo R$ 0)
    2. MONTAGEM (ordem=2) - Se montagem_contratada=True
    3. FRETE (ordem=3) - Se pedido.valor_frete_cliente > 0
    4. VENDA (ordem=4) - Sempre cria

    VALORES são calculados por:
    calcular_valores_titulos_moto(item, equipe, pedido, total_motos)
    """
```

#### **Cálculo de Valores** (`calcular_valores_titulos_moto()`)
```python
# Local: app/motochefe/services/titulo_service.py:205

return {
    'movimentacao': equipe.custo_movimentacao if equipe.incluir_custo_movimentacao else 0,
    'movimentacao_custo': equipe.custo_movimentacao,  # SEMPRE > 0 (empresa paga)
    'montagem': item.valor_montagem if item.montagem_contratada else 0,
    'frete': pedido.valor_frete_cliente / total_motos,
    'venda': item.preco_venda
}
```

### **Passo 3: Gerar Títulos A Pagar** (TituloAPagar - A PAGAR)
```python
# Local: app/motochefe/services/pedido_service.py:151-182

# Para CADA MOTO no pedido:
# 1. MOVIMENTACAO (empresa SEMPRE paga MargemSogima)
criar_titulo_a_pagar_movimentacao(item, pedido, equipe, empresa_destino=margem_sogima)

# 2. MONTAGEM (se contratada)
if item.montagem_contratada:
    criar_titulo_a_pagar_montagem(item, pedido, custo_real=custo_montagem)

# 3. FRETE (via EmbarqueMoto, não via TituloAPagar)
# Frete é gerenciado em EmbarqueMoto.valor_frete_contratado
```

---

## 📥 FLUXO DE IMPORTAÇÃO HISTÓRICA

### **Contexto: Por que deduzir do VENDA?**

Na importação histórica, estamos importando pedidos **JÁ CONCLUÍDOS**. O cliente já pagou um valor TOTAL na época.

**Exemplo Real:**
- Cliente comprou moto em 2023 por R$ 15.600 (VALOR TOTAL PAGO)
- Desse valor:
  - R$ 15.000 era o preço da moto (VENDA)
  - R$ 400 era frete (FRETE)
  - R$ 200 era montagem (MONTAGEM)
  - R$ 0 era movimentação (empresa absorveu)

**No sistema atual (importação fase 4):**
- Foi criado apenas `TituloFinanceiro` tipo VENDA = R$ 15.600

**Agora (fases 5, 6, 7):**
- Precisamos criar títulos FRETE, MONTAGEM, MOVIMENTACAO
- E DEDUZIR do VENDA para manter total = R$ 15.600

---

## ✅ MODELO CORRETO DE IMPORTAÇÃO

### **Arquivo: importacao_historico_service.py (JÁ EXISTE!)**

**Local:** `/app/motochefe/services/importacao_historico_service.py`

### **FASE 6: Importar Montagens Históricas**

```python
def importar_montagens_historico(df_montagens, usuario='IMPORTACAO_HISTORICO'):
    """
    AÇÕES EXECUTADAS:

    1. Buscar item do pedido (PedidoVendaMotoItem)
    2. Atualizar campos:
       - montagem_contratada = True
       - valor_montagem = valor_cliente
       - fornecedor_montagem = fornecedor

    3. Criar TituloFinanceiro tipo MONTAGEM (A RECEBER):
       - valor_original = valor_cliente
       - valor_saldo = 0 (se PAGO) ou valor_cliente (se ABERTO)
       - ordem_pagamento = 2

    4. DEDUZIR do TituloFinanceiro tipo VENDA:
       titulo_venda.valor_original -= valor_cliente
       titulo_venda.valor_saldo -= valor_cliente

    5. Criar TituloAPagar tipo MONTAGEM (A PAGAR):
       - valor_original = valor_custo (custo real da montagem)
       - status = PAGO ou ABERTO

    6. Se PAGO: Criar MovimentacaoFinanceira (recebimento E pagamento)
    """
```

### **FASE 7: Importar Movimentações Históricas**

```python
def importar_movimentacoes_historico(df_movimentacoes, usuario='IMPORTACAO_HISTORICO'):
    """
    AÇÕES EXECUTADAS:

    1. Criar TituloFinanceiro tipo MOVIMENTACAO (A RECEBER):
       - valor_original = valor_cliente (pode ser R$ 0!)
       - valor_saldo = 0 (se PAGO) ou valor_cliente
       - ordem_pagamento = 1

    2. DEDUZIR do TituloFinanceiro tipo VENDA:
       titulo_venda.valor_original -= valor_cliente
       titulo_venda.valor_saldo -= valor_cliente

    3. Criar TituloAPagar tipo MOVIMENTACAO (A PAGAR):
       - valor_original = valor_custo (SEMPRE > 0, MargemSogima)
       - status = PAGO ou ABERTO

    4. Se PAGO: Criar MovimentacaoFinanceira
    """
```

### **FASE 8: Importar Fretes Históricos** (NOVO - PRECISA CRIAR)

```python
def importar_fretes_historico(df_fretes, usuario='IMPORTACAO_HISTORICO'):
    """
    AÇÕES A EXECUTAR:

    1. Buscar pedido (PedidoVendaMoto)
    2. Atualizar campo:
       - valor_frete_cliente = valor_total_frete

    3. Para CADA MOTO no pedido:
       a) Criar TituloFinanceiro tipo FRETE (A RECEBER):
          - valor_original = valor_frete_cliente / total_motos
          - valor_saldo = 0 (se PAGO) ou valor rateado
          - ordem_pagamento = 3

       b) DEDUZIR do TituloFinanceiro tipo VENDA:
          titulo_venda.valor_original -= valor_rateado
          titulo_venda.valor_saldo -= valor_rateado

    4. Criar EmbarqueMoto (se existir transportadora):
       - valor_frete_contratado = custo_real_frete
       - status_pagamento_frete = PAGO ou PENDENTE

    5. Se PAGO: Criar MovimentacaoFinanceira
    """
```

---

## 🗂️ TABELAS E CAMPOS AFETADOS

### **1. TituloFinanceiro** (Títulos A RECEBER do cliente)

| Campo | Tipo MOVIMENTACAO | Tipo MONTAGEM | Tipo FRETE | Tipo VENDA |
|-------|-------------------|---------------|------------|------------|
| `tipo_titulo` | 'MOVIMENTACAO' | 'MONTAGEM' | 'FRETE' | 'VENDA' |
| `ordem_pagamento` | 1 | 2 | 3 | 4 |
| `valor_original` | R$ cliente | R$ cliente | R$ rateado | ⚠️ **DEDUZIDO** |
| `valor_saldo` | 0 (se pago) | 0 (se pago) | 0 (se pago) | ⚠️ **DEDUZIDO** |
| `status` | PAGO/ABERTO | PAGO/ABERTO | PAGO/ABERTO | PAGO/ABERTO |

### **2. TituloAPagar** (Títulos A PAGAR para fornecedores)

| Campo | Tipo MOVIMENTACAO | Tipo MONTAGEM | Tipo FRETE |
|-------|-------------------|---------------|------------|
| `tipo` | 'MOVIMENTACAO' | 'MONTAGEM' | ❌ Não usa TituloAPagar |
| `valor_original` | Custo MargemSogima | Custo real montagem | - |
| `status` | PAGO/ABERTO/PENDENTE | PAGO/ABERTO/PENDENTE | - |
| `empresa_destino_id` | ID MargemSogima | NULL | - |
| `fornecedor_montagem` | NULL | Nome fornecedor | - |

### **3. PedidoVendaMotoItem**

| Campo | Quando preencher |
|-------|------------------|
| `montagem_contratada` | TRUE se importar montagem |
| `valor_montagem` | Valor cobrado do cliente |
| `fornecedor_montagem` | Nome do fornecedor |

### **4. PedidoVendaMoto**

| Campo | Quando preencher |
|-------|------------------|
| `valor_frete_cliente` | Valor total de frete (será rateado entre motos) |

### **5. EmbarqueMoto** (para FRETE)

| Campo | Quando preencher |
|-------|------------------|
| `pedido_id` | ID do pedido |
| `transportadora_id` | ID da transportadora (se existir) |
| `valor_frete_contratado` | Custo real do frete |
| `status_pagamento_frete` | PAGO/PENDENTE |

### **6. MovimentacaoFinanceira** (para registros PAGOS)

Criada automaticamente quando `status=PAGO` na importação, usando:
- `registrar_recebimento_titulo()` para títulos a receber
- `registrar_pagamento_lote()` para títulos a pagar

---

## 📝 ESTRUTURA DO EXCEL DE IMPORTAÇÃO

### **FASE 6: Montagens**
```
| chassi | numero_pedido | valor_cliente | valor_custo | fornecedor | status_recebimento | status_pagamento | empresa_recebedora | empresa_pagadora | data_recebimento | data_pagamento |
|--------|---------------|---------------|-------------|------------|-------------------|--------------------|--------------------|--------------------|------------------|----------------|
```

### **FASE 7: Movimentações**
```
| chassi | numero_pedido | valor_cliente | valor_custo | status_recebimento | status_pagamento | empresa_recebedora | empresa_pagadora | data_recebimento | data_pagamento |
|--------|---------------|---------------|-------------|-------------------|--------------------|--------------------|--------------------|------------------|----------------|
```

### **FASE 8: Fretes** (NOVO)
```
| numero_pedido | valor_frete_cliente | valor_frete_custo | transportadora | status_recebimento | status_pagamento | empresa_recebedora | empresa_pagadora | data_recebimento | data_pagamento |
|---------------|---------------------|-------------------|----------------|-------------------|--------------------|--------------------|--------------------|------------------|----------------|
```

**OBSERVAÇÃO:** `valor_frete_cliente` será **rateado** entre todas as motos do pedido automaticamente.

---

## ⚠️ REGRAS DE NEGÓCIO CRÍTICAS

### **1. Dedução do Título VENDA**

```python
# SEMPRE deduzir do título VENDA para manter total correto
titulo_venda = TituloFinanceiro.query.filter_by(
    pedido_id=pedido.id,
    numero_chassi=chassi,
    tipo_titulo='VENDA'
).first()

if titulo_venda:
    titulo_venda.valor_original -= valor_servico
    titulo_venda.valor_saldo -= valor_servico

    # ✅ VALIDAÇÃO: Valor VENDA não pode ficar negativo
    if titulo_venda.valor_original < 0:
        raise Exception(f'Dedução excede valor VENDA! Chassi: {chassi}')
```

### **2. Valor Cliente pode ser R$ 0**

- **MOVIMENTAÇÃO:** Se empresa absorveu custo, `valor_cliente = 0`
- **MONTAGEM:** Se não foi contratada, NÃO IMPORTAR a linha
- **FRETE:** Se foi frete CIF (empresa pagou), `valor_cliente = 0`

### **3. TituloAPagar SEMPRE tem custo > 0**

Mesmo que cliente não pague (R$ 0), empresa SEMPRE paga:
- **MOVIMENTACAO:** MargemSogima (valor fixo da equipe)
- **MONTAGEM:** Fornecedor (custo real)
- **FRETE:** Transportadora (custo contratado)

### **4. Status PENDENTE vs ABERTO**

```python
# TituloAPagar tem 3 status:
- PENDENTE: Cliente ainda não pagou (empresa aguarda receber para pagar)
- ABERTO: Cliente já pagou, empresa deve pagar fornecedor
- PAGO: Empresa já pagou fornecedor
```

### **5. MovimentacaoFinanceira PAI/FILHO**

Quando importar PAGO em lote, criar estrutura hierárquica:
```python
# 1 PAI (agrupamento)
mov_pai = MovimentacaoFinanceira(
    tipo='RECEBIMENTO_LOTE',
    descricao=f'Recebimento Lote - Importação Histórica',
    valor_total=soma_valores
)

# N FILHOS (um por título)
for titulo in titulos:
    mov_filho = MovimentacaoFinanceira(
        movimentacao_pai_id=mov_pai.id,
        tipo='RECEBIMENTO',
        titulo_financeiro_id=titulo.id,
        valor=titulo.valor_original
    )
```

---

## 🚀 PRÓXIMOS PASSOS

### ✅ **O QUE JÁ EXISTE:**
1. ✅ FASE 5: Importação de Comissões
2. ✅ FASE 6: Importação de Montagens
3. ✅ FASE 7: Importação de Movimentações

### ❌ **O QUE FALTA CRIAR:**
4. ❌ **FASE 8: Importação de Fretes**

---

## 📋 CHECKLIST DE VERIFICAÇÃO

Ao importar títulos históricos, SEMPRE verificar:

- [ ] Pedido existe no sistema
- [ ] Moto existe e pertence ao pedido
- [ ] Título VENDA existe para dedução
- [ ] Valor a deduzir NÃO excede valor VENDA
- [ ] Se MONTAGEM: `montagem_contratada=True` no item
- [ ] Se FRETE: `valor_frete_cliente` no pedido
- [ ] Se PAGO: Empresa recebedora/pagadora existe
- [ ] Se PAGO: Atualizar saldo das empresas
- [ ] Se PAGO: Criar MovimentacaoFinanceira
- [ ] Validar integridade: soma(títulos) = valor_total_pedido

---

## 🔗 ARQUIVOS RELACIONADOS

### **Services:**
- `/app/motochefe/services/titulo_service.py` - Geração normal de títulos
- `/app/motochefe/services/titulo_a_pagar_service.py` - Gestão de títulos a pagar
- `/app/motochefe/services/importacao_historico_service.py` - Importação histórica (FASES 5, 6, 7)
- `/app/motochefe/services/pedido_service.py` - Criação de pedidos

### **Models:**
- `/app/motochefe/models/financeiro.py` - TituloFinanceiro, TituloAPagar, MovimentacaoFinanceira
- `/app/motochefe/models/vendas.py` - PedidoVendaMoto, PedidoVendaMotoItem
- `/app/motochefe/models/produto.py` - Moto, EmbarqueMoto

### **Routes:**
- `/app/motochefe/routes/carga_inicial.py` - Rotas de importação
- `/app/motochefe/routes/financeiro.py` - Contas a pagar/receber

---

## 📞 DÚVIDAS FREQUENTES

### **Q: Por que deduzir do VENDA e não somar?**
**A:** Importação histórica trabalha com valor TOTAL já pago. Se não deduzir, o total a receber ficaria inflado.

### **Q: Posso criar títulos FRETE/MONTAGEM sem deduzir?**
**A:** NÃO para histórico. SIM para pedidos novos (modo operacional).

### **Q: E se o cliente não pagou frete/montagem?**
**A:** `valor_cliente = 0`, mas `TituloAPagar` continua com `valor_custo > 0`.

### **Q: Como saber se usar importação histórica ou modo operacional?**
**A:** Histórico = dados antigos. Operacional = pedidos novos do sistema.

---

**Última Atualização:** 16/10/2025
**Autor:** Claude AI (Precision Engineer Mode)
**Status:** ✅ Validado e Documentado
