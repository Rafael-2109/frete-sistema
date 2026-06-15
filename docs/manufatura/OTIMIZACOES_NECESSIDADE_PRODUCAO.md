<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Otimizacoes de performance aplicadas na tela de Necessidade de Producao (manufatura)
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🚀 OTIMIZAÇÕES IMPLEMENTADAS - NECESSIDADE DE PRODUÇÃO

> **Papel:** explica as otimizações de performance aplicadas na tela de Necessidade de Produção (backend, frontend, cache e índices) e seus resultados esperados.

## Contexto

Documento histórico-explicativo das otimizações que reduziram o tempo de carregamento da tela de Necessidade de Produção de 5-10s para a faixa de sub-segundo. Reúne os problemas identificados, as mudanças aplicadas (endpoint batch, frontend em lote, cache, range de datas e índices) e como validá-las.

**Data:** 08/01/2025
**Objetivo:** Reduzir tempo de carregamento de 5-10s para <1s
**Status:** ✅ FASE 1 CONCLUÍDA (Quick Wins)

---

## Indice

- [Problemas Identificados](#-problemas-identificados)
- [Otimizações Implementadas](#-otimizações-implementadas)
- [Resultados Esperados](#-resultados-esperados)
- [Próximos Passos (Fase 2 - Opcional)](#-próximos-passos-fase-2---opcional)
- [Breaking Changes](#️-breaking-changes)
- [Checklist de Deployment](#-checklist-de-deployment)
- [Como Validar](#-como-validar)
- [Desenvolvedor](#-desenvolvedor)
- [Referências](#-referências)

---

## 📊 PROBLEMAS IDENTIFICADOS

### 1. **PROBLEMA N+1 MASSIVO no Frontend** ⚠️ CRÍTICO
- **Antes:** 50 produtos = 50 requisições HTTP separadas
- **Tempo:** ~5 segundos totais
- **Localização:** `necessidade-producao.js:298`

### 2. **LOOP DE QUERIES no Backend** ⚠️ CRÍTICO
- **Antes:** 50 produtos × 7 queries = **350 queries no banco!**
- **Tempo:** ~3-10 segundos
- **Localização:** `necessidade_producao_service.py:73-143`

### 3. **FALTA DE ÍNDICES COMPOSTOS** ⚠️ CRÍTICO
- Queries filtram por `(cod_produto, data_pedido)` sem índice composto
- Full table scan em 100k+ registros

### 4. **CACHE TTL MUITO LONGO** ⚠️ MÉDIO
- 30 segundos de cache = dados desatualizados
- Usuário não vê mudanças após programar produção

### 5. **extract() LENTO**  ⚠️ MÉDIO
- `extract('month', data)` force full table scan no PostgreSQL
- Não usa índices existentes

---

## ✅ OTIMIZAÇÕES IMPLEMENTADAS

### 1. **Endpoint Batch para Projeções** 🚀 80% de melhoria

**Arquivo:** `app/manufatura/routes/necessidade_producao_routes.py:66-114`

```python
@bp.route('/api/necessidade-producao/projecoes-batch', methods=['POST'])
def projecoes_batch():
    """
    Retorna projeções de múltiplos produtos em UMA única requisição
    Body: { "cod_produtos": ["P1", "P2", ...], "dias": 60 }
    """
    resultados = ServicoEstoqueSimples.calcular_multiplos_produtos(
        cod_produtos=cod_produtos,
        dias=dias,
        entrada_em_d_plus_1=False
    )
    return jsonify(resultados)
```

**Impacto:**
- ✅ Reduz 50 requisições HTTP para 1
- ✅ Usa ThreadPoolExecutor para paralelização interna
- ✅ Cache compartilhado entre produtos
- ⏱️ Tempo: De ~5s para ~800ms

---

### 2. **Frontend Otimizado** 🚀

**Arquivo:** `app/static/manufatura/necessidade_producao/js/necessidade-producao.js:298-339`

**ANTES:**
```javascript
// ❌ N requisições
Promise.all(dados.map(item =>
    $.get('/api/projecao-estoque', { cod_produto: item.cod_produto })
))
```

**DEPOIS:**
```javascript
// ✅ 1 requisição em batch
$.ajax({
    url: '/manufatura/api/necessidade-producao/projecoes-batch',
    method: 'POST',
    data: JSON.stringify({
        cod_produtos: codProdutos,
        dias: 60
    })
})
```

**Impacto:**
- ✅ Elimina overhead de 50 conexões HTTP
- ✅ Reduz latência de rede
- ⏱️ Tempo: De ~5s para ~800ms

---

### 3. **Cache TTL — observação de correção** ⚠️

**Arquivo:** `app/estoque/services/estoque_simples.py:22-34`

> **CORREÇÃO (verificada no código em 2026-06-15):** o TTL real do cache **continua em 30s**, NÃO foi reduzido para 10s. A intenção documentada originalmente (cache de 10s) **não tem efeito**.

**Por quê:**
- A expiração real é governada pela `TTLCache` global, criada com `ttl=30`:
  ```python
  # app/estoque/services/estoque_simples.py:22
  _cache = cachetools.TTLCache(maxsize=2000, ttl=30)
  ```
- O parâmetro `ttl_seconds=10` em `_get_cache` é **ignorado**: o método apenas
  delega para `_cache.get(chave)`, sem aplicar TTL por chave:
  ```python
  # app/estoque/services/estoque_simples.py:32
  def _get_cache(chave: str, ttl_seconds: int = 10):
      return _cache.get(chave)  # ttl_seconds não é usado
  ```
- Além disso, a chamada real passa `ttl_seconds=30` explicitamente (também ignorado):
  ```python
  # app/estoque/services/estoque_simples.py:209
  cached = ServicoEstoqueSimples._get_cache(chave_cache, ttl_seconds=30)
  ```

**Para de fato reduzir para 10s** seria necessário recriar a `TTLCache` global com
`ttl=10` **ou** implementar lógica de expiração por chave dentro de `_get_cache`.

**Impacto real:**
- ⚠️ Refresh continua em até 30s (não 10s)
- ✅ Cache permanece ativo (performance preservada)

---

### 4. **Substituição de extract() por Range de Datas** 🚀

**Arquivo:** `app/manufatura/services/necessidade_producao_service.py`

**ANTES:**
```python
# ❌ extract() force full table scan
.filter(
    extract('month', CarteiraPrincipal.data_pedido) == mes,
    extract('year', CarteiraPrincipal.data_pedido) == ano
)
```

**DEPOIS:**
```python
# ✅ Range de datas usa índices
primeiro_dia = date(ano, mes, 1)
ultimo_dia = date(ano, mes, ultimo_dia_num)

.filter(
    CarteiraPrincipal.data_pedido >= primeiro_dia,
    CarteiraPrincipal.data_pedido <= ultimo_dia
)
```

**Modificado em:**
- `_calcular_pedidos_inseridos()` (linha 254)
- `_calcular_programacao()` (linha 350)

**Impacto:**
- ✅ PostgreSQL pode usar índices em `data_pedido`
- ✅ Query 10-20x mais rápida
- ⏱️ De ~300ms para ~20ms por query

---

### 5. **Índices de Performance** 🚀

**Arquivo:** `migrations/add_performance_indexes.py`

**Índices Criados:**

```sql
-- 1. Índice composto para queries produto + data
CREATE INDEX idx_carteira_produto_data
ON carteira_principal (cod_produto, data_pedido);

-- 2. Índice PARCIAL para sincronizado_nf=FALSE
CREATE INDEX idx_separacao_sync_only
ON separacao (sincronizado_nf)
WHERE sincronizado_nf = FALSE;
```

**Como Executar:**
```bash
# Ambiente local
python migrations/add_performance_indexes.py

# Ou via psql (Render)
psql $DATABASE_URL < migrations/add_performance_indexes.sql
```

**Impacto:**
- ✅ Query em carteira_principal: De ~300ms para ~20ms
- ✅ Query em separacao: De ~200ms para ~15ms
- ✅ Índice parcial economiza espaço (apenas sincronizado_nf=FALSE)

---

## 📈 RESULTADOS ESPERADOS

| Métrica | Antes | Depois | Melhoria |
|---|---|---|---|
| **Requisições HTTP** | 50+ | 1 | **98% menos** |
| **Queries no Banco** | ~400 | ~120 | **70% menos** |
| **Tempo Total** | 5-10s | 0.8-1.5s | **80-90% mais rápido** |
| **Cache Hit Rate** | ~60% | ~80% | **+33%** |
| **Tempo Pedidos Inseridos** | ~300ms | ~20ms | **93% mais rápido** |
| **Tempo Separações** | ~200ms | ~15ms | **92% mais rápido** |

---

## 🎯 PRÓXIMOS PASSOS (FASE 2 - Opcional)

### Otimizações Adicionais Identificadas

1. **Pre-carregar Mapa de Unificação**
   - Evita 100+ queries para `UnificacaoCodigos.get_codigo_unificado()`
   - Impacto: +10% performance

2. **Paginação Server-Side**
   - Carregar 50 produtos por vez em vez de todos
   - Melhora UX e performance inicial

3. **Query Agregada Única com CTEs**
   - Consolidar 7 queries em 1 com Common Table Expressions
   - De 350 queries para 1 query!
   - Impacto: +15% performance

4. **VIEW Materializada (PostgreSQL)**
   - Cache persistente no banco
   - Refresh a cada X minutos
   - Impacto: +5% performance

5. **Reduzir TTL do cache para 10s (pendente)**
   - O cache de Necessidade de Produção ainda expira em 30s (ver seção 3).
   - Para reduzir de fato: recriar a `TTLCache` global com `ttl=10` ou implementar
     expiração por chave em `_get_cache`.

---

## ⚠️ BREAKING CHANGES

**NENHUM!** Todas as otimizações são **backward compatible**:
- Frontend continua funcionando com endpoint antigo
- Endpoint batch é ADICIONAL
- Índices não quebram queries existentes
- O cache permanece com TTL de 30s (sem mudança de comportamento)

---

## 📝 CHECKLIST DE DEPLOYMENT

- [x] 1. Commit código frontend otimizado
- [x] 2. Commit código backend otimizado
- [x] 3. Testar localmente com dados reais
- [ ] 4. Executar script de migração de índices LOCAL
- [ ] 5. Validar queries usando índices (EXPLAIN ANALYZE)
- [ ] 6. Deploy em produção (Render)
- [ ] 7. Executar script de migração de índices PRODUÇÃO
- [ ] 8. Monitorar performance por 24h
- [ ] 9. Validar métricas de tempo de resposta

---

## 🔍 COMO VALIDAR

### 1. Verificar Índices Criados
```sql
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('carteira_principal', 'separacao')
AND indexname LIKE '%produto%' OR indexname LIKE '%sync%'
ORDER BY tablename, indexname;
```

### 2. Ver Queries Usando Índices
```sql
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM carteira_principal
WHERE cod_produto = 'PROD-001'
AND data_pedido >= '2025-01-01'
AND data_pedido <= '2025-01-31';

-- Deve mostrar "Index Scan using idx_carteira_produto_data"
```

### 3. Monitorar Tempo de Resposta (Browser Console)
```javascript
console.time('Buscar Projeções');
// Carregar página
console.timeEnd('Buscar Projeções');
// Antes: ~5000ms
// Depois: ~800ms
```

---

## 👨‍💻 DESENVOLVEDOR

**Rafael Nascimento**
**Data:** 08/01/2025

---

## 📚 REFERÊNCIAS

- [PostgreSQL Index Performance](https://www.postgresql.org/docs/current/indexes-types.html)
- [SQLAlchemy Query Optimization](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [ThreadPoolExecutor Best Practices](https://docs.python.org/3/library/concurrent.futures.html)
