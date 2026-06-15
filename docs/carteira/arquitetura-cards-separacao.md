<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Mapeamento das funcoes JS de renderizacao/atualizacao/criacao/remocao de cards de separacao na carteira agrupada
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🎯 MAPEAMENTO PRECISO: FUNÇÕES DE CARDS DE SEPARAÇÃO

> **Papel:** Mapear, por arquivo e linha, as funcoes JavaScript que renderizam, atualizam, criam e removem cards de separacao na carteira agrupada, e os problemas de duplicacao entre as superficies (workspace x view compacta).

## Contexto

Os cards de separacao da carteira sao renderizados por multiplas funcoes espalhadas em `lote-manager.js`, `carteira-agrupada.js`, `workspace-montagem.js` e `modal-separacoes.js`. Este documento e o inventario verificado dessas funcoes (com linha de definicao) e a analise dos pontos de duplicacao de logica e de estrutura de dados entre as superficies.

## Indice

- [Inventario completo](#-inventário-completo)
- [Problemas identificados por função](#-problemas-identificados-por-função)
- [Análise função por função](#-análise-função-por-função)
- [Ordem de análise sugerida](#-ordem-de-análise-sugerida)

---

## 📋 **INVENTÁRIO COMPLETO**

### **1. FUNÇÕES DE RENDERIZAÇÃO**

#### **A. LoteManager (lote-manager.js)**
```javascript
// Linha 61: definição de renderizarCardLote(loteId) — linha 51 é chamada interna em criarLote()
renderizarCardLote(loteId) → renderizarCardUniversal(loteData)

// Linha 109: Template principal do card
renderizarCardUniversal(loteData) → HTML completo do card

// Linha 353: Renderiza lista de produtos dentro do card  
renderizarProdutosUniversal(produtos, loteId, podeRemover)
```

#### **B. CarteiraAgrupada (carteira-agrupada.js)**
```javascript
// Linha 1134: Renderiza tabela compacta de separações
renderizarSeparacoesCompactas(separacoesData) → HTML da tabela

// Linha 1201: Renderiza linha individual da tabela compacta
renderizarLinhaSeparacaoCompacta(item) → HTML de 1 linha <tr>

// Linha 964: Renderiza do cache
renderizarSeparacaoDoCache(numPedido) → chama renderizarSeparacoesCompactas
```

#### **C. WorkspaceMontagem (workspace-montagem.js)**
```javascript
// Linha 171: Renderiza container de todas as separações
renderizarTodasSeparacoes(numPedido) → cria múltiplos cards

// Linha 206: Usa LoteManager para criar cada card
loteCard.innerHTML = this.loteManager.renderizarCardUniversal(loteData)
```

#### **D. ModalSeparacoes (modal-separacoes.js)**
```javascript
// Linha 70: Renderiza separações no modal
renderizarSeparacoes() → HTML do modal

// Linha 148: Renderiza separação individual no modal
renderizarSeparacao(separacao, numero) → HTML de 1 separação
```

---

### **2. FUNÇÕES DE ATUALIZAÇÃO**

#### **A. LoteManager (lote-manager.js)**
```javascript
// Linha 694: Re-renderiza card completo
atualizarCardLote(loteId) {
    cardElement.outerHTML = this.renderizarCardLote(loteId);
}
```

#### **B. WorkspaceMontagem (workspace-montagem.js)**
```javascript
// Linha 1681: Atualiza células específicas da view compacta
atualizarViewCompactaDireto(loteId, expedicao, agendamento, protocolo, confirmado) {
    // Atualiza células individuais sem re-renderizar
}
```

#### **C. CarteiraAgrupada (carteira-agrupada.js)**
```javascript
// Linha 2165: Atualiza dados na memória
atualizarSeparacaoCompacta(loteId, dadosAtualizados) {
    // Atualiza múltiplas estruturas de dados
}
```

---

### **3. FUNÇÕES DE CRIAÇÃO**

#### **A. LoteManager (lote-manager.js)**
```javascript
// Linha 27: Cria novo lote
criarNovoLote(numPedido) → criarLote(numPedido, loteId)

// Linha 32: Cria lote específico
criarLote(numPedido, loteId) → cria card HTML
```

#### **B. WorkspaceMontagem (workspace-montagem.js)**
```javascript
// Linha 362: Delega para LoteManager
criarNovoLote(numPedido) → this.loteManager.criarNovoLote(numPedido)
```

---

### **4. FUNÇÕES DE REMOÇÃO**

#### **A. CarteiraAgrupada (carteira-agrupada.js)**
```javascript
// Linha 1463: Remove separação compacta
excluirSeparacao(loteId) → delega para separacaoManager
```

#### **B. WorkspaceMontagem (workspace-montagem.js)**
```javascript
// Linha 714: Remove lote
excluirLote(loteId) → delega para separacaoManager
```

---

## 🚨 **PROBLEMAS IDENTIFICADOS POR FUNÇÃO**

### **PROBLEMA 1: renderizarCardUniversal vs renderizarLinhaSeparacaoCompacta**
- **Mesmo lote** aparece como **card no workspace** e **linha na view compacta**
- **Estruturas de dados diferentes** (loteData vs item)
- **Templates diferentes** (card vs linha de tabela)

### **PROBLEMA 2: atualizarCardLote vs atualizarViewCompactaDireto**
- **atualizarCardLote**: Re-renderiza card **completo** (workspace)
- **atualizarViewCompactaDireto**: Atualiza **células específicas** (view compacta)
- **Mesmo lote** precisa ser atualizado em **2 lugares diferentes**

### **PROBLEMA 3: Múltiplas estruturas de dados**
```javascript
// Workspace usa:
loteData.lote_id, loteData.totais.valor

// View compacta usa:  
item.loteId, item.valor

// API retorna:
separacao.separacao_lote_id, separacao.valor_total
```

---

## 🎯 **ANÁLISE FUNÇÃO POR FUNÇÃO**

### **FUNÇÃO 1: LoteManager.renderizarCardUniversal()**
**Arquivo**: `lote-manager.js` (linha 109)
**Uso**: Cards do workspace
**Status**: ✅ **MANTER** - É a implementação mais completa
**Problema**: Recebe dados em formato inconsistente

### **FUNÇÃO 2: CarteiraAgrupada.renderizarLinhaSeparacaoCompacta()**  
**Arquivo**: `carteira-agrupada.js` (linha 1201)
**Uso**: Linhas da tabela compacta
**Status**: ⚠️ **ANALISAR** - Pode ser simplificada
**Problema**: Template muito específico, difícil de manter

### **FUNÇÃO 3: LoteManager.atualizarCardLote()**
**Arquivo**: `lote-manager.js` (linha 694)  
**Uso**: Atualiza cards do workspace
**Status**: ✅ **MANTER** - Funciona bem
**Problema**: Só atualiza workspace, não view compacta

### **FUNÇÃO 4: WorkspaceMontagem.atualizarViewCompactaDireto()**
**Arquivo**: `workspace-montagem.js` (linha 1681)
**Uso**: Atualiza view compacta
**Status**: ⚠️ **ANALISAR** - Muito complexa, muitos seletores
**Problema**: Lógica duplicada para encontrar elementos

---

## 🎯 **ORDEM DE ANÁLISE SUGERIDA**

**Começar pela mais problemática:**

### **FUNÇÃO PARA ANALISAR PRIMEIRO: `atualizarViewCompactaDireto()`**

**Por que essa primeiro?**
- ✅ É a **mais complexa** (80+ linhas)
- ✅ Tem **múltiplos seletores** (muitos pontos de falha)
- ✅ É chamada **frequentemente** 
- ✅ **Não quebra nada** se simplificada

A análise dessa função deve cobrir: o que ela faz exatamente, onde é chamada, como simplificar sem quebrar e o teste específico para validar.
