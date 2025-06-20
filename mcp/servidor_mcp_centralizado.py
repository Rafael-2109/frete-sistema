#!/usr/bin/env python3
"""
Servidor MCP Centralizado para Sistema de Fretes
Permite acesso multiusuário via rede
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceResult,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

# Importar funcionalidades do servidor estável
from mcp_server_estavel import (
    _consultar_embarques,
    _consultar_fretes, 
    _consultar_monitoramento,
    _consultar_cliente_detalhado,
    _exportar_relatorio_cliente,
    _estatisticas_sistema,
    _consultar_portaria
)

# Criar instância do servidor
server = Server("frete-sistema-centralizado")

# Log de usuários (para auditoria)
user_log = []

def log_user_request(user_info: str, tool_name: str, arguments: dict):
    """Log das requisições dos usuários"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user': user_info,
        'tool': tool_name,
        'args': arguments
    }
    user_log.append(log_entry)
    print(f"📝 LOG: {user_info} usou {tool_name}")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista ferramentas disponíveis - mesmo do servidor estável"""
    return [
        Tool(
            name="consultar_embarques",
            description="Consulta embarques do sistema com filtros opcionais",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Status do embarque (ativo, cancelado)"},
                    "limite": {"type": "integer", "default": 10, "description": "Limite de resultados"},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["usuario"]
            }
        ),
        Tool(
            name="consultar_fretes",
            description="Consulta fretes pendentes de aprovação",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_aprovacao": {"type": "string", "description": "Status da aprovação"},
                    "limite": {"type": "integer", "default": 10},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["usuario"]
            }
        ),
        Tool(
            name="consultar_monitoramento",
            description="Consulta entregas em monitoramento",
            inputSchema={
                "type": "object",
                "properties": {
                    "nf_numero": {"type": "string", "description": "Número da NF"},
                    "pendencia_financeira": {"type": "boolean", "description": "Se tem pendência financeira"},
                    "limite": {"type": "integer", "default": 10},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["usuario"]
            }
        ),
        Tool(
            name="consultar_cliente_detalhado",
            description="Consulta detalhada de pedidos e entregas por cliente",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente": {"type": "string", "description": "Nome do cliente para buscar (ex: Assai)"},
                    "uf": {"type": "string", "description": "UF para filtrar (ex: SP)"},
                    "limite": {"type": "integer", "default": 5},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["cliente", "usuario"]
            }
        ),
        Tool(
            name="exportar_relatorio_cliente",
            description="Gera relatório Excel detalhado por cliente [AUDITADO]",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente": {"type": "string", "description": "Nome do cliente para o relatório"},
                    "uf": {"type": "string", "description": "UF para filtrar"},
                    "limite": {"type": "integer", "default": 10},
                    "nome_arquivo": {"type": "string", "default": "relatorio_cliente.xlsx"},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["cliente", "usuario"]
            }
        ),
        Tool(
            name="estatisticas_sistema",
            description="Retorna estatísticas gerais do sistema",
            inputSchema={
                "type": "object",
                "properties": {
                    "periodo_dias": {"type": "integer", "default": 30},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["usuario"]
            }
        ),
        Tool(
            name="consultar_portaria",
            description="Consulta veículos na portaria",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Status na portaria"},
                    "limite": {"type": "integer", "default": 10},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["usuario"]
            }
        ),
        Tool(
            name="listar_logs_uso",
            description="Lista logs de uso do sistema (apenas administradores)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limite": {"type": "integer", "default": 50},
                    "usuario": {"type": "string", "description": "Identificação do usuário (obrigatório)"}
                },
                "required": ["usuario"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executa ferramentas com log de usuário"""
    
    # Verificar se usuário foi fornecido
    user_info = arguments.get('usuario', 'ANONIMO')
    if user_info == 'ANONIMO':
        return [TextContent(
            type="text",
            text="❌ Identificação de usuário é obrigatória para usar o sistema"
        )]
    
    # Log da requisição
    log_user_request(user_info, name, {k: v for k, v in arguments.items() if k != 'usuario'})
    
    try:
        # Importar sistema Flask dentro da função
        from app import create_app
        app = create_app()
        
        with app.app_context():
            if name == "consultar_embarques":
                return await _consultar_embarques(arguments)
            elif name == "consultar_fretes":
                return await _consultar_fretes(arguments)
            elif name == "consultar_monitoramento":
                return await _consultar_monitoramento(arguments)
            elif name == "consultar_cliente_detalhado":
                return await _consultar_cliente_detalhado(arguments)
            elif name == "exportar_relatorio_cliente":
                # Adicionar informação do usuário no resultado
                result = await _exportar_relatorio_cliente(arguments)
                if result and len(result) > 0:
                    original_text = result[0].text
                    new_text = f"{original_text}\n\n👤 **Gerado por:** {user_info}\n📅 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                    result[0].text = new_text
                return result
            elif name == "estatisticas_sistema":
                return await _estatisticas_sistema(arguments)
            elif name == "consultar_portaria":
                return await _consultar_portaria(arguments)
            elif name == "listar_logs_uso":
                return await _listar_logs_uso(arguments)
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Ferramenta '{name}' não encontrada"
                )]
                
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao executar '{name}': {str(e)}"
        )]

