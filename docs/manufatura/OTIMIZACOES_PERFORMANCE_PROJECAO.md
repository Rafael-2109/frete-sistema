<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Estrategia de cache em memoria do ServicoProjecaoEstoque (projecao de estoque de componentes/intermediarios) — motivacao, pontos criticos e limitacoes
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Otimizações de Performance - Projeção de Estoque

> **Papel:** Explicar a estratégia de cache em memória do `ServicoProjecaoEstoque` — por que existe, onde atua e quais limitações tem.

## Contexto

Documento que registra o sistema de cache em memória adotado em `app/manufatura/services/projecao_estoque_service.py` para resolver a degradação de performance da projeção de estoque após a introdução do consumo recursivo de produtos intermediários. Cobre motivação, os três caches, gestão de ciclo de vida e limitações conhecidas.

**Data**: 04/11/2025
**Status**: ✅ IMPLEMENTADO
**Ganho estimado**: 40-50x redução de queries no banco de dados

## Indice

- [Problema Original](#-problema-original)
- [Solução Implementada: Sistema de Cache em Memória](#-solução-implementada-sistema-de-cache-em-memória)
- [Gestão do Cache](#-gestão-do-cache)
- [Impacto Esperado](#-impacto-esperado)
- [Pontos Críticos de Cache](#-pontos-críticos-de-cache)
- [Testes Recomendados](#-testes-recomendados)
- [Checklist de Validação](#-checklist-de-validação)
- [Observações Importantes](#️-observações-importantes)
- [Conclusão](#-conclusão)

---

## 🚨 PROBLEMA ORIGINAL

Ao implementar o consumo recursivo de produtos intermediários, a performance da projeção de estoque caiu drasticamente:

- **Tempo de carregamento**: ~50 segundos (inaceitável)
- **Causa**: Queries redundantes ao banco de dados
  - Verificações repetidas se produto é intermediário
  - Buscas upstream duplicadas
  - Consultas à BOM para o mesmo produto várias vezes

---

## ✅ SOLUÇÃO IMPLEMENTADA: Sistema de Cache em Memória

### 1. **Cache de Programações Upstream**

**Arquivo**: [app/manufatura/services/projecao_estoque_service.py:45](app/manufatura/services/projecao_estoque_service.py#L45)

```python
self._cache_programacoes_upstream = {}
# Estrutura: {(cod_produto, data_inicio, data_fim): [(ProgramacaoProducao, fator), ...]}
```

**Uso**: [linha 933-935](app/manufatura/services/projecao_estoque_service.py#L933)

**Benefício**:
- Evita buscar programações upstream repetidamente para o mesmo produto
- Componentes que compartilham intermediários reutilizam resultado
- Exemplo: 100 componentes → SALMOURA → AZEITONA
  - Sem cache: 100 buscas upstream
  - Com cache: 1 busca upstream ✅

---

### 2. **Cache de Produtos Intermediários**

**Arquivo**: [app/manufatura/services/projecao_estoque_service.py:46](app/manufatura/services/projecao_estoque_service.py#L46)

```python
self._cache_eh_intermediario = {}
# Estrutura: {cod_produto: bool}
```

**Uso**: [linha 1124-1125](app/manufatura/services/projecao_estoque_service.py#L1124)

**Benefício**:
- Método `_eh_produto_intermediario()` faz 3 queries:
  1. CadastroPalletizacao (produto_produzido?)
  2. ListaMateriais (tem BOM?)
  3. ListaMateriais (é usado como componente?)
- Chamado centenas de vezes durante recursão
- Exemplo: SALMOURA verificada 50 vezes
  - Sem cache: 150 queries (3 × 50)
  - Com cache: 3 queries ✅

---

### 3. **Cache de BOMs Upstream**

**Arquivo**: [app/manufatura/services/projecao_estoque_service.py:47](app/manufatura/services/projecao_estoque_service.py#L47)

```python
self._cache_boms_upstream = {}
# Estrutura: {cod_produto: [ListaMateriais]}
```

**Uso**: [linha 967-973](app/manufatura/services/projecao_estoque_service.py#L967)

**Benefício**:
- Query `ListaMateriais.filter(cod_produto_componente=X)` só executa uma vez por produto
- Reutilizado em todas chamadas recursivas
- Exemplo: SALMOURA consultada 20 vezes durante projeção
  - Sem cache: 20 queries
  - Com cache: 1 query ✅

---

## 🔄 GESTÃO DO CACHE

### Limpeza Automática

**Método**: `_limpar_cache()` ([linha 49-53](app/manufatura/services/projecao_estoque_service.py#L49))

**Chamado em**:
- Início de cada projeção completa ([linha 63](app/manufatura/services/projecao_estoque_service.py#L63))

**Por quê**:
- Garante dados frescos a cada execução
- Evita cache desatualizado entre projeções
- Libera memória ao finalizar

---

## 📊 IMPACTO ESPERADO

### Cenário Real: 100 Componentes Comprados

**Estrutura hierárquica comum**:
```
100 Componentes finais (ACIDO, BENZOATO, SAL, AGUA, etc.)
    ↓
10 Produtos intermediários (SALMOURA, TEMPERO, BASE, etc.)
    ↓
20 Produtos finais programados (PIZZA, AZEITONA, EMPADA, etc.)
```

### Queries SEM Cache:

| Operação | Queries por Item | Total (100 itens) |
|----------|------------------|-------------------|
| Verificar se é intermediário | 3 | 300 |
| Buscar programações upstream | 5 | 500 |
| Buscar BOMs upstream | 3 | 300 |
| **TOTAL** | **11** | **1.100** |

### Queries COM Cache:

| Operação | Queries (únicos) | Total |
|----------|------------------|-------|
| Verificar se é intermediário | 3 | 30 |
| Buscar programações upstream | 5 | 50 |
| Buscar BOMs upstream | 3 | 30 |
| **TOTAL** | **11** | **110** |

### Ganho: **10x menos queries!**

---

## 🎯 PONTOS CRÍTICOS DE CACHE

### 1. Cache Condicional em `_buscar_programacoes_upstream()`

**Código**: [linha 933-935](app/manufatura/services/projecao_estoque_service.py#L933)

```python
# ✅ Somente cacheia quando fator_multiplicador = 1.0 (raiz da busca)
if fator_multiplicador == 1.0 and cache_key in self._cache_programacoes_upstream:
    return [(prog, fator * fator_multiplicador) for prog, fator in self._cache_programacoes_upstream[cache_key]]
```

**Razão**:
- Fator muda dependendo do caminho na hierarquia
- Ex: ACIDO via SALMOURA (fator 0.005) vs ACIDO direto (fator 1.0)
- Somente resultado "puro" (fator=1.0) é cacheado
- Fatores customizados são calculados dinamicamente

---

### 2. Cópia de Lista ao Retornar Cache

**Código**: [linha 935](app/manufatura/services/projecao_estoque_service.py#L935)

```python
# ✅ Retorna CÓPIA para não afetar cache original
return [(prog, fator * fator_multiplicador) for prog, fator in self._cache_programacoes_upstream[cache_key]]
```

**Razão**:
- Evita que modificações acidentais corrompam o cache
- List comprehension cria nova lista

---

### 3. Cache por Período de Datas

**Chave**: `(cod_produto, data_inicio, data_fim)`

**Razão**:
- Programações variam por período
- Cache separado para diferentes intervalos
- Ex: SALMOURA em Nov vs Dez pode ter programações diferentes

---

## 🧪 TESTES RECOMENDADOS

### Teste 1: Performance Comparativa

```python
import time

# Sem cache (desabilitar temporariamente)
inicio = time.time()
resultado_sem_cache = service.projetar_componentes_60_dias()
tempo_sem_cache = time.time() - inicio

# Com cache
service._limpar_cache()  # Resetar
inicio = time.time()
resultado_com_cache = service.projetar_componentes_60_dias()
tempo_com_cache = time.time() - inicio

ganho = tempo_sem_cache / tempo_com_cache
print(f"Ganho de performance: {ganho:.1f}x mais rápido")
```

### Teste 2: Contagem de Queries

```python
from flask_sqlalchemy import get_debug_queries

# Habilitar debug no config.py:
# SQLALCHEMY_RECORD_QUERIES = True

resultado = service.projetar_componentes_60_dias()
queries = get_debug_queries()

print(f"Total de queries executadas: {len(queries)}")
print(f"Tempo total em queries: {sum(q.duration for q in queries):.2f}s")
```

---

## 📋 CHECKLIST DE VALIDAÇÃO

- [x] Cache declarado no `__init__`
- [x] Método `_limpar_cache()` implementado
- [x] Limpeza chamada no início da projeção
- [x] `_eh_produto_intermediario()` verifica cache antes de query
- [x] `_buscar_programacoes_upstream()` usa cache condicional
- [x] `_buscar_programacoes_upstream()` cacheia BOMs upstream
- [x] Retorno de cache usa cópia (não referência)
- [ ] Teste de performance executado
- [ ] Ganho de performance validado (>5x esperado)

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

### Limitações do Cache Atual:

1. **Cache em memória**: Não persiste entre requisições HTTP
   - Cada request cria nova instância de ServicoProjecaoEstoque
   - Cache válido apenas dentro da mesma execução

2. **Não compartilhado entre usuários**
   - Cada usuário tem seu próprio cache
   - Não há Redis ou Memcached

3. **Tamanho não controlado**
   - Cache pode crescer com muitos produtos
   - Em sistemas com milhares de produtos, considerar limite

### Possíveis Melhorias Futuras:

1. **Cache persistente (Redis)**:
   - TTL de 5 minutos
   - Compartilhado entre requisições
   - Invalidação quando BOM ou programação muda

2. **Cache LRU (Least Recently Used)**:
   ```python
   from functools import lru_cache
   ```
   - Limita tamanho do cache
   - Remove entradas menos usadas

3. **Pré-carregamento em background**:
   - Calcular cache durante madrugada
   - Usuário sempre vê resultado instantâneo

---

## 🎯 CONCLUSÃO

O sistema de cache implementado resolve o problema de performance **sem** adicionar complexidade externa (Redis, workers, etc.).

**Ganho esperado**: De 50s para ~5s (10x mais rápido)

**Próximo passo**: Executar testes de carga e validar métricas reais (carga real e métricas de produção ainda pendentes).
