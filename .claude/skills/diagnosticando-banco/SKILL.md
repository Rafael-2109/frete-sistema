---
name: diagnosticando-banco
description: >-
  Esta skill deve ser usada quando o usuario pergunta "como esta o banco?",
  "indices nao usados", "queries lentas", "cache hit rate", "conexoes ativas",
  "vacuum", "bloat", "recomendacao de indice", "otimizar query", "EXPLAIN",
  "indice hipotetico", "por que essa query e lenta?", "saude do banco",
  ou precisa de diagnostico de saude, performance e otimizacao do PostgreSQL.
  Tambem usar quando o usuario quer analisar plano de execucao de uma query,
  receber sugestoes de indices para melhorar performance, ou investigar
  problemas de lentidao no banco.
  - Conexoes: "quantas conexoes?", "conexoes idle", "pool"
  - Vacuum: "precisa de vacuum?", "dead tuples", "tabelas inchadas"
  - Sequences: "sequences proximas do limite?", "risco de overflow INTEGER"
  - Tamanho: "maiores tabelas", "tamanho do banco", "quanto ocupa?"
  - Indices: "quais indices criar?", "indice pra essa query", "indices redundantes"
  - Performance: "query lenta", "EXPLAIN ANALYZE", "plano de execucao"

  NAO USAR QUANDO:
  - Consultas analiticas de dados de negocio → usar **consultando-sql**
  - Metricas de CPU/memoria do servico → usar **mcp__render__get_metrics**
  - Logs de aplicacao → usar **mcp__render__list_logs**
  - Status de deploy → usar **mcp__render__list_deploys**
allowed-tools: Read, Bash, Glob, Grep, mcp__postgres__analyze_db_health, mcp__postgres__get_top_queries, mcp__postgres__analyze_workload_indexes, mcp__postgres__analyze_query_indexes, mcp__postgres__explain_query, mcp__postgres__execute_sql, mcp__postgres__list_schemas, mcp__postgres__list_objects, mcp__postgres__get_object_details
---

# Diagnosticando Banco — Health Check & Otimizacao PostgreSQL

Skill para diagnosticos de saude, performance e otimizacao do banco PostgreSQL.
Combina um script local com o Postgres MCP Pro (9 tools DBA-level).

> **ESCOPO:** Esta skill executa checks read-only no banco. Nao modifica dados nem estrutura.
> Para consultas de dados de negocio, use `consultando-sql`.
> Para metricas de infra (CPU, memoria, HTTP), use `mcp__render__get_metrics`.

---

## Quando NAO Usar Esta Skill

| Situacao | Ferramenta Correta | Por que? |
|----------|-------------------|----------|
| Consultas de dados de negocio | **consultando-sql** | Health check e sobre infra, nao dados |
| Metricas CPU/memoria do servico | **mcp__render__get_metrics** | Metricas de container, nao de banco |
| Logs de aplicacao/request | **mcp__render__list_logs** | Logs de app, nao de banco |
| Status de deploys | **mcp__render__list_deploys** | Deploys sao infra, nao banco |

---

## REGRAS CRITICAS

### R1: FIDELIDADE AO OUTPUT
```
OBRIGATORIO: Toda informacao apresentada ao usuario DEVE vir EXATAMENTE
do output da tool ou script utilizado.

PROIBIDO:
- Inventar valores que nao existem no output (ex: "shared_buffers = 256MB")
- Arredondar ou alterar percentuais do output
- Especular causa de problemas sem evidencia no output
- Inventar recomendacoes com valores especificos nao fornecidos pela tool

PERMITIDO:
- Usar as faixas de interpretacao desta SKILL.md (cache >= 99% = EXCELENTE)
- Citar acoes sugeridas que existem no output
- Alertar sobre dados criticos (sequences > 50%, cache < 90%)
```

### R2: MODO DE EXECUCAO — QUAL USAR

O sistema oferece 3 modos. A escolha depende do contexto:

