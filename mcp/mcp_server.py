#!/usr/bin/env python3
"""
Servidor MCP para Sistema de Fretes
Permite integração de IA com dados do sistema de fretes através do Model Context Protocol
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

import anyio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
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

# Importar sistema Flask
sys.path.append('..')
from app import create_app


class FreteSystemMCPServer:
    """Servidor MCP para o Sistema de Fretes"""
    
    def __init__(self):
        self.app = create_app()
        self.server = Server("frete-sistema")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers do MCP"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Lista todas as ferramentas disponíveis"""
            return [
                Tool(
                    name="consultar_embarques",
                    description="Consulta embarques do sistema com filtros opcionais",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "description": "Status do embarque (ativo, cancelado)"},
                            "data_inicio": {"type": "string", "description": "Data início no formato YYYY-MM-DD"},
                            "data_fim": {"type": "string", "description": "Data fim no formato YYYY-MM-DD"},
                            "transportadora": {"type": "string", "description": "Nome da transportadora"},
                            "limite": {"type": "integer", "default": 10, "description": "Limite de resultados"}
                        }
                    }
                ),
                Tool(
                    name="consultar_fretes",
                    description="Consulta fretes do sistema com filtros",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "embarque_id": {"type": "integer", "description": "ID do embarque"},
                            "transportadora": {"type": "string", "description": "Nome da transportadora"},
                            "status_aprovacao": {"type": "string", "description": "Status da aprovação"},
                            "tem_cte": {"type": "boolean", "description": "Se possui CTe"},
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
                            "status": {"type": "string", "description": "Status da entrega"},
                            "pendencia_financeira": {"type": "boolean", "description": "Se tem pendência financeira"},
                            "limite": {"type": "integer", "default": 10}
                        }
                    }
                ),
                Tool(
                    name="consultar_transportadoras",
                    description="Lista transportadoras cadastradas",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ativa": {"type": "boolean", "description": "Se a transportadora está ativa"},
                            "freteiro": {"type": "boolean", "description": "Se é freteiro"},
                            "nome": {"type": "string", "description": "Filtro por nome"}
                        }
                    }
                ),
                Tool(
                    name="consultar_pedidos",
                    description="Consulta pedidos do sistema",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "numero_pedido": {"type": "string", "description": "Número do pedido"},
                            "status": {"type": "string", "description": "Status do pedido"},
                            "cliente": {"type": "string", "description": "Nome do cliente"},
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
                            "periodo_dias": {"type": "integer", "default": 30, "description": "Período em dias para estatísticas"}
                        }
                    }
                ),
                Tool(
                    name="consultar_portaria",
                    description="Consulta registros da portaria",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "description": "Status na portaria"},
                            "placa": {"type": "string", "description": "Placa do veículo"},
                            "data_inicio": {"type": "string", "description": "Data início"},
                            "limite": {"type": "integer", "default": 10}
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Executa uma ferramenta específica"""
            
            with self.app.app_context():
                if name == "consultar_embarques":
                    return await self._consultar_embarques(arguments)
                elif name == "consultar_fretes":
                    return await self._consultar_fretes(arguments)
                elif name == "consultar_monitoramento":
                    return await self._consultar_monitoramento(arguments)
                elif name == "consultar_transportadoras":
                    return await self._consultar_transportadoras(arguments)
                elif name == "consultar_pedidos":
                    return await self._consultar_pedidos(arguments)
                elif name == "estatisticas_sistema":
                    return await self._estatisticas_sistema(arguments)
                elif name == "consultar_portaria":
                    return await self._consultar_portaria(arguments)
                else:
                    raise ValueError(f"Ferramenta desconhecida: {name}")
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """Lista recursos disponíveis"""
            return [
                Resource(
                    uri=AnyUrl("frete://config/database"),
                    name="Configuração do Banco de Dados",
                    description="Informações sobre a configuração do banco",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("frete://schemas/embarques"),
                    name="Schema de Embarques",
                    description="Estrutura das tabelas de embarques",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("frete://schemas/fretes"),
                    name="Schema de Fretes",
                    description="Estrutura das tabelas de fretes",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("frete://help/api"),
                    name="Ajuda da API",
                    description="Documentação das funcionalidades disponíveis",
                    mimeType="text/markdown",
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            """Lê um recurso específico"""
            
            if str(uri) == "frete://config/database":
                return json.dumps({
                    "driver": "PostgreSQL",
                    "tabelas_principais": [
                        "embarques", "fretes", "entregas_monitoradas", 
                        "transportadoras", "pedidos", "controle_portaria"
                    ],
                    "relacionamentos": {
                        "embarques": "contém vários fretes e pedidos",
                        "fretes": "vinculado a embarque e transportadora",
                        "entregas_monitoradas": "vinculado a pedidos",
                        "controle_portaria": "registra movimentação de veículos"
                    }
                }, indent=2)
            
            elif str(uri) == "frete://schemas/embarques":
                return json.dumps({
                    "tabela": "embarques",
                    "campos_principais": {
                        "id": "integer - Chave primária",
                        "numero": "string - Número único do embarque",
                        "status": "string - ativo/cancelado",
                        "data_embarque": "datetime - Data/hora da saída",
                        "transportadora_id": "integer - FK transportadora",
                        "observacoes": "text - Observações gerais"
                    },
                    "relacionamentos": {
                        "pedidos": "via embarque_itens",
                        "fretes": "direto via embarque_id",
                        "transportadora": "via transportadora_id"
                    }
                }, indent=2)
            
            elif str(uri) == "frete://schemas/fretes":
                return json.dumps({
                    "tabela": "fretes",
                    "campos_principais": {
                        "id": "integer - Chave primária",
                        "embarque_id": "integer - FK embarque",
                        "transportadora_id": "integer - FK transportadora",
                        "valor_cotado": "decimal - Valor cotado",
                        "valor_considerado": "decimal - Valor considerado",
                        "status_aprovacao": "string - pendente/aprovado/rejeitado",
                        "numero_cte": "string - Número do CTe",
                        "valor_cte": "decimal - Valor do CTe"
                    },
                    "status_possiveis": [
                        "pendente", "aprovado", "rejeitado", "pago"
                    ]
                }, indent=2)
            
            elif str(uri) == "frete://help/api":
                return """# Sistema de Fretes - API MCP