async def _listar_logs_uso(args: dict) -> list[TextContent]:
    """Lista logs de uso do sistema"""
    try:
        user_info = args.get('usuario', 'ANONIMO')
        limite = args.get('limite', 50)
        
        # Verificar se é administrador (você pode implementar sua lógica aqui)
        if not user_info.lower().startswith('admin'):
            return [TextContent(
                type="text",
                text="❌ Acesso negado. Apenas administradores podem ver logs de uso."
            )]
        
        # Pegar logs mais recentes
        logs_recentes = user_log[-limite:] if len(user_log) > limite else user_log
        
        if not logs_recentes:
            return [TextContent(
                type="text",
                text="📋 Nenhum log de uso encontrado."
            )]
        
        resultado = ["📊 **LOGS DE USO DO SISTEMA MCP**\n"]
        
        for log in reversed(logs_recentes):  # Mais recentes primeiro
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%d/%m/%Y %H:%M:%S')
            resultado.append(f"🕒 **{timestamp}** | 👤 **{log['user']}** | 🔧 **{log['tool']}**")
        
        # Estatísticas resumidas
        total_requests = len(user_log)
        unique_users = len(set(log['user'] for log in user_log))
        most_used_tool = max(set(log['tool'] for log in user_log), 
                           key=lambda x: sum(1 for log in user_log if log['tool'] == x)) if user_log else "N/A"
        
        resultado.extend([
            f"\n📈 **ESTATÍSTICAS:**",
            f"• **Total de requisições:** {total_requests}",
            f"• **Usuários únicos:** {unique_users}",
            f"• **Ferramenta mais usada:** {most_used_tool}"
        ])
        
        return [TextContent(
            type="text",
            text="\n".join(resultado)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao listar logs: {str(e)}"
        )]

@server.list_resources()
async def list_resources() -> list[Resource]:
    """Lista recursos disponíveis"""
    return [
        Resource(
            uri=AnyUrl("frete://help/multiuser"),
            name="Guia Multiusuário",
            description="Como usar o sistema MCP com múltiplos usuários",
            mimeType="text/markdown",
        )
    ]

@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Lê recursos do sistema"""
    if str(uri) == "frete://help/multiuser":
        return """# 🚀 Sistema MCP Multiusuário

## 👥 Como Usar

### 🔑 Identificação Obrigatória
Todos os comandos requerem identificação:
```
"Consultar embarques ativos" + identificar como "João Silva"
```

### 📊 Ferramentas Disponíveis
- **consultar_embarques** - Lista embarques
- **consultar_fretes** - Fretes pendentes  
- **consultar_monitoramento** - Status entregas
- **consultar_cliente_detalhado** - Análise por cliente
- **exportar_relatorio_cliente** - Gera Excel (auditado)
- **estatisticas_sistema** - KPIs gerais
- **consultar_portaria** - Veículos na portaria

### 🔒 Auditoria e Logs
- Todas as ações são registradas
- Identificação do usuário em relatórios
- Logs disponíveis para administradores

### 💡 Exemplos de Uso
```
"Como administrador, listar logs de uso"
"Como Maria Santos, gerar Excel do Assai"
"Como João Silva, consultar fretes pendentes"
```
"""
    else:
        return "Recurso não encontrado"

async def main():
    """Função principal do servidor centralizado"""
    print("🌐 Iniciando Servidor MCP Centralizado...")
    print("👥 Modo Multiusuário Ativo")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frete-sistema-centralizado",
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
        print("\n👋 Servidor MCP Centralizado finalizado")
        print(f"📊 Total de requisições processadas: {len(user_log)}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc() 