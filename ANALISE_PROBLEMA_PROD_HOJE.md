# 🔍 ANÁLISE DO PROBLEMA: "Prod. Hoje" Zerado após Carregamento Assíncrono

## 🎯 COMPORTAMENTO OBSERVADO

### ✅ Renderização Inicial (t=0ms)
- Endpoint: `/api/pedido/{num_pedido}/workspace`
- Arquivo: `app/carteira/routes/workspace_api.py`
- **RESULTADO**: Prod. Hoje aparece PREENCHIDO corretamente

### ❌ Carregamento Assíncrono (t=500ms)
- Endpoint: `/api/pedido/{num_pedido}/workspace-estoque`
- Arquivo: `app/carteira/routes/estoque_api.py`
- **RESULTADO**: Prod. Hoje fica ZERADO

---

## 🔬 ANÁLISE DETALHADA DO FLUXO

### 1️⃣ PRIMEIRO CARREGAMENTO (workspace_api.py)
```python
# Linha 86: processar_dados_workspace_produto é chamado
produto_data = processar_dados_workspace_produto(produto, resumo_estoque)

# PROBLEMA IDENTIFICADO - Linha 83:
resumo_estoque = None  # ⚠️ PASSANDO None!
```

**Por que funciona mesmo com None?**
```python
# workspace_utils.py, linha 272:
producao_hoje = obter_producao_hoje(produto.cod_produto, resumo_estoque)

# Se resumo_estoque é None, vai para o fallback (linha 127-129):
hoje = agora_brasil().date()
producao = SaldoEstoque.calcular_producao_periodo(cod_produto, hoje, hoje)
return float(producao)
```

**CONCLUSÃO**: No primeiro carregamento, `producao_hoje` vem do FALLBACK que calcula diretamente do banco.

### 2️⃣ SEGUNDO CARREGAMENTO (estoque_api.py)
```python
# Linha 156: Busca projeção completa
projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)

# Linha 172-179: Cria resumo_estoque
resumo_estoque = {
    'projecao_29_dias': projecao_completa.get('projecao', []),
    # ...
}

# Linha 184: Processa dados
produto_data = processar_dados_workspace_produto(produto, resumo_estoque)
```

**O que acontece em obter_producao_hoje?**
```python
# workspace_utils.py, linha 108-121:
projecao = resumo_estoque.get('projecao_29_dias')  # ✅ Existe
if projecao and len(projecao) > 0:
    hoje_dados = projecao[0]  # D0
    if isinstance(hoje_dados, dict):
        entrada = hoje_dados.get('entrada', 0)  # ⚠️ AQUI ESTÁ O PROBLEMA!
```

---

## ❌ PROBLEMA RAIZ IDENTIFICADO

### ServicoEstoqueSimples.get_projecao_completa

```python
# estoque_simples.py, linha 174-175:
# Para D0 (hoje), obtém entrada do dia
entrada_dia = entradas.get(data, 0)  # ⚠️ 'data' é date.today()
```

**PROBLEMA**: `entradas` é um dicionário onde as chaves são objetos `date`.

### ServicoEstoqueSimples.calcular_entradas_previstas

```python
# estoque_simples.py, linha 99-103:
# Busca produção programada
producao_query = db.session.query(
    ProgramacaoProducao.data_programacao,
    func.sum(ProgramacaoProducao.qtd_programada).label('total')
).filter(
    ProgramacaoProducao.data_programacao.between(data_inicio, data_fim)
)

# Linha 116-117:
for data, qtd in producao_query:
    entradas[data] = entradas.get(data, 0) + float(qtd)
```

**ANÁLISE**: O dicionário `entradas` usa objetos `date` como chaves. Se não há produção programada para hoje, `entradas.get(date.today(), 0)` retorna 0.

---

## 🔍 DIFERENÇA ENTRE OS DOIS ENDPOINTS

### workspace_api.py (FUNCIONA)
1. Passa `resumo_estoque = None`
2. `obter_producao_hoje` vai para o fallback
3. Fallback chama `SaldoEstoque.calcular_producao_periodo`
4. **RETORNA**: Valor calculado diretamente

### estoque_api.py (NÃO FUNCIONA)
1. Passa `resumo_estoque` com projeção
2. `obter_producao_hoje` usa a projeção
3. Projeção D0 tem `entrada = 0` (se não há produção programada para hoje)
4. **RETORNA**: 0

---

## 🐛 BUG CONFIRMADO

O problema está na diferença de comportamento entre:
1. **Fallback** (usado no primeiro carregamento): Calcula produção diretamente
2. **Projeção** (usado no carregamento assíncrono): Usa apenas `programacao_producao` 

### Possíveis causas do valor diferente:
1. `SaldoEstoque.calcular_producao_periodo` pode estar usando lógica diferente
2. Pode haver dados em `movimentacao_estoque` tipo 'PRODUÇÃO' que não estão em `programacao_producao`
3. O fallback pode estar considerando fontes de dados adicionais

---

## ✅ SOLUÇÃO PROPOSTA

### Opção 1: Fazer estoque_api.py usar o mesmo fallback
```python
# Em estoque_api.py, após linha 184:
if not produto_data.get('producao_hoje'):
    # Usar o mesmo fallback do workspace_api
    hoje = agora_brasil().date()
    producao = SaldoEstoque.calcular_producao_periodo(produto.cod_produto, hoje, hoje)
    produto_data['producao_hoje'] = float(producao)
```

### Opção 2: Corrigir ServicoEstoqueSimples para incluir todas as fontes
```python
# Em calcular_entradas_previstas, adicionar:
# Buscar também movimentações tipo PRODUÇÃO
movimentacoes_producao = db.session.query(
    MovimentacaoEstoque.data_movimentacao,
    func.sum(MovimentacaoEstoque.qtd_movimentacao).label('total')
).filter(
    MovimentacaoEstoque.tipo_movimentacao.in_(['PRODUÇÃO', 'ENTRADA']),
    MovimentacaoEstoque.data_movimentacao.between(data_inicio, data_fim)
).group_by(MovimentacaoEstoque.data_movimentacao)
```

### Opção 3: Sempre usar o fallback para D0
```python
# Em workspace_utils.py, modificar obter_producao_hoje:
if projecao and len(projecao) > 0:
    hoje_dados = projecao[0]
    # Para D0, sempre usar fallback para garantir consistência
    if hoje_dados.get('dia') == 0:
        hoje = agora_brasil().date()
        return float(SaldoEstoque.calcular_producao_periodo(cod_produto, hoje, hoje))
```

---

## 📋 TESTE PARA CONFIRMAR

### 1. No Console do Navegador:
```javascript
// Antes do carregamento assíncrono (logo após abrir workspace)
console.log('INICIAL:', workspace.dadosProdutos.get('4310071'));

// Depois de 1 segundo (após carregamento assíncrono)
setTimeout(() => {
    console.log('APÓS ASYNC:', workspace.dadosProdutos.get('4310071'));
}, 1000);
```

### 2. Debug no Backend:
```python
# Adicionar logs em workspace_utils.py:
logger.info(f"obter_producao_hoje({cod_produto}): resumo_estoque={bool(resumo_estoque)}")
logger.info(f"Usando fallback: {not resumo_estoque}")
logger.info(f"Retornando producao_hoje: {producao}")
```

---

## 🎯 CONCLUSÃO

**O problema está confirmado**: A diferença entre o fallback (que funciona) e a projeção (que retorna 0) causa a inconsistência observada. O valor aparece inicialmente porque usa o fallback, mas é zerado quando a projeção (que não tem os mesmos dados) sobrescreve o valor.