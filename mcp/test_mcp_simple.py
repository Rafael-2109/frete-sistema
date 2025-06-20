#!/usr/bin/env python3
"""
Servidor MCP Simplificado para testes
"""

import asyncio
import json
import sys
import os

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# Criar instância do servidor
server = Server("frete-sistema-test")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista ferramentas disponíveis"""
    return [
        Tool(
            name="test_sistema",
            description="Testa se o sistema está funcionando",
            inputSchema={
                "type": "object",
                "properties": {
                    "mensagem": {"type": "string", "description": "Mensagem de teste"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executa ferramentas"""
    if name == "test_sistema":
        mensagem = arguments.get("mensagem", "Sistema funcionando!")
        
        # Teste simples sem conexão com banco
        resultado = {
            "status": "OK",
            "mensagem": mensagem,
            "timestamp": "2025-06-20 07:30:00",
            "sistema": "Sistema de Fretes MCP"
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(resultado, indent=2, ensure_ascii=False)
        )]
    else:
        return [TextContent(
            type="text",
            text=f"Ferramenta '{name}' não encontrada"
        )]

async def main():
    """Função principal"""
    print("🚀 Testando Servidor MCP Simplificado...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frete-sistema-test",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Servidor teste finalizado")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc() 