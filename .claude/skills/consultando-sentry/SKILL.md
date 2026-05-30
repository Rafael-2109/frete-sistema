---
name: consultando-sentry
description: >
  Consulta issues, eventos e metricas do Sentry via MCP Server.
  Use quando o usuario mencionar "Sentry", "issues do Sentry", "erros em producao",
  "bugs no Sentry", "exceptions nao tratadas", "500 errors no Sentry", "resolver issue",
  "marcar resolvido no Sentry", ou qualquer variacao que envolva monitoramento de erros.
  Tambem usar quando o usuario pedir para "ver erros", "checar exceptions",
  "quantos bugs tem", "issues abertas", "erros das ultimas 24h", ou "root cause analysis".
  NAO usar para logs do Render (usar MCP Render list_logs), metricas de CPU/memoria
  (usar MCP Render get_metrics), ou diagnostico de banco (usar diagnosticando-banco).
---

# Consultando Sentry

Skill para consultar e operar o Sentry da Nacom Goya via **MCP Server** (acesso direto, sem script intermediario).

## Contexto

- **Organizacao**: `nacom`
- **Projeto**: `python-flask` (unico)
- **Region URL**: `https://us.sentry.io` (OBRIGATORIO em todas as tools)
- **Auth**: OAuth via MCP Server (Bearer token configurado em `~/.claude/settings.json`)
- **Dashboard Web**: https://nacom.sentry.io/
- **Referencia**: `.claude/references/INFRAESTRUTURA.md` secao "Sentry"

## Como Usar — MCP Tools (metodo primario)

### 1. Listar issues nao resolvidas

```
mcp__sentry__search_issues(
    organizationSlug="nacom",
    projectSlugOrId="python-flask",
    naturalLanguageQuery="unresolved issues from last 24 hours",
    regionUrl="https://us.sentry.io",
    limit=25
)
```

Exemplos de queries naturais:
- `"critical bugs from last week"`
- `"unhandled errors affecting 100+ users"`
- `"issues assigned to me"`
- `"errors in devolucao module"`
- `"user feedback from production"`

### 2. Eventos / stacktrace de uma issue

NAO existe `get_issue_details` neste MCP server. Para stacktrace e detalhes
dos eventos de uma issue use `search_issue_events`; para causa raiz + arquivos
afetados use `analyze_issue_with_seer` (secao 3).

```
mcp__sentry__search_issue_events(
    organizationSlug="nacom",
    issueId="PYTHON-FLASK-5",
    naturalLanguageQuery="latest event with stacktrace",
    regionUrl="https://us.sentry.io"
)
```

### 3. Root Cause Analysis com Seer (AI)

```
mcp__sentry__analyze_issue_with_seer(
    organizationSlug="nacom",
    issueId="PYTHON-FLASK-5",
    regionUrl="https://us.sentry.io"
)
```

Retorna: causa raiz, arquivos/linhas afetados, sugestoes de fix com codigo. Resultados cached (~2-5min primeira vez).

### 4. Resolver/Ignorar issues

```
mcp__sentry__update_issue(
    organizationSlug="nacom",
    issueId="PYTHON-FLASK-5",
    status="resolved",
    regionUrl="https://us.sentry.io"
)
```

Status validos: `resolved`, `resolvedInNextRelease`, `unresolved`, `ignored`.

### 5. Eventos de uma issue (filtrados)

```
mcp__sentry__search_issue_events(
    organizationSlug="nacom",
    issueId="PYTHON-FLASK-5",
    naturalLanguageQuery="from last hour in production",
    regionUrl="https://us.sentry.io"
)
```

### 6. Contagens e estatisticas

```
mcp__sentry__search_events(
    organizationSlug="nacom",
    projectSlug="python-flask",
    naturalLanguageQuery="how many errors today",
    regionUrl="https://us.sentry.io"
)
```

Exemplos: `"count of database failures this week"`, `"total tokens used by model"`, `"average response time"`.

### 7. Tags de uma issue (distribuicao)

```
mcp__sentry__get_issue_tag_values(
    organizationSlug="nacom",
    issueId="PYTHON-FLASK-5",
    tagKey="url",
    regionUrl="https://us.sentry.io"
)
```

Tag keys comuns: `url`, `browser`, `environment`, `release`, `user`, `transaction`.

### 8. Releases

```
mcp__sentry__find_releases(
    organizationSlug="nacom",
    projectSlug="python-flask",
    regionUrl="https://us.sentry.io"
)
```

### 9. Documentacao Sentry

NAO existe `get_trace_details` neste MCP server. Para consultar a documentacao
oficial do Sentry use `search_docs` + `get_doc`.

```
mcp__sentry__search_docs(query="distributed tracing setup", maxResults=3)
```

## Tools MCP Disponíveis (principais)

| Tool | Funcao |
|------|--------|
| `whoami` | Identificar usuario autenticado |
| `find_organizations` | Listar organizacoes |
| `find_projects` | Listar projetos |
| `find_teams` | Listar teams |
| `find_releases` | Listar releases |
| `find_dsns` | Listar DSNs do projeto |
| `search_issues` | Buscar issues (linguagem natural) |
| `search_events` | Buscar eventos + contagens/agregacoes |
| `search_issue_events` | Filtrar eventos de uma issue (stacktrace) |
| `get_issue_tag_values` | Distribuicao de tags |
| `get_event_attachment` | Baixar attachments |
| `analyze_issue_with_seer` | Root cause analysis AI (Seer) |
| `update_issue` | Resolver/ignorar/atribuir issue |
| `update_project` | Atualizar config do projeto |
| `create_project` / `create_team` / `create_dsn` | Criar recursos |
| `search_docs` / `get_doc` | Documentacao Sentry |

> NAO existem neste MCP server: `get_issue_details` e `get_trace_details`
> (use `search_issue_events` + `analyze_issue_with_seer` no lugar). Tools de
> snapshot/profile/replay existem mas nao sao usadas por esta skill.

## Metodo Secundario — Sentry CLI

Para uso no terminal (quando MCP nao esta disponivel):

```bash
sentry issue list                        # Listar issues
sentry issue explain PYTHON-FLASK-5      # Root cause analysis (Seer)
sentry issue plan PYTHON-FLASK-5         # Plano de fix automatico
```

## Fluxo Recomendado

1. **Visao geral**: `search_issues` com `"unresolved issues"` ou `search_events` com `"how many errors today"`
2. **Investigar**: `search_issue_events` para stacktrace + `analyze_issue_with_seer` para causa raiz
3. **Contexto**: `get_issue_tag_values` para entender distribuicao (URLs, browsers, environments)
4. **Corrigir**: implementar fix no codigo
5. **Fechar**: `update_issue` com status `"resolved"`

## IMPORTANTE

- **SEMPRE incluir `regionUrl="https://us.sentry.io"`** nas tools que aceitam esse parametro
- O MCP Server substitui completamente o script REST antigo (`sentry_api.py`)
- `search_issues` retorna LISTA de issues. Para contagens, usar `search_events`
- `analyze_issue_with_seer` pode demorar 2-5min na primeira vez (resultado cached depois)
