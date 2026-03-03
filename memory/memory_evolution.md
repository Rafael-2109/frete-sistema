# Memory System Evolution — Detalhes

## T3-3: Knowledge Graph Simplificado (2026-03-02)

### Resumo
Extrai entidades de memórias e cria links em grafo. Na busca, além de similaridade vetorial,
encontra memórias conectadas por entidades compartilhadas (multi-hop retrieval).

### 3 Tabelas Novas
- `agent_memory_entities` — nós do grafo (entidades canônicas, UNIQUE user_id+tipo+nome)
- `agent_memory_entity_links` — entidade ↔ memória (FK CASCADE em ambas)
- `agent_memory_entity_relations` — entidade ↔ entidade (co_occurs, atrasa_para, etc.)

### 3 Layers de Extração
- **Layer 1 (Regex, ~2ms)**: UF, pedido (VCD/VCB), CNPJ raiz, valor R$
- **Layer 2 (Voyage, ~300ms)**: transportadora (carrier_embeddings), produto (product_search),
  cliente/fornecedor (entity_search) — reutiliza infra existente, threshold 0.70
- **Layer 3 (Haiku, 0ms extra)**: entidades + relações semânticas — piggyback no prompt
  contextual (T3-1), max_tokens 150→250, parse estruturado com fallback

### Arquivos Criados
- `app/agente/services/knowledge_graph_service.py` — extract, upsert, query, cleanup, stats
- `scripts/migrations/criar_tabelas_knowledge_graph.py` + `.sql`

### Arquivos Modificados
- `app/agente/models.py` — +3 models (AgentMemoryEntity, EntityLink, EntityRelation)
- `app/agente/tools/memory_mcp_tool.py` — prompt T3-3, _generate_memory_context retorna tupla,
  _embed_memory_best_effort retorna (entities, relations), integração KG em save/update/delete
- `app/agente/sdk/client.py` — Tier 2b graph retrieval em _load_user_memories_for_context()
- `app/embeddings/config.py` — +flag MEMORY_KNOWLEDGE_GRAPH (default true)
- `app/agente/services/insights_service.py` — +knowledge_graph stats em get_memory_metrics()

### Feature Flag
`MEMORY_KNOWLEDGE_GRAPH` (default `true`) — controla write path (extração) e read path (retrieval).
Quando `false`, comportamento idêntico ao pré-T3-3.

### Read Path — Tier 2b
```
_load_user_memories_for_context()
  |-- TIER 1: protegidas (user.xml, preferences.xml)
  |-- TIER 2a: busca_memorias_semantica (existente)
  |-- TIER 2b [NOVO]: query_graph_memories()
  |   |-- Extrai entidades do prompt (Layer 1 + Layer 2)
  |   |-- SQL: entity_names → entity_ids → memory_ids
  |   |-- Filtra: exclui semantic_results
  |   |-- Composite scoring com similarity=0.5 (proxy)
  |-- MERGE: dedup por memory_id
```

### Delete Path
FK CASCADE cuida automaticamente. Cleanup explícito em delete_memory como defense-in-depth.
GC de entidades órfãs via `cleanup_orphan_entities()` (mention_count tracking).
