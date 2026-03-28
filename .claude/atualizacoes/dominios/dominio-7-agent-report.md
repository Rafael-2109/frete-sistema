Voce e o agente de inteligencia do sistema de agente web do projeto Sistema de Fretes.
Consulte o banco de dados Render Postgres, analise sessoes/memorias/ferramentas, e gere um
relatorio prescritivo com recomendacoes para melhoria de tools e skills.

DATA: usar output de `date +%Y-%m-%d`

---

## INSTRUCOES OBRIGATORIAS

- Este dominio e READ-ONLY no Render Postgres (apenas SELECTs)
- A ESCRITA do relatorio no banco e feita via POST ao endpoint da API web
- Gerar relatorio em `.claude/atualizacoes/agent-reports/report-{DATA}.md`
- Atualizar `.claude/atualizacoes/agent-reports/historico.md` com ponteiro para o relatorio
- Escrever status JSON em `/tmp/manutencao-{DATA}/dominio-7-status.json`

---

## RENDER POSTGRES CONFIG

- **postgresId**: `dpg-d13m38vfte5s738t6p50-a`
- **Tool**: `mcp__render__query_render_postgres`

---

## RENDER API CONFIG (para persistencia do relatorio)

- **URL**: obtida de `RENDER_EXTERNAL_URL` ou `https://sistema-fretes.onrender.com`
- **Endpoint**: `POST /agente/api/intelligence-report`
- **Header**: `X-Cron-Key: <valor de CRON_API_KEY env var>`
- **Tool para POST**: usar `WebFetch` com method POST, ou `Bash` com curl

Se CRON_API_KEY nao estiver definida localmente, PULAR a persistencia no banco
e registrar em `erros` do status.json. O relatorio markdown no repo ainda sera gerado.

---

## QUERIES A EXECUTAR

### Q1 — Distribuicao de Uso de Tools (ultimos 30d)

```sql
WITH tool_calls AS (
    SELECT
        jsonb_array_elements_text(msg->'tools_used') as tool_name
    FROM agent_sessions s,
         jsonb_array_elements(s.data->'messages') as msg
    WHERE msg->>'role' = 'assistant'
      AND msg->'tools_used' IS NOT NULL
      AND jsonb_array_length(msg->'tools_used') > 0
      AND s.updated_at > NOW() - INTERVAL '30 days'
),
tool_calls_7d AS (
    SELECT
        jsonb_array_elements_text(msg->'tools_used') as tool_name
    FROM agent_sessions s,
         jsonb_array_elements(s.data->'messages') as msg
    WHERE msg->>'role' = 'assistant'
      AND msg->'tools_used' IS NOT NULL
      AND jsonb_array_length(msg->'tools_used') > 0
      AND s.updated_at > NOW() - INTERVAL '7 days'
)
SELECT
    t30.tool_name,
    t30.calls_30d,
    COALESCE(t7.calls_7d, 0) as calls_7d,
    CASE
        WHEN COALESCE(t7.calls_7d, 0) > (t30.calls_30d * 7.0 / 30 * 1.2) THEN 'up'
        WHEN COALESCE(t7.calls_7d, 0) < (t30.calls_30d * 7.0 / 30 * 0.8) THEN 'down'
        ELSE 'stable'
    END as trend
FROM (
    SELECT tool_name, COUNT(*) as calls_30d
    FROM tool_calls
    GROUP BY tool_name
) t30
LEFT JOIN (
    SELECT tool_name, COUNT(*) as calls_7d
    FROM tool_calls_7d
    GROUP BY tool_name
) t7 ON t30.tool_name = t7.tool_name
ORDER BY t30.calls_30d DESC
LIMIT 25
```

### Q2 — Sinais de Qualidade de Sessoes (ultimos 30d)

```sql
SELECT
    CASE
        WHEN message_count < 3 THEN 'ultra_short'
        WHEN message_count >= 3 AND NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(data->'messages') m
            WHERE m->>'role' = 'assistant' AND m->'tools_used' IS NOT NULL
              AND jsonb_array_length(m->'tools_used') > 0
        ) THEN 'no_tools'
        WHEN message_count >= 3 AND EXISTS (
            SELECT 1 FROM jsonb_array_elements(data->'messages') m
            WHERE m->>'role' = 'assistant' AND m->'tools_used' IS NOT NULL
              AND jsonb_array_length(m->'tools_used') > 0
        ) AND total_cost_usd <= 2.00 THEN 'resolved'
        WHEN total_cost_usd > 2.00 THEN 'high_cost'
        ELSE 'other'
    END as quality_bucket,
    COUNT(*) as session_count,
    ROUND(AVG(message_count)) as avg_messages,
    ROUND(AVG(total_cost_usd::numeric), 4) as avg_cost
FROM agent_sessions
WHERE updated_at > NOW() - INTERVAL '30 days'
GROUP BY quality_bucket
ORDER BY session_count DESC
```

