#!/usr/bin/env python3
"""
Servidor MCP Estável para Sistema de Fretes
Versão compatível com mcp==1.0.0
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

# Criar instância do servidor
server = Server("frete-sistema")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista ferramentas disponíveis"""
    return [
        Tool(
            name="consultar_embarques",
            description="Consulta embarques do sistema com filtros opcionais",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Status do embarque (ativo, cancelado)"},
                    "limite": {"type": "integer", "default": 10, "description": "Limite de resultados"}
                }
            }
        ),
        Tool(
            name="consultar_fretes",
            description="Consulta fretes pendentes de aprovação",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_aprovacao": {"type": "string", "description": "Status da aprovação"},
                    "limite": {"type": "integer", "default": 10}
                }
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
                    "limite": {"type": "integer", "default": 10}
                }
            }
        ),
        Tool(
            name="estatisticas_sistema",
            description="Retorna estatísticas gerais do sistema",
            inputSchema={
                "type": "object",
                "properties": {
                    "periodo_dias": {"type": "integer", "default": 30}
                }
            }
        ),
        Tool(
            name="consultar_portaria",
            description="Consulta veículos na portaria",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Status na portaria"},
                    "limite": {"type": "integer", "default": 10}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executa ferramentas do sistema"""
    
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
            elif name == "estatisticas_sistema":
                return await _estatisticas_sistema(arguments)
            elif name == "consultar_portaria":
                return await _consultar_portaria(arguments)
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

# Implementação das funções
async def _consultar_embarques(args: dict) -> list[TextContent]:
    """Consulta embarques do sistema"""
    try:
        from app.embarques.models import Embarque
        from sqlalchemy import and_
        
        query = Embarque.query
        filtros = []
        
        if args.get('status'):
            filtros.append(Embarque.status == args['status'])
        
        if filtros:
            query = query.filter(and_(*filtros))
        
        limite = args.get('limite', 10)
        embarques = query.order_by(Embarque.id.desc()).limit(limite).all()
        
        resultado = []
        for embarque in embarques:
            resultado.append({
                'id': embarque.id,
                'numero': embarque.numero,
                'status': embarque.status,
                'data_embarque': embarque.data_embarque.isoformat() if embarque.data_embarque else None,
                'transportadora': embarque.transportadora.nome if embarque.transportadora else None,
                'total_fretes': len(embarque.fretes) if embarque.fretes else 0
            })
        
        return [TextContent(
            type="text",
            text=json.dumps({
                '📦 Embarques': f'{len(resultado)} encontrados',
                'dados': resultado
            }, indent=2, ensure_ascii=False)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao consultar embarques: {str(e)}"
        )]

async def _consultar_fretes(args: dict) -> list[TextContent]:
    """Consulta fretes do sistema"""
    try:
        from app.fretes.models import Frete
        from sqlalchemy import and_
        
        query = Frete.query
        filtros = []
        
        if args.get('status_aprovacao'):
            filtros.append(Frete.status_aprovacao == args['status_aprovacao'])
        
        if filtros:
            query = query.filter(and_(*filtros))
        
        limite = args.get('limite', 10)
        fretes = query.order_by(Frete.id.desc()).limit(limite).all()
        
        resultado = []
        for frete in fretes:
            resultado.append({
                'id': frete.id,
                'embarque_numero': frete.embarque.numero if frete.embarque else None,
                'transportadora': frete.transportadora.nome if frete.transportadora else None,
                'valor_cotado': float(frete.valor_cotado) if frete.valor_cotado else None,
                'status_aprovacao': frete.status_aprovacao,
                'tem_cte': bool(frete.numero_cte)
            })
        
        return [TextContent(
            type="text",
            text=json.dumps({
                '🚛 Fretes': f'{len(resultado)} encontrados',
                'dados': resultado
            }, indent=2, ensure_ascii=False)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao consultar fretes: {str(e)}"
        )]

async def _consultar_monitoramento(args: dict) -> list[TextContent]:
    """Consulta entregas em monitoramento"""
    try:
        from app.monitoramento.models import EntregaMonitorada
        from sqlalchemy import and_
        
        query = EntregaMonitorada.query
        filtros = []
        
        if args.get('nf_numero'):
            filtros.append(EntregaMonitorada.numero_nf == args['nf_numero'])
        
        if args.get('pendencia_financeira') is not None:
            filtros.append(EntregaMonitorada.pendencia_financeira == args['pendencia_financeira'])
        
        if filtros:
            query = query.filter(and_(*filtros))
        
        limite = args.get('limite', 10)
        entregas = query.order_by(EntregaMonitorada.id.desc()).limit(limite).all()
        
        resultado = []
        for entrega in entregas:
            resultado.append({
                'id': entrega.id,
                'numero_nf': entrega.numero_nf,
                'status': entrega.status_finalizacao,
                'cliente': entrega.cliente,
                'cidade_destino': entrega.cidade_destino,
                'pendencia_financeira': entrega.pendencia_financeira,
                'valor_nf': float(entrega.valor_nf) if entrega.valor_nf else None
            })
        
        return [TextContent(
            type="text",
            text=json.dumps({
                '📋 Entregas Monitoradas': f'{len(resultado)} encontradas',
                'dados': resultado
            }, indent=2, ensure_ascii=False)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao consultar monitoramento: {str(e)}"
        )]

async def _estatisticas_sistema(args: dict) -> list[TextContent]:
    """Retorna estatísticas do sistema"""
    try:
        periodo_dias = args.get('periodo_dias', 30)
        data_inicio = datetime.now() - timedelta(days=periodo_dias)
        
        from app.embarques.models import Embarque
        from app.fretes.models import Frete
        from app.monitoramento.models import EntregaMonitorada
        from app.transportadoras.models import Transportadora
        from sqlalchemy import func
        
        # Estatísticas básicas
        total_embarques = Embarque.query.count()
        embarques_ativos = Embarque.query.filter(Embarque.status == 'ativo').count()
        
        total_fretes = Frete.query.count()
        fretes_pendentes = Frete.query.filter(Frete.status_aprovacao == 'pendente').count()
        fretes_aprovados = Frete.query.filter(Frete.status_aprovacao == 'aprovado').count()
        
        total_entregas = EntregaMonitorada.query.count()
        entregas_entregues = EntregaMonitorada.query.filter(
            EntregaMonitorada.status_finalizacao == 'Entregue'
        ).count()
        
        pendencias_financeiras = EntregaMonitorada.query.filter(
            EntregaMonitorada.pendencia_financeira == True
        ).count()
        
        total_transportadoras = Transportadora.query.count()
        transportadoras_ativas = Transportadora.query.filter(
            Transportadora.ativa == True
        ).count()
        
        resultado = {
            '📊 Período Analisado': f'Últimos {periodo_dias} dias',
            '📦 Embarques': {
                'Total': total_embarques,
                'Ativos': embarques_ativos,
                'Cancelados': total_embarques - embarques_ativos
            },
            '🚛 Fretes': {
                'Total': total_fretes,
                'Pendentes Aprovação': fretes_pendentes,
                'Aprovados': fretes_aprovados,
                '% Aprovação': round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0
            },
            '📋 Entregas': {
                'Total Monitoradas': total_entregas,
                'Entregues': entregas_entregues,
                'Pendências Financeiras': pendencias_financeiras,
                '% Entrega': round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0
            },
            '🚚 Transportadoras': {
                'Total': total_transportadoras,
                'Ativas': transportadoras_ativas
            }
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(resultado, indent=2, ensure_ascii=False)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao gerar estatísticas: {str(e)}"
        )]

async def _consultar_portaria(args: dict) -> list[TextContent]:
    """Consulta registros da portaria"""
    try:
        from app.portaria.models import ControlePortaria
        from sqlalchemy import and_
        
        query = ControlePortaria.query
        filtros = []
        
        if args.get('status'):
            filtros.append(ControlePortaria.status == args['status'])
        
        if filtros:
            query = query.filter(and_(*filtros))
        
        limite = args.get('limite', 10)
        registros = query.order_by(ControlePortaria.data_chegada.desc()).limit(limite).all()
        
        resultado = []
        for registro in registros:
            resultado.append({
                'id': registro.id,
                'placa': registro.placa,
                'status': registro.status,
                'data_chegada': registro.data_chegada.isoformat() if registro.data_chegada else None,
                'tipo_carga': registro.tipo_carga,
                'motorista': registro.motorista.nome if registro.motorista else None
            })
        
        return [TextContent(
            type="text",
            text=json.dumps({
                '🚪 Portaria': f'{len(resultado)} registros',
                'dados': resultado
            }, indent=2, ensure_ascii=False)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao consultar portaria: {str(e)}"
        )]

@server.list_resources()
async def list_resources() -> list[Resource]:
    """Lista recursos disponíveis"""
    return [
        Resource(
            uri=AnyUrl("frete://help/comandos"),
            name="Comandos Disponíveis",
            description="Lista de comandos que você pode usar",
            mimeType="text/markdown",
        )
    ]

@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Lê recursos do sistema"""
    if str(uri) == "frete://help/comandos":
        return """# 🚀 Sistema de Fretes - Comandos MCP

## 📋 Comandos Disponíveis

### 🔍 Consultas Básicas
- **"Quais embarques estão ativos?"** → consultar_embarques
- **"Mostre fretes pendentes"** → consultar_fretes
- **"Status da NF 123456"** → consultar_monitoramento

### 📊 Análises
- **"Estatísticas dos últimos 30 dias"** → estatisticas_sistema
- **"Quantos veículos na portaria?"** → consultar_portaria

### 💡 Exemplos Práticos

**Para Gestores:**
- "Quantos embarques saíram esta semana?"
- "Qual o percentual de fretes aprovados?"
- "Há entregas em atraso?"

**Para Operação:**
- "Quais veículos estão aguardando?"
- "Embarques sem CTe"
- "Pedidos prontos para embarque"

**Para Financeiro:**
- "Fretes pendentes de pagamento"
- "Pendências financeiras em aberto"
- "Relatório do mês"

---
*Sistema integrado via Model Context Protocol*
"""
    else:
        return "Recurso não encontrado"

async def main():
    """Função principal"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frete-sistema",
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
        print("\n👋 Servidor MCP finalizado")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc() 