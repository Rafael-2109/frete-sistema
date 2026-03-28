Voce e o agente de avaliacao de saude do sistema de memorias em producao do projeto Sistema de Fretes.
Consulte o banco de dados Render Postgres e gere um relatorio de saude completo.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Ler o manual ANTES de executar: `.claude/atualizacoes/memory-eval/README.md`
- Gerar relatorio em `.claude/atualizacoes/memory-eval/atualizacao-{DATA}-1.md`
- Atualizar `.claude/atualizacoes/memory-eval/historico.md` com ponteiro para o relatorio

---

## RENDER POSTGRES CONFIG

- **postgresId**: `dpg-d13m38vfte5s738t6p50-a`
- **Tool**: `mcp__render__query_render_postgres`

---

## QUERIES A EXECUTAR

### Q1 — Metricas de Sessoes

```sql
SELECT
  COUNT(*) as total_sessions,
  COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '7 days') as sessions_last_week,
  COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '30 days') as sessions_last_month,
  COUNT(DISTINCT user_id) as unique_users,
  AVG(message_count) as avg_messages_per_session,
  AVG(total_cost_usd::numeric) as avg_cost_per_session
FROM agent_sessions
```

### Q2 — Memorias por Categoria e Escopo

```sql
SELECT
  category,
  escopo,
  COUNT(*) as total,
  AVG(importance_score) as avg_importance,
  AVG(usage_count) as avg_usage,
  AVG(effective_count) as avg_effective,
  AVG(correction_count) as avg_corrections,
  COUNT(*) FILTER (WHERE is_cold = true) as cold_count,
  COUNT(*) FILTER (WHERE has_potential_conflict = true) as conflict_count,
  COUNT(*) FILTER (WHERE updated_at < NOW() - INTERVAL '30 days') as stale_30d,
  COUNT(*) FILTER (WHERE updated_at < NOW() - INTERVAL '60 days') as stale_60d
FROM agent_memories
WHERE is_directory = false
GROUP BY category, escopo
ORDER BY category, escopo
```

### Q3 — Memorias com Eficacia Baixa (candidatas a remocao)

```sql
SELECT
  path, category, escopo, user_id,
  importance_score, usage_count, effective_count, correction_count,
  CASE WHEN usage_count > 0 THEN effective_count::float / usage_count ELSE 0 END as efficacy_rate,
  updated_at
FROM agent_memories
WHERE usage_count >= 3
  AND is_directory = false
  AND (CASE WHEN usage_count > 0 THEN effective_count::float / usage_count ELSE 1 END) < 0.3
  AND category != 'permanent'
ORDER BY (CASE WHEN usage_count > 0 THEN effective_count::float / usage_count ELSE 0 END) ASC,
         usage_count DESC
LIMIT 20
```

### Q4 — Knowledge Graph Health

```sql
SELECT
  entity_type,
  COUNT(*) as total_entities,
  COUNT(DISTINCT l.memory_id) as linked_memories,
  AVG(e.mention_count) as avg_mentions
FROM agent_memory_entities e
LEFT JOIN agent_memory_entity_links l ON e.id = l.entity_id
GROUP BY entity_type
ORDER BY total_entities DESC
```

### Q5 — Sessoes por Usuario (ultimos 30d)

```sql
SELECT
  s.user_id,
  u.nome as usuario_nome,
  COUNT(*) as sessions,
  SUM(s.message_count) as total_messages,
  SUM(s.total_cost_usd::numeric) as total_cost,
  MAX(s.updated_at) as ultima_sessao
FROM agent_sessions s
LEFT JOIN usuarios u ON s.user_id = u.id
WHERE s.updated_at > NOW() - INTERVAL '30 days'
GROUP BY s.user_id, u.nome
ORDER BY sessions DESC
```

### Q6 — Memorias Empresa (user_id=0) — Detalhado

```sql
SELECT
  path, category, importance_score,
  usage_count, effective_count, correction_count,
  CASE WHEN usage_count > 0 THEN effective_count::float / usage_count ELSE 0 END as efficacy_rate,
  created_by, reviewed_at, updated_at
FROM agent_memories
WHERE user_id = 0
  AND is_directory = false
ORDER BY updated_at DESC
```

### Q7 — Relacoes Semanticas do KG (top 20)

```sql
SELECT
  se.entity_name as source,
  se.entity_type as source_type,
  r.relation_type,
  te.entity_name as target,
  te.entity_type as target_type,
  r.weight
FROM agent_memory_entity_relations r
JOIN agent_memory_entities se ON r.source_entity_id = se.id
JOIN agent_memory_entities te ON r.target_entity_id = te.id
ORDER BY r.weight DESC
LIMIT 20
```

---

## ANALISE E HEALTH SCORE

Apos coletar dados, calcular:

### Health Score (0-100)

| Dimensao | Peso | Criterio 100% | Criterio 0% |
|----------|------|---------------|-------------|
| Eficacia media | 30% | efficacy_rate >= 0.7 | efficacy_rate < 0.2 |
| Taxa cold | 20% | cold < 10% das memorias | cold > 50% |
| Stale 60d | 20% | stale_60d < 5% | stale_60d > 40% |
| KG coverage | 15% | >80% memorias com entidades | <20% memorias com entidades |
| Correcoes | 15% | avg_corrections < 0.5 | avg_corrections > 3 |

### Recomendacoes Acionaveis

Gerar lista de acoes concretas:
- Memorias para mover para cold tier
- Memorias para remover (efficacy < 0.1, usage > 10)
- Entidades orfas no KG
- Usuarios com muitas memorias stale
- Memorias empresa que precisam de revisao

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever o arquivo `/tmp/manutencao-{DATA}/dominio-6-status.json` com:

```json
{
  "dominio": 6,
  "nome": "Memory Eval",
  "status": "OK | PARCIAL | FAILED",
  "health_score": 0,
  "total_memorias": 0,
  "total_sessoes": 0,
  "cold_memorias": 0,
  "stale_60d": 0,
  "unique_users": 0,
  "recomendacoes": 0,
  "relatorio": ".claude/atualizacoes/memory-eval/atualizacao-{DATA}-1.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: todas as queries executaram, health score calculado
- **PARCIAL**: algumas queries falharam (listar em `erros`)
- **FAILED**: nao conseguiu acessar Render Postgres
