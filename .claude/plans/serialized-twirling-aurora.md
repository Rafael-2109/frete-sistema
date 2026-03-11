# Plano: Atualizar Skill diagnosticando-banco (v2)

## Contexto

Apos executar um diagnostico completo do banco (2026-03-11), foram identificados gaps:
1. **Sentry NAO integrado** — a skill nao verifica erros de aplicacao relacionados ao banco
2. **Skill desatualizada** — faltam checks que fizemos manualmente no diagnostico
3. **Sentry MCP NAO esta configurado** — `@sentry/mcp-server` documentado em INFRAESTRUTURA.md mas nunca instalado como plugin

### Estado Real do Sentry MCP

| Item | Estado |
|------|--------|
| SDK Flask (`sentry-sdk[flask]==2.54.0`) | Instalado e ativo em producao |
| Inicializacao (`app/__init__.py:45-88`) | Condicional via `SENTRY_DSN` |
| MCP Server (`@sentry/mcp-server@latest`) | **NAO instalado** — nao e plugin, nao ha `mcp__sentry__*` tools |
| Plugin instalado | **NAO** — nao aparece em `installed_plugins.json` |
| Env var `SENTRY_AUTH_TOKEN` | Documentada em INFRAESTRUTURA.md mas status desconhecido |

**Conclusao**: Para integrar Sentry na skill, precisa-se PRIMEIRO instalar o MCP server como plugin ou configurar como server externo. Isso e um prerequisito, nao faz parte desta atualizacao da skill.

---

## Escopo — 2 Frentes

### Frente 1: Instalar Sentry MCP (prerequisito)

**Acao**: Configurar `@sentry/mcp-server@latest` como MCP server no Claude Code
- Verificar se `SENTRY_AUTH_TOKEN` existe no Render
- Instalar via `claude mcp add sentry` ou configuracao manual
- Testar quais tools ficam disponiveis (`mcp__sentry__*`)
- **SE funcionar**: adicionar na Frente 2

**Risco**: Se `SENTRY_AUTH_TOKEN` nao estiver configurada, Sentry MCP nao vai funcionar. Nesse caso, documentar como "futuro" e prosseguir so com Frente 2.

### Frente 2: Atualizar SKILL.md + Script

#### 2A. Novo cenario "Diagnostico Completo" (orquestracao)

Hoje a skill trata so o PostgreSQL. Para "diagnostico completo", adicionar orquestracao:

```
## Cenario: Diagnostico Completo ("como esta o banco?")

### Bloco 1 — Saude do PostgreSQL (core)
- Cache hit rate, conexoes, indices nao usados, vacuum, sequences, queries lentas
- Ferramentas: checks existentes (Modo 1/2/3)

### Bloco 2 — Contexto de Infraestrutura (novo)
- Versao, plano, status do Postgres: `mcp__render__get_postgres`
- CPU, memoria, conexoes ativas do container: `mcp__render__get_metrics`
- Tamanho total da database: SQL `pg_database_size()`

### Bloco 3 — Erros de Aplicacao (novo, opcional)
- Erros recentes relacionados a banco: tools Sentry (se disponivel)
- Graceful degradation: se Sentry nao configurado, informar e pular
```

#### 2B. Novos checks no script (`health_check_banco.py`)

| Check novo | O que faz | SQL |
|------------|-----------|-----|
| `database_info` | Versao PG, tamanho total, uptime, extensions | `SELECT version()`, `pg_database_size()`, `pg_postmaster_start_time()`, `pg_available_extensions` |
| `autovacuum_detail` | Ultimo vacuum/autovacuum por tabela, vacuums em andamento | `pg_stat_user_tables` (last_vacuum, last_autovacuum) + `pg_stat_progress_vacuum` |

#### 2C. Novas SQLs no Modo 3

Adicionar a SKILL.md:

```sql
-- Tamanho total do banco
SELECT pg_size_pretty(pg_database_size(current_database())) AS tamanho_total;

-- Versao e uptime
SELECT version() AS versao,
  current_timestamp - pg_postmaster_start_time() AS uptime;

-- Autovacuum detalhado
SELECT relname, last_vacuum, last_autovacuum,
  n_dead_tup, n_live_tup,
  CASE WHEN n_live_tup + n_dead_tup = 0 THEN 0
    ELSE round(n_dead_tup::numeric / (n_live_tup + n_dead_tup) * 100, 2)
  END AS dead_ratio_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 20;
```

#### 2D. Atualizar `allowed-tools`

Adicionar:
- `mcp__render__query_render_postgres`
- `mcp__render__get_metrics`
- `mcp__render__get_postgres`
- Tools Sentry (se Frente 1 funcionar)

#### 2E. Atualizar Decision Tree

Adicionar linhas para:
- "diagnostico completo" → Bloco 1 + 2 + 3
- "tamanho do banco" → check `database_info`
- "versao do postgres" → check `database_info`
- "erros no banco" / "timeouts" → Sentry (se disponivel)

#### 2F. Atualizar Interpretacao de Resultados

Adicionar secao para metricas Render:
- CPU DB > 80% = CRITICO
- Memoria DB > 90% = CRITICO
- Conexoes > 80% do limite = CRITICO

---

## Arquivos a Modificar

| Arquivo | Mudanca |
|---------|---------|
| `.claude/skills/diagnosticando-banco/SKILL.md` | Cenario completo, Decision Tree, SQLs, allowed-tools, Sentry |
| `.claude/skills/diagnosticando-banco/scripts/health_check_banco.py` | +2 checks: `database_info`, `autovacuum_detail` |
| `.claude/skills/diagnosticando-banco/SCRIPTS.md` | Documentar novos checks |
| `.claude/references/INFRAESTRUTURA.md` | Atualizar status Sentry MCP (instalado/nao) |

---

## Ordem de Execucao

1. Verificar se `SENTRY_AUTH_TOKEN` esta configurada no Render
2. Tentar instalar Sentry MCP → testar tools
3. Atualizar `SKILL.md` com cenario completo + Sentry (ou marcado como futuro)
4. Adicionar checks `database_info` + `autovacuum_detail` ao script
5. Atualizar `SCRIPTS.md`
6. Verificacao: executar diagnostico completo usando skill atualizada

## Verificacao

- `health_check_banco.py --check database_info autovacuum_detail` (local)
- Diagnostico completo via skill com os 3 blocos
- Sentry tools respondendo (se configurado)
