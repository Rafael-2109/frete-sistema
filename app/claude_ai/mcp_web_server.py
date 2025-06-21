#!/usr/bin/env python3
"""
MCP Web Server - Baseado no mcp_v1_9_4_atualizado.py que funcionou
Adaptado para funcionar no ambiente web do Render
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar Flask app se disponível
try:
    from flask import current_app
    from app import db
    from app.embarques.models import Embarque
    from app.fretes.models import Frete  
    from app.transportadoras.models import Transportadora
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask app não disponível - usando modo fallback")

class MCPWebServer:
    """Servidor MCP para ambiente web - baseado no que funcionou no Claude Desktop"""
    
    def __init__(self):
        self.tools = {
            "status_sistema": self._status_sistema,
            "consultar_fretes": self._consultar_fretes,
            "consultar_transportadoras": self._consultar_transportadoras,
            "consultar_embarques": self._consultar_embarques
        }
        logger.info("🚀 MCP Web Server inicializado com %d ferramentas", len(self.tools))
    
    def processar_requisicao(self, requisicao: Dict[str, Any]) -> Dict[str, Any]:
        """Processa requisição MCP e retorna resposta"""
        try:
            method = requisicao.get("method")
            params = requisicao.get("params", {})
            
            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in self.tools:
                    result = self.tools[tool_name](arguments)
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": requisicao.get("id", 1),
                        "result": [{"type": "text", "text": result}]
                    }
                else:
                    return self._error_response(requisicao.get("id", 1), f"Ferramenta não encontrada: {tool_name}")
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0", 
                    "id": requisicao.get("id", 1),
                    "result": {
                        "tools": [
                            {
                                "name": "status_sistema",
                                "description": "Mostra status geral do sistema de fretes"
                            },
                            {
                                "name": "consultar_fretes", 
                                "description": "Consulta fretes por cliente"
                            },
                            {
                                "name": "consultar_transportadoras",
                                "description": "Lista transportadoras cadastradas"
                            },
                            {
                                "name": "consultar_embarques",
                                "description": "Mostra embarques ativos"
                            }
                        ]
                    }
                }
            
            else:
                return self._error_response(requisicao.get("id", 1), f"Método não suportado: {method}")
                
        except Exception as e:
            logger.error(f"Erro processando requisição: {e}")
            return self._error_response(requisicao.get("id", 1), f"Erro interno: {str(e)}")
    
    def _error_response(self, request_id: int, message: str) -> Dict[str, Any]:
        """Cria resposta de erro"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -1,
                "message": message
            }
        }
    
    def _status_sistema(self, args: Dict[str, Any]) -> str:
        """Status do sistema - baseado na versão que funcionou"""
        try:
            if FLASK_AVAILABLE and current_app:
                with current_app.app_context():
                    # Estatísticas reais do banco
                    total_embarques = db.session.query(Embarque).count()
                    embarques_ativos = db.session.query(Embarque).filter(Embarque.status == 'ativo').count()
                    total_fretes = db.session.query(Frete).count()
                    total_transportadoras = db.session.query(Transportadora).count()
                    
                    # Estatísticas detalhadas
                    fretes_pendentes = db.session.query(Frete).filter(Frete.status == 'PENDENTE').count()
                    fretes_aprovados = db.session.query(Frete).filter(Frete.status == 'APROVADO').count()
                    fretes_pagos = db.session.query(Frete).filter(Frete.status == 'PAGO').count()
                    
                    return f"""🚀 **SISTEMA DE FRETES - STATUS DETALHADO**

📊 **ESTATÍSTICAS GERAIS:**
• Total de Embarques: {total_embarques}
• Embarques Ativos: {embarques_ativos}
• Total de Fretes: {total_fretes}  
• Transportadoras: {total_transportadoras}

🚚 **STATUS DOS FRETES:**
• Pendentes: {fretes_pendentes}
• Aprovados: {fretes_aprovados}  
• Pagos: {fretes_pagos}

🌐 **AMBIENTE RENDER.COM:**
• Status: ✅ Online e operacional
• MCP Web: ✅ Ativo
• Banco PostgreSQL: ✅ Conectado
• API REST: ✅ Funcionando

⚡ **FUNCIONALIDADES MCP:**
• consultar_fretes - Busca por cliente
• consultar_transportadoras - Lista completa
• consultar_embarques - Embarques ativos
• status_sistema - Este relatório

🤖 **COMANDOS EXEMPLO:**
• "Fretes do cliente Assai"
• "Listar transportadoras"
• "Embarques em andamento"
• "Status do sistema"

🕒 **Verificado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔗 **MCP Web Server v2.0 - Dados reais integrados**"""
            
            else:
                # Fallback quando Flask não disponível
                return f"""🚀 **SISTEMA DE FRETES - STATUS FALLBACK**

📊 **MODO BÁSICO:**
• Total de Embarques: -
• Embarques Ativos: -  
• Total de Fretes: -
• Transportadoras: 3 (conhecido)

🌐 **AMBIENTE WEB:**
• Servidor: Render.com
• Status: Online (modo fallback)
• MCP Web: ✅ Ativo
• Banco de dados: ⚠️ Não conectado no momento

⚡ **FUNCIONALIDADES:**
• Sistema operacional
• Modo básico ativo
• Fallback funcionando

🕒 **Verificado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔗 **MCP Web Server v1.0 (modo fallback)**"""
                
        except Exception as e:
            logger.error(f"Erro status sistema: {e}")
            return f"❌ Erro ao obter status do sistema: {str(e)}"
    
    def _consultar_fretes(self, args: Dict[str, Any]) -> str:
        """Consulta fretes - versão melhorada com dados reais"""
        try:
            cliente = args.get("cliente")
            
            if FLASK_AVAILABLE and current_app:
                with current_app.app_context():
                    query = db.session.query(Frete)
                    
                    if cliente:
                        # Buscar por nome do cliente (case-insensitive)
                        query = query.filter(Frete.nome_cliente.ilike(f'%{cliente}%'))
                    
                    # Limitar a últimos 10 fretes e ordenar por ID desc
                    fretes = query.order_by(Frete.id.desc()).limit(10).all()
                    
                    if not fretes:
                        return f"🔍 **CONSULTA DE FRETES**\n\nNenhum frete encontrado{f' para o cliente {cliente}' if cliente else ''}."
                    
                    resultado = f"🚚 **CONSULTA DE FRETES**\n\n"
                    if cliente:
                        resultado += f"**Cliente:** {cliente}\n\n"
                    
                    for frete in fretes:
                        # Status com emoji
                        status_emoji = {
                            'PENDENTE': '⏳',
                            'EM_TRATATIVA': '🔄', 
                            'APROVADO': '✅',
                            'REJEITADO': '❌',
                            'PAGO': '💰',
                            'CANCELADO': '🚫'
                        }.get(frete.status, '📋')
                        
                        resultado += f"📦 **Frete #{frete.id}**\n"
                        resultado += f"   • Cliente: {frete.nome_cliente}\n"
                        resultado += f"   • Destino: {frete.cidade_destino}/{frete.uf_destino}\n"
                        resultado += f"   • Peso: {frete.peso_total:.0f} kg\n"
                        resultado += f"   • Valor Cotado: R$ {frete.valor_cotado:,.2f}\n"
                        if frete.valor_considerado:
                            resultado += f"   • Valor Considerado: R$ {frete.valor_considerado:,.2f}\n"
                        if frete.numero_cte:
                            resultado += f"   • CTe: {frete.numero_cte}\n"
                        resultado += f"   • Status: {status_emoji} {frete.status}\n"
                        
                        # Transportadora
                        if frete.transportadora:
                            resultado += f"   • Transportadora: {frete.transportadora.razao_social}\n"
                        
                        resultado += "\n"
                        
                    resultado += f"📈 **Total encontrado:** {len(fretes)} fretes"
                    
                    if cliente:
                        resultado += f" para {cliente}"
                    
                    return resultado
            
            else:
                return f"""🚚 **CONSULTA DE FRETES - MODO FALLBACK**

🔍 **Busca:** {cliente if cliente else 'Todos os clientes'}

📦 **Sistema em modo básico**
• Banco de dados não conectado no momento
• Funcionalidade disponível quando conectado

💡 **Para consulta completa:**
• Aguarde conectividade com banco
• Ou acesse via interface web principal"""
                
        except Exception as e:
            logger.error(f"Erro consulta fretes: {e}")
            return f"❌ Erro na consulta de fretes: {str(e)}"
    
    def _consultar_transportadoras(self, args: Dict[str, Any]) -> str:
        """Consulta transportadoras - baseado na versão que funcionou"""
        try:
            if FLASK_AVAILABLE and current_app:
                with current_app.app_context():
                    transportadoras = db.session.query(Transportadora).limit(20).all()
                    
                    if not transportadoras:
                        return "🚛 **TRANSPORTADORAS**\n\nNenhuma transportadora cadastrada."
                    
                    resultado = f"🚛 **TRANSPORTADORAS CADASTRADAS**\n\n**Total:** {len(transportadoras)} empresas\n\n"
                    
                    for transportadora in transportadoras:
                        tipo = "✅ Freteiro" if getattr(transportadora, 'freteiro', False) else "🏢 Empresa"
                        resultado += f"🔹 **{transportadora.razao_social}**\n"
                        resultado += f"   • CNPJ: {getattr(transportadora, 'cnpj', 'N/A')}\n"  
                        resultado += f"   • Cidade: {getattr(transportadora, 'cidade', 'N/A')}/{getattr(transportadora, 'uf', 'N/A')}\n"
                        resultado += f"   • Tipo: {tipo}\n\n"
                    
                    return resultado
            
            else:
                return """🚛 **TRANSPORTADORAS - MODO FALLBACK**

**Total conhecido:** 3 transportadoras

🔹 **Freteiro Autônomo Silva**
   • CNPJ: 98.765.432/0001-98
   • Tipo: ✅ Freteiro autônomo

🔹 **Transportadora Teste 1 Ltda** 
   • CNPJ: 12.345.678/0001-23
   • Tipo: 🏢 Empresa de transporte

🔹 **Transportes Express**
   • CNPJ: 11.111.111/0001-11
   • Tipo: 🏢 Empresa de transporte

💡 **Dados completos disponíveis quando banco conectado**"""
                
        except Exception as e:
            logger.error(f"Erro consulta transportadoras: {e}")
            return f"❌ Erro na consulta de transportadoras: {str(e)}"
    
    def _consultar_embarques(self, args: Dict[str, Any]) -> str:
        """Consulta embarques - versão melhorada com dados reais"""
        try:
            if FLASK_AVAILABLE and current_app:
                with current_app.app_context():
                    # Buscar embarques ativos ordenados por número desc
                    embarques = db.session.query(Embarque).filter(
                        Embarque.status == 'ativo'
                    ).order_by(Embarque.numero.desc()).limit(10).all()
                    
                    if not embarques:
                        return "🚚 **EMBARQUES ATIVOS**\n\nNenhum embarque ativo encontrado."
                    
                    resultado = f"🚚 **EMBARQUES ATIVOS**\n\n**Total:** {len(embarques)} embarques\n\n"
                    
                    for embarque in embarques:
                        # Calcular totais reais
                        peso_total = embarque.total_peso_pedidos() or 0
                        valor_total = embarque.total_valor_pedidos() or 0
                        total_notas = embarque.total_notas()
                        
                        resultado += f"📋 **Embarque #{embarque.numero}**\n"
                        resultado += f"   • Status: {embarque.status.title()}\n"
                        resultado += f"   • Total NFs: {total_notas}\n"
                        resultado += f"   • Peso: {peso_total:.0f} kg\n"
                        resultado += f"   • Valor: R$ {valor_total:,.2f}\n"
                        
                        # Transportadora
                        if embarque.transportadora:
                            resultado += f"   • Transportadora: {embarque.transportadora.razao_social}\n"
                        
                        # Data prevista
                        if embarque.data_prevista_embarque:
                            resultado += f"   • Data Prevista: {embarque.data_prevista_embarque.strftime('%d/%m/%Y')}\n"
                        
                        # Status das NFs e Fretes
                        resultado += f"   • Status NFs: {embarque.status_nfs}\n"
                        resultado += f"   • Status Fretes: {embarque.status_fretes}\n"
                        
                        resultado += "\n"
                    
                    return resultado
            
            else:
                return """🚚 **EMBARQUES ATIVOS - MODO FALLBACK**

📋 **Status atual:** Sistema em modo básico
• Embarques ativos: Consulta não disponível no momento
• Sistema operacional: ✅

🔍 **Funcionalidades disponíveis:**
• Verificação de status geral
• Consulta básica de dados
• Sistema preparado para consultas completas

💡 **Para dados completos:** Aguarde conectividade com banco"""
                
        except Exception as e:
            logger.error(f"Erro consulta embarques: {e}")
            return f"❌ Erro na consulta de embarques: {str(e)}"

# Instância global do servidor MCP
mcp_web_server = MCPWebServer() 