## Ferramentas Disponíveis

### consultar_embarques
Consulta embarques com filtros opcionais:
- `status`: ativo, cancelado
- `data_inicio`, `data_fim`: Período
- `transportadora`: Nome da transportadora
- `limite`: Número máximo de resultados

### consultar_fretes
Consulta fretes do sistema:
- `embarque_id`: ID específico do embarque
- `transportadora`: Nome da transportadora
- `status_aprovacao`: pendente, aprovado, rejeitado
- `tem_cte`: true/false se possui CTe

### consultar_monitoramento
Consulta entregas em monitoramento:
- `nf_numero`: Número da nota fiscal
- `status`: Status da entrega
- `pendencia_financeira`: true/false

### estatisticas_sistema
Retorna estatísticas gerais:
- `periodo_dias`: Período para cálculo (padrão 30 dias)

## Exemplos de Uso

```json
{
  "name": "consultar_embarques",
  "arguments": {
    "status": "ativo",
    "limite": 5
  }
}
```

```json
{
  "name": "estatisticas_sistema",
  "arguments": {
    "periodo_dias": 7
  }
}
```
"""
            
            else:
                raise ValueError(f"Recurso não encontrado: {uri}")
    
    # Métodos para execução das ferramentas
    async def _consultar_embarques(self, args: dict) -> list[TextContent]:
        """Consulta embarques do sistema"""
        try:
            from app.embarques.models import Embarque
            from sqlalchemy import and_
            
            query = Embarque.query
            filtros = []
            
            if args.get('status'):
                filtros.append(Embarque.status == args['status'])
            
            if args.get('data_inicio'):
                data_inicio = datetime.strptime(args['data_inicio'], '%Y-%m-%d')
                filtros.append(Embarque.data_embarque >= data_inicio)
            
            if args.get('data_fim'):
                data_fim = datetime.strptime(args['data_fim'], '%Y-%m-%d')
                filtros.append(Embarque.data_embarque <= data_fim)
            
            if args.get('transportadora'):
                from app.transportadoras.models import Transportadora
                transp = Transportadora.query.filter(
                    Transportadora.nome.ilike(f"%{args['transportadora']}%")
                ).first()
                if transp:
                    filtros.append(Embarque.transportadora_id == transp.id)
            
            if filtros:
                query = query.filter(and_(*filtros))
            
            limite = args.get('limite', 10)
            embarques = query.limit(limite).all()
            
            resultado = []
            for embarque in embarques:
                resultado.append({
                    'id': embarque.id,
                    'numero': embarque.numero,
                    'status': embarque.status,
                    'data_embarque': embarque.data_embarque.isoformat() if embarque.data_embarque else None,
                    'transportadora': embarque.transportadora.nome if embarque.transportadora else None,
                    'observacoes': embarque.observacoes,
                    'total_fretes': len(embarque.fretes) if embarque.fretes else 0
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'total_encontrados': len(resultado),
                    'embarques': resultado
                }, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao consultar embarques: {str(e)}"
            )]
    
    async def _consultar_fretes(self, args: dict) -> list[TextContent]:
        """Consulta fretes do sistema"""
        try:
            from app.fretes.models import Frete
            from sqlalchemy import and_
            
            query = Frete.query
            filtros = []
            
            if args.get('embarque_id'):
                filtros.append(Frete.embarque_id == args['embarque_id'])
            
            if args.get('transportadora'):
                from app.transportadoras.models import Transportadora
                transp = Transportadora.query.filter(
                    Transportadora.nome.ilike(f"%{args['transportadora']}%")
                ).first()
                if transp:
                    filtros.append(Frete.transportadora_id == transp.id)
            
            if args.get('status_aprovacao'):
                filtros.append(Frete.status_aprovacao == args['status_aprovacao'])
            
            if args.get('tem_cte') is not None:
                if args['tem_cte']:
                    filtros.append(Frete.numero_cte.isnot(None))
                else:
                    filtros.append(Frete.numero_cte.is_(None))
            
            if filtros:
                query = query.filter(and_(*filtros))
            
            limite = args.get('limite', 10)
            fretes = query.limit(limite).all()
            
            resultado = []
            for frete in fretes:
                resultado.append({
                    'id': frete.id,
                    'embarque_numero': frete.embarque.numero if frete.embarque else None,
                    'transportadora': frete.transportadora.nome if frete.transportadora else None,
                    'valor_cotado': float(frete.valor_cotado) if frete.valor_cotado else None,
                    'valor_considerado': float(frete.valor_considerado) if frete.valor_considerado else None,
                    'status_aprovacao': frete.status_aprovacao,
                    'numero_cte': frete.numero_cte,
                    'valor_cte': float(frete.valor_cte) if frete.valor_cte else None
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'total_encontrados': len(resultado),
                    'fretes': resultado
                }, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao consultar fretes: {str(e)}"
            )]
    
    async def _consultar_monitoramento(self, args: dict) -> list[TextContent]:
        """Consulta entregas em monitoramento"""
        try:
            from app.monitoramento.models import EntregaMonitorada
            from sqlalchemy import and_
            
            query = EntregaMonitorada.query
            filtros = []
            
            if args.get('nf_numero'):
                filtros.append(EntregaMonitorada.nf_numero == args['nf_numero'])
            
            if args.get('status'):
                filtros.append(EntregaMonitorada.status_finalizacao == args['status'])
            
            if args.get('pendencia_financeira') is not None:
                filtros.append(EntregaMonitorada.pendencia_financeira == args['pendencia_financeira'])
            
            if filtros:
                query = query.filter(and_(*filtros))
            
            limite = args.get('limite', 10)
            entregas = query.limit(limite).all()
            
            resultado = []
            for entrega in entregas:
                resultado.append({
                    'id': entrega.id,
                    'nf_numero': entrega.nf_numero,
                    'status_finalizacao': entrega.status_finalizacao,
                    'cliente': entrega.cliente,
                    'cidade_destino': entrega.cidade_destino,
                    'data_embarque': entrega.data_embarque.isoformat() if entrega.data_embarque else None,
                    'data_prevista': entrega.data_prevista.isoformat() if entrega.data_prevista else None,
                    'pendencia_financeira': entrega.pendencia_financeira,
                    'valor_nf': float(entrega.valor_nf) if entrega.valor_nf else None
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'total_encontrados': len(resultado),
                    'entregas': resultado
                }, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao consultar monitoramento: {str(e)}"
            )]
    
    async def _consultar_transportadoras(self, args: dict) -> list[TextContent]:
        """Consulta transportadoras"""
        try:
            from app.transportadoras.models import Transportadora
            from sqlalchemy import and_
            
            query = Transportadora.query
            filtros = []
            
            if args.get('ativa') is not None:
                filtros.append(Transportadora.ativa == args['ativa'])
            
            if args.get('freteiro') is not None:
                filtros.append(Transportadora.freteiro == args['freteiro'])
            
            if args.get('nome'):
                filtros.append(Transportadora.nome.ilike(f"%{args['nome']}%"))
            
            if filtros:
                query = query.filter(and_(*filtros))
            
            transportadoras = query.all()
            
            resultado = []
            for transp in transportadoras:
                resultado.append({
                    'id': transp.id,
                    'nome': transp.nome,
                    'cnpj': transp.cnpj,
                    'ativa': transp.ativa,
                    'freteiro': transp.freteiro if hasattr(transp, 'freteiro') else False
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'total_encontrados': len(resultado),
                    'transportadoras': resultado
                }, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao consultar transportadoras: {str(e)}"
            )]
    
    async def _consultar_pedidos(self, args: dict) -> list[TextContent]:
        """Consulta pedidos"""
        try:
            from app.pedidos.models import Pedido
            from sqlalchemy import and_
            
            query = Pedido.query
            filtros = []
            
            if args.get('numero_pedido'):
                filtros.append(Pedido.numero_pedido == args['numero_pedido'])
            
            if args.get('status'):
                filtros.append(Pedido.status == args['status'])
            
            if args.get('cliente'):
                filtros.append(Pedido.cliente.ilike(f"%{args['cliente']}%"))
            
            if filtros:
                query = query.filter(and_(*filtros))
            
            limite = args.get('limite', 10)
            pedidos = query.limit(limite).all()
            
            resultado = []
            for pedido in pedidos:
                resultado.append({
                    'id': pedido.id,
                    'numero_pedido': pedido.numero_pedido,
                    'cliente': pedido.cliente,
                    'status': pedido.status,
                    'cidade_destino': pedido.cidade_destino,
                    'valor_total': float(pedido.valor_total) if pedido.valor_total else None,
                    'peso_total': float(pedido.peso_total) if pedido.peso_total else None
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'total_encontrados': len(resultado),
                    'pedidos': resultado
                }, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao consultar pedidos: {str(e)}"
            )]
    
    async def _estatisticas_sistema(self, args: dict) -> list[TextContent]:
        """Retorna estatísticas do sistema"""
        try:
            periodo_dias = args.get('periodo_dias', 30)
            data_inicio = datetime.now() - timedelta(days=periodo_dias)
            
            from app.embarques.models import Embarque
            from app.fretes.models import Frete
            from app.monitoramento.models import EntregaMonitorada
            from app.transportadoras.models import Transportadora
            from sqlalchemy import func
            
            # Estatísticas de embarques
            total_embarques = Embarque.query.count()
            embarques_periodo = Embarque.query.filter(
                Embarque.data_embarque >= data_inicio
            ).count()
            
            # Estatísticas de fretes
            total_fretes = Frete.query.count()
            fretes_aprovados = Frete.query.filter(
                Frete.status_aprovacao == 'aprovado'
            ).count()
            
            # Estatísticas de monitoramento
            total_entregas = EntregaMonitorada.query.count()
            entregas_entregues = EntregaMonitorada.query.filter(
                EntregaMonitorada.status_finalizacao == 'Entregue'
            ).count()
            
            # Estatísticas de transportadoras
            total_transportadoras = Transportadora.query.count()
            transportadoras_ativas = Transportadora.query.filter(
                Transportadora.ativa == True
            ).count()
            
            resultado = {
                'periodo_analisado_dias': periodo_dias,
                'data_inicio_periodo': data_inicio.isoformat(),
                'embarques': {
                    'total': total_embarques,
                    'no_periodo': embarques_periodo
                },
                'fretes': {
                    'total': total_fretes,
                    'aprovados': fretes_aprovados,
                    'percentual_aprovacao': round((fretes_aprovados / total_fretes * 100), 2) if total_fretes > 0 else 0
                },
                'entregas': {
                    'total': total_entregas,
                    'entregues': entregas_entregues,
                    'percentual_entrega': round((entregas_entregues / total_entregas * 100), 2) if total_entregas > 0 else 0
                },
                'transportadoras': {
                    'total': total_transportadoras,
                    'ativas': transportadoras_ativas
                }
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(resultado, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao gerar estatísticas: {str(e)}"
            )]
    
    async def _consultar_portaria(self, args: dict) -> list[TextContent]:
        """Consulta registros da portaria"""
        try:
            from app.portaria.models import ControlePortaria
            from sqlalchemy import and_
            
            query = ControlePortaria.query
            filtros = []
            
            if args.get('status'):
                filtros.append(ControlePortaria.status == args['status'])
            
            if args.get('placa'):
                filtros.append(ControlePortaria.placa.ilike(f"%{args['placa']}%"))
            
            if args.get('data_inicio'):
                data_inicio = datetime.strptime(args['data_inicio'], '%Y-%m-%d')
                filtros.append(ControlePortaria.data_chegada >= data_inicio)
            
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
                    'hora_chegada': str(registro.hora_chegada) if registro.hora_chegada else None,
                    'hora_entrada': str(registro.hora_entrada) if registro.hora_entrada else None,
                    'hora_saida': str(registro.hora_saida) if registro.hora_saida else None,
                    'tipo_carga': registro.tipo_carga,
                    'motorista_nome': registro.motorista.nome if registro.motorista else None
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'total_encontrados': len(resultado),
                    'registros_portaria': resultado
                }, indent=2, ensure_ascii=False)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Erro ao consultar portaria: {str(e)}"
            )]
    
    async def run(self):
        """Executa o servidor MCP"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="frete-sistema",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


async def main():
    """Função principal"""
    server = FreteSystemMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 