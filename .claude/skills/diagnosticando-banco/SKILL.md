---
name: diagnosticando-banco
description: >-
  Esta skill deve ser usada quando o usuario pergunta "como esta o banco?",
  "indices nao usados", "queries lentas", "cache hit rate", "conexoes ativas",
  "vacuum", "bloat", ou precisa de diagnostico de saude do PostgreSQL.
  Nao usar para consultas analiticas de dados de negocio (usar consultando-sql),
  logs do servidor (usar mcp__render__consultar_logs), ou performance da
  aplicacao web (usar mcp__render__status_servicos).
  - Conexoes: "quantas conexoes?", "conexoes idle", "pool"
  - Vacuum: "precisa de vacuum?", "dead tuples", "tabelas inchadas"
  - Sequences: "sequences proximas do limite?", "risco de overflow INTEGER"
  - Tamanho: "maiores tabelas", "tamanho do banco", "quanto ocupa?"

  NAO USAR QUANDO:
  - Consultas analiticas de dados de negocio → usar **consultando-sql**
  - Metricas de CPU/memoria do servico → usar **mcp__render__get_metrics**
  - Logs de aplicacao → usar **mcp__render__list_logs**
  - Status de deploy → usar **mcp__render__list_deploys**
allowed-tools: Read, Bash, Glob, Grep
---

# Diagnosticando Banco — Health Check PostgreSQL

Skill para diagnosticos de saude, performance e otimizacao do banco PostgreSQL.

> **ESCOPO:** Esta skill executa checks read-only no banco. Nao modifica dados nem estrutura.
> Para consultas de dados de negocio, use `consultando-sql`.
> Para metricas de infra (CPU, memoria, HTTP), use `mcp__render__get_metrics`.

## Quando NAO Usar Esta Skill

| Situacao | Ferramenta Correta | Por que? |
|----------|-------------------|----------|
| Consultas de dados de negocio | **consultando-sql** | Health check e sobre infra, nao dados |
| Metricas CPU/memoria do servico | **mcp__render__get_metrics** | Metricas de container, nao de banco |
| Logs de aplicacao/request | **mcp__render__list_logs** | Logs de app, nao de banco |
| Status de deploys | **mcp__render__list_deploys** | Deploys sao infra, nao banco |

---

## REGRAS CRITICAS

### R1: FIDELIDADE AO OUTPUT DO SCRIPT
```
OBRIGATORIO: Toda informacao apresentada ao usuario DEVE vir EXATAMENTE
dos campos do JSON retornado pelo script.

PROIBIDO:
- Inventar valores que nao existem no JSON (ex: "shared_buffers = 256MB")
- Arredondar ou alterar percentuais do JSON (usar EXATAMENTE hit_rate_pct)
- Especular causa de problemas sem evidencia no JSON
- Inventar recomendacoes com valores especificos (ex: "aumente para 512MB")

PERMITIDO:
- Usar as faixas de interpretacao da SKILL.md (cache >= 99% = EXCELENTE)
- Citar a acao_sugerida que JA EXISTE no JSON de cada check
- Alertar sobre dados criticos (sequences > 50%, cache < 90%)
```

### R2: MODO DE EXECUCAO
```
AMBIENTE LOCAL (Claude Code / dev):
  → Executar health_check_banco.py via Bash

AMBIENTE PRODUCAO (agente web / Render):
  → Usar mcp__render__query_render_postgres com postgresId
  → SQLs prontas na secao "SQL Templates para Render MCP"

NUNCA: Executar o script Python em producao (nao tem acesso ao banco)
NUNCA: Usar mcp__render__ em ambiente local
```

### R3: RESULTADOS VAZIOS OU ERROS
```
Se o script retorna "dados": [] ou total: 0:
  → Informar CLARAMENTE: "Nenhum [tipo] encontrado"
  → NAO inventar explicacao para resultado vazio

Se o script falha (erro de conexao, permissao):
  → Mostrar a mensagem de erro EXATA
  → Sugerir verificar conexao com o banco
  → NAO tentar adivinhar a causa

Se pg_stat_statements nao esta disponivel:
  → Informar: "pg_stat_statements nao habilitado"
  → NAO inventar dados de queries lentas
```

