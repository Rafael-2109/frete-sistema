# Infraestrutura — Render & Servicos

**Ultima Atualizacao**: 22/04/2026

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
| frete-sistema | Web Service | Free (SUSPENDED) | frete-sistema.onrender.com (DEPRECATED) |
| sistema-fretes-worker-atacadao | Background Worker | Standard 2GB 1CPU | — |
| sistema-fretes-redis | Key Value | Starter 256MB | — |
| sistema-fretes-db | Postgres | Basic 4GB, disco 5 GB, limite ~197 conn | — |

---

### Capacity Planning — baseline 2026-04-22 (30 dias)

> **Use este baseline antes de discutir escalonamento ou downgrade.** Se os numeros
> mudarem > 50%, reexecute `mcp__render__get_metrics` e atualize aqui.

**Web service `sistema-fretes` (Pro Plus 8GB 4CPU):**
- CPU (hourly MAX): p50 0.08 / p95 3.10 / p99 4.00 vCPU. 15h/30d em CPU > 87% (2.5% do tempo).
- Memoria: avg 2.21 GB (28%), p95 3.56 GB, max 4.40 GB (55%). Nunca > 55%.
- HTTP pico: **1.44 rps** (p95 0.84 rps). Capacidade config atual (4w × 2t = 8 concurrent): ~20-30 rps sustentados → **uso real ~5% da capacidade**.
- Instance count: 1 (sem autoscaling).
- Errors 7d: 500 0.12%, 502 0.004%, 499 0.22% (SSE disconnect normal).

**Postgres `sistema-fretes-db` (Basic 4GB):**
- Conexoes pico: **31 de ~197** (16%). psycopg2 + asyncpg pool somados ja sao visiveis.
- CPU pico: 8.6%. Memoria pico: 1.4 GB de 4 GB (35%).
- Disco: 5 GB (atencao: `claude_session_store` cresce sem TTL — monitorar).

**Gunicorn config atual** (`start_render.sh` gunicorn_config):
- `workers=4, threads=2` gthread — 8 req concorrentes
- `timeout=600s` (alinhado com Render 600s + SSE teto 540s web / 600s teams)
- `graceful_timeout=60s` (deploy/reload)

**Decisoes:**
- **NAO escalar workers** — uso real 5% da capacidade.
- **Pro Plus sobredimensionado para workload atual** mas picos 4 vCPU (2.5% do tempo) justificam. Downgrade Pro (4GB 2CPU) viavel com `workers=2` se aceitar latencia pior nos picos — economia ~50%.
- **Standard 2GB 1CPU nao recomendado** — picos 4 vCPU nao cabem em 1 vCPU.

**Stack de timeouts** (ordem critica — nao quebrar):
```
Heartbeat SSE 10s < AskUser web 55s < Inatividade 240s < SSE teto 540s < Gunicorn timeout 600s = Render hard limit 600s
```
Detalhes e ordem completa em `app/agente/CLAUDE.md` secao "Hierarquia de Timeouts".

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
