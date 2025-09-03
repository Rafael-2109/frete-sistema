# 🔍 RASTREAMENTO COMPLETO DO CAMPO "PROD. HOJE"

## 📋 Resumo Executivo
Este documento rastreia o fluxo completo do campo de produção desde a origem no banco de dados até a renderização na coluna "Prod. Hoje" do workspace e no cardex.

**STATUS ATUAL: ❌ QUEBRADO**
- **Problema identificado**: Incompatibilidade de nomes de campos entre backend e utils
- **Campo esperado**: `producao_programada` 
- **Campo retornado**: `entrada`

---

## 🔄 FLUXO COMPLETO DE DADOS

### 1️⃣ ORIGEM: Banco de Dados

#### 1.1 Tabelas Envolvidas
```sql
-- programacao_producao: Armazena produção programada
CREATE TABLE programacao_producao (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50),
    data_programacao DATE,
    qtd_programada NUMERIC(15,3),
    -- outros campos...
);

-- movimentacao_estoque: Armazena entradas/saídas
CREATE TABLE movimentacao_estoque (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50),
    tipo_movimentacao VARCHAR(20), -- 'ENTRADA' ou 'SAIDA'
    data_movimentacao DATE,
    qtd_movimentacao NUMERIC(15,3),
    -- outros campos...
);
```

### 2️⃣ BACKEND: Cálculo da Produção

#### 2.1 ServicoEstoqueSimples (`app/estoque/services/estoque_simples.py`)

**Método: `calcular_entradas_previstas`** (linhas 86-119)
```python
@staticmethod
def calcular_entradas_previstas(cod_produto: str, data_inicio: date, data_fim: date) -> Dict[date, float]:
    """
    Calcula todas as entradas previstas (produção, devoluções, etc).
    Retorna dicionário {data: quantidade}
    """
    # IMPORTANTE: Aqui busca da programacao_producao
    producao_query = db.session.query(
        ProgramacaoProducao.data_programacao,
        func.sum(ProgramacaoProducao.qtd_programada).label('total')
    ).filter(
        ProgramacaoProducao.cod_produto.in_(codigos_relacionados),
        ProgramacaoProducao.data_programacao.between(data_inicio, data_fim),
        ProgramacaoProducao.ativo == True
    ).group_by(ProgramacaoProducao.data_programacao)
    
    # Resultado combinado no dicionário 'entradas'
    for data, qtd in producao_query:
        entradas[data] = entradas.get(data, 0) + float(qtd)
    
    return entradas
```

**Método: `get_projecao_completa`** (linhas 148-234)
```python
# Linha 160-162: Busca entradas (produção)
entradas = ServicoEstoqueSimples.calcular_entradas_previstas(
    cod_produto, hoje, data_fim
)

# Linha 174: Obtém entrada do dia
entrada_dia = entradas.get(data, 0)

# Linha 201: Adiciona à projeção com nome 'entrada' ⚠️
projecao.append({
    'dia': dia,
    'data': data.isoformat(),
    'saldo_inicial': saldo_inicial,
    'entrada': entrada_dia,  # ⚠️ AQUI: Campo chamado 'entrada'
    'saida': saida_dia,
    'saldo': saldo_sem_producao,
    'saldo_final': saldo_final
})
```

### 3️⃣ API: Transmissão dos Dados

#### 3.1 Endpoint `/workspace-estoque` (`app/carteira/routes/estoque_api.py`)

**Linha 156**: Busca projeção completa
```python
projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=28)
```

**Linhas 172-179**: Cria resumo_estoque
```python
resumo_estoque = {
    'estoque_inicial': projecao_completa['estoque_atual'],
    'estoque_atual': projecao_completa['estoque_atual'],
    'menor_estoque_d7': projecao_completa.get('menor_estoque_d7'),
    'dia_ruptura': projecao_completa.get('dia_ruptura'),
    'projecao_29_dias': projecao_completa.get('projecao', []),  # ⚠️ Contém 'entrada'
    'status_ruptura': 'CRÍTICO' if projecao_completa.get('dia_ruptura') else 'OK'
}
```

**Linha 184**: Processa dados com workspace_utils
```python
produto_data = processar_dados_workspace_produto(produto, resumo_estoque)
```

### 4️⃣ UTILS: Processamento dos Dados

#### 4.1 workspace_utils.py

**Função `obter_producao_hoje`** (linhas 101-134)
```python
def obter_producao_hoje(cod_produto, resumo_estoque):
    """
    Obtém quantidade programada para produzir hoje
    """
    try:
        if resumo_estoque:
            projecao = resumo_estoque.get('projecao_29_dias') or resumo_estoque.get('projecao', [])
            if projecao and len(projecao) > 0:
                hoje_dados = projecao[0]  # D0 (hoje)
                if isinstance(hoje_dados, dict):
                    # ❌ PROBLEMA AQUI: Busca 'producao_programada' mas backend envia 'entrada'
                    entrada = hoje_dados.get('entrada', 0)
                    if entrada:
                        return float(entrada)
                    # Fallback para formato antigo
                    return float(hoje_dados.get('producao_programada', 0))  # ❌ Não existe!
```

**Função `processar_dados_workspace_produto`** (linha 272)
```python
# Linha 272: Chama obter_producao_hoje
producao_hoje = obter_producao_hoje(produto.cod_produto, resumo_estoque)

# Linha 291: Retorna no produto_data
return {
    # ...
    'producao_hoje': float(producao_hoje),
    # ...
}
```

### 5️⃣ FRONTEND: Renderização

#### 5.1 workspace-montagem.js

**Linha 95**: Armazena producao_hoje
```javascript
produtoCompleto = {
    // ...
    producao_hoje: produto.producao_hoje || 0,
    // ...
};
```

