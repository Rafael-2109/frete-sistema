# Infraestrutura — Render & Servicos

**Ultima Atualizacao**: 08/02/2026

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
| sistema-fretes | Web Service | Pro 4GB 2CPU | sistema-fretes.onrender.com |
| frete-sistema | Web Service | Free | frete-sistema.onrender.com (DEPRECATED) |
| sistema-fretes-worker-atacadao | Background Worker | Standard 2GB 1CPU | — |
| sistema-fretes-redis | Key Value | Starter 256MB | — |
| sistema-fretes-db | Postgres | Basic 1GB | — |

---

## ODOO

### ERP
- odoo.nacomgoya.com.br