```
MODO 1 — POSTGRES MCP PRO (preferido para producao)
  Quando: Claude Code com acesso ao MCP server "postgres"
  Como: Chamar tools mcp__postgres__* diretamente
  Vantagem: 9 tools DBA-level, recomendacao de indices, EXPLAIN hipotetico
  Usar para: health check, queries lentas, otimizacao de indices, EXPLAIN

MODO 2 — SCRIPT LOCAL (dev/staging)
  Quando: Ambiente local com acesso ao banco via .env
  Como: Executar health_check_banco.py via Bash
  Vantagem: JSON estruturado, resumo executivo, 9 checks combinaveis
  Usar para: checks rapidos em dev, validacao pre-deploy

MODO 3 — RENDER MCP SQL (fallback para producao)
  Quando: MCP postgres NAO disponivel (ex: agente web)
  Como: mcp__render__query_render_postgres com SQLs desta skill
  Vantagem: Funciona sem postgres-mcp instalado
  Usar para: checks basicos quando Modo 1 indisponivel
```

**Regra de selecao**: Tentar Modo 1 primeiro. Se tool nao disponivel, usar Modo 2 (local) ou Modo 3 (producao).

### R3: RESULTADOS VAZIOS OU ERROS
```
Se o output retorna lista vazia ou total: 0:
  → Informar CLARAMENTE: "Nenhum [tipo] encontrado"
  → NAO inventar explicacao para resultado vazio

Se a tool/script falha (erro de conexao, permissao):
  → Mostrar a mensagem de erro EXATA
  → Sugerir verificar conexao com o banco
  → NAO tentar adivinhar a causa
```

---

## DECISION TREE — Qual Ferramenta Usar?

### Diagnosticos de saude (checks existentes)

| Se a pergunta menciona... | Modo 1 (MCP Pro) | Modo 2 (Script) | Modo 3 (Render SQL) |
|----------------------------|------------------|-----------------|---------------------|
| **Saude geral, visao completa** | `analyze_db_health` | `--all --resumo` | Multiplas SQLs |
| **Queries lentas** | `get_top_queries` | `--check top_queries` | SQL pg_stat_statements |
| **Indices nao usados** | `analyze_db_health` | `--check unused_indexes` | SQL pg_stat_user_indexes |
| **Indices duplicados** | `analyze_db_health` | `--check duplicate_indexes` | — |
| **Cache / buffer** | `analyze_db_health` | `--check cache_hit_rate` | SQL pg_statio |
| **Conexoes** | `analyze_db_health` | `--check connections` | SQL pg_stat_activity |
| **Bloat de indices** | `analyze_db_health` | `--check index_bloat` | — |
| **Maiores tabelas** | `execute_sql` | `--check table_sizes` | SQL pg_stat_user_tables |
| **Vacuum / dead tuples** | `analyze_db_health` | `--check vacuum_stats` | SQL pg_stat_user_tables |
| **Sequences / overflow** | `analyze_db_health` | `--check sequence_capacity` | SQL pg_sequences |

### Otimizacao de performance (capacidades NOVAS — apenas Modo 1)

| Se a pergunta menciona... | Tool MCP Pro | O que retorna |
|----------------------------|-------------|---------------|
| **Recomendacao de indices para o banco** | `analyze_workload_indexes` | Analisa workload completo e sugere indices otimos |
| **Recomendacao de indice para query X** | `analyze_query_indexes` | Sugere indices para ate 10 queries especificas |
| **EXPLAIN / plano de execucao** | `explain_query` | EXPLAIN com suporte a indices hipoteticos |
| **Estrutura de tabela/objeto** | `get_object_details` | Colunas, constraints, indices de um objeto |
| **Listar tabelas/views de um schema** | `list_objects` | Objetos de um schema |

Estas capacidades so estao disponiveis via Postgres MCP Pro (Modo 1).
Se o usuario pedir e o MCP nao estiver disponivel, informar que requer o server postgres-mcp.

### Cenarios Compostos

**"Diagnostico completo"** ou **"o que precisa de atencao"**:
1. Modo 1: `analyze_db_health` (cobre tudo em uma chamada)
2. Modo 2: `--all --resumo` primeiro → detalhar problemas
3. Priorizar: sequences > 50% → cache < 90% → vacuum > 10% → indices

**"Essa query ta lenta, o que fazer?"**:
1. `explain_query` com a query do usuario → ver plano de execucao
2. `analyze_query_indexes` com a query → receber recomendacao de indice
3. Apresentar: plano atual + indice sugerido + ganho estimado

