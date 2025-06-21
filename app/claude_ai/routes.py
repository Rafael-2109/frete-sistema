from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import subprocess
import json
import os
import sys
from datetime import datetime
from .mcp_connector import MCPSistemaOnline
from . import claude_ai_bp

@claude_ai_bp.route('/chat')
@login_required
def chat_page():
    """Página principal do chat com Claude AI"""
    return render_template('claude_ai/chat.html')

@claude_ai_bp.route('/dashboard')
@login_required
def dashboard_mcp():
    """Dashboard MCP - Status do sistema em tempo real"""
    try:
        mcp_connector = MCPSistemaOnline(current_app.root_path)
        status_data = mcp_connector.status_rapido()
        
        return render_template('claude_ai/dashboard.html', 
                             status=status_data,
                             user=current_user.nome)
    except Exception as e:
        current_app.logger.error(f"Erro dashboard MCP: {e}")
        return render_template('claude_ai/dashboard.html', 
                             status={'online': False, 'error': str(e)},
                             user=current_user.nome)

@claude_ai_bp.route('/widget')
@login_required
def chat_widget():
    """Widget de chat para incluir em outras páginas"""
    return render_template('claude_ai/widget.html')

@claude_ai_bp.route('/api/query', methods=['POST'])
@login_required
def query_claude():
    """API para enviar consultas ao Claude via MCP REAL"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query não pode estar vazia'
            }), 400
        
        # 🚀 IMPLEMENTAÇÃO MCP SISTEMA ONLINE
        mcp_connector = MCPSistemaOnline(current_app.root_path)
        
        try:
            # Consulta otimizada para sistema online
            resultado = mcp_connector.consulta_rapida(query)
            
            if resultado['success']:
                return jsonify({
                    'success': True,
                    'response': resultado['response'],
                    'timestamp': resultado['timestamp'],
                    'user': current_user.nome,
                    'source': resultado['source']
                })
            else:
                # Em caso de erro, tenta fallback
                resposta_fallback = simulate_mcp_response(query)
                
                return jsonify({
                    'success': True,
                    'response': f"⚠️ **Modo Fallback** (MCP temporariamente indisponível)\n\n{resposta_fallback}",
                    'timestamp': datetime.now().isoformat(),
                    'user': current_user.nome,
                    'source': 'FALLBACK',
                    'mcp_error': resultado.get('error', 'Erro desconhecido')
                })
                
        except Exception as mcp_error:
            # Em caso de erro total, usa fallback
            current_app.logger.error(f"Erro MCP connector: {mcp_error}")
            resposta_fallback = simulate_mcp_response(query)
            
            return jsonify({
                'success': True,
                'response': f"⚠️ **Modo Fallback** (Erro MCP)\n\n{resposta_fallback}",
                'timestamp': datetime.now().isoformat(),
                'user': current_user.nome,
                'source': 'FALLBACK_ERROR',
                'error_details': str(mcp_error)
                         })
        
    except Exception as e:
        current_app.logger.error(f"Erro na consulta Claude: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor'
        }), 500

def simulate_mcp_response(query):
    """Simula respostas do MCP baseado na query (placeholder)"""
    from datetime import datetime
    
    query_lower = query.lower()
    
    if 'status' in query_lower or 'sistema' in query_lower:
        return """🟢 **SISTEMA DE FRETES ONLINE**

📊 **ESTATÍSTICAS ATUAIS:**
- Sistema operacional desde: """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """
- Status: Funcionando normalmente
- Módulos ativos: Todos operacionais

⚡ **FUNCIONALIDADES DISPONÍVEIS:**
- Consulta de fretes e transportadoras
- Monitoramento de embarques
- Análise de dados em tempo real"""

    elif 'transportadora' in query_lower:
        return """🚛 **TRANSPORTADORAS CADASTRADAS**

**Total:** 3 transportadoras ativas

🔹 **Freteiro Autônomo Silva**
   - CNPJ: 98.765.432/0001-98
   - Local: Rio de Janeiro/RJ
   - Tipo: Freteiro autônomo ✅

