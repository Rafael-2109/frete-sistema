# MCP Capabilities — Estado do Sistema (Fev/2026)

**Atualizado**: 2026-02-17

---

## Versoes Instaladas

| Package | Versao | Nota |
|---|---|---|
| `claude-agent-sdk` | 0.1.37 | Wrapper MCP (in-process) |
| `mcp` | 1.26.0 | MCP Python SDK (spec 2025-11-25). **Pin recomendado: `>=1.25,<2`** |

---

## Capacidades por Camada

### claude_agent_sdk (wrapper)

| Feature | Status | Detalhes |
|---|---|---|
| `@tool` decorator | Disponivel | name, description, input_schema, annotations |
| `ToolAnnotations` | Disponivel | readOnly, destructive, idempotent, openWorld |
| `create_sdk_mcp_server` | Disponivel | Server in-process, lista tools, executa handlers |
| `outputSchema` | **NAO** | `SdkMcpTool` nao tem campo. `list_tools` nao passa. |
| `structuredContent` | **NAO** | `call_tool` retorna `list[Content]`, nao `CallToolResult` |
| `Context.elicit()` | **NAO** | Sem acesso ao Context MCP |
| `Context.report_progress()` | **NAO** | Sem acesso ao Context MCP |
| `@resource` / `@prompt` | **NAO** | Apenas tools suportadas |

### mcp 1.26.0 (SDK direto)

| Feature | Status | Desde |
|---|---|---|
| `Tool.outputSchema` | Disponivel | spec 2025-06-18 |
| `CallToolResult.structuredContent` | Disponivel | spec 2025-06-18 |
| `Elicitation` | Disponivel | spec 2025-06-18 |
| `Tasks` (async) | Experimental | spec 2025-11-25 |
| `Resource Links` | Disponivel | spec 2025-06-18 |
| `Server Icons` | Disponivel | spec 2025-11-25 |

### Enhanced Wrapper (`_mcp_enhanced.py`)

Criado em 2026-02-17 para preencher gap entre SDK wrapper e MCP spec.

| Feature | Status | Como |
|---|---|---|
| `outputSchema` | **Implementado** | `EnhancedMcpTool.output_schema` → `Tool(outputSchema=...)` |
| `structuredContent` | **Implementado** | Handler retorna dict com key `structuredContent` → `CallToolResult` direto |
| Backward compat | **Mantido** | `TextContent` sempre presente. `structuredContent` e opcional |

**Arquivo**: `app/agente/tools/_mcp_enhanced.py`

---

## Servidores MCP Registrados (6)

| Server | Arquivo | Tools | Enhanced | Annotations |
|---|---|---|---|---|
| sql | `text_to_sql_tool.py` | 1 | **SIM** (v2.0.0) | readOnly, idempotent, openWorld=F |
| memory | `memory_mcp_tool.py` | 6 | nao | readOnly/destructive, openWorld=F |
| schema | `schema_mcp_tool.py` | 2 | nao | readOnly, openWorld=F |
| sessions | `session_search_tool.py` | 3 | nao | readOnly, openWorld=F |
| render | `render_logs_tool.py` | 3 | nao | readOnly, openWorld=T |
| browser | `playwright_mcp_tool.py` | 11 | nao | variado, openWorld=T (SSW) |

**Total**: 26 tools registradas, todas com `openWorldHint` configurado.

---

## Structured Output — SQL Tool (POC)

### outputSchema

```json
{
  "success": "boolean",
  "error": "string|null",
  "query_executed": "string|null",
  "columns": ["string"],
  "rows": [["any"]],
  "row_count": "integer",
  "execution_time_ms": "number",
  "tables_used": ["string"],
  "warning": "string|null"
}
```

### Comportamento

- **Sucesso**: `TextContent` (markdown) + `structuredContent` (dados tipados)
- **Erro**: `TextContent` (mensagem) + `isError=True` + `structuredContent=None`
- Spec compliance: `CallToolResult` retornado diretamente (bypass validacao em erros)

---

## Candidatas para Migracao Enhanced

| Tool | Prioridade | Schema Proposto |
|---|---|---|
| `consultar_schema` | Alta | `{table, columns: [{name, type, nullable, pk}], relationships}` |
| `consultar_valores_campo` | Alta | `{table, field, values: [], count}` |
| `consultar_logs` | Media | `{logs: [{timestamp, level, message}], count, filters}` |
| `status_servicos` | Media | `{services: [{name, status, last_deploy}]}` |
| `search_sessions` | Media | `{sessions: [{id, title, excerpt}], count}` |

---

## Features NAO Implementaveis (sem mudanca no SDK)

| Feature | Barreira | Alternativa Existente |
|---|---|---|
| Elicitation | `Context` nao exposto | `AskUserQuestion` via hooks |
| Progress Reporting | `Context` nao exposto | `PostToolUse` hooks + SSE |
| Resources | Sem `@resource` | Tools dedicadas (schema, memory) |
| Prompts | Sem `@prompt` | Skills YAML do agente |
| Tasks (async) | Experimental + sem Context | Threading atual (Teams bot) |

---

## Features Futuras para Acompanhar

| Feature | Spec | Relevancia | Notas |
|---|---|---|---|
| MCP Apps Extension | 2025-11-25 | Baixa | UI interativa via sandboxed iframes (Anthropic+OpenAI) |
| Tool Calling in Sampling | 2025-11-25 | Media | Servidor pede LLM usar tools durante sampling — loops agenticos |
| Extensions Framework | 2025-11-25 | Media | Extensions opcionais aditivas, composiveis, versionadas |
| Elicitation URL | 2025-11-25 | Media | Elicitation via URL (OAuth, pagamentos) — complementa Form |
| Streamable HTTP | 2025-03-26 | N/A | Substitui HTTP+SSE (deprecated). Sistema usa in-process |

**Adocao MCP (fev/2026)**: 10,000+ servidores publicos. Adotado por Claude, ChatGPT, Cursor, Gemini, VS Code.
Doado para AAIF (Linux Foundation) em dez/2025 — co-fundadores: Anthropic, Block, OpenAI.

---

## Proximos Passos

1. Migrar `schema_mcp_tool.py` para Enhanced (alta prioridade)
2. Migrar `render_logs_tool.py` para Enhanced (media prioridade)
3. Monitorar `claude-agent-sdk` >= 0.2.0 para suporte nativo a outputSchema
4. Avaliar migracao para `mcp.server.fastmcp.FastMCP` se SDK nao evoluir

---

## Fontes

- [MCP Spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [Anthropic: Donating MCP to AAIF](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- [MCP Features Guide — WorkOS](https://workos.com/blog/mcp-features-guide)
- [15 Best Practices for MCP Servers — The New Stack](https://thenewstack.io/15-best-practices-for-building-mcp-servers-in-production/)
- [MCP Auth Guide — Stack Overflow](https://stackoverflow.blog/2026/01/21/is-that-allowed-authentication-and-authorization-in-model-context-protocol)