**Linha 163**: Carrega dados assíncronos
```javascript
this.carregarDadosEstoqueAssincrono(numPedido);
```

**Função `carregarDadosEstoqueAssincrono`** (atualiza producao_hoje)
```javascript
// Atualiza célula de Prod. Hoje
const prodHojeCell = row.cells[8];
if (prodHojeCell) {
    const producao = Math.floor(produto.producao_hoje || 0);
    const badgeClass = producao > 0 ? 'bg-info' : 'bg-secondary';
    prodHojeCell.innerHTML = `
        <span class="badge ${badgeClass}" title="Quantidade programada para produzir hoje">
            ${producao.toLocaleString('pt-BR')}
        </span>
    `;
}
```

#### 5.2 workspace-tabela.js

**Linha 83**: Define producaoHoje
```javascript
const producaoHoje = produto.producao_hoje || 0;
```

**Linhas 160-165**: Renderiza coluna Prod. Hoje
```javascript
<td class="text-center">
    <span class="badge ${this.getProducaoHojeBadgeClass(producaoHoje)}"
          title="Quantidade programada para produzir hoje">
        ${this.formatarQuantidade(producaoHoje)}
    </span>
</td>
```

### 6️⃣ CARDEX: Renderização no Modal

#### 6.1 cardex_api.py

**Linha 30**: Busca projeção
```python
projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)
```

**Linha 61**: Mapeia 'entrada' para 'producao'
```python
producao = float(dia_proj.get('entrada', 0))  # 'entrada' no backend = 'producao' no frontend
```

**Linha 113**: Envia como 'producao' para frontend
```javascript
cardex_list.append({
    // ...
    'producao': producao,  # Mapeado de 'entrada'
    // ...
})
```

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### PROBLEMA 1: Incompatibilidade de Nomes de Campos
- **Backend (ServicoEstoqueSimples)**: Retorna `'entrada'`
- **Utils (workspace_utils)**: Espera `'producao_programada'`
- **Status**: ❌ PARCIALMENTE CORRIGIDO (linha 117-121 de workspace_utils.py)

### PROBLEMA 2: Cardex Funcionando por Mapeamento Manual
- **cardex_api.py**: Mapeia corretamente `entrada` → `producao` (linha 61)
- **Status**: ✅ FUNCIONANDO

### PROBLEMA 3: Workspace Inicial sem Dados
- **workspace_api.py**: Passa `resumo_estoque = None` (linha 83)
- **Consequência**: `producao_hoje` inicial sempre 0
- **Status**: ❌ QUEBRADO

---

## 🔄 VALIDAÇÃO REVERSA DO CAMINHO

### Do Frontend para o Backend:

1. **workspace-montagem.js** renderiza `producao_hoje` → ✅ OK
2. **workspace-montagem.js** recebe de `/workspace-estoque` → ✅ OK
3. **estoque_api.py** chama `processar_dados_workspace_produto` → ✅ OK
4. **workspace_utils.py** chama `obter_producao_hoje` → ⚠️ PROBLEMA
5. **workspace_utils.py** busca `producao_programada` → ❌ NÃO EXISTE
6. **workspace_utils.py** busca `entrada` como fallback → ✅ CORRIGIDO
7. **ServicoEstoqueSimples** retorna `entrada` → ✅ OK
8. **ProgramacaoProducao** tem `qtd_programada` → ✅ OK

---

## 🔧 CORREÇÕES NECESSÁRIAS

### ✅ Correção 1: workspace_utils.py (JÁ APLICADA)
```python
# Linha 117-121: Priorizar 'entrada'
entrada = hoje_dados.get('entrada', 0)
if entrada:
    return float(entrada)
return float(hoje_dados.get('producao_programada', 0))  # Fallback
```

### ❌ Correção 2: converter_projecao_para_cardex (PENDENTE)
```python
# Linha 327: Deve priorizar 'entrada'
producao = float(dia_info.get('entrada', 0) or dia_info.get('producao_programada', 0))
```

### ❓ Possível Problema 3: Verificar se dados estão no banco
- Verificar se `programacao_producao` tem dados para hoje
- Verificar se `movimentacao_estoque` tem entradas tipo 'PRODUÇÃO'

---

## 📊 TESTE DE VALIDAÇÃO

### SQL para verificar dados de produção:
```sql
-- Verificar produção programada para hoje
SELECT cod_produto, data_programacao, qtd_programada
FROM programacao_producao
WHERE data_programacao = CURRENT_DATE
  AND ativo = true;

-- Verificar movimentações de entrada para hoje
SELECT cod_produto, tipo_movimentacao, data_movimentacao, qtd_movimentacao
FROM movimentacao_estoque
WHERE data_movimentacao = CURRENT_DATE
  AND tipo_movimentacao IN ('ENTRADA', 'PRODUÇÃO')
  AND ativo = true;
```

### JavaScript Console para debug:
```javascript
// No console do navegador, com workspace aberto:
workspace.dadosProdutos.forEach((produto, cod) => {
    console.log(`${cod}: producao_hoje = ${produto.producao_hoje}`);
});
```

---

## 🎯 CONCLUSÃO

O fluxo está **PARCIALMENTE QUEBRADO** devido a:

1. ✅ **Cardex**: Funcionando (mapeia corretamente)
2. ⚠️ **Workspace Assíncrono**: Parcialmente corrigido (workspace_utils.py atualizado)
3. ❌ **Workspace Inicial**: Quebrado (resumo_estoque = None)
4. ❌ **converter_projecao_para_cardex**: Ainda precisa correção

**Próximos passos**:
1. Aplicar correção em converter_projecao_para_cardex
2. Verificar se há dados de produção no banco para hoje
3. Testar novamente após correções