**Nota sobre buckets**: `resolved` avaliado ANTES de `high_cost` para que sessoes com tools usadas e custo <= $2.00 sejam contadas como resolucao. Threshold de $2.00 reflete custo medio de sessoes operacionais com Opus. Sessoes > $2.00 sem tools continuam como `other`.

### Q3 — Mensagens Iniciais Repetidas (proxy friccao, ultimos 30d)

```sql
WITH first_messages AS (
    SELECT
        LOWER(TRIM(
            (data->'messages'->0->>'content')
        )) as first_msg,
        session_id,
        user_id
    FROM agent_sessions
    WHERE updated_at > NOW() - INTERVAL '30 days'
      AND data->'messages' IS NOT NULL
      AND jsonb_array_length(data->'messages') > 0
      AND (data->'messages'->0->>'role') = 'user'
)
SELECT
    first_msg,
    COUNT(*) as repetitions,
    COUNT(DISTINCT user_id) as unique_users
FROM first_messages
WHERE first_msg IS NOT NULL
  AND LENGTH(first_msg) > 10
GROUP BY first_msg
HAVING COUNT(*) >= 3
ORDER BY repetitions DESC
LIMIT 15
```

### Q4 — Memorias com Correcoes Frequentes (baixa eficacia)

```sql
SELECT
    path, category, escopo, user_id,
    importance_score, usage_count, effective_count, correction_count,
    CASE WHEN usage_count > 0
         THEN ROUND(effective_count::numeric / usage_count, 2)
         ELSE 0 END as efficacy_rate,
    updated_at
FROM agent_memories
WHERE correction_count >= 2
  AND is_directory = false
ORDER BY correction_count DESC, usage_count DESC
LIMIT 20
```

### Q5 — Topicos de Sessoes vs Tools (gap analysis, ultimos 30d)

```sql
WITH topics AS (
    SELECT
        jsonb_array_elements_text(summary->'topicos_abordados') as topic
    FROM agent_sessions
    WHERE updated_at > NOW() - INTERVAL '30 days'
      AND summary IS NOT NULL
      AND summary->'topicos_abordados' IS NOT NULL
),
tool_usage AS (
    SELECT DISTINCT
        jsonb_array_elements_text(msg->'tools_used') as tool_name
    FROM agent_sessions s,
         jsonb_array_elements(s.data->'messages') as msg
    WHERE msg->>'role' = 'assistant'
      AND msg->'tools_used' IS NOT NULL
      AND s.updated_at > NOW() - INTERVAL '30 days'
)
SELECT
    t.topic,
    COUNT(*) as frequency,
    EXISTS(
        SELECT 1 FROM tool_usage tu
        WHERE tu.tool_name ILIKE '%' || t.topic || '%'
    ) as has_matching_tool
FROM topics t
GROUP BY t.topic
ORDER BY frequency DESC
LIMIT 20
```

### Q6 — Sessoes Mais Caras (top 10, ultimos 30d)

```sql
SELECT
    session_id,
    user_id,
    model,
    message_count,
    total_cost_usd,
    summary->>'resumo_geral' as resumo,
    updated_at
FROM agent_sessions
WHERE updated_at > NOW() - INTERVAL '30 days'
  AND total_cost_usd > 0
ORDER BY total_cost_usd DESC
LIMIT 10
```

### Q7 — Tendencias Semana a Semana (4 semanas)

```sql
SELECT
    DATE_TRUNC('week', updated_at)::date as semana,
    COUNT(*) as sessoes,
    COUNT(DISTINCT user_id) as usuarios,
    ROUND(SUM(total_cost_usd::numeric), 4) as custo_total,
    ROUND(AVG(message_count)) as avg_mensagens,
    ROUND(
        COUNT(*) FILTER (
            WHERE message_count >= 4
        )::numeric / NULLIF(COUNT(*), 0) * 100, 1
    ) as resolution_rate_approx
FROM agent_sessions
WHERE updated_at > NOW() - INTERVAL '28 days'
GROUP BY DATE_TRUNC('week', updated_at)
ORDER BY semana DESC
```

### Q8 — Backlog Anterior (relatorio mais recente)

