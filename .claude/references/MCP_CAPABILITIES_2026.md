<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-08
-->
# MCP Capabilities — Estado do Sistema (Mai/2026)

> **Papel:** MCP Capabilities — Estado do Sistema (Mai/2026).

## Indice

- [Versoes Instaladas](#versoes-instaladas)
- [Capacidades por Camada](#capacidades-por-camada)
  - [claude_agent_sdk (wrapper)](#claude_agent_sdk-wrapper)
  - [mcp 1.26.0 (SDK direto)](#mcp-1260-sdk-direto)
  - [Enhanced Wrapper (`_mcp_enhanced.py`)](#enhanced-wrapper-_mcp_enhancedpy)
- [Servidores MCP Registrados (7)](#servidores-mcp-registrados-7)
  - [SDK 0.1.49–0.1.55 — Features por AgentDefinition](#sdk-01490155-features-por-agentdefinition)
- [Structured Output — SQL Tool (POC)](#structured-output-sql-tool-poc)
  - [outputSchema](#outputschema)
  - [Comportamento](#comportamento)
- [Features NAO Implementaveis (sem mudanca no SDK)](#features-nao-implementaveis-sem-mudanca-no-sdk)
- [Features Futuras para Acompanhar](#features-futuras-para-acompanhar)
- [Fontes](#fontes)

**Atualizado**: 2026-06-08

---

## Versoes Instaladas

| Package | Versao | Nota |
|---|---|---|
| `claude-agent-sdk` | 0.2.89 | CLI 2.1.162 (bundled). Atualizado de 0.2.87 em 2026-06-03 (0.2.88/CLI 2.1.161 -> 0.2.89/CLI 2.1.162). ZERO breaking no SDK Python: 0.2.89 e so bump do CLI bundled; 0.2.88 traz 1 bug fix `session_store` asyncio->anyio (so afeta runtime **trio**, que NAO usamos). Ganho real = CLI bundled (2.1.156 fix Opus 4.8 thinking blocks; 2.1.161 fix subagente background corrompendo stdout `claude -p`). 0.1.77: `skills` option em `ClaudeAgentOptions`. Historico completo (0.1.49->0.2.89) em `app/agente/SDK_CHANGELOG.md` |
| `anthropic` | 0.98.1 | Atualizado de 0.84.0 em 2026-05-09 |
| `mcp` | >=1.26.0 | MCP Python SDK (spec 2025-11-25). Pin atual em requirements.txt |

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

## Servidores MCP Registrados (7)

| Server | Arquivo | Tools | Enhanced | Annotations |
|---|---|---|---|---|
| sql | `text_to_sql_tool.py` | 1 | **SIM** (v2.0.0) | readOnly, idempotent, openWorld=F |
| memory | `memory_mcp_tool.py` | 11 | nao | readOnly/destructive, openWorld=F |
| schema | `schema_mcp_tool.py` | 2 | nao | readOnly, openWorld=F |
| sessions | `session_search_tool.py` | 4 | nao | readOnly, openWorld=F |
| render | `render_logs_tool.py` | 3 | nao | readOnly, openWorld=T |
| browser | `playwright_mcp_tool.py` | 13 | nao | variado, openWorld=T (SSW) |
| routes | `routes_search_tool.py` | 1 | nao | readOnly, openWorld=F |

**Total**: 35 tools registradas, todas com `openWorldHint` configurado.

### SDK 0.1.49–0.1.55 — Features por AgentDefinition

| Campo | Status | Nota |
|---|---|---|
| `AgentDefinition.skills` | **ADOTADO** | `agent_loader.py` passa skills nativas. Fallback texto para SDK < 0.1.49 |
| `AgentDefinition.disallowedTools` | **PRONTO** (0.1.51) | `agent_loader.py` parseia `disallowed_tools` do frontmatter. Nao aplicado por default — `tools` whitelist ja restringe |
| `AgentDefinition.maxTurns` | **PRONTO** (0.1.51) | `agent_loader.py` parseia `max_turns` do frontmatter. Disponivel quando necessario |
| `AgentDefinition.initialPrompt` | **PRONTO** (0.1.51) | `agent_loader.py` parseia `initial_prompt` do frontmatter |
| `AgentDefinition.mcpServers` | N/A | Apenas para servers stdio/sse/http EXTERNOS. In-process herdados via tool inheritance |
| `AgentDefinition.memory` | N/A | Conflita com sistema custom `mcp__memory__*` (PostgreSQL). Reservado |
| `typing.Annotated` params | **ADOTADO** (0.1.52) | `_mcp_enhanced.py:_python_type_to_json_schema()` + 34 tools com descriptions |
| `ToolPermissionContext.agent_id` | **ADOTADO** (0.1.52) | Mapa agent_id→agent_type em `permissions.py`. Audit trail + politicas opt-in |
| `ClaudeAgentOptions.session_id` | **ADOTADO** (0.1.52) | Naming deterministico do JSONL via `_build_options()` |
| `ResultMessage.errors` | **ADOTADO** (0.1.51) | Logado e propagado no StreamEvent `done` |
| MCP Runtime Control | Disponivel | `get_mcp_status()`, `toggle_mcp_server()` — requer ClaudeSDKClient |
| `get_context_usage()` | Disponivel (0.1.52) | NAO implementado — requer wiring 3-layer |

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

## Fontes

- [MCP Spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [Anthropic: Donating MCP to AAIF](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- [MCP Features Guide — WorkOS](https://workos.com/blog/mcp-features-guide)
- [15 Best Practices for MCP Servers — The New Stack](https://thenewstack.io/15-best-practices-for-building-mcp-servers-in-production/)
- [MCP Auth Guide — Stack Overflow](https://stackoverflow.blog/2026/01/21/is-that-allowed-authentication-and-authorization-in-model-context-protocol)