🔹 **Transportadora Teste 1 Ltda**
   - CNPJ: 12.345.678/0001-23
   - Local: São Paulo/SP
   - Tipo: Empresa de transporte

🔹 **Transportes Express**
   - CNPJ: 11.111.111/0001-11
   - Local: Belo Horizonte/MG
   - Tipo: Empresa de transporte"""

    elif 'frete' in query_lower:
        return """📦 **CONSULTA DE FRETES**

**Status atual:** Sistema em fase inicial
- Fretes cadastrados: 0
- Sistema pronto para receber dados

🔍 **Para consultar fretes específicos:**
- Digite o nome do cliente
- Especifique período desejado
- Informe origem/destino se necessário"""

    elif 'embarque' in query_lower:
        return """🚚 **EMBARQUES ATIVOS**

**Status atual:** 0 embarques em andamento

📋 **Funcionalidades disponíveis:**
- Consulta de embarques por período
- Filtros por transportadora
- Status de embarques em tempo real"""

    elif 'help' in query_lower or 'ajuda' in query_lower:
        return """🤖 **ASSISTENTE CLAUDE - SISTEMA DE FRETES**

**Comandos disponíveis:**
- "status do sistema" - Verifica funcionamento
- "transportadoras" - Lista empresas cadastradas  
- "fretes" - Consulta fretes cadastrados
- "embarques" - Mostra embarques ativos

**Exemplos de consultas:**
- "Mostre fretes do cliente X"
- "Qual transportadora tem mais embarques?"
- "Estatísticas do último mês"

💡 **Dica:** Seja específico nas suas perguntas para respostas mais precisas!"""

    else:
        return f"""🤖 **Claude AI - Sistema de Fretes**

Recebi sua consulta: *"{query}"*

Para obter informações mais precisas, tente consultas como:
- "Status do sistema"
- "Listar transportadoras"
- "Consultar fretes"
- "Embarques ativos"

💡 Digite "ajuda" para ver todos os comandos disponíveis."""

@claude_ai_bp.route('/api/health')
@login_required
def health_check():
    """Verifica se o serviço Claude está funcionando - SISTEMA ONLINE"""
    try:
        mcp_connector = MCPSistemaOnline(current_app.root_path)
        status_data = mcp_connector.status_rapido()
        
        return jsonify({
            'success': status_data['online'],
            'status': 'online' if status_data['online'] else 'degraded',
            'service': 'Claude AI Integration - Sistema Online',
            'components': status_data['components'],
            'message': status_data.get('message', ''),
            'timestamp': status_data['timestamp']
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro health check: {e}")
        return jsonify({
            'success': False,
            'status': 'error',
            'service': 'Claude AI Integration',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@claude_ai_bp.route('/api/test-mcp', methods=['POST'])
@login_required
def test_mcp_directly():
    """Testa MCP diretamente para debugging"""
    try:
        data = request.get_json()
        tool_name = data.get('tool', 'status_sistema')
        args = data.get('args', {})
        
        mcp_connector = MCPSistemaOnline(current_app.root_path)
        
        # Chama ferramenta específica
        if tool_name == 'status_sistema':
            sucesso, resposta = mcp_connector.status_sistema()
        elif tool_name == 'consultar_fretes':
            cliente = args.get('cliente')
            sucesso, resposta = mcp_connector.consultar_fretes(cliente)
        elif tool_name == 'consultar_transportadoras':
            sucesso, resposta = mcp_connector.consultar_transportadoras()
        elif tool_name == 'consultar_embarques':
            sucesso, resposta = mcp_connector.consultar_embarques()
        else:
            return jsonify({
                'success': False,
                'error': f'Ferramenta não suportada: {tool_name}'
            }), 400
        
        return jsonify({
            'success': sucesso,
            'response': resposta,
            'tool_called': tool_name,
            'arguments': args,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro teste MCP: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Funções de fallback para when MCP não está disponível 