```sql
SELECT
    report_date,
    backlog_json,
    health_score,
    recommendation_count
FROM agent_intelligence_reports
ORDER BY report_date DESC
LIMIT 1
```

NOTA: Se a tabela `agent_intelligence_reports` nao existir (primeira execucao),
esta query vai falhar. Nesse caso, tratar como backlog vazio e continuar.

---

## ANALISE E GERACAO DO RELATORIO

Apos coletar dados das 8 queries, executar a analise:

### 1. Metricas Agregadas

De Q2 e Q7, calcular:
- Total de sessoes (30d)
- Taxa de resolucao (resolved / total)
- Custo total e medio
- Usuarios ativos
- Trend (comparar semana atual vs anterior de Q7)

### 2. Efetividade de Ferramentas

De Q1, classificar tools em categorias usando este mapeamento:

| Prefixo tool | Categoria |
|--------------|-----------|
| `mcp__sql__*` | Consulta SQL |
| `mcp__memory__*` | Memoria do Agente |
| `mcp__schema__*` | Catalogo de Dados |
| `mcp__sessions__*` | Busca de Sessoes |
| `mcp__render__*` | Monitoramento Render |
| `mcp__browser__*` | Operacao SSW |
| `Bash`, `Read`, `Write`, `Edit` | Operacao de Arquivos |
| `Skill` | Execucao de Skill |
| `AskUserQuestion` | Interacao com Usuario |
| `Task` | Subagente |

Identificar:
- Tools mais usadas (top 5)
- Tools com trend DOWN (possivel problema)
- Tools NUNCA usadas mas registradas (consultar lista acima)

### 3. Lacunas de Skills (Skill Gaps)

De Q5, identificar topicos com `has_matching_tool = false` e `frequency >= 3`.
Esses sao topicos que usuarios perguntam mas nao ha ferramenta dedicada.

Para cada gap, recomendar uma acao concreta:
- "Criar MCP tool para X" ou "Criar skill para Y"
- Indicar arquivos relevantes (ex: `app/agente/tools/` para nova tool)

### 4. Pontos de Friccao

De Q3 (mensagens repetidas):
- Mensagens repetidas 3+ vezes indicam que o agente nao resolveu bem
- Para cada pattern, sugerir melhoria (melhor prompt, nova skill, cache)

De Q2 (sessoes sem tools):
- Se `no_tools` > 20% do total: agente nao esta entendendo solicitacoes
- Recomendar revisao do system_prompt ou criacao de novas tools

### 5. Saude de Memorias

De Q4 (correcoes frequentes):
- Memorias com correction_count >= 3 e efficacy_rate < 0.3: candidatas a remocao
- Memorias empresa (user_id=0) com correcoes: CRITICO (afetam todos os usuarios)

### 6. Recomendacoes Prescritivas

Gerar lista de recomendacoes acionaveis. Cada uma com:
- `id`: formato `REC-{DATA}-NNN` (ex: `REC-2026-03-28-001`)
- `severity`: critical | warning | info
- `title`: titulo conciso
- `description`: o que foi detectado e por que importa
- `affected_files`: lista de caminhos de arquivos afetados
- `suggested_action`: acao concreta que o desenvolvedor deve tomar
- `weeks_open`: 1 (novo) ou N (do backlog)

Criterios de severity:
- **critical**: resolution_rate < 60%, memoria empresa com 5+ correcoes, friccao alta (>50)
- **warning**: tool com trend DOWN, skill gap com 5+ mencoes, custo subindo >50%
- **info**: oportunidades de melhoria, tools nunca usadas, patterns informativos

### 7. Merge de Backlog

De Q8, carregar backlog anterior (se existir):
- Incrementar `weeks_open` de cada item
- Auto-escalate: itens com 4+ semanas abertos sobem para severity `critical`
- Remover itens que a analise atual detectou como resolvidos (metrica melhorou)
- Adicionar novos itens desta analise
- O merge final vai no campo `backlog_json` do POST

---

## FORMATO DO RELATORIO MARKDOWN

Escrever em `.claude/atualizacoes/agent-reports/report-{DATA}.md`:

