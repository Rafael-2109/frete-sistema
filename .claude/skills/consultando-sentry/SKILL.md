---
name: consultando-sentry
description: >
  Consulta issues, eventos e metricas do Sentry via MCP Server (20 tools).
  Usar SEMPRE que o usuario mencionar "Sentry", "issues do Sentry", "erros em producao",
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

### 2. Detalhes de uma issue (stacktrace, tags, metadata)

```
mcp__sentry__get_issue_details(
    organizationSlug="nacom",
    issueId="PYTHON-FLASK-5",
    regionUrl="https://us.sentry.io"
)
```

Tambem aceita URL completa:
```
mcp__sentry__get_issue_details(
    issueUrl="https://nacom.sentry.io/issues/PYTHON-FLASK-5"
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

### 9. Trace details

```
mcp__sentry__get_trace_details(
    organizationSlug="nacom",
    traceId="a4d1aae7216b47ff8117cf4e09ce9d0a",
    regionUrl="https://us.sentry.io"
)
```

## Tools MCP Disponíveis (20 total)

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
| `search_issue_events` | Filtrar eventos de uma issue |
| `get_issue_details` | Detalhes completos de issue |
| `get_issue_tag_values` | Distribuicao de tags |
| `get_trace_details` | Detalhes de trace |
| `get_event_attachment` | Baixar attachments |
| `analyze_issue_with_seer` | Root cause analysis AI (Seer) |
| `update_issue` | Resolver/ignorar/atribuir issue |
| `update_project` | Atualizar config do projeto |
| `create_project` | Criar novo projeto |
| `create_team` | Criar team |
| `create_dsn` | Criar DSN adicional |
| `search_docs` / `get_doc` | Documentacao Sentry |

## Metodo Secundario — Sentry CLI

Para uso no terminal (quando MCP nao esta disponivel):

```bash
sentry issue list                        # Listar issues
sentry issue explain PYTHON-FLASK-5      # Root cause analysis (Seer)
sentry issue plan PYTHON-FLASK-5         # Plano de fix automatico
```

## Fluxo Recomendado

1. **Visao geral**: `search_issues` com `"unresolved issues"` ou `search_events` com `"how many errors today"`
2. **Investigar**: `get_issue_details` para stacktrace + `analyze_issue_with_seer` para causa raiz
3. **Contexto**: `get_issue_tag_values` para entender distribuicao (URLs, browsers, environments)
4. **Corrigir**: implementar fix no codigo
5. **Fechar**: `update_issue` com status `"resolved"`

## IMPORTANTE

- **SEMPRE incluir `regionUrl="https://us.sentry.io"`** nas tools que aceitam esse parametro
- O MCP Server substitui completamente o script REST antigo (`sentry_api.py`)
- `search_issues` retorna LISTA de issues. Para contagens, usar `search_events`
- `analyze_issue_with_seer` pode demorar 2-5min na primeira vez (resultado cached depois)
