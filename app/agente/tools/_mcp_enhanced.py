"""
Enhanced MCP Server Factory — Suporte a outputSchema + structuredContent.

O wrapper `claude_agent_sdk.create_sdk_mcp_server` (v0.1.38) NÃO suporta:
- `outputSchema` no Tool (MCP spec 2025-06-18)
- `structuredContent` no CallToolResult (MCP spec 2025-06-18)

Este módulo fornece um factory drop-in que adiciona essas capacidades,
mantendo backward compatibility com a interface existente do SDK.

Uso:
    from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

    @enhanced_tool(
        "consultar_sql",
        "Descrição da tool...",
        {"pergunta": str},
        annotations=ToolAnnotations(readOnlyHint=True, ...),
        output_schema={
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
                "rows": {"type": "array"},
                "row_count": {"type": "integer"},
            },
        },
    )
    async def consultar_sql(args):
        # Retornar AMBOS: content (TextContent) + structuredContent (dict)
        return {
            "content": [{"type": "text", "text": "Resultado formatado..."}],
            "structuredContent": {"columns": [...], "rows": [...], "row_count": 42},
        }

Referências:
    - MCP Spec 2025-06-18: Structured Output
    - mcp.server.Server.call_tool: suporta CallToolResult direto
    - mcp.types.Tool: campo outputSchema (dict | None)
    - mcp.types.CallToolResult: campo structuredContent (dict | None)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =====================================================================
# ENHANCED TOOL DATACLASS
# =====================================================================

@dataclass
class EnhancedMcpTool(Generic[T]):
    """
    Tool definition com suporte a outputSchema.

    Extensão do SdkMcpTool que adiciona `output_schema` para
    MCP Structured Output (spec 2025-06-18).

    Campos adicionais vs SdkMcpTool:
        output_schema: JSON Schema do output estruturado (opcional).
            Se definido, a tool DEVE retornar structuredContent no handler.
    """
    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[T], Awaitable[dict[str, Any]]]
    annotations: Any | None = None  # mcp.types.ToolAnnotations
    output_schema: dict[str, Any] | None = field(default=None)


# =====================================================================
# ENHANCED TOOL DECORATOR
# =====================================================================

def enhanced_tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any],
    annotations: Any | None = None,
    output_schema: dict[str, Any] | None = None,
) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], EnhancedMcpTool[Any]]:
    """
    Decorator para definir MCP tools com suporte a outputSchema.

    Drop-in replacement para `@tool` do claude_agent_sdk, com campo
    `output_schema` adicional.

    Args:
        name: Identificador único da tool
        description: Descrição legível
        input_schema: Schema dos parâmetros de entrada
        annotations: ToolAnnotations (readOnlyHint, etc.)
        output_schema: JSON Schema do output estruturado (opcional)

    Returns:
        EnhancedMcpTool instance

    Exemplo:
        @enhanced_tool(
            "minha_tool", "Faz algo", {"param": str},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )
        async def minha_tool(args):
            return {
                "content": [{"type": "text", "text": "Resultado legível"}],
                "structuredContent": {"result": "dados estruturados"},
            }
    """
    def decorator(
        handler: Callable[[Any], Awaitable[dict[str, Any]]],
    ) -> EnhancedMcpTool[Any]:
        return EnhancedMcpTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            annotations=annotations,
            output_schema=output_schema,
        )
    return decorator


# =====================================================================
# ENHANCED MCP SERVER FACTORY
# =====================================================================

def create_enhanced_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[EnhancedMcpTool[Any]] | None = None,
):
    """
    Cria MCP server in-process com suporte a outputSchema/structuredContent.

    Drop-in replacement para `create_sdk_mcp_server` do claude_agent_sdk,
    com suporte às features da MCP spec 2025-06-18:

    1. `outputSchema` no Tool (list_tools): informa ao client o schema do output
    2. `structuredContent` no CallToolResult (call_tool): retorna dados tipados

    O handler pode retornar:
        - {"content": [...]}  — apenas TextContent (backward compat)
        - {"content": [...], "structuredContent": {...}}  — ambos (recomendado)
        - {"content": [...], "is_error": True}  — erro

    Quando `structuredContent` está presente, o MCP SDK Server automaticamente
    o inclui no CallToolResult enviado ao client.

    Args:
        name: Nome do MCP server
        version: Versão do server
        tools: Lista de EnhancedMcpTool instances

    Returns:
        McpSdkServerConfig compatível com ClaudeAgentOptions.mcp_servers
    """
    from mcp.server import Server
    from mcp.types import (
        CallToolResult,
        ImageContent,
        TextContent,
        Tool,
    )
    from claude_agent_sdk import McpSdkServerConfig

    server = Server(name, version=version)

    if tools:
        tool_map = {tool_def.name: tool_def for tool_def in tools}

        @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
        async def list_tools() -> list[Tool]:
            """Return available tools with outputSchema support."""
            tool_list = []
            for tool_def in tools:
                # Convert input_schema to JSON Schema format
                if isinstance(tool_def.input_schema, dict):
                    if (
                        "type" in tool_def.input_schema
                        and "properties" in tool_def.input_schema
                    ):
                        schema = tool_def.input_schema
                    else:
                        properties = {}
                        for param_name, param_type in tool_def.input_schema.items():
                            if param_type is str:
                                properties[param_name] = {"type": "string"}
                            elif param_type is int:
                                properties[param_name] = {"type": "integer"}
                            elif param_type is float:
                                properties[param_name] = {"type": "number"}
                            elif param_type is bool:
                                properties[param_name] = {"type": "boolean"}
                            else:
                                properties[param_name] = {"type": "string"}
                        schema = {
                            "type": "object",
                            "properties": properties,
                            "required": list(properties.keys()),
                        }
                else:
                    schema = {"type": "object", "properties": {}}

                # Build Tool with optional outputSchema
                tool_kwargs: dict[str, Any] = {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "inputSchema": schema,
                }
                if tool_def.annotations is not None:
                    tool_kwargs["annotations"] = tool_def.annotations
                if tool_def.output_schema is not None:
                    tool_kwargs["outputSchema"] = tool_def.output_schema

                tool_list.append(Tool(**tool_kwargs))

            return tool_list

        @server.call_tool()  # type: ignore[untyped-decorator]
        async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
            """Execute tool with structuredContent support."""
            if name not in tool_map:
                raise ValueError(f"Tool '{name}' not found")

            tool_def = tool_map[name]
            result = await tool_def.handler(arguments)

            # Build content list (backward compat — always present)
            content: list[TextContent | ImageContent] = []
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        content.append(TextContent(type="text", text=item["text"]))
                    if item.get("type") == "image":
                        content.append(
                            ImageContent(
                                type="image",
                                data=item["data"],
                                mimeType=item["mimeType"],
                            )
                        )

            # Check for structuredContent (MCP spec 2025-06-18)
            structured = result.get("structuredContent")
            is_error = result.get("is_error", False)

            # ALWAYS return CallToolResult directly.
            # This bypasses the Server's output validation which rejects
            # missing structuredContent when outputSchema is defined.
            # For errors (is_error=True), structuredContent is None — correct per spec.
            # For success with outputSchema, structuredContent carries the typed data.
            return CallToolResult(
                content=content,
                structuredContent=structured if not is_error else None,
                isError=is_error,
            )

    return McpSdkServerConfig(type="sdk", name=name, instance=server)