---

## DECISION TREE — Qual Check Usar?

| Se a pergunta menciona... | Use este check | O que retorna |
|----------------------------|----------------|---------------|
| **Saude geral, visao completa** | `--all --resumo` | Resumo executivo de todos os checks |
| **Indices nao usados** | `--check unused_indexes` | Indices com 0 scans + espaco desperdicado |
| **Indices duplicados** | `--check duplicate_indexes` | Indices com mesma definicao na mesma tabela |
| **Queries lentas** | `--check top_queries` | Top N queries por tempo total (requer pg_stat_statements) |
| **Cache / buffer** | `--check cache_hit_rate` | Hit rate de heap e index cache |
| **Conexoes** | `--check connections` | Breakdown por estado + utilizacao |
| **Bloat de indices** | `--check index_bloat` | Maiores indices com analise de eficiencia |
| **Maiores tabelas** | `--check table_sizes` | Top N tabelas por tamanho total |
| **Vacuum / dead tuples** | `--check vacuum_stats` | Tabelas com dead tuples + ultimo vacuum |
| **Sequences / overflow** | `--check sequence_capacity` | Uso % de sequences (risco INTEGER overflow) |

### Combinando Checks

```bash
# Checks especificos combinados
health_check_banco.py --check unused_indexes cache_hit_rate connections

# Todos com resumo executivo
health_check_banco.py --all --resumo
```

### Cenarios Compostos

Quando o usuario pede "diagnostico completo" ou "o que precisa de atencao":

1. Executar `--all --resumo` primeiro
2. Se `resumo_executivo.total_problemas > 0`: detalhar cada problema
3. Se `saude_geral == "CRITICO"`: alertar imediatamente
4. Priorizar problemas: sequences > 50% → cache < 90% → vacuum > 10% → indices

---

## Modos de Execucao

### Modo 1: Script Local (dev/staging)

```bash
source .venv/bin/activate && \
python .claude/skills/diagnosticando-banco/scripts/health_check_banco.py --all --resumo
```

### Modo 2: Render MCP (producao)

Para producao, executar as SQLs diretamente via `mcp__render__query_render_postgres` com `postgresId = "dpg-d13m38vfte5s738t6p50-a"`.

SQLs prontas para uso direto — ver secao "SQL Templates para Render MCP" abaixo.

---

## SQL Templates para Render MCP

Quando nao puder executar o script (ex: producao via agente web), usar estas queries diretamente:

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
**Nota:** Query assume INTEGER (2.1B limite). No Render MCP, `data_type` causa erro de casting — usar versao simplificada acima.

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

## Script Principal

### health_check_banco.py

```bash
source .venv/bin/activate && \
python .claude/skills/diagnosticando-banco/scripts/health_check_banco.py [opcoes]
```

**Para parametros completos, retornos JSON e exemplos**: LER `SCRIPTS.md`

---

## Formato de Resposta ao Usuario

### Diagnostico Completo (--all)
```
## Saude do Banco: [STATUS do resumo_executivo.saude_geral]

### Problemas Encontrados
- [Listar resumo_executivo.problemas — EXATAMENTE como vem do JSON]

### Destaques
- [Listar resumo_executivo.destaques — EXATAMENTE como vem do JSON]

### Detalhes [se solicitado]
[Expandir checks individuais com dados EXATOS do JSON]
```

### Check Especifico
```
## [Nome do Check]: [Status/Resultado principal]

[Dados EXATOS do JSON formatados para leitura humana]

Acao sugerida: [EXATAMENTE o campo acao_sugerida do JSON]
```

---

## Pre-requisitos

| Extensao | Necessaria para | Status Render |
|----------|----------------|---------------|
| pg_stat_statements | `top_queries` | Instalada (v1.10) |
| HypoPG | Indices hipoteticos | NAO disponivel |

---

## Referencia Cruzada

| Skill / Ferramenta | Quando usar em vez desta |
|---------------------|--------------------------|
| **consultando-sql** | Consultas de dados de negocio |
| **mcp__render__get_metrics** | Metricas de infra (CPU, memoria) |
| **mcp__render__list_logs** | Logs de aplicacao |
| **mcp__render__list_deploys** | Status de deploys |