**"Quais indices criar pra melhorar performance?"**:
1. `analyze_workload_indexes` → analisa queries reais do pg_stat_statements
2. Apresentar: indices sugeridos com impacto estimado
3. Se usuario quiser validar: `explain_query` com indice hipotetico

---

## Modo 1: Postgres MCP Pro (producao — preferido)

### Tools Disponiveis

| Tool | Descricao | Quando usar |
|------|-----------|-------------|
| `mcp__postgres__analyze_db_health` | Health check completo: cache, conexoes, constraints, indices, sequences, vacuum | Diagnostico geral, substitui `--all` |
| `mcp__postgres__get_top_queries` | Queries mais lentas via pg_stat_statements | "queries lentas", "o que ta pesado" |
| `mcp__postgres__analyze_workload_indexes` | Recomendacao de indices para workload inteiro | "quais indices criar", "otimizar banco" |
| `mcp__postgres__analyze_query_indexes` | Recomendacao de indices para queries especificas (ate 10) | "indice pra essa query", "otimizar SELECT" |
| `mcp__postgres__explain_query` | EXPLAIN com suporte a indices hipoteticos | "EXPLAIN", "plano de execucao", "por que lento" |
| `mcp__postgres__execute_sql` | Executa SQL (read-only em modo restricted) | Queries ad-hoc nao cobertas pelas tools acima |
| `mcp__postgres__list_schemas` | Lista schemas do banco | Explorar estrutura |
| `mcp__postgres__list_objects` | Lista objetos de um schema (tabelas, views, sequences) | "quais tabelas existem" |
| `mcp__postgres__get_object_details` | Detalhes de objeto (colunas, constraints, indices) | "mostra a estrutura da tabela X" |

### Exemplo de uso: Diagnostico completo

```
1. Chamar mcp__postgres__analyze_db_health
2. Se problemas de performance → mcp__postgres__get_top_queries
3. Se queries lentas identificadas → mcp__postgres__analyze_query_indexes com as queries
4. Apresentar resultado consolidado ao usuario
```

### Exemplo de uso: Otimizar query

```
1. mcp__postgres__explain_query com a query do usuario
2. mcp__postgres__analyze_query_indexes com a mesma query
3. Se indice sugerido → mcp__postgres__explain_query novamente COM indice hipotetico
4. Mostrar: plano antes vs depois + indice sugerido
```

---

## Modo 2: Script Local (dev/staging)

```bash
source .venv/bin/activate && \
python .claude/skills/diagnosticando-banco/scripts/health_check_banco.py [opcoes]
```

### Combinando Checks

```bash
# Checks especificos combinados
health_check_banco.py --check unused_indexes cache_hit_rate connections

# Todos com resumo executivo
health_check_banco.py --all --resumo
```

**Para parametros completos, retornos JSON e exemplos**: LER `SCRIPTS.md`

---

## Modo 3: Render MCP SQL (fallback producao)

Para producao quando Postgres MCP Pro nao estiver disponivel.
Usar `mcp__render__query_render_postgres` com `postgresId = "dpg-d13m38vfte5s738t6p50-a"`.

### Indices Nao Usados
```sql
SELECT s.relname AS tabela, s.indexrelname AS indice,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho,
       s.idx_scan AS scans
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
WHERE s.idx_scan = 0 AND NOT i.indisunique AND NOT i.indisprimary
  AND s.schemaname = 'public'
ORDER BY pg_relation_size(s.indexrelid) DESC LIMIT 20;
```

### Cache Hit Rate
```sql
SELECT round(sum(heap_blks_hit)::numeric /
  NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2) AS hit_rate_pct
FROM pg_statio_user_tables;
```

### Top Queries Lentas (requer pg_stat_statements)
```sql
SELECT substring(query, 1, 200) AS query, calls,
       round(total_exec_time::numeric, 2) AS tempo_total_ms,
       round(mean_exec_time::numeric, 2) AS tempo_medio_ms, rows
FROM pg_stat_statements
WHERE query NOT LIKE 'SET %' AND query NOT LIKE 'BEGIN%'
  AND userid = (SELECT usesysid FROM pg_user WHERE usename = current_user)
ORDER BY total_exec_time DESC LIMIT 10;
```

