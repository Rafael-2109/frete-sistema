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
            name="consultar_cliente_detalhado",
            description="Consulta detalhada de pedidos e entregas por cliente, incluindo status financeiro",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente": {"type": "string", "description": "Nome do cliente para buscar (ex: Assai)"},
                    "uf": {"type": "string", "description": "UF para filtrar (ex: SP)"},
                    "limite": {"type": "integer", "default": 5, "description": "Quantidade de pedidos mais recentes"}
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
        ),
        Tool(
            name="exportar_relatorio_cliente",
            description="Gera relatório Excel detalhado por cliente com pedidos, faturamento e monitoramento",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente": {"type": "string", "description": "Nome do cliente para o relatório (ex: Assai)"},
                    "uf": {"type": "string", "description": "UF para filtrar (ex: SP)"},
                    "limite": {"type": "integer", "default": 10, "description": "Quantidade de pedidos"},
                    "nome_arquivo": {"type": "string", "default": "relatorio_cliente.xlsx", "description": "Nome do arquivo Excel"}
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
            elif name == "consultar_cliente_detalhado":
                return await _consultar_cliente_detalhado(arguments)
            elif name == "estatisticas_sistema":
                return await _estatisticas_sistema(arguments)
            elif name == "consultar_portaria":
                return await _consultar_portaria(arguments)
            elif name == "exportar_relatorio_cliente":
                return await _exportar_relatorio_cliente(arguments)
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

async def _consultar_cliente_detalhado(args: dict) -> list[TextContent]:
    """Consulta detalhada por cliente com informações completas"""
    try:
        from app.pedidos.models import Pedido
        from app.faturamento.models import RelatorioFaturamentoImportado
        from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
        from sqlalchemy import and_, desc, func
        
        cliente_busca = args.get('cliente', '').strip()
        uf_filtro = args.get('uf', '').strip().upper()
        limite = args.get('limite', 5)
        
        if not cliente_busca:
            return [TextContent(
                type="text",
                text="❌ Nome do cliente é obrigatório para a consulta"
            )]
        
        # Buscar pedidos do cliente
        query = Pedido.query.filter(
            Pedido.raz_social_red.ilike(f"%{cliente_busca}%")
        )
        
        if uf_filtro:
            query = query.filter(Pedido.cod_uf == uf_filtro)
        
        # Ordenar por data de pedido mais recente
        pedidos = query.order_by(desc(Pedido.data_pedido)).limit(limite).all()
        
        if not pedidos:
            return [TextContent(
                type="text",
                text=f"❌ Nenhum pedido encontrado para '{cliente_busca}'" + (f" em {uf_filtro}" if uf_filtro else "")
            )]
        
        resultado = []
        resultado.append(f"🔍 **CONSULTA DETALHADA: {cliente_busca.upper()}**")
        if uf_filtro:
            resultado.append(f"📍 **Estado: {uf_filtro}**")
        resultado.append(f"📋 **{len(pedidos)} pedido(s) mais recente(s):**\n")
        
        for i, pedido in enumerate(pedidos, 1):
            resultado.append(f"**═══ PEDIDO {i} ═══**")
            
            # Informações básicas do pedido
            resultado.append(f"📦 **Pedido:** {pedido.num_pedido}")
            resultado.append(f"🏢 **Cliente:** {pedido.raz_social_red}")
            resultado.append(f"📅 **Data Pedido:** {pedido.data_pedido.strftime('%d/%m/%Y') if pedido.data_pedido else 'Não informada'}")
            resultado.append(f"🏙️ **Destino:** {pedido.nome_cidade}/{pedido.cod_uf}")
            resultado.append(f"💰 **Valor:** R$ {pedido.valor_saldo_total:,.2f}" if pedido.valor_saldo_total else "💰 **Valor:** Não informado")
            resultado.append(f"📊 **Status:** {pedido.status_calculado}")
            
            # Informações de agendamento
            if pedido.agendamento:
                resultado.append(f"📅 **Agendamento:** {pedido.agendamento.strftime('%d/%m/%Y')}")
            if pedido.protocolo:
                resultado.append(f"🔖 **Protocolo:** {pedido.protocolo}")
            
            # Se tem NF, buscar informações de faturamento
            if pedido.nf and pedido.nf.strip():
                resultado.append(f"📄 **NF:** {pedido.nf}")
                
                # Buscar no faturamento
                faturamento = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=pedido.nf
                ).first()
                
                if faturamento:
                    resultado.append(f"💳 **Faturado em:** {faturamento.data_fatura.strftime('%d/%m/%Y') if faturamento.data_fatura else 'Data não informada'}")
                    if faturamento.valor_total:
                        resultado.append(f"💵 **Valor NF:** R$ {faturamento.valor_total:,.2f}")
                        
                        # Calcular se é faturamento parcial
                        if pedido.valor_saldo_total and faturamento.valor_total:
                            saldo = pedido.valor_saldo_total - faturamento.valor_total
                            if saldo > 0:
                                resultado.append(f"⚠️ **Faturamento parcial - Saldo na carteira:** R$ {saldo:,.2f}")
                            elif saldo < 0:
                                resultado.append(f"ℹ️ **Faturamento superior ao pedido:** +R$ {abs(saldo):,.2f}")
                            else:
                                resultado.append(f"✅ **Faturamento completo**")
                
                # Buscar no monitoramento
                entrega = EntregaMonitorada.query.filter_by(
                    numero_nf=pedido.nf
                ).first()
                
                if entrega:
                    resultado.append(f"🚚 **Status Entrega:** {entrega.status_finalizacao or 'Em andamento'}")
                    
                    if entrega.data_embarque:
                        resultado.append(f"🚛 **Data Embarque:** {entrega.data_embarque.strftime('%d/%m/%Y')}")
                    
                    if entrega.transportadora:
                        resultado.append(f"🚐 **Transportadora:** {entrega.transportadora}")
                    
                    if entrega.data_entrega_prevista:
                        resultado.append(f"📅 **Previsão Entrega:** {entrega.data_entrega_prevista.strftime('%d/%m/%Y')}")
                    
                    if entrega.data_hora_entrega_realizada:
                        resultado.append(f"✅ **Entregue em:** {entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y às %H:%M')}")
                    
                    # Agendamentos
                    agendamentos = AgendamentoEntrega.query.filter_by(
                        entrega_id=entrega.id
                    ).order_by(desc(AgendamentoEntrega.criado_em)).limit(3).all()
                    
                    if agendamentos:
                        resultado.append(f"📋 **Agendamentos:**")
                        for ag in agendamentos:
                            status_ag = "✅" if ag.status == "confirmado" else "⏳"
                            data_ag = ag.data_agendada.strftime('%d/%m/%Y') if ag.data_agendada else "Sem data"
                            resultado.append(f"  {status_ag} {data_ag}" + (f" - {ag.observacao}" if ag.observacao else ""))
                    
                    if entrega.pendencia_financeira:
                        resultado.append(f"💰 **⚠️ PENDÊNCIA FINANCEIRA**")
                    
                    if entrega.observacao_operacional:
                        resultado.append(f"📝 **Obs. Operacional:** {entrega.observacao_operacional}")
            
            else:
                resultado.append(f"📄 **NF:** Não faturado")
                if pedido.data_embarque:
                    resultado.append(f"🚛 **Data Embarque:** {pedido.data_embarque.strftime('%d/%m/%Y')}")
            
            if i < len(pedidos):  # Não adiciona linha no último
                resultado.append("")
        
        # Resumo final
        resultado.append("\n📊 **RESUMO GERAL:**")
        total_valor_pedidos = sum(p.valor_saldo_total for p in pedidos if p.valor_saldo_total)
        pedidos_faturados = sum(1 for p in pedidos if p.nf and p.nf.strip())
        pedidos_embarcados = sum(1 for p in pedidos if p.data_embarque)
        
        resultado.append(f"• **Total de pedidos:** {len(pedidos)}")
        resultado.append(f"• **Valor total:** R$ {total_valor_pedidos:,.2f}")
        resultado.append(f"• **Faturados:** {pedidos_faturados}/{len(pedidos)}")
        resultado.append(f"• **Embarcados:** {pedidos_embarcados}/{len(pedidos)}")
        
        return [TextContent(
            type="text",
            text="\n".join(resultado)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao consultar cliente: {str(e)}"
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

### 🏢 Consultas por Cliente (NOVO!)
- **"Como estão as entregas do Assai de SP?"** → consultar_cliente_detalhado
- **"Últimos pedidos do Carrefour"** → consultar_cliente_detalhado
- **"Status financeiro dos pedidos da Renner"** → consultar_cliente_detalhado

### 📊 Análises
- **"Estatísticas dos últimos 30 dias"** → estatisticas_sistema
- **"Quantos veículos na portaria?"** → consultar_portaria

### 📋 Relatórios Excel (NOVO!)
- **"Gerar relatório Excel do Assai"** → exportar_relatorio_cliente
- **"Exportar dados do cliente X para Excel"** → exportar_relatorio_cliente
- **"Relatório financeiro detalhado por cliente"** → exportar_relatorio_cliente

### 🎯 Consulta Detalhada por Cliente

**Exemplo de pergunta:**
"Como estão as entregas do Assai de SP do último pedido?"

**Resposta esperada:**
```
🔍 CONSULTA DETALHADA: ASSAI
📍 Estado: SP
📋 1 pedido(s) mais recente(s):

═══ PEDIDO 1 ═══
📦 Pedido: VCD2519284
🏢 Cliente: Assai LJ 264
📅 Data Pedido: 10/06/2024
🏙️ Destino: São Paulo/SP
💰 Valor: R$ 1.250,00
📊 Status: FATURADO
📄 NF: 133526
💳 Faturado em: 15/06/2024
💵 Valor NF: R$ 465,61
⚠️ Faturamento parcial - Saldo na carteira: R$ 784,39
🚚 Status Entrega: Em andamento
🚛 Data Embarque: 20/06/2024
🚐 Transportadora: Transportes ABC
📅 Previsão Entrega: 27/06/2024
📋 Agendamentos:
  ✅ 27/06/2024 - Confirmado pelo cliente
```

---
*Sistema integrado via Model Context Protocol*
"""
    else:
        return "Recurso não encontrado"

async def _exportar_relatorio_cliente(args: dict) -> list[TextContent]:
    """Gera relatório Excel detalhado por cliente"""
    try:
        import pandas as pd
        import tempfile
        import os
        from datetime import datetime
        
        from app.pedidos.models import Pedido
        from app.faturamento.models import RelatorioFaturamentoImportado
        from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
        from sqlalchemy import and_, desc, func
        
        cliente_busca = args.get('cliente', '').strip()
        uf_filtro = args.get('uf', '').strip().upper()
        limite = args.get('limite', 10)
        nome_arquivo = args.get('nome_arquivo', 'relatorio_cliente.xlsx')
        
        if not cliente_busca:
            return [TextContent(
                type="text",
                text="❌ Nome do cliente é obrigatório para gerar o relatório"
            )]
        
        # Buscar pedidos do cliente
        query = Pedido.query.filter(
            Pedido.raz_social_red.ilike(f"%{cliente_busca}%")
        )
        
        if uf_filtro:
            query = query.filter(Pedido.cod_uf == uf_filtro)
        
        pedidos = query.order_by(desc(Pedido.data_pedido)).limit(limite).all()
        
        if not pedidos:
            return [TextContent(
                type="text",
                text=f"❌ Nenhum pedido encontrado para '{cliente_busca}'" + (f" em {uf_filtro}" if uf_filtro else "")
            )]
        
        # Preparar dados para Excel
        dados_pedidos = []
        dados_faturamento = []
        dados_monitoramento = []
        dados_agendamentos = []
        
        for pedido in pedidos:
            # Dados básicos do pedido
            dados_pedidos.append({
                'numero_pedido': pedido.num_pedido,
                'data_pedido': pedido.data_pedido.strftime('%d/%m/%Y') if pedido.data_pedido else '',
                'cliente': pedido.raz_social_red,
                'cnpj_cpf': pedido.cnpj_cpf,
                'destino': f"{pedido.nome_cidade}/{pedido.cod_uf}",
                'valor_pedido': pedido.valor_saldo_total,
                'peso_kg': pedido.peso_total,
                'pallets': pedido.pallet_total,
                'status': pedido.status_calculado,
                'nf': pedido.nf or '',
                'data_embarque': pedido.data_embarque.strftime('%d/%m/%Y') if pedido.data_embarque else '',
                'data_agendamento': pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                'protocolo': pedido.protocolo or '',
                'transportadora': pedido.transportadora or '',
                'valor_frete': pedido.valor_frete,
                'modalidade': pedido.modalidade or ''
            })
            
            # Se tem NF, buscar dados de faturamento
            if pedido.nf and pedido.nf.strip():
                faturamento = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=pedido.nf
                ).first()
                
                if faturamento:
                    saldo_carteira = 0
                    status_faturamento = "Completo"
                    
                    if pedido.valor_saldo_total and faturamento.valor_total:
                        saldo_carteira = pedido.valor_saldo_total - faturamento.valor_total
                        if saldo_carteira > 0:
                            status_faturamento = "Parcial"
                        elif saldo_carteira < 0:
                            status_faturamento = "Superior"
                    
                    dados_faturamento.append({
                        'numero_nf': pedido.nf,
                        'numero_pedido': pedido.num_pedido,
                        'cliente': faturamento.nome_cliente,
                        'cnpj_cliente': faturamento.cnpj_cliente,
                        'data_fatura': faturamento.data_fatura.strftime('%d/%m/%Y') if faturamento.data_fatura else '',
                        'valor_nf': faturamento.valor_total,
                        'valor_pedido': pedido.valor_saldo_total,
                        'saldo_carteira': saldo_carteira,
                        'status_faturamento': status_faturamento,
                        'peso_bruto': faturamento.peso_bruto,
                        'transportadora_faturamento': faturamento.nome_transportadora,
                        'municipio': faturamento.municipio,
                        'estado': faturamento.estado,
                        'incoterm': faturamento.incoterm,
                        'vendedor': faturamento.vendedor
                    })
                
                # Buscar dados de monitoramento
                entrega = EntregaMonitorada.query.filter_by(
                    numero_nf=pedido.nf
                ).first()
                
                if entrega:
                    dados_monitoramento.append({
                        'numero_nf': pedido.nf,
                        'numero_pedido': pedido.num_pedido,
                        'cliente': entrega.cliente,
                        'status_entrega': entrega.status_finalizacao or 'Em andamento',
                        'data_embarque': entrega.data_embarque.strftime('%d/%m/%Y') if entrega.data_embarque else '',
                        'data_prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else '',
                        'data_realizada': entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y %H:%M') if entrega.data_hora_entrega_realizada else '',
                        'transportadora': entrega.transportadora,
                        'lead_time': entrega.lead_time,
                        'pendencia_financeira': 'Sim' if entrega.pendencia_financeira else 'Não',
                        'reagendar': 'Sim' if entrega.reagendar else 'Não',
                        'motivo_reagendamento': entrega.motivo_reagendamento or '',
                        'observacao_operacional': entrega.observacao_operacional or '',
                        'nf_cd': 'Sim' if entrega.nf_cd else 'Não',
                        'finalizado_por': entrega.finalizado_por or '',
                        'finalizado_em': entrega.finalizado_em.strftime('%d/%m/%Y %H:%M') if entrega.finalizado_em else ''
                    })
                    
                    # Agendamentos da entrega
                    agendamentos = AgendamentoEntrega.query.filter_by(
                        entrega_id=entrega.id
                    ).order_by(desc(AgendamentoEntrega.criado_em)).all()
                    
                    for ag in agendamentos:
                        dados_agendamentos.append({
                            'numero_nf': pedido.nf,
                            'numero_pedido': pedido.num_pedido,
                            'cliente': entrega.cliente,
                            'data_agendada': ag.data_agendada.strftime('%d/%m/%Y') if ag.data_agendada else '',
                            'hora_agendada': ag.hora_agendada.strftime('%H:%M') if ag.hora_agendada else '',
                            'forma_agendamento': ag.forma_agendamento or '',
                            'protocolo': ag.protocolo_agendamento or '',
                            'motivo': ag.motivo or '',
                            'observacao': ag.observacao or '',
                            'status': ag.status or 'aguardando',
                            'autor': ag.autor or '',
                            'criado_em': ag.criado_em.strftime('%d/%m/%Y %H:%M') if ag.criado_em else '',
                            'confirmado_por': ag.confirmado_por or '',
                            'confirmado_em': ag.confirmado_em.strftime('%d/%m/%Y %H:%M') if ag.confirmado_em else ''
                        })
        
        # Estatísticas do cliente
        total_pedidos = len(pedidos)
        total_valor_pedidos = sum(p.valor_saldo_total for p in pedidos if p.valor_saldo_total)
        pedidos_faturados = len([p for p in pedidos if p.nf and p.nf.strip()])
        pedidos_embarcados = len([p for p in pedidos if p.data_embarque])
        total_valor_faturado = sum(d['valor_nf'] for d in dados_faturamento if d['valor_nf'])
        total_saldo_carteira = sum(d['saldo_carteira'] for d in dados_faturamento if d['saldo_carteira'] > 0)
        
        estatisticas = {
            'Cliente': cliente_busca.upper(),
            'UF Filtro': uf_filtro or 'Todas',
            'Período Análise': f"Últimos {limite} pedidos",
            'Data Relatório': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'Total Pedidos': total_pedidos,
            'Valor Total Pedidos': f"R$ {total_valor_pedidos:,.2f}",
            'Pedidos Faturados': f"{pedidos_faturados}/{total_pedidos}",
            'Pedidos Embarcados': f"{pedidos_embarcados}/{total_pedidos}",
            'Valor Total Faturado': f"R$ {total_valor_faturado:,.2f}",
            'Saldo em Carteira': f"R$ {total_saldo_carteira:,.2f}",
            '% Faturamento': f"{(total_valor_faturado/total_valor_pedidos*100):.1f}%" if total_valor_pedidos > 0 else "0%"
        }
        
        # Criar arquivo Excel
        arquivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        arquivo_temp.close()
        
        with pd.ExcelWriter(arquivo_temp.name, engine='xlsxwriter') as writer:
            # Aba 1: Resumo dos Pedidos
            if dados_pedidos:
                df_pedidos = pd.DataFrame(dados_pedidos)
                df_pedidos.to_excel(writer, sheet_name='Pedidos', index=False)
            
            # Aba 2: Dados de Faturamento
            if dados_faturamento:
                df_faturamento = pd.DataFrame(dados_faturamento)
                df_faturamento.to_excel(writer, sheet_name='Faturamento', index=False)
            
            # Aba 3: Monitoramento de Entregas
            if dados_monitoramento:
                df_monitoramento = pd.DataFrame(dados_monitoramento)
                df_monitoramento.to_excel(writer, sheet_name='Monitoramento', index=False)
            
            # Aba 4: Agendamentos
            if dados_agendamentos:
                df_agendamentos = pd.DataFrame(dados_agendamentos)
                df_agendamentos.to_excel(writer, sheet_name='Agendamentos', index=False)
            
            # Aba 5: Estatísticas
            df_stats = pd.DataFrame(list(estatisticas.items()), columns=['Métrica', 'Valor'])
            df_stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        # Verificar se arquivo foi criado
        if os.path.exists(arquivo_temp.name):
            tamanho_arquivo = os.path.getsize(arquivo_temp.name)
            resultado = f"""📊 **RELATÓRIO EXCEL GERADO COM SUCESSO!**

📁 **Arquivo:** {nome_arquivo}
📏 **Tamanho:** {tamanho_arquivo:,} bytes
🏢 **Cliente:** {cliente_busca.upper()}
📍 **Estado:** {uf_filtro if uf_filtro else 'Todos'}

📋 **Conteúdo do Relatório:**
• **Aba 1 - Pedidos:** {len(dados_pedidos)} registros
• **Aba 2 - Faturamento:** {len(dados_faturamento)} registros  
• **Aba 3 - Monitoramento:** {len(dados_monitoramento)} registros
• **Aba 4 - Agendamentos:** {len(dados_agendamentos)} registros
• **Aba 5 - Estatísticas:** Resumo executivo

💰 **Resumo Financeiro:**
• **Total Pedidos:** R$ {total_valor_pedidos:,.2f}
• **Total Faturado:** R$ {total_valor_faturado:,.2f}
• **Saldo Carteira:** R$ {total_saldo_carteira:,.2f}

📍 **Localização:** {arquivo_temp.name}

✅ **O arquivo está pronto para download!**
"""
            
            # Limpar arquivo temporário após um tempo
            import threading
            def limpar_arquivo():
                import time
                time.sleep(300)  # 5 minutos
                try:
                    os.unlink(arquivo_temp.name)
                except:
                    pass
            
            threading.Thread(target=limpar_arquivo, daemon=True).start()
            
            return [TextContent(
                type="text", 
                text=resultado
            )]
        else:
            return [TextContent(
                type="text",
                text="❌ Erro ao gerar arquivo Excel"
            )]
            
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Erro ao gerar relatório: {str(e)}"
        )]

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