```markdown
---
date: {DATA}
health_score: {score calculado}
friction_score: {score de Q2/Q3}
sessions_analyzed: {total de Q2}
recommendation_count: {total de recomendacoes}
trend: improving | stable | declining
---

# Agent Intelligence Report — {DATA}

## Metricas ({periodo})
| Metrica | Valor | Trend |
|---------|-------|-------|
| Sessoes | N | +X% |
| Resolucao | N% | +Xpp |
| Custo total | $N.NN | +X% |
| Usuarios ativos | N | = |

<!-- SECTION:TOOL_EFFECTIVENESS -->
## Efetividade de Ferramentas
| Tool | Chamadas (30d) | Chamadas (7d) | Categoria | Trend |
|------|----------------|---------------|-----------|-------|
(dados de Q1 com categorias mapeadas)
<!-- /SECTION:TOOL_EFFECTIVENESS -->

<!-- SECTION:SKILL_GAPS -->
## Lacunas de Skills
| Topico | Frequencia | Tool existente? | Recomendacao |
|--------|------------|-----------------|--------------|
(dados de Q5 filtrados)
<!-- /SECTION:SKILL_GAPS -->

<!-- SECTION:FRICTION -->
## Pontos de Friccao
| Pattern (mensagem repetida) | Repeticoes | Usuarios | Sugestao |
|-----------------------------|------------|----------|----------|
(dados de Q3)

### Qualidade de Sessoes
| Bucket | Sessoes | % | Avg Msgs | Avg Custo |
|--------|---------|---|----------|-----------|
(dados de Q2)
<!-- /SECTION:FRICTION -->

<!-- SECTION:MEMORY_HEALTH -->
## Saude de Memorias
| Path | Categoria | Correcoes | Eficacia | Acao |
|------|-----------|-----------|----------|------|
(dados de Q4, top 10)
<!-- /SECTION:MEMORY_HEALTH -->

<!-- SECTION:COST_OUTLIERS -->
## Sessoes Mais Caras
| Sessao | Modelo | Msgs | Custo | Resumo |
|--------|--------|------|-------|--------|
(dados de Q6, top 5)
<!-- /SECTION:COST_OUTLIERS -->

<!-- SECTION:TRENDS -->
## Tendencias (4 semanas)
| Semana | Sessoes | Usuarios | Custo | Resolution Rate |
|--------|---------|----------|-------|-----------------|
(dados de Q7)
<!-- /SECTION:TRENDS -->

<!-- SECTION:RECOMMENDATIONS -->
## Recomendacoes Acionaveis
### [{SEVERITY}] {ID}: {titulo}
- **Impacto**: descricao do impacto
- **Arquivos**: `path/to/file1`, `path/to/file2`
- **Acao sugerida**: descricao da acao concreta
- **Semanas aberto**: N
(repetir para cada recomendacao)
<!-- /SECTION:RECOMMENDATIONS -->

<!-- SECTION:BACKLOG -->
## Backlog Acumulado
| ID | Severity | Titulo | Semanas | Status |
|----|----------|--------|---------|--------|
(itens do backlog mergeado)
<!-- /SECTION:BACKLOG -->
```

---

## PERSISTENCIA NO BANCO

Apos gerar o relatorio markdown, tentar persistir no banco via POST:

```bash
CRON_KEY="${CRON_API_KEY}"
RENDER_URL="${RENDER_EXTERNAL_URL:-https://sistema-fretes.onrender.com}"

curl -s -X POST "$RENDER_URL/agente/api/intelligence-report" \
  -H "Content-Type: application/json" \
  -H "X-Cron-Key: $CRON_KEY" \
  -d '{
    "report_date": "{DATA}",
    "health_score": {score},
    "friction_score": {friction},
    "recommendation_count": {count},
    "sessions_analyzed": {total},
    "report_json": {json_completo},
    "report_markdown": "{markdown_escapado}",
    "backlog_json": {backlog}
  }'
```

Se falhar (CRON_API_KEY ausente, servidor indisponivel, etc.):
- Registrar erro no status.json
- O relatorio markdown no repo AINDA e gerado normalmente
- Marcar status como PARCIAL

---

## CONTRATO DE OUTPUT

AO CONCLUIR, escrever o arquivo `/tmp/manutencao-{DATA}/dominio-7-status.json` com:

```json
{
  "dominio": 7,
  "nome": "Agent Intelligence Report",
  "status": "OK | PARCIAL | FAILED",
  "health_score": 0,
  "friction_score": 0,
  "sessions_analyzed": 0,
  "recommendation_count": 0,
  "backlog_items": 0,
  "persisted_to_db": true,
  "trend": "improving | stable | declining",
  "relatorio": ".claude/atualizacoes/agent-reports/report-{DATA}.md",
  "resumo": "Descricao curta do que foi feito",
  "erros": []
}
```

Status:
- **OK**: todas as queries executaram, relatorio gerado, persistido no banco
- **PARCIAL**: queries OK, relatorio gerado, mas persistencia no banco falhou
- **FAILED**: nao conseguiu acessar Render Postgres ou erro critico na analise
