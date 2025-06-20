#!/usr/bin/env python3
"""
🌐 SERVIDOR MCP PARA RENDER
Servidor MCP otimizado para rodar no Render.com junto com o sistema Flask
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
import tempfile
import requests
import pandas as pd
from typing import Dict, List, Any

# Adicionar o diretório raiz ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
    import mcp.types as types
    from mcp.server.stdio import stdio_server
except ImportError as e:
    print(f"❌ ERRO: Não foi possível importar MCP. Certifique-se de que está instalado: {e}")
    sys.exit(1)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MCP Render - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('mcp_render.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# URL base do sistema Flask (Render ou local)
BASE_URL = os.environ.get('FLASK_URL', 'https://frete-sistema.onrender.com')
SYSTEM_USER = os.environ.get('MCP_USER', 'sistema_mcp')

# Headers para autenticação (se necessário)
API_HEADERS = {
    'User-Agent': 'MCP-Server-Render/1.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# ============================================================================
# UTILITÁRIOS
# ============================================================================

def fazer_requisicao_api(endpoint: str, params: Dict = None) -> Dict:
    """
    Faz requisição para a API Flask do sistema
    """
    try:
        url = f"{BASE_URL}/api/v1{endpoint}"
        
        logger.info(f"🌐 Requisição: {url} | Params: {params}")
        
        response = requests.get(
            url, 
            params=params, 
            headers=API_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Sucesso: {endpoint}")
            return data
        else:
            error_msg = f"❌ Erro {response.status_code}: {endpoint}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': f"Erro {response.status_code}: {response.text[:200]}"
            }
            
    except requests.exceptions.Timeout:
        error_msg = f"⏰ Timeout na requisição: {endpoint}"
        logger.error(error_msg)
        return {'success': False, 'error': 'Timeout na requisição'}
    except requests.exceptions.ConnectionError:
        error_msg = f"🔌 Erro de conexão: {endpoint}"
        logger.error(error_msg)
        return {'success': False, 'error': 'Erro de conexão com o servidor'}
    except Exception as e:
        error_msg = f"💥 Erro inesperado: {endpoint} - {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': f"Erro inesperado: {str(e)}"}

def baixar_excel(endpoint: str, nome_arquivo: str, params: Dict = None) -> str:
    """
    Baixa arquivo Excel da API
    """
    try:
        url = f"{BASE_URL}/api/v1{endpoint}"
        
        response = requests.get(
            url,
            params=params,
            headers=API_HEADERS,
            timeout=60
        )
        
        if response.status_code == 200:
            # Salvar arquivo temporário
            arquivo_temp = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.xlsx',
                prefix=f'{nome_arquivo}_'
            )
            
            arquivo_temp.write(response.content)
            arquivo_temp.close()
            
            logger.info(f"📊 Excel baixado: {arquivo_temp.name}")
            return arquivo_temp.name
        else:
            logger.error(f"❌ Erro ao baixar Excel: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"💥 Erro ao baixar Excel: {str(e)}")
        return None

# ============================================================================
# SERVIDOR MCP
# ============================================================================

server = Server("frete-sistema-render")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Lista as ferramentas disponíveis"""
    return [
        Tool(
            name="consultar_embarques",
            description="Consulta embarques do sistema de fretes via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Status do embarque (ativo, cancelado)",
                        "default": "ativo"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de resultados",
                        "default": 10
                    }
                }
            },
        ),
        Tool(
            name="consultar_fretes",
            description="Consulta fretes do sistema via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_aprovacao": {
                        "type": "string",
                        "description": "Status da aprovação do frete",
                        "default": "pendente"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de resultados",
                        "default": 10
                    }
                }
            },
        ),
        Tool(
            name="consultar_monitoramento",
            description="Consulta entregas em monitoramento via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "nf_numero": {
                        "type": "string",
                        "description": "Número da NF para buscar",
                        "default": ""
                    },
                    "pendencia_financeira": {
                        "type": "string",
                        "description": "Filtrar por pendência financeira (true/false)",
                        "default": ""
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de resultados",
                        "default": 10
                    }
                }
            },
        ),
        Tool(
            name="consultar_cliente_detalhado",
            description="Consulta detalhada por cliente com dados integrados via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente_nome": {
                        "type": "string",
                        "description": "Nome do cliente para buscar",
                        "required": True
                    },
                    "uf": {
                        "type": "string",
                        "description": "UF para filtrar (opcional)",
                        "default": ""
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de pedidos",
                        "default": 5
                    }
                },
                "required": ["cliente_nome"]
            },
        ),
        Tool(
            name="exportar_relatorio_cliente",
            description="Gera e baixa relatório Excel completo por cliente via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente_nome": {
                        "type": "string",
                        "description": "Nome do cliente para gerar relatório",
                        "required": True
                    },
                    "uf": {
                        "type": "string",
                        "description": "UF para filtrar (opcional)",
                        "default": ""
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de pedidos no relatório",
                        "default": 10
                    }
                },
                "required": ["cliente_nome"]
            },
        ),
        Tool(
            name="estatisticas_sistema",
            description="Obtém estatísticas gerais do sistema via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "periodo_dias": {
                        "type": "integer",
                        "description": "Período em dias para análise",
                        "default": 30
                    }
                }
            },
        ),
        Tool(
            name="consultar_portaria",
            description="Consulta veículos na portaria via API",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Status na portaria",
                        "default": ""
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de resultados",
                        "default": 10
                    }
                }
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Executa as ferramentas via API"""
    
    try:
        resultado = None
        
        if name == "consultar_embarques":
            params = {
                'status': arguments.get('status', 'ativo'),
                'limite': arguments.get('limite', 10)
            }
            resultado = fazer_requisicao_api('/embarques', params)
            
        elif name == "consultar_fretes":
            params = {
                'status_aprovacao': arguments.get('status_aprovacao', 'pendente'),
                'limite': arguments.get('limite', 10)
            }
            resultado = fazer_requisicao_api('/fretes', params)
            
        elif name == "consultar_monitoramento":
            params = {}
            if arguments.get('nf_numero'):
                params['nf_numero'] = arguments['nf_numero']
            if arguments.get('pendencia_financeira'):
                params['pendencia_financeira'] = arguments['pendencia_financeira']
            params['limite'] = arguments.get('limite', 10)
            resultado = fazer_requisicao_api('/monitoramento', params)
            
        elif name == "consultar_cliente_detalhado":
            cliente_nome = arguments.get('cliente_nome', '')
            if not cliente_nome:
                return [types.TextContent(
                    type="text", 
                    text="❌ Erro: Nome do cliente é obrigatório"
                )]
            
            params = {
                'uf': arguments.get('uf', ''),
                'limite': arguments.get('limite', 5)
            }
            resultado = fazer_requisicao_api(f'/cliente/{cliente_nome}', params)
            
        elif name == "exportar_relatorio_cliente":
            cliente_nome = arguments.get('cliente_nome', '')
            if not cliente_nome:
                return [types.TextContent(
                    type="text", 
                    text="❌ Erro: Nome do cliente é obrigatório"
                )]
            
            params = {
                'uf': arguments.get('uf', ''),
                'limite': arguments.get('limite', 10)
            }
            
            # Baixar Excel
            arquivo_excel = baixar_excel(
                f'/cliente/{cliente_nome}/excel',
                f'relatorio_{cliente_nome.replace(" ", "_")}',
                params
            )
            
            if arquivo_excel:
                return [types.TextContent(
                    type="text",
                    text=f"📊 **Relatório Excel Gerado com Sucesso!**\n\n"
                         f"**Cliente:** {cliente_nome.upper()}\n"
                         f"**Arquivo:** {os.path.basename(arquivo_excel)}\n"
                         f"**Localização:** {arquivo_excel}\n\n"
                         f"O arquivo Excel contém dados completos integrados do cliente."
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Erro ao gerar relatório Excel para {cliente_nome}"
                )]
            
        elif name == "estatisticas_sistema":
            params = {
                'periodo_dias': arguments.get('periodo_dias', 30)
            }
            resultado = fazer_requisicao_api('/estatisticas', params)
            
        elif name == "consultar_portaria":
            params = {
                'limite': arguments.get('limite', 10)
            }
            if arguments.get('status'):
                params['status'] = arguments['status']
            resultado = fazer_requisicao_api('/portaria', params)
            
        else:
            return [types.TextContent(
                type="text", 
                text=f"❌ Ferramenta '{name}' não encontrada"
            )]
        
        # Processar resultado
        if resultado and resultado.get('success'):
            # Formatação específica por tipo de consulta
            if name == "consultar_cliente_detalhado":
                texto = f"📋 **CONSULTA DETALHADA - {resultado.get('cliente', 'Cliente')}**\n\n"
                
                if 'resumo' in resultado:
                    resumo = resultado['resumo']
                    texto += f"📊 **Resumo Executivo:**\n"
                    texto += f"• Total de pedidos: {resumo.get('total_pedidos', 0)}\n"
                    texto += f"• Valor total: R$ {resumo.get('valor_total', 0):,.2f}\n"
                    texto += f"• Pedidos faturados: {resumo.get('pedidos_faturados', 0)}\n"
                    texto += f"• % Faturamento: {resumo.get('percentual_faturado', 0)}%\n\n"
                
                if 'data' in resultado:
                    texto += "📦 **Pedidos Detalhados:**\n\n"
                    for i, item in enumerate(resultado['data'], 1):
                        pedido = item.get('pedido', {})
                        texto += f"**{i}. Pedido {pedido.get('numero', 'N/A')}**\n"
                        texto += f"   Data: {pedido.get('data', 'N/A')}\n"
                        texto += f"   Destino: {pedido.get('destino', 'N/A')}\n"
                        texto += f"   Valor: R$ {pedido.get('valor', 0):,.2f}\n"
                        texto += f"   Status: {pedido.get('status', 'N/A')}\n"
                        
                        if item.get('faturamento'):
                            fat = item['faturamento']
                            texto += f"   💰 Faturado: {fat.get('data_fatura', 'N/A')} - R$ {fat.get('valor_nf', 0):,.2f}\n"
                            texto += f"   💳 Saldo: R$ {fat.get('saldo_carteira', 0):,.2f} ({fat.get('status_faturamento', 'N/A')})\n"
                        
                        if item.get('monitoramento'):
                            mon = item['monitoramento']
                            texto += f"   🚚 Entrega: {mon.get('status_entrega', 'N/A')}\n"
                            if mon.get('data_prevista'):
                                texto += f"   📅 Prevista: {mon['data_prevista']}\n"
                        
                        texto += "\n"
                
                return [types.TextContent(type="text", text=texto)]
            
            else:
                # Formatação padrão para outras consultas
                import json
                texto_formatado = json.dumps(resultado, indent=2, ensure_ascii=False)
                return [types.TextContent(type="text", text=texto_formatado)]
        
        else:
            erro = resultado.get('error', 'Erro desconhecido') if resultado else 'Sem resposta da API'
            return [types.TextContent(
                type="text", 
                text=f"❌ Erro na consulta: {erro}"
            )]
            
    except Exception as e:
        logger.error(f"💥 Erro na ferramenta {name}: {str(e)}")
        return [types.TextContent(
            type="text",
            text=f"❌ Erro interno: {str(e)}"
        )]

async def main():
    """Função principal do servidor MCP"""
    logger.info("🚀 Iniciando Servidor MCP para Render...")
    logger.info(f"🌐 Base URL: {BASE_URL}")
    logger.info(f"👤 Usuário: {SYSTEM_USER}")
    
    # Verificar conectividade com a API
    try:
        health_check = fazer_requisicao_api('/health')
        if health_check and health_check.get('status') == 'healthy':
            logger.info("✅ Conectividade com API verificada")
        else:
            logger.warning("⚠️ API pode estar indisponível")
    except Exception as e:
        logger.error(f"❌ Erro na verificação de conectividade: {e}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frete-sistema-render",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Servidor MCP interrompido pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro fatal no servidor MCP: {e}")
        sys.exit(1) 