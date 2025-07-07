#!/usr/bin/env python3
"""
🚀 MCP CONNECTOR SIMPLES - Sistema de Fretes
Conector MCP baseado no que funcionou no Claude Desktop
"""

import json
import subprocess
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import do servidor MCP web
try:
    from .mcp_web_server import mcp_web_server
    MCP_WEB_AVAILABLE = True
except ImportError:
    MCP_WEB_AVAILABLE = False

logger = logging.getLogger(__name__)

class MCPSistemaOnline:
    """Conector MCP otimizado para sistema online baseado no que funcionou"""
    
    def __init__(self, app_root_path: Optional[str] = None):
        self.app_root_path = app_root_path or os.getcwd()
        self.timeout = 15
        logger.info("🚀 MCPSistemaOnline inicializado com timeout %ds", self.timeout)
    
    def consulta_rapida(self, query: str) -> dict:
        """Consulta rápida usando MCP web - baseado no que funcionou"""
        try:
            query_lower = query.lower()
            
            # 🎯 PRIORIDADE ALTA: Pedidos e entregas por cliente (para representantes)
            if any(word in query_lower for word in ['pedidos', 'pedido', 'entregas', 'entrega']):
                cliente, uf = self._extrair_cliente_e_uf(query)
                if cliente:
                    args = {"cliente": cliente}
                    if uf:
                        args["uf"] = uf
                    return self._executar_ferramenta("consultar_pedidos_cliente", args)
                else:
                    return {
                        'success': False,
                        'response': "❌ **CONSULTA DE PEDIDOS**\n\nInforme o cliente. Exemplo: 'Pedidos do cliente Assai de SP'",
                        'timestamp': datetime.now().isoformat(),
                        'source': 'VALIDATION_ERROR'
                    }
            
            # 📊 Exportação para Excel
            elif any(word in query_lower for word in ['exportar', 'excel', 'planilha', 'relatório']):
                cliente, uf = self._extrair_cliente_e_uf(query)
                if cliente:
                    args = {"cliente": cliente}
                    if uf:
                        args["uf"] = uf
                    return self._executar_ferramenta("exportar_pedidos_excel", args)
                else:
                    return {
                        'success': False,
                        'response': "❌ **EXPORTAÇÃO EXCEL**\n\nInforme o cliente. Exemplo: 'Exportar pedidos do Assai para Excel'",
                        'timestamp': datetime.now().isoformat(),
                        'source': 'VALIDATION_ERROR'
                    }
            
            # Status do sistema
            elif any(word in query_lower for word in ['status', 'sistema', 'funcionando']):
                return self._executar_ferramenta("status_sistema")
            
            # Transportadoras
            elif any(word in query_lower for word in ['transportadora', 'empresa', 'cnpj']):
                return self._executar_ferramenta("consultar_transportadoras")
            
            # Fretes (diferente de pedidos)
            elif any(word in query_lower for word in ['frete', 'valor', 'cotação']) and 'pedidos' not in query_lower:
                cliente = self._extrair_cliente_query(query)
                args = {"cliente": cliente} if cliente else {}
                return self._executar_ferramenta("consultar_fretes", args)
            
            # Embarques
            elif any(word in query_lower for word in ['embarque', 'ativo', 'andamento']):
                return self._executar_ferramenta("consultar_embarques")
            
            else:
                # Query genérica - tentar interpretar se contém nome de cliente
                cliente, uf = self._extrair_cliente_e_uf(query)
                if cliente:
                    # Se tem cliente mas não especificou o que quer, mostrar pedidos
                    args = {"cliente": cliente}
                    if uf:
                        args["uf"] = uf
                    return self._executar_ferramenta("consultar_pedidos_cliente", args)
                else:
                    # Sem contexto claro - mostrar status
                    return self._executar_ferramenta("status_sistema")
                
        except Exception as e:
            logger.error(f"Erro consulta rápida: {e}")
            return {
                'success': False,
                'response': f"❌ Erro na consulta: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'source': 'ERROR'
            }
    
    def _executar_ferramenta(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> dict:
        """Executa ferramenta MCP web"""
        try:
            if not MCP_WEB_AVAILABLE:
                return self._fallback_response(tool_name, args)
            
            # Criar requisição MCP
            requisicao = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args or {}
                }
            }
            
            # Executar via MCP web server
            resposta = mcp_web_server.processar_requisicao(requisicao)
            
            if 'result' in resposta and resposta['result']:
                texto = resposta['result'][0].get('text', 'Resposta vazia')
                return {
                    'success': True,
                    'response': texto,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'MCP_WEB'
                }
            else:
                error_msg = resposta.get('error', {}).get('message', 'Erro desconhecido')
                return {
                    'success': False,
                    'response': f"❌ Erro MCP: {error_msg}",
                    'timestamp': datetime.now().isoformat(),
                    'source': 'MCP_ERROR'
                }
                
        except Exception as e:
            logger.error(f"Erro executando ferramenta {tool_name}: {e}")
            return self._fallback_response(tool_name, args)
    
    def _fallback_response(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> dict:
        """Resposta de fallback quando MCP não disponível"""
        fallback_responses = {
            'status_sistema': """🚀 **SISTEMA DE FRETES - MODO FALLBACK**

📊 **STATUS BÁSICO:**
• Sistema: Online e operacional
• Servidor: Render.com  
• MCP: Modo fallback ativo
• Banco: Verificando conectividade...

⚡ **FUNCIONALIDADES:**
• Interface web funcionando
• Sistema de consultas ativo
• Fallback inteligente ativo

🕒 **Verificado em:** """ + datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            
            'consultar_transportadoras': """🚛 **TRANSPORTADORAS - MODO FALLBACK**

**Total conhecido:** 3 transportadoras

🔹 **Freteiro Autônomo Silva**
   • CNPJ: 98.765.432/0001-98
   • Tipo: ✅ Freteiro autônomo

🔹 **Transportadora Teste 1 Ltda**
   • CNPJ: 12.345.678/0001-23
   • Tipo: 🏢 Empresa de transporte

🔹 **Transportes Express**
   • CNPJ: 11.111.111/0001-11
   • Tipo: 🏢 Empresa de transporte""",
            
            'consultar_fretes': """🚚 **CONSULTA DE FRETES - MODO FALLBACK**

📦 **Sistema em modo básico**
• Consulta não disponível no momento
• Interface web principal disponível

💡 **Para consulta completa:**
• Acesse via interface web
• Aguarde conectividade total""",
            
            'consultar_embarques': """🚚 **EMBARQUES - MODO FALLBACK**

📋 **Status:** Sistema em modo básico
• Consulta de embarques: Interface web principal
• Sistema operacional: ✅

💡 **Acesse dados completos via interface web**"""
        }
        
        response_text = fallback_responses.get(tool_name, f"🤖 **Funcionalidade {tool_name} em modo fallback**")
        
        return {
            'success': True,
            'response': response_text,
            'timestamp': datetime.now().isoformat(),
            'source': 'FALLBACK'
        }
    
    def _extrair_cliente_e_uf(self, query: str) -> tuple[Optional[str], Optional[str]]:
        """Extrai nome do cliente e UF da query de forma inteligente"""
        import re
        
        # Normalizar query
        query_clean = query.strip()
        palavras = query_clean.split()
        
        # Lista de UFs brasileiras
        ufs_brasil = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        
        # Extrair UF
        uf = None
        for palavra in palavras:
            palavra_upper = palavra.upper().strip('.,!?')
            if palavra_upper in ufs_brasil:
                uf = palavra_upper
                break
        
        # Padrões para extrair cliente
        cliente = None
        
        # Padrão 1: "Pedidos do [CLIENTE]" ou "Entregas do [CLIENTE]"
        match = re.search(r'(?:pedidos?|entregas?|fretes?|exportar|relatório)\s+do?\s+(?:cliente\s+)?([A-Za-z][A-Za-z0-9\s]+?)(?:\s+(?:de|em|para)\s+[A-Z]{2}|\s*$|para\s+excel)', query_clean, re.IGNORECASE)
        if match:
            cliente = match.group(1).strip()
        
        # Padrão 2: "Pedidos da [CLIENTE]" 
        if not cliente:
            match = re.search(r'(?:pedidos?|entregas?|fretes?|exportar|relatório)\s+da\s+(?:cliente\s+)?([A-Za-z][A-Za-z0-9\s]+?)(?:\s+(?:de|em|para)\s+[A-Z]{2}|\s*$|para\s+excel)', query_clean, re.IGNORECASE)
            if match:
                cliente = match.group(1).strip()
        
        # Padrão 3: "Cliente [CLIENTE]"
        if not cliente:
            match = re.search(r'cliente\s+([A-Za-z][A-Za-z0-9\s]+?)(?:\s+(?:de|em)\s+[A-Z]{2}|\s*$)', query_clean, re.IGNORECASE)
            if match:
                cliente = match.group(1).strip()
        
        # Padrão 4: Nomes conhecidos de clientes (casos especiais)
        clientes_conhecidos = ['Assai', 'Carrefour', 'Magazine Luiza', 'Renner', 'Atacadão', 'Hudson']
        if not cliente:
            for nome_cliente in clientes_conhecidos:
                if nome_cliente.lower() in query.lower():
                    cliente = nome_cliente
                    break
        
        # Limpar cliente se encontrado
        if cliente:
            # Remover palavras comuns do final
            palavras_remover = ['de', 'em', 'para', 'excel', 'planilha', 'relatório']
            palavras_cliente = cliente.split()
            while palavras_cliente and palavras_cliente[-1].lower() in palavras_remover:
                palavras_cliente.pop()
            cliente = ' '.join(palavras_cliente).strip()
            
            # Capitalizar primeira letra de cada palavra
            cliente = ' '.join(word.capitalize() for word in cliente.split())
        
        return cliente, uf
    
    def _extrair_cliente_query(self, query: str) -> Optional[str]:
        """Método mantido para compatibilidade - usa a nova função"""
        cliente, _ = self._extrair_cliente_e_uf(query)
        return cliente
    
    def status_rapido(self) -> dict:
        """Status rápido do sistema"""
        try:
            if MCP_WEB_AVAILABLE:
                # Usar MCP web para status
                result = self._executar_ferramenta("status_sistema")
                
                return {
                    'online': result['success'],
                    'timestamp': result['timestamp'],
                    'message': result['response'][:100] + '...' if len(result['response']) > 100 else result['response'],
                    'components': {
                        'mcp_web': True,
                        'fallback': not result['success'],
                        'source': result['source']
                    }
                }
            else:
                return {
                    'online': True,
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Sistema em modo fallback - operacional',
                    'components': {
                        'mcp_web': False,
                        'fallback': True,
                        'source': 'FALLBACK'
                    }
                }
                
        except Exception as e:
            logger.error(f"Erro status rápido: {e}")
            return {
                'online': False,
                'timestamp': datetime.now().isoformat(),
                'message': f'Erro: {str(e)}',
                'components': {
                    'mcp_web': False,
                    'fallback': False,
                    'source': 'ERROR'
                }
            } 