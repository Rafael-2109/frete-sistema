# Manual: Avaliacao de Saude do Sistema de Memorias

**Dominio**: Memory Eval | **Fonte**: Render Postgres (`dpg-d13m38vfte5s738t6p50-a`)

---

## Objetivo

Avaliar a saude do sistema de memorias em producao, gerando relatorio com:
- Metricas de sessoes e uso por usuario
- Distribuicao de memorias por categoria e escopo
- Identificacao de memorias com eficacia baixa (candidatas a remocao)
- Saude do Knowledge Graph
- Health score consolidado (0-100)
- Recomendacoes acionaveis

---

## Tabelas Consultadas

| Tabela | Colunas-chave | Uso |
|--------|---------------|-----|
| `agent_sessions` | user_id, message_count, total_cost_usd, model, updated_at | Metricas de sessoes |
| `agent_memories` | path, category, escopo, importance_score, usage_count, effective_count, correction_count, is_cold, updated_at | Saude das memorias |
| `agent_memory_entities` | entity_type, entity_name, mention_count | KG nodes |
| `agent_memory_entity_links` | entity_id, memory_id, relation_type | KG edges (entity-memory) |
| `agent_memory_entity_relations` | source_entity_id, target_entity_id, relation_type, weight | KG edges (entity-entity) |

---

## Procedimento

### Fase 1: Coleta via MCP

Executar 7 queries SQL via `mcp__render__query_render_postgres`:
1. **Q1**: Metricas gerais de sessoes (total, last_week, unique_users)
2. **Q2**: Memorias por categoria/escopo (avg importance, usage, effective, cold, stale)
3. **Q3**: Memorias com eficacia baixa (efficacy_rate < 0.3, usage >= 3)
4. **Q4**: Knowledge Graph health (entities por tipo, linked memories)
5. **Q5**: Sessoes por usuario (ultimos 30d, custo, mensagens)
6. **Q6**: Memorias empresa detalhado (user_id=0)
7. **Q7**: Relacoes semanticas do KG (top 20 por weight)

### Fase 2: Calcular Health Score

| Dimensao | Peso | 100% | 0% |
|----------|------|------|----|
| Eficacia media | 30% | efficacy >= 0.7 | efficacy < 0.2 |
| Taxa cold | 20% | cold < 10% | cold > 50% |
| Stale 60d | 20% | stale < 5% | stale > 40% |
| KG coverage | 15% | >80% memorias linkadas | <20% linkadas |
| Correcoes | 15% | avg_corrections < 0.5 | avg_corrections > 3 |

### Fase 3: Gerar Recomendacoes

Acoes concretas baseadas nos dados:
- Memorias para mover para cold tier
- Memorias para remover (efficacy < 0.1, usage > 10)
- Entidades orfas no KG
- Usuarios com muitas memorias stale
- Memorias empresa que precisam de revisao (reviewed_at NULL ou > 30d)

### Fase 4: Relatorio

Criar `atualizacao-YYYY-MM-DD-N.md` com:

```markdown
# Atualizacao Memory Eval — YYYY-MM-DD-N

**Data**: YYYY-MM-DD
**Health Score**: X/100

## Metricas de Sessoes
- Total: X, ultima semana: Y, usuarios unicos: Z

## Memorias por Categoria
| Categoria | Total | Avg Importance | Avg Efficacy | Cold | Stale 60d |
|-----------|-------|----------------|--------------|------|-----------|
| ... | ... | ... | ... | ... | ... |

## Top 20 Memorias Baixa Eficacia
(tabela com path, category, efficacy_rate, usage_count)

## Knowledge Graph
- Entidades: X, Relacoes: Y, Coverage: Z%

## Recomendacoes
1. ...
2. ...
```

Atualizar `historico.md` com ponteiro para o novo relatorio.

---

## Checklist Pre-Commit

- [ ] Todas as 7 queries executaram com sucesso
- [ ] Health score calculado
- [ ] Recomendacoes geradas (minimo 3)
- [ ] Relatorio gerado
- [ ] `historico.md` atualizado

---

## Limites e Cuidados

1. **Read-only**: Este dominio NUNCA modifica dados no Render Postgres — apenas consulta
2. **Timeout de queries**: Se uma query demorar > 30s, abortar e marcar como PARCIAL
3. **Dados sensiveis**: NAO incluir conteudo de memorias no relatorio — apenas paths e metricas
