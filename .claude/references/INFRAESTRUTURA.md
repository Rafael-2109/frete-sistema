# Infraestrutura — Render & Servicos

**Ultima Atualizacao**: 11/03/2026

---

## RENDER — MCP Server

### REGRA: DADOS DE PRODUCAO = RENDER
Quando o usuario perguntar sobre dados, registros, quantidades, status de servicos,
metricas, logs ou deploys, SEMPRE consultar via MCP Render (`mcp__render__*`).
Os dados reais estao no Render. O banco local existe para desenvolvimento e migrations.

---

### IDs dos Recursos (usar direto nas tools)

| Recurso | ID | Nome |
|---------|----|------|
| Postgres | `dpg-d13m38vfte5s738t6p50-a` | sistema-fretes-db |
| Web Service (Pro) | `srv-d13m38vfte5s738t6p60` | sistema-fretes |
| Worker | `srv-d2muidggjchc73d4segg` | sistema-fretes-worker-atacadao |
| Web Service (free) | `srv-d1k6gcbe5dus73e5o3hg` | frete-sistema (DEPRECATED) |
| Redis | `red-d1c4jheuk2gs73absk10` | sistema-fretes-redis |

---

### Ferramentas MCP Disponiveis

| Ferramenta | Uso |
|------------|-----|
| `query_render_postgres` | Consulta SQL read-only no banco de producao |
| `list_services` | Listar servicos e status |
| `list_deploys` | Historico de deploys por servico |
| `get_deploy` | Detalhes de um deploy especifico |
| `get_metrics` | CPU, memoria, HTTP requests, latencia, bandwidth |
| `list_logs` | Logs de app, request e build |
| `list_postgres_instances` | Info do Postgres |
| `list_key_value` | Info do Redis |
| `get_service` | Detalhes de um servico |

---

### Exemplos de Uso

```
# Consultar dados de producao
mcp__render__query_render_postgres(postgresId="dpg-d13m38vfte5s738t6p50-a", sql="SELECT ...")

# Ver metricas
mcp__render__get_metrics(resourceId="srv-d13m38vfte5s738t6p60", metricTypes=["cpu_usage", "memory_usage"])

# Ver logs recentes
mcp__render__list_logs(resource=["srv-d13m38vfte5s738t6p60"], limit=20)

# Ver ultimos deploys
mcp__render__list_deploys(serviceId="srv-d13m38vfte5s738t6p60", limit=5)
```

---

### Servicos

| Servico | Tipo | Plano | Dominio |
|---------|------|-------|---------|
| sistema-fretes | Web Service | Pro Plus 8GB 4CPU | sistema-fretes.onrender.com |
| frete-sistema | Web Service | Free | frete-sistema.onrender.com (DEPRECATED) |
| sistema-fretes-worker-atacadao | Background Worker | Standard 2GB 1CPU | — |
| sistema-fretes-redis | Key Value | Starter 256MB | — |
| sistema-fretes-db | Postgres | Basic 1GB | — |

---

## Sentry — Application Monitoring (APM)

| Recurso | Valor |
|---------|-------|
| SDK | `sentry-sdk[flask]==2.54.0` |
| Integracao | `app/__init__.py` (FlaskIntegration + AnthropicIntegration condicional) |
| MCP Server | `https://mcp.sentry.dev/mcp` (OAuth Bearer, 20 tools) |
| CLI | `sentry-cli` 3.3.2 (AI: explain, plan) |
| Org / Projeto | `nacom` / `python-flask` |
| Region URL | `https://us.sentry.io` |
| Escopo | Erros Flask + AI Monitoring agente web |

### Env Vars (Render)

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `SENTRY_DSN` | — | DSN do projeto Sentry (sem = Sentry desabilitado) |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | % de transacoes HTTP amostradas para performance |
| `SENTRY_PROFILES_SAMPLE_RATE` | `0.1` | % de profiles coletados |
| `SENTRY_AI_MONITORING` | `false` | Ativa AnthropicIntegration (token usage, latencia, prompts) |

### Acesso (por ordem de preferencia)

1. **MCP Server** — Claude Code usa diretamente (20 tools, Seer integrado)
2. **Sentry CLI** — Terminal: `sentry-cli issues list`, AI: `explain`, `plan`
3. **Skill `consultando-sentry`** — Trigger automatico quando mencionar Sentry/erros
4. **Dashboard Web** — https://nacom.sentry.io/

### Tools MCP Disponiveis (20 total)

| Tool | Funcao |
|------|--------|
| `search_issues` | Buscar issues (linguagem natural) |
| `search_events` | Eventos + contagens/agregacoes |
| `get_issue_details` | Detalhes completos de issue (stacktrace, tags) |
| `analyze_issue_with_seer` | Root cause analysis AI (Seer) |
| `update_issue` | Resolver/ignorar/atribuir |
| `find_releases` | Listar releases |
| `get_trace_details` | Detalhes de trace |
| `search_docs` / `get_doc` | Documentacao Sentry |
| + 12 outras | whoami, find_orgs/projects/teams/dsns, create_*, update_project, tag_values, etc. |

---

## Odoo ERP

| Recurso | Valor |
|---------|-------|
| URL | odoo.nacomgoya.com.br |
| Conexao | `app/odoo/utils/connection.py` → `get_odoo_connection()` |
| Companies | FB(1), SC(3), CD(4), LF(5) — detalhes em `odoo/IDS_FIXOS.md` |
