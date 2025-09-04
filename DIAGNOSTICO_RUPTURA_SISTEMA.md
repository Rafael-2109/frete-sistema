# 🔍 DIAGNÓSTICO COMPLETO - SISTEMA DE RUPTURA DE ESTOQUE

## 📊 ANÁLISE DA SITUAÇÃO ATUAL

### 🗂️ ESTRUTURA DE ARQUIVOS ATUAL

```
app/
├── carteira/
│   └── routes/
│       ├── ruptura_api.py          [513 linhas] - API síncrona com cache Redis
│       └── ruptura_api_async.py     [213 linhas] - API para enfileirar jobs
│
├── portal/
│   └── workers/
│       └── ruptura_jobs.py          [301 linhas] - Worker que processa lotes
│
├── static/carteira/js/
│   ├── ruptura-estoque.js          [1061 linhas] - Sistema completo com fila
│   ├── ruptura-estoque-async.js     [487 linhas] - Processamento em lote SEM workers
│   └── ruptura-estoque-integrado.js [471 linhas] - Híbrido workers + polling
│
└── templates/carteira/
    ├── js/
    │   └── ruptura-estoque.js      [1061 linhas] - DUPLICADO do static
    └── agrupados_balanceado.html   - Carrega 2 scripts simultaneamente!
```

## 🔴 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. REDUNDÂNCIAS GRAVES

#### 📁 Arquivos Duplicados
- **DUPLICAÇÃO COMPLETA**: 
  - `static/carteira/js/ruptura-estoque.js`
  - `templates/carteira/js/ruptura-estoque.js`
  - **1061 linhas idênticas** carregadas 2x no HTML!

#### 🔄 Implementações Redundantes
- **3 arquivos JS** fazendo a mesma coisa de formas diferentes
- **2 APIs Python** com lógica quase idêntica
- **Múltiplos sistemas de fila** competindo

### 2. CONFLITOS NO DOM

```javascript
// ruptura-estoque.js - Linha 283
btnContainer.innerHTML = `
    <button class="btn btn-sm btn-outline-info btn-analisar-ruptura"...

// ruptura-estoque-integrado.js - Linha 220  
const btnAnalise = document.createElement('button');
btnAnalise.className = 'btn btn-sm btn-outline-primary btn-ruptura-manual-novo';

// ruptura-estoque-async.js - Linha 64
resultContainer.innerHTML = `
    <span class="badge bg-secondary">
```

**RESULTADO**: 3 scripts tentando manipular a mesma célula `.coluna-entrega-obs`!

### 3. FLUXO INCOERENTE

#### Fluxo Atual (Quebrado):
```
1. agrupados_balanceado.html carrega 2 scripts
2. ruptura-estoque.js adiciona botões e inicia análise automática
3. ruptura-estoque-integrado.js TAMBÉM adiciona botões
4. Usuário clica no botão
5. Não sabe qual handler será executado
6. Workers processam mas resultados vão para Redis
7. Frontend faz polling a cada 2s (ineficiente)
8. Cache de 30s pode mostrar dados obsoletos
```

### 4. PROBLEMAS DE PERFORMANCE

- **Polling a cada 2 segundos** sobrecarrega servidor
- **Cache Redis de 30s** mostra dados desatualizados
- **Múltiplas requisições** para o mesmo pedido
- **Sem comunicação real-time** (WebSocket/SSE)

## ❌ ARQUIVOS PARA REMOVER

1. `/app/templates/carteira/js/ruptura-estoque.js` - Duplicado
2. `/app/static/carteira/js/ruptura-estoque-async.js` - Implementação incompleta
3. `/app/static/carteira/js/ruptura-estoque.js` - Será substituído

## ⚠️ IMPACTO NO USUÁRIO

- **Botões duplicados** ou comportamento inconsistente
- **Dados desatualizados** por causa do cache
- **Performance ruim** com polling constante
- **Interface travando** durante análises

## 📋 REQUISITOS DO CLIENTE

1. ✅ Manter funcionalidade do botão na coluna "Entrega/Obs"
2. ✅ Processar via 2 workers em paralelo
3. ✅ Enfileirar análises para não sobrecarregar
4. ✅ Atualizar a cada 20 pedidos processados
5. ✅ Atualizar apenas botões/dados sem recarregar página
6. ✅ Polling a cada 2 segundos para verificar resultados
7. ✅ SEM CACHE para ter informação real-time

## 🎯 CONCLUSÃO

O sistema atual tem **múltiplas implementações conflitantes** tentando resolver o mesmo problema. Precisamos:

1. **UNIFICAR** em uma única implementação
2. **REMOVER** arquivos redundantes
3. **IMPLEMENTAR** comunicação eficiente com workers
4. **GARANTIR** dados sempre atualizados

Próximo arquivo: `SOLUCAO_RUPTURA_WORKERS.md` com a arquitetura proposta.