### Conexoes Ativas
```sql
SELECT state, count(*) AS quantidade,
  max(extract(epoch from (now() - state_change)))::integer AS max_duracao_seg
FROM pg_stat_activity WHERE pid <> pg_backend_pid()
GROUP BY state ORDER BY quantidade DESC;
```

### Maiores Tabelas
```sql
SELECT relname AS tabela,
  pg_size_pretty(pg_total_relation_size(relid)) AS tamanho_total,
  n_live_tup AS linhas_vivas, n_dead_tup AS linhas_mortas
FROM pg_stat_user_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;
```

### Sequences (Risco de Overflow INTEGER)
```sql
SELECT sequencename, last_value,
  round(last_value::numeric / 2147483647 * 100, 4) AS uso_pct
FROM pg_sequences WHERE schemaname = 'public' AND last_value IS NOT NULL
ORDER BY last_value DESC;
```

---

## Interpretacao de Resultados

### Cache Hit Rate
| Faixa | Status | Acao |
|-------|--------|------|
| >= 99% | EXCELENTE | Nenhuma |
| 95-99% | BOM | Monitorar |
| 90-95% | ATENCAO | Avaliar shared_buffers |
| < 90% | CRITICO | Aumentar shared_buffers ou otimizar queries |

### Sequences
| Uso | Risco | Acao |
|-----|-------|------|
| < 10% | Nenhum | Monitorar |
| 10-50% | Baixo | Planejar migracao para BIGINT |
| > 50% | ALTO | Migrar para BIGINT urgentemente |

### Vacuum
| Dead Ratio | Status | Acao |
|------------|--------|------|
| < 5% | OK | Autovacuum funcionando |
| 5-10% | Atencao | Verificar autovacuum config |
| > 10% | Problema | Executar VACUUM ANALYZE manual |

### Conexoes
| Utilizacao | Status | Acao |
|------------|--------|------|
| < 50% | OK | Normal |
| 50-80% | Atencao | Monitorar pool |
| > 80% | Critico | Verificar pool e conexoes idle |

---

## Formato de Resposta ao Usuario

### Diagnostico Completo
```
## Saude do Banco: [STATUS]

### Problemas Encontrados
- [Listar problemas — EXATAMENTE como vem do output]

### Destaques
- [Listar destaques positivos — EXATAMENTE como vem do output]

### Detalhes [se solicitado]
[Expandir checks individuais com dados EXATOS do output]
```

### Recomendacao de Indices (novo)
```
## Indices Recomendados

### Indice 1: [nome sugerido]
- Tabela: [tabela]
- Colunas: [colunas]
- Impacto estimado: [ganho projetado pela tool]
- Query beneficiada: [query que melhora]

### Como criar:
CREATE INDEX CONCURRENTLY [nome] ON [tabela] ([colunas]);

Nota: Usar CONCURRENTLY para nao bloquear operacoes.
```

### Analise de Query (novo)
```
## Analise de Performance: [query resumida]

### Plano de Execucao Atual
[Output do EXPLAIN formatado]

### Gargalos Identificados
- [Seq Scan onde Index Scan seria melhor]
- [Custo alto em operacoes especificas]

### Indice Sugerido
[CREATE INDEX recomendado]

### Plano Estimado COM Indice
[Output do EXPLAIN com indice hipotetico, se disponivel]
```

---

## Pre-requisitos

| Extensao | Necessaria para | Status Render |
|----------|----------------|---------------|
| pg_stat_statements | `top_queries`, `analyze_workload_indexes` | Instalada (v1.12) |
| HypoPG | Indices hipoteticos no `explain_query` | NAO disponivel |

**Nota sobre HypoPG**: `explain_query` suporta indices hipoteticos, mas depende da extensao HypoPG estar instalada no servidor. No Render, HypoPG nao esta disponivel, entao indices hipoteticos nao funcionarao no EXPLAIN. O `analyze_workload_indexes` e `analyze_query_indexes` ainda funcionam normalmente (usam algoritmo proprio para recomendar indices).

---

## Referencia Cruzada

| Skill / Ferramenta | Quando usar em vez desta |
|---------------------|--------------------------|
| **consultando-sql** | Consultas de dados de negocio |
| **mcp__render__get_metrics** | Metricas de infra (CPU, memoria) |
| **mcp__render__list_logs** | Logs de aplicacao |
| **mcp__render__list_deploys** | Status de deploys |
