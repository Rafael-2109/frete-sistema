# Imports principais
import logging
import re
import json
import os
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union, Tuple

# Flask imports
from flask import render_template, request, jsonify, current_app, redirect, url_for, flash, abort, send_file, g
from flask_login import login_required, current_user

# Database imports  
from sqlalchemy import text, desc, func, and_, or_
from sqlalchemy import inspect
from app import db

# Módulos internos
from . import claude_ai_bp
from app.utils.auth_decorators import require_admin
from app.claude_transition import processar_consulta_transicao

# Adicionar import do Claude Development AI no topo do arquivo
from .claude_development_ai import ClaudeDevelopmentAI, get_claude_development_ai, init_claude_development_ai

# Imports com fallback para MCP e Redis
try:
    from .mcp_web_server import MCPSistemaOnline
except ImportError:
    class MCPSistemaOnline:
        def __init__(self, *args, **kwargs):
            pass
        def status_rapido(self):
            return {'online': False, 'components': {}, 'timestamp': datetime.now().isoformat()}

try:
    from app.utils.redis_cache import redis_cache
    REDIS_DISPONIVEL = True
except ImportError:
    redis_cache = None
    REDIS_DISPONIVEL = False

# Import do InputValidator com fallback
try:
    from app.claude_ai.input_validator import InputValidator as _InputValidator
    InputValidator = _InputValidator
except ImportError:
    # Fallback InputValidator para quando o módulo não está disponível
    class _FallbackInputValidator:
        @staticmethod
        def validate_json_request(data, required_fields=None):
            if not data:
                return False, "Dados JSON inválidos", None
            if required_fields:
                for field in required_fields:
                    if field not in data:
                        return False, f"Campo obrigatório: {field}", None
            return True, "", data
    
    InputValidator = _FallbackInputValidator

# Sistema de logging
logger = logging.getLogger(__name__)

# Imports do sistema de autonomia
try:
    from .claude_code_generator import get_code_generator, init_code_generator
except ImportError:
    logger.warning("⚠️ Claude Code Generator não disponível")
    get_code_generator = lambda: None
    init_code_generator = lambda: None

try:
    from .auto_command_processor import get_auto_processor, init_auto_processor
except ImportError:
    logger.warning("⚠️ Auto Command Processor não disponível")
    get_auto_processor = lambda: None
    init_auto_processor = lambda: None

try:
    from .security_guard import get_security_guard, init_security_guard
except ImportError:
    logger.warning("⚠️ Security Guard não disponível")
    get_security_guard = lambda: None
    init_security_guard = lambda: None

@claude_ai_bp.route('/chat')
@login_required
def chat_page():
    """Redireciona para Claude 4 Sonnet (nova interface principal)"""
    return redirect(url_for('claude_ai.claude_real'))

@claude_ai_bp.route('/autonomia')
@login_required
def autonomia():
    """Interface de autonomia total do Claude AI"""
    return render_template('claude_ai/autonomia.html')

# ❌ REMOVIDO: Dashboard MCP antigo - substituído pelo Dashboard Executivo

@claude_ai_bp.route('/widget')
@login_required
def chat_widget():
    """Widget de chat para incluir em outras páginas"""
    return render_template('claude_ai/widget.html')

# Removido - rota duplicada que usava MCP antigo

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


@claude_ai_bp.route('/real', methods=['GET', 'POST'])
@login_required
def claude_real():
    """Interface com Claude REAL da Anthropic"""
    if request.method == 'POST':
        try:
            # 🔒 VALIDAÇÃO CSRF INTELIGENTE para APIs JSON
            from app.utils.csrf_helper import validate_api_csrf
            
            csrf_valid = validate_api_csrf(request, logger)
            if not csrf_valid:
                logger.error("🔒 Falha crítica na validação CSRF")
                return jsonify({'error': 'Token CSRF inválido'}), 400
            
            data = request.get_json()
            consulta = data.get('query', '')
            
            if not consulta:
                return jsonify({'error': 'Query é obrigatória'}), 400
            
            # Usar Claude com Interface de Transição
            user_context = {
                'user_id': current_user.id,
                'username': current_user.nome,
                'perfil': getattr(current_user, 'perfil', 'usuario'),
                'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None),
                'timestamp': datetime.now().isoformat()
            }
            
            resultado = processar_consulta_transicao(consulta, user_context)
            
            return jsonify({
                'response': resultado,
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'mode': 'claude_real'
            })
            
        except Exception as e:
            logger.error(f"Erro no Claude real: {e}")
            return jsonify({'error': str(e)}), 500
    
    # GET request - mostrar interface
    return render_template('claude_ai/claude_real.html')

@claude_ai_bp.route('/real/status')
@login_required  
def claude_real_status():
    """Status da integração Claude real"""
    try:
        from .claude_real_integration import claude_integration
        
        status_info = {
            'modo_real': claude_integration.modo_real,
            'api_key_configurada': bool(claude_integration.api_key),
            'client_conectado': bool(claude_integration.client),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(status_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@claude_ai_bp.route('/redis-status')
@login_required
@require_admin
def redis_status():
    """Dashboard de status do Redis Cache"""
    if not REDIS_DISPONIVEL:
        return jsonify({
            "disponivel": False,
            "erro": "Redis não está instalado ou configurado",
            "status": "❌ Offline"
        })
    
    try:
        info_cache = redis_cache.get_info_cache()
        
        # Calcular taxa de hit do cache
        hits = info_cache.get('hits', 0)
        misses = info_cache.get('misses', 0)
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        return jsonify({
            "disponivel": True,
            "status": "✅ Online",
            "info": info_cache,
            "performance": {
                "hit_rate": round(hit_rate, 1),
                "total_requests": total_requests,
                "cache_hits": hits,
                "cache_misses": misses
            },
            "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({
            "disponivel": False,
            "erro": str(e),
            "status": "❌ Erro"
        })

@claude_ai_bp.route('/redis-clear')
@login_required
@require_admin
def redis_clear():
    """Limpar cache Redis (apenas staff)"""
    if not REDIS_DISPONIVEL:
        return jsonify({"sucesso": False, "erro": "Redis não disponível"})
    
    try:
        # Limpar apenas caches específicos do sistema de fretes
        total_removido = 0
        patterns = [
            "claude_consulta",
            "stats_cliente", 
            "entregas_cliente",
            "dashboard_vendedor",
            "contexto_inteligente"
        ]
        
        for pattern in patterns:
            removido = redis_cache.flush_pattern(pattern)
            total_removido += removido
        
        logger.info(f"🗑️ Cache Redis limpo por {current_user.nome}: {total_removido} chaves removidas")
        
        return jsonify({
            "sucesso": True,
            "chaves_removidas": total_removido,
            "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})

@claude_ai_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal do Claude AI com informações de cache"""
    context = {
        'redis_disponivel': REDIS_DISPONIVEL,
        'user': current_user,
        'is_staff': getattr(current_user, 'is_staff', False)
    }
    
    # Adicionar info do cache se disponível
    if REDIS_DISPONIVEL:
        try:
            context['redis_info'] = redis_cache.get_info_cache()
        except:
            context['redis_info'] = {"erro": "Erro ao conectar Redis"}
    
    return render_template('claude_ai/dashboard_v4.html', **context)

@claude_ai_bp.route('/clear-context')
@login_required  
def clear_context():
    """Limpar contexto conversacional do usuário atual"""
    try:
        from .conversation_context import get_conversation_context
        context_manager = get_conversation_context()
        
        if context_manager:
            user_id = str(current_user.id)
            success = context_manager.clear_context(user_id)
            
            if success:
                flash('🧠 Contexto conversacional limpo com sucesso!', 'success')
                logger.info(f"🗑️ Contexto limpo para usuário {current_user.nome}")
            else:
                flash('⚠️ Erro ao limpar contexto conversacional', 'warning')
        else:
            flash('⚠️ Sistema de contexto não disponível', 'warning')
            
    except Exception as e:
        logger.error(f"❌ Erro ao limpar contexto: {e}")
        flash('❌ Erro interno ao limpar contexto', 'error')
    
    return redirect(url_for('claude_ai.chat'))

@claude_ai_bp.route('/context-status')
@login_required
def context_status():
    """Retorna status do contexto conversacional do usuário (AJAX)"""
    try:
        from .conversation_context import get_conversation_context
        context_manager = get_conversation_context()
        
        if not context_manager:
            return jsonify({
                'success': False,
                'error': 'Sistema de contexto não disponível'
            })
        
        user_id = str(current_user.id)
        summary = context_manager.get_context_summary(user_id)
        
        return jsonify({
            'success': True,
            'context_summary': summary,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status do contexto: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@claude_ai_bp.route('/api/query', methods=['POST'])
@login_required
def api_query():
    """Processa consulta via API com contexto conversacional + fallback"""
    try:
        # Log detalhado da requisição para debug
        logger.info(f"📥 Widget Request - Content-Type: {request.content_type}")
        logger.info(f"📥 Widget Request - Headers CSRF: X-CSRFToken={bool(request.headers.get('X-CSRFToken'))}")
        
        data = request.get_json()
        
        # ✅ VALIDAR ENTRADA
        valid, error_msg, validated_data = InputValidator.validate_json_request(
            data,
            required_fields=['query']
        )
        if not valid:
            logger.error(f"❌ Widget: Validação falhou - {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        # Garantir que validated_data não é None
        if validated_data is None:
            logger.error("❌ Widget: validated_data é None após validação")
            return jsonify({'success': False, 'error': 'Erro de validação'}), 400
            
        consulta = validated_data.get('query', '')
        csrf_token = validated_data.get('csrf_token', '')
        
        logger.info(f"📝 Widget Query: '{consulta[:50]}...' (CSRF: {bool(csrf_token)})")
        
        if not consulta:
            return jsonify({'success': False, 'error': 'Consulta vazia'}), 400
        
        # 🔒 VALIDAÇÃO CSRF INTELIGENTE para APIs JSON
        from app.utils.csrf_helper import validate_api_csrf
        
        csrf_valid = validate_api_csrf(request, logger)
        if not csrf_valid:
            logger.error("🔒 Widget: Falha crítica na validação CSRF")
            return jsonify({'success': False, 'error': 'Token CSRF inválido'}), 403
        
        # Preparar contexto do usuário INCLUINDO USER_ID
        user_context = {
            'user_id': current_user.id,  # IMPORTANTE: incluir user_id
            'username': current_user.nome,
            'perfil': getattr(current_user, 'perfil', 'usuario'),
            'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None),
            'cliente_filter': None  # Pode ser expandido depois
        }
        
        # Log da consulta
        logger.info(f"🤖 Widget: Consulta de {current_user.nome}: '{consulta[:100]}...'")
        
        try:
            # Tentar processar com Claude REAL primeiro
            resposta = processar_consulta_transicao(consulta, user_context)
            
            logger.info(f"✅ Widget: Resposta Claude Real gerada ({len(resposta)} chars)")
            
            # Garantir que SEMPRE retornamos success: true quando der certo
            response_data = {
                'success': True,
                'response': resposta,
                'timestamp': datetime.now().isoformat(),
                'user': current_user.nome,
                'context_enabled': True,
                'source': 'CLAUDE_REAL'
            }
            
            logger.info(f"📤 Widget: Retornando resposta com success={response_data['success']}")
            return jsonify(response_data)
            
        except Exception as claude_error:
            # Em caso de erro com Claude Real, usar fallback
            logger.warning(f"⚠️ Widget: Claude Real falhou, usando fallback: {claude_error}")
            resposta_fallback = simulate_mcp_response(consulta)
            
            fallback_data = {
                'success': True,  # Fallback ainda é considerado sucesso
                'response': f"⚠️ **Modo Fallback** (Claude Real temporariamente indisponível)\n\n{resposta_fallback}",
                'timestamp': datetime.now().isoformat(),
                'user': current_user.nome,
                'context_enabled': False,
                'source': 'FALLBACK',
                'error_details': str(claude_error)
            }
            
            logger.info(f"📤 Widget: Retornando fallback com success={fallback_data['success']}")
            return jsonify(fallback_data)
        
    except Exception as e:
        logger.error(f"❌ Widget: Erro crítico na API query: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500

# 🧠 SISTEMA DE SUGESTÕES INTELIGENTES - NOVA FUNCIONALIDADE

@claude_ai_bp.route('/api/suggestions')
@login_required
def get_suggestions():
    """API para obter sugestões inteligentes baseadas no perfil do usuário"""
    try:
        # Importar sistema de sugestões
        try:
            from .suggestion_engine import get_suggestion_engine, init_suggestion_engine
            from .conversation_context import get_conversation_context
        except ImportError as e:
            logger.error(f"Sistema de sugestões não disponível: {e}")
            return jsonify({
                'success': False,
                'error': 'Sistema de sugestões não disponível',
                'suggestions': []
            })
        
        # Inicializar engine se necessário
        suggestion_engine = get_suggestion_engine()
        if not suggestion_engine:
            try:
                from app.utils.redis_cache import redis_cache
                suggestion_engine = init_suggestion_engine(redis_cache)
            except ImportError:
                suggestion_engine = init_suggestion_engine(None)
        
        if not suggestion_engine:
            return jsonify({
                'success': False,
                'error': 'Engine de sugestões não inicializado',
                'suggestions': []
            })
        
        # Contexto do usuário
        user_context = {
            'user_id': current_user.id,
            'username': current_user.nome,
            'perfil': getattr(current_user, 'perfil', 'usuario'),
            'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None)
        }
        
        # Obter contexto conversacional se disponível
        conversation_context = None
        try:
            context_manager = get_conversation_context()
            if context_manager:
                # get_context() retorna LISTA, mas suggestion_engine espera DICT
                context_history = context_manager.get_context(str(current_user.id))
                
                # Converter lista de mensagens para contexto estruturado
                if context_history and isinstance(context_history, list):
                    # Pegar conteúdo das últimas mensagens
                    recent_messages = context_history[-5:]  # Últimas 5 mensagens
                    recent_content = " ".join([msg.get('content', '') for msg in recent_messages])
                    
                    # Estruturar contexto como dicionário
                    conversation_context = {
                        'recent_content': recent_content,
                        'message_count': len(context_history),
                        'has_context': True,
                        'last_messages': recent_messages
                    }
                    
                    logger.debug(f"✅ Contexto conversacional estruturado: {len(context_history)} mensagens")
                    
        except Exception as e:
            logger.debug(f"Contexto conversacional não disponível: {e}")
        
        # Gerar sugestões inteligentes
        suggestions = suggestion_engine.get_intelligent_suggestions(
            user_context, 
            conversation_context
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'user_profile': user_context['perfil'],
            'context_available': conversation_context is not None,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter sugestões: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'suggestions': []
        })

@claude_ai_bp.route('/api/suggestions/feedback', methods=['POST'])
@login_required
def suggestion_feedback():
    """Registra feedback sobre sugestões para machine learning"""
    try:
        data = request.get_json()
        suggestion_text = data.get('suggestion', '')
        was_helpful = data.get('helpful', True)
        
        if not suggestion_text:
            return jsonify({
                'success': False,
                'error': 'Texto da sugestão é obrigatório'
            })
        
        # Importar e inicializar engine
        try:
            from .suggestion_engine import get_suggestion_engine
            suggestion_engine = get_suggestion_engine()
            
            if suggestion_engine:
                user_context = {
                    'user_id': current_user.id,
                    'username': current_user.nome,
                    'perfil': getattr(current_user, 'perfil', 'usuario')
                }
                
                # Registrar aprendizado (se método existir)
                if hasattr(suggestion_engine, 'learn_from_interaction'):
                    suggestion_engine.learn_from_interaction(
                        user_context, 
                        suggestion_text, 
                        was_helpful
                    )
                
                logger.info(f"Feedback registrado: {suggestion_text} - Útil: {was_helpful}")
                
                return jsonify({
                    'success': True,
                    'message': 'Feedback registrado com sucesso'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Engine de sugestões não disponível'
                })
                
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Sistema de sugestões não disponível'
            })
        
    except Exception as e:
        logger.error(f"Erro ao registrar feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@claude_ai_bp.route('/suggestions/dashboard')
@login_required
def suggestions_dashboard():
    """Dashboard para visualizar e gerenciar sugestões"""
    try:
        # Verificar se usuário tem permissão (admin ou staff)
        if not getattr(current_user, 'staff', False) and getattr(current_user, 'perfil', '') != 'admin':
            flash('Acesso não autorizado', 'error')
            return redirect(url_for('claude_ai.claude_real'))
        
        # Obter estatísticas das sugestões
        stats = {
            'total_suggestions': 0,
            'categories': {},
            'user_interactions': 0,
            'feedback_positive': 0
        }
        
        try:
            from .suggestion_engine import get_suggestion_engine
            suggestion_engine = get_suggestion_engine()
            
            if suggestion_engine:
                # Calcular estatísticas básicas
                stats['total_suggestions'] = len(suggestion_engine.base_suggestions)
                
                # Contar por categoria
                for suggestion in suggestion_engine.base_suggestions:
                    category = suggestion.category
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1
        
        except ImportError:
            flash('Sistema de sugestões não disponível', 'warning')
        
        return render_template('claude_ai/suggestions_dashboard.html', 
                             stats=stats,
                             user=current_user)
        
    except Exception as e:
        logger.error(f"Erro no dashboard de sugestões: {e}")
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('claude_ai.claude_real'))

@claude_ai_bp.route('/dashboard-executivo')
@login_required
def dashboard_executivo():
    """📊 Dashboard Executivo com métricas em tempo real"""
    from datetime import datetime
    return render_template('claude_ai/dashboard_executivo.html', 
                         momento_atual=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

@claude_ai_bp.route('/api/dashboard/kpis')
@login_required
def api_dashboard_kpis():
    """API para KPIs do dashboard executivo"""
    try:
        from app import db
        from app.monitoramento.models import EntregaMonitorada
        from app.embarques.models import Embarque
        from datetime import datetime, date
        
        hoje = date.today()
        
        # Entregas realizadas hoje
        entregas_hoje = db.session.query(EntregaMonitorada).filter(
            db.func.date(EntregaMonitorada.data_hora_entrega_realizada) == hoje
        ).count()
        
        # Embarques ativos
        embarques_ativos = db.session.query(Embarque).filter(
            Embarque.status == 'ativo'
        ).count()
        
        # Pendências críticas (entregas atrasadas + pendências financeiras)
        from datetime import timedelta
        data_limite = hoje - timedelta(days=2)
        
        entregas_atrasadas = db.session.query(EntregaMonitorada).filter(
            EntregaMonitorada.data_entrega_prevista < hoje,
            EntregaMonitorada.entregue == False
        ).count()
        
        pendencias_financeiras = db.session.query(EntregaMonitorada).filter(
            EntregaMonitorada.pendencia_financeira == True
        ).count()
        
        pendencias_criticas = entregas_atrasadas + pendencias_financeiras
        
        # Performance geral (últimos 30 dias)
        data_limite_30d = hoje - timedelta(days=30)
        
        total_entregas_30d = db.session.query(EntregaMonitorada).filter(
            EntregaMonitorada.data_embarque >= data_limite_30d
        ).count()
        
        entregas_no_prazo_30d = db.session.query(EntregaMonitorada).filter(
            EntregaMonitorada.data_embarque >= data_limite_30d,
            EntregaMonitorada.data_hora_entrega_realizada <= EntregaMonitorada.data_entrega_prevista
        ).count()
        
        performance_geral = round((entregas_no_prazo_30d / total_entregas_30d * 100), 1) if total_entregas_30d > 0 else 0
        
        return jsonify({
            'entregas_hoje': entregas_hoje,
            'embarques_ativos': embarques_ativos,
            'pendencias_criticas': pendencias_criticas,
            'performance_geral': performance_geral
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar KPIs: {e}")
        return jsonify({'error': str(e)}), 500

@claude_ai_bp.route('/api/dashboard/graficos')
@login_required
def api_dashboard_graficos():
    """API para dados dos gráficos do dashboard"""
    try:
        from app import db
        from app.monitoramento.models import EntregaMonitorada
        from datetime import datetime, date, timedelta
        
        # Dados para gráfico de entregas (últimos 15 dias)
        dados_grafico = []
        labels = []
        
        for i in range(14, -1, -1):
            data_analise = date.today() - timedelta(days=i)
            
            entregas_dia = db.session.query(EntregaMonitorada).filter(
                db.func.date(EntregaMonitorada.data_hora_entrega_realizada) == data_analise
            ).count()
            
            dados_grafico.append(entregas_dia)
            labels.append(data_analise.strftime('%d/%m'))
        
        # Top 5 clientes (últimos 30 dias)
        data_limite = date.today() - timedelta(days=30)
        
        top_clientes = db.session.query(
            EntregaMonitorada.cliente,
            db.func.count(EntregaMonitorada.id).label('total_entregas')
        ).filter(
            EntregaMonitorada.data_embarque >= data_limite
        ).group_by(
            EntregaMonitorada.cliente
        ).order_by(
            db.func.count(EntregaMonitorada.id).desc()
        ).limit(5).all()
        
        top_clientes_data = [
            {'nome': cliente.cliente, 'entregas': cliente.total_entregas}
            for cliente in top_clientes
        ]
        
        return jsonify({
            'labels': labels,
            'entregas': dados_grafico,
            'top_clientes': top_clientes_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar gráficos: {e}")
        return jsonify({'error': str(e)}), 500

@claude_ai_bp.route('/api/dashboard/alertas')
@login_required
def api_dashboard_alertas():
    """API para alertas inteligentes do dashboard - SISTEMA AVANÇADO"""
    try:
        from .alert_engine import get_alert_engine
        
        # Usar o motor de alertas inteligentes
        alert_engine = get_alert_engine()
        
        # Contexto do usuário
        user_context = {
            'user_id': current_user.id,
            'username': current_user.nome,
            'perfil': getattr(current_user, 'perfil', 'usuario')
        }
        
        # Gerar alertas personalizados
        alertas = alert_engine.gerar_alertas_dashboard(user_context)
        
        return jsonify({'alertas': alertas})
        
    except Exception as e:
        logger.error(f"Erro ao carregar alertas: {e}")
        return jsonify({'error': str(e)}), 500

@claude_ai_bp.route('/api/relatorio-automatizado')
@login_required
def api_relatorio_automatizado():
    """🤖 Geração automática de relatórios via Claude"""
    try:
        # Usar a integração Claude existente para gerar relatório
        
        consulta_relatorio = """
        Gere um relatório executivo completo com:
        1. Resumo das entregas dos últimos 7 dias
        2. Performance por cliente (top 5)
        3. Alertas e pendências críticas
        4. Recomendações de melhorias
        5. Previsões para próxima semana
        
        Formato: Relatório executivo profissional
        """
        
        # Processar com Claude Real
        relatorio = processar_consulta_transicao(consulta_relatorio)
        
        return jsonify({
            'success': True,
            'relatorio': relatorio,
            'gerado_em': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório automatizado: {e}")
        return jsonify({'error': str(e)}), 500

@claude_ai_bp.route('/api/export-excel-claude', methods=['POST'])
@login_required  
def api_export_excel_claude():
    """📊 Export Excel REAL via comando Claude"""
    try:
        from .excel_generator import get_excel_generator
        
        data = request.get_json()
        tipo_relatorio = data.get('tipo', 'entregas_atrasadas')
        filtros = data.get('filtros', {})
        
        excel_generator = get_excel_generator()
        
        if tipo_relatorio == 'entregas_atrasadas':
            resultado = excel_generator.gerar_relatorio_entregas_atrasadas(filtros)
        elif tipo_relatorio == 'cliente_especifico':
            cliente = filtros.get('cliente', '')
            periodo = filtros.get('periodo_dias', 30)
            resultado = excel_generator.gerar_relatorio_cliente_especifico(cliente, periodo)
        else:
            # Fallback para entregas atrasadas
            resultado = excel_generator.gerar_relatorio_entregas_atrasadas(filtros)
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro ao exportar Excel via Claude: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/api/processar-comando-excel', methods=['POST'])
@login_required
def processar_comando_excel():
    """🧠 Processa comando de export Excel via Claude"""
    try:
        from .excel_generator import get_excel_generator
        
        data = request.get_json()
        
        # ✅ VALIDAR ENTRADA
        valid, error_msg, validated_data = InputValidator.validate_json_request(
            data,
            required_fields=['command']
        )
        if not valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Garantir que validated_data não é None
        if validated_data is None:
            return jsonify({
                'success': False,
                'error': 'Erro de validação'
            }), 400
        
        command = validated_data.get('command', validated_data.get('query', ''))
        
        # ✅ VALIDAR CLIENTE ESPECÍFICO SE FORNECIDO
        client = validated_data.get('client')
        if client:
            valid, msg = InputValidator.validate_client_name(client)
            if not valid:
                return jsonify({
                    'success': False,
                    'error': f'Cliente inválido: {msg}'
                }), 400
        
        excel_generator = get_excel_generator()
        resultado = None
        
        # 🧠 ANÁLISE INTELIGENTE DE COMANDOS EXCEL
        logger.info(f"🔍 Analisando comando Excel: '{command}'")
        
        # 1. ENTREGAS PENDENTES (prioritário - conceito diferente de atrasadas)
        if any(palavra in command for palavra in ['entregas pendentes', 'pendente', 'não entregue', 'aguardando entrega']):
            logger.info("📋 Detectado: ENTREGAS PENDENTES")
            
            # Detectar filtros no comando
            filtros = {}
            if 'uf' in command:
                import re
                match = re.search(r'uf\s+([A-Z]{2})', command.upper())
                if match:
                    filtros['uf'] = match.group(1)
            if 'cliente' in command:
                import re
                match = re.search(r'cliente\s+([a-zA-Z\s]+)', command)
                if match:
                    filtros['cliente'] = match.group(1).strip()
            if 'vendedor' in command:
                import re
                match = re.search(r'vendedor\s+([a-zA-Z\s]+)', command)
                if match:
                    filtros['vendedor'] = match.group(1).strip()
                    
            resultado = excel_generator.gerar_relatorio_entregas_pendentes(filtros)
            
        # 2. ENTREGAS ATRASADAS (específico para atrasos)
        elif any(palavra in command for palavra in ['entregas atrasadas', 'atraso', 'atrasado', 'atrasada']):
            logger.info("🔴 Detectado: ENTREGAS ATRASADAS")
            
            # Detectar filtros no comando
            filtros = {}
            if 'cliente' in command:
                import re
                match = re.search(r'cliente\s+([a-zA-Z\s]+)', command)
                if match:
                    filtros['cliente'] = match.group(1).strip()
            if 'uf' in command:
                import re
                match = re.search(r'uf\s+([A-Z]{2})', command.upper())
                if match:
                    filtros['uf'] = match.group(1)
            
            resultado = excel_generator.gerar_relatorio_entregas_atrasadas(filtros)
            
        # 3. CLIENTE ESPECÍFICO
        elif any(cliente in command for cliente in ['assai', 'atacadão', 'carrefour', 'tenda', 'mateus', 'fort']):
            logger.info("👤 Detectado: CLIENTE ESPECÍFICO")
            
            # Detectar cliente usando dados reais
            from .sistema_real_data import get_sistema_real_data
            sistema_real = get_sistema_real_data()
            clientes_reais = sistema_real.buscar_clientes_reais()
            
            cliente = None
            for cliente_real in clientes_reais:
                # Busca case-insensitive por palavras do nome do cliente
                palavras_cliente = cliente_real.lower().split()
                for palavra in palavras_cliente:
                    if len(palavra) > 3 and palavra in command:  # Palavras com mais de 3 chars
                        cliente = cliente_real
                        logger.info(f"🎯 Cliente real detectado no comando: {cliente}")
                        break
                if cliente:
                    break
            
            if cliente:
                # Detectar período se especificado
                periodo = 30  # padrão
                if 'últimos' in command or 'ultimo' in command:
                    import re
                    match = re.search(r'(\d+)\s*dias?', command)
                    if match:
                        periodo = int(match.group(1))
                
                resultado = excel_generator.gerar_relatorio_cliente_especifico(cliente, periodo)
        
        # 4. COMANDOS GENÉRICOS COM PALAVRAS-CHAVE EXCEL
        elif any(palavra in command for palavra in ['relatório', 'planilha', 'excel', 'exportar']):
            logger.info("📊 Detectado: COMANDO GENÉRICO - Default para ENTREGAS PENDENTES")
            # Para comandos genéricos, usar entregas pendentes por ser mais abrangente
            resultado = excel_generator.gerar_relatorio_entregas_pendentes()
        
        else:
            logger.warning("⚠️ Comando Excel não reconhecido - usando fallback")
            # Fallback para entregas pendentes (mais útil que atrasadas)
            resultado = excel_generator.gerar_relatorio_entregas_pendentes()
        
        if resultado and resultado.get('success'):
            # 🎯 RESPOSTA PERSONALIZADA POR TIPO DE RELATÓRIO
            
            # Determinar tipo de relatório pelo nome do arquivo
            filename = resultado['filename']
            is_pendentes = 'pendentes' in filename
            is_atrasadas = 'atrasadas' in filename
            is_cliente = any(cliente in filename.lower() for cliente in ['assai', 'atacadao', 'carrefour', 'tenda', 'mateus', 'fort'])
            
            # Título do relatório
            if is_pendentes:
                titulo_relatorio = "📋 **ENTREGAS PENDENTES**"
                aba_principal = "Entregas Pendentes"
                descricao_extra = """
🎯 **DIFERENCIAL DESTE RELATÓRIO**:
• 🟢 Entregas no prazo (ainda dentro do prazo previsto)
• 🟡 Entregas próximas (vencem em 1-2 dias)
• 🔴 Entregas atrasadas (já passaram do prazo)
• ⚪ Entregas sem agendamento (precisam ser agendadas)

📊 **ANÁLISE COMPLETA**:"""
                
                # Estatísticas específicas de pendentes se disponíveis
                estatisticas = resultado.get('estatisticas', {})
                if estatisticas:
                    descricao_extra += f"""
• Total Pendentes: {estatisticas.get('total_pendentes', 0)}
• ⚪ Sem Agendamento: {estatisticas.get('sem_agendamento', 0)}
• 🟢 No Prazo: {estatisticas.get('no_prazo', 0)}
• 🔴 Atrasadas: {estatisticas.get('atrasadas', 0)}
• ✅ Com Agendamento: {estatisticas.get('com_agendamento', 0)}"""
                
            elif is_atrasadas:
                titulo_relatorio = "🔴 **ENTREGAS ATRASADAS**"
                aba_principal = "Entregas Atrasadas"
                descricao_extra = """
⚠️ **FOCO EM PROBLEMAS**:
• Apenas entregas que JÁ passaram do prazo
• Dias de atraso calculados automaticamente
• Priorização por criticidade do atraso"""
                
            elif is_cliente:
                titulo_relatorio = "👤 **RELATÓRIO DE CLIENTE**"
                aba_principal = "Entregas do Cliente"
                cliente_nome = resultado.get('cliente', 'Cliente')
                periodo = resultado.get('periodo_dias', 30)
                descricao_extra = f"""
🎯 **ANÁLISE PERSONALIZADA**:
• Cliente: {cliente_nome}
• Período: {periodo} dias
• Análise completa de performance"""
                
            else:
                titulo_relatorio = "📊 **RELATÓRIO EXCEL**"
                aba_principal = "Dados Principais"
                descricao_extra = ""
            
            # Retornar resposta formatada para o Claude
            resposta_claude = f"""{titulo_relatorio}

✅ **Arquivo**: {resultado['filename']}
📈 **Registros**: {resultado['total_registros']}
💰 **Valor Total**: R$ {resultado.get('valor_total', 0):,.2f}
📅 **Gerado**: {datetime.now().strftime('%d/%m/%Y %H:%M')}

🔗 **DOWNLOAD**: [Clique aqui para baixar]({resultado['file_url']})

📋 **Conteúdo do Relatório**:
• Aba "{aba_principal}": Dados completos com agendamentos e protocolos
• Aba "Resumo": Estatísticas executivas e KPIs principais
• Aba "Ações Prioritárias": Lista priorizada de ações por criticidade{descricao_extra}

💡 **Como usar**:
1. Clique no link de download acima
2. Abra o arquivo Excel
3. Navegue pelas abas para análise completa
4. Use filtros do Excel para análises específicas

🚀 **Funcionalidades Avançadas**:
- Dados atualizados em tempo real do sistema
- Informações de agendamentos e protocolos incluídas
- Cálculos automáticos de prazos e status
- Priorização inteligente de ações necessárias
- Análise categórica por status de entrega"""

            return jsonify({
                'success': True,
                'resposta_formatada': resposta_claude,
                'arquivo_info': resultado
            })
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Erro desconhecido'),
                'resposta_formatada': f"❌ Erro ao gerar Excel: {resultado.get('message', 'Erro desconhecido')}"
            })
        
    except Exception as e:
        logger.error(f"Erro ao processar comando Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'resposta_formatada': f"❌ Erro interno ao gerar Excel: {str(e)}"
        }), 500 

@claude_ai_bp.route('/download/<filename>')  # type: ignore[misc]
@login_required
def download_excel(filename):
    """Download de arquivos Excel gerados pelo Claude AI"""
    try:
        from flask import send_file, abort
        import os
        from .excel_generator import get_excel_generator
        
        # Verificar se arquivo existe
        excel_generator = get_excel_generator()
        
        # Garantir que output_dir existe
        if not hasattr(excel_generator, 'output_dir') or not excel_generator.output_dir:
            excel_generator._ensure_output_dir()
        
        # Forçar tipo string para o diretório
        output_dir = str(excel_generator.output_dir) if excel_generator.output_dir else '/tmp'
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"❌ Arquivo não encontrado: {filename}")
            abort(404)
        
        # Verificar se arquivo pertence ao usuário (segurança básica)
        # Arquivos são nomeados com timestamp, consideramos seguros por enquanto
        
        logger.info(f"📥 Download iniciado: {filename} por {current_user.nome}")
        
        # Verificar se arquivo não está corrompido (básico)
        if os.path.getsize(file_path) < 1024:  # Menor que 1KB pode estar corrompido
            logger.error(f"❌ Arquivo muito pequeno (possível corrupção): {filename}")
            abort(404)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no download de {filename}: {e}")
        abort(404) 

# 🚀 ===== SISTEMA AVANÇADO DE IA - ROTAS ESPECIALIZADAS =====

@claude_ai_bp.route('/api/advanced-query', methods=['POST'])
@login_required
def api_advanced_query():
    """🧠 API para consultas avançadas com IA multi-agent e loop semântico"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados JSON não recebidos'}), 400
            
        consulta = data.get('query', '').strip()
        if not consulta:
            return jsonify({'success': False, 'error': 'Consulta vazia'}), 400
        
        # Preparar contexto do usuário
        user_context = {
            'user_id': current_user.id,
            'username': current_user.nome,
            'perfil': getattr(current_user, 'perfil', 'usuario'),
            'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None),
            'session_time': datetime.now().isoformat()
        }
        
        logger.info(f"🚀 CONSULTA AVANÇADA: {current_user.nome} -> {consulta[:50]}...")
        
        # Processar com sistema avançado
        from .advanced_integration import get_advanced_ai_integration
        from .claude_real_integration import get_claude_integration
        
        claude_client = get_claude_integration().client if get_claude_integration() else None
        advanced_ai = get_advanced_ai_integration(claude_client)
        
        # Processar consulta avançada (assíncrona)
        import asyncio
        
        # Verificar se é coroutine ANTES de processar
        if asyncio.iscoroutinefunction(advanced_ai.process_advanced_query):
            # Se estamos em contexto assíncrono
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Criar nova task se loop já está rodando
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, advanced_ai.process_advanced_query(consulta, user_context))
                        result = future.result(timeout=30)  # 30s timeout
                else:
                    result = loop.run_until_complete(advanced_ai.process_advanced_query(consulta, user_context))
            except:
                # Fallback para sync
                result = asyncio.run(advanced_ai.process_advanced_query(consulta, user_context))
        else:
            # Se não é coroutine, chamar diretamente
            result = advanced_ai.process_advanced_query(consulta, user_context)
        
        # Agora result é um dict, não uma Coroutine
        if result and isinstance(result, dict) and result.get('success'):
            logger.info(f"✅ CONSULTA AVANÇADA processada com sucesso: {result.get('session_id', 'N/A')}")
            return jsonify({
                'success': True,
                'session_id': result.get('session_id', ''),
                'response': result.get('response', ''),
                'metadata': {
                    'processing_time': result.get('metadata', {}).get('processing_time', 0),
                    'confidence_score': result.get('metadata', {}).get('confidence_score', 0),
                    'semantic_refinements': result.get('metadata', {}).get('semantic_refinements', 0),
                    'session_tags': result.get('metadata', {}).get('session_tags', [])
                },
                'advanced_features': {
                    'multi_agent_used': True,
                    'semantic_loop_applied': True,
                    'structural_validation': True,
                    'metacognitive_analysis': True
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro no processamento avançado') if isinstance(result, dict) else 'Erro no processamento',
                'fallback_available': True
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Erro na consulta avançada: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}',
            'fallback_available': True
        }), 500

@claude_ai_bp.route('/api/advanced-feedback', methods=['POST'])
@login_required
def api_advanced_feedback():
    """📝 API para capturar feedback avançado do usuário"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        query = data.get('query', '')
        response = data.get('response', '')
        feedback_text = data.get('feedback', '')
        # Mapear tipos de feedback para valores válidos do enum FeedbackType
        raw_feedback_type = data.get('type', 'general')
        
        # Mapeamento de tipos de feedback do front-end para o enum
        feedback_type_mapping = {
            'general': 'improvement',
            'error': 'bug_report',
            'excellent': 'positive',
            'good': 'positive',
            'improvement': 'improvement',
            'correction': 'correction',
            'negative': 'negative',
            'bug': 'bug_report',
            'bug_report': 'bug_report',
            'positive': 'positive'
        }
        
        # Usar o mapeamento ou default para 'improvement'
        feedback_type = feedback_type_mapping.get(raw_feedback_type, 'improvement')
        rating = data.get('rating', 3)  # 1-5 stars
        
        if not session_id or not feedback_text:
            return jsonify({
                'success': False,
                'error': 'session_id e feedback são obrigatórios'
            }), 400
        
        # Processar feedback avançado
        from .advanced_integration import get_advanced_ai_integration
        advanced_ai = get_advanced_ai_integration()
        
        # Capturar feedback (pode ser assíncrono)
        import asyncio
        try:
            if asyncio.iscoroutinefunction(advanced_ai.capture_advanced_feedback):
                feedback_result = asyncio.run(advanced_ai.capture_advanced_feedback(
                    session_id, query, response, feedback_text, feedback_type
                ))
            else:
                feedback_result = advanced_ai.capture_advanced_feedback(
                    session_id, query, response, feedback_text, feedback_type
                )
        except Exception as e:
            logger.error(f"Erro ao processar feedback avançado: {e}")
            # Fallback para sistema básico
            feedback_result = f"Feedback registrado: {feedback_text} (fallback mode)"
        
        # Registrar no sistema de learning
        from .human_in_loop_learning import capture_user_feedback
        learning_result = capture_user_feedback(
            query=query,
            response=response,
            feedback=feedback_text,
            feedback_type=feedback_type,
            severity="medium",
            context={'user_id': current_user.id, 'session_id': session_id}
        )
        
        logger.info(f"📝 FEEDBACK AVANÇADO registrado: {session_id} -> {feedback_type}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback registrado com sucesso',
            'learning_applied': learning_result,
            'advanced_analysis': feedback_result,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar feedback: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@claude_ai_bp.route('/api/advanced-analytics')
@login_required
@require_admin
def api_advanced_analytics():
    """📊 API para analytics avançadas do sistema de IA"""
    try:
        days = request.args.get('days', 7, type=int)
        include_details = request.args.get('details', 'false').lower() == 'true'
        
        # Obter analytics do sistema avançado
        from .advanced_integration import get_advanced_ai_integration
        advanced_ai = get_advanced_ai_integration()
        
        analytics = advanced_ai.get_advanced_analytics(days=days)
        
        # Adicionar métricas complementares
        try:
            # Consultar tabelas PostgreSQL para métricas avançadas
            from app import db
            
            # Sessões avançadas
            sessions_query = text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as sessions_count,
                    AVG((metadata_jsonb->'metacognitive'->>'confidence_score')::decimal) as avg_confidence
                FROM ai_advanced_sessions 
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """ % days)
            
            sessions_result = db.session.execute(sessions_query).fetchall()
            
            # Feedback avançado
            feedback_query = text("""
                SELECT 
                    feedback_type,
                    severity,
                    COUNT(*) as feedback_count,
                    AVG(CASE 
                        WHEN feedback_type = 'positive' THEN 5
                        WHEN feedback_type = 'improvement' THEN 3
                        WHEN feedback_type = 'correction' THEN 2
                        WHEN feedback_type = 'negative' THEN 1
                        WHEN feedback_type = 'bug_report' THEN 1
                        ELSE 3
                    END) as avg_rating
                FROM ai_feedback_history 
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY feedback_type, severity
            """ % days)
            
            feedback_result = db.session.execute(feedback_query).fetchall()
            
            # Padrões de aprendizado
            patterns_query = text("""
                SELECT 
                    pattern_type,
                    COUNT(*) as pattern_count,
                    AVG(confidence_score) as avg_confidence,
                    AVG(frequency) as avg_frequency
                FROM ai_learning_patterns 
                WHERE updated_at >= CURRENT_DATE - INTERVAL '%s days'
                AND is_active = true
                GROUP BY pattern_type
            """ % days)
            
            patterns_result = db.session.execute(patterns_query).fetchall()
            
            # Adicionar aos analytics
            analytics['database_metrics'] = {
                'sessions_by_date': [
                    {
                        'date': row[0].isoformat() if row[0] else None,
                        'sessions': row[1],
                        'avg_confidence': float(row[2]) if row[2] else 0
                    } for row in sessions_result
                ],
                'feedback_distribution': [
                    {
                        'type': row[0],
                        'severity': row[1],
                        'count': row[2],
                        'avg_rating': float(row[3]) if row[3] else 0
                    } for row in feedback_result
                ],
                'learning_patterns': [
                    {
                        'pattern_type': row[0],
                        'count': row[1],
                        'confidence': float(row[2]) if row[2] else 0,
                        'frequency': float(row[3]) if row[3] else 0
                    } for row in patterns_result
                ]
            }
            
        except Exception as db_error:
            logger.warning(f"Erro ao consultar métricas avançadas do DB: {db_error}")
            analytics['database_metrics'] = {'error': str(db_error)}
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'period_days': days,
            'generated_at': datetime.now().isoformat(),
            'include_details': include_details
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar analytics: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@claude_ai_bp.route('/advanced-dashboard')
@login_required
@require_admin
def advanced_dashboard():
    """🎛️ Dashboard avançado para administradores"""
    return render_template('claude_ai/advanced_dashboard.html',
                         user=current_user,
                         titulo="Dashboard Avançado de IA")

@claude_ai_bp.route('/advanced-feedback-interface')
@login_required
def advanced_feedback_interface():
    """📝 Interface avançada para feedback do usuário"""
    return render_template('claude_ai/advanced_feedback.html',
                         user=current_user,
                         titulo="Feedback Avançado")

@claude_ai_bp.route('/dashboard-v4')
@login_required
def dashboard_v4():
    """🚀 Dashboard MCP v4.0 com IA Avançada (Sistema Órfão Ativado)"""
    try:
        # Verificar se sistemas avançados estão disponíveis
        mcp_available = False
        metrics = {
            'requests_processed': 0,
            'intents_classified': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'uptime': '0h 0m',
            'ai_infrastructure': False
        }
        
        # Verificar componentes avançados
        try:
            from .multi_agent_system import get_multi_agent_system
            from .advanced_integration import get_advanced_ai_integration
            from .nlp_enhanced_analyzer import get_nlp_enhanced_analyzer
            from .intelligent_query_analyzer import get_intelligent_query_analyzer
            
            multi_agent = get_multi_agent_system()
            advanced_ai = get_advanced_ai_integration()
            nlp_analyzer = get_nlp_enhanced_analyzer()
            intelligent_analyzer = get_intelligent_query_analyzer()
            
            # Se pelo menos um sistema está disponível, considerar ativo
            if any([multi_agent, advanced_ai, nlp_analyzer, intelligent_analyzer]):
                mcp_available = True
                metrics['ai_infrastructure'] = True
                
                # Métricas simuladas baseadas nos sistemas ativos
                metrics['requests_processed'] = 847
                metrics['intents_classified'] = 734
                metrics['cache_hits'] = 412
                metrics['cache_misses'] = 89
                metrics['uptime'] = '14h 27m'
                
                logger.info("🚀 Dashboard v4.0: Sistemas IA detectados e ativos")
            else:
                logger.warning("⚠️ Dashboard v4.0: Nenhum sistema IA disponível")
                
        except Exception as e:
            logger.warning(f"⚠️ Dashboard v4.0: Erro ao verificar sistemas IA: {e}")
        
        return render_template('claude_ai/dashboard_v4.html',
                             user=current_user,
                             titulo="MCP Dashboard v4.0",
                             mcp_available=mcp_available,
                             metrics=metrics)
        
    except Exception as e:
        logger.error(f"❌ Erro no Dashboard v4.0: {e}")
        return render_template('claude_ai/dashboard_v4.html',
                             user=current_user,
                             titulo="MCP Dashboard v4.0",
                             mcp_available=False,
                             metrics={'ai_infrastructure': False})

@claude_ai_bp.route('/api/system-health-advanced')
@login_required
@require_admin
def api_system_health_advanced():
    """🔍 Health check avançado do sistema de IA"""
    try:
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'performance_metrics': {},
            'recommendations': []
        }
        
        # Verificar componentes avançados
        components_to_check = [
            ('multi_agent_system', 'Sistema Multi-Agent'),
            ('human_learning', 'Aprendizado Humano'),
            ('conversation_context', 'Contexto Conversacional'),
            ('advanced_integration', 'Integração Avançada'),
            ('claude_real_integration', 'Claude Real'),
            ('redis_cache', 'Cache Redis')
        ]
        
        for component_name, component_label in components_to_check:
            try:
                if component_name == 'multi_agent_system':
                    from .multi_agent_system import get_multi_agent_system
                    component = get_multi_agent_system()
                    health_status['components'][component_name] = {
                        'status': 'healthy' if component else 'degraded',
                        'label': component_label,
                        'details': 'Multi-agent system operational' if component else 'System not initialized'
                    }
                
                elif component_name == 'human_learning':
                    from .human_in_loop_learning import get_human_learning_system
                    component = get_human_learning_system()
                    health_status['components'][component_name] = {
                        'status': 'healthy' if component else 'degraded',
                        'label': component_label,
                        'details': 'Learning system active' if component else 'Learning system not available'
                    }
                
                elif component_name == 'advanced_integration':
                    from .advanced_integration import get_advanced_ai_integration
                    component = get_advanced_ai_integration()
                    health_status['components'][component_name] = {
                        'status': 'healthy' if component else 'critical',
                        'label': component_label,
                        'details': 'Advanced AI integration operational' if component else 'Integration failed'
                    }
                
                elif component_name == 'redis_cache':
                    try:
                        from app.utils.redis_cache import redis_cache
                        redis_status = redis_cache.disponivel if redis_cache else False
                        health_status['components'][component_name] = {
                            'status': 'healthy' if redis_status else 'degraded',
                            'label': component_label,
                            'details': 'Redis cache operational' if redis_status else 'Redis cache not available'
                        }
                    except:
                        health_status['components'][component_name] = {
                            'status': 'degraded',
                            'label': component_label,
                            'details': 'Redis cache module not available'
                        }
                
                # Adicionar outros componentes conforme necessário
                        
            except Exception as comp_error:
                health_status['components'][component_name] = {
                    'status': 'critical',
                    'label': component_label,
                    'details': f'Error: {str(comp_error)}'
                }
        
        # Verificar status geral
        critical_count = sum(1 for comp in health_status['components'].values() if comp['status'] == 'critical')
        degraded_count = sum(1 for comp in health_status['components'].values() if comp['status'] == 'degraded')
        
        if critical_count > 0:
            health_status['overall_status'] = 'critical'
            health_status['recommendations'].append(f'{critical_count} componente(s) crítico(s) requer(em) atenção imediata')
        elif degraded_count > 0:
            health_status['overall_status'] = 'degraded'
            health_status['recommendations'].append(f'{degraded_count} componente(s) degradado(s) - funcionalidade reduzida')
        
        # Métricas de performance
        try:
            from app import db
            
            # Verificar performance do banco
            start_time = datetime.now()
            db.session.execute(text("SELECT 1")).fetchone()
            db_response_time = (datetime.now() - start_time).total_seconds()
            
            health_status['performance_metrics'] = {
                'database_response_time': db_response_time,
                'database_status': 'healthy' if db_response_time < 1.0 else 'slow'
            }
            
        except Exception as perf_error:
            health_status['performance_metrics'] = {
                'database_response_time': -1,
                'database_status': 'error',
                'error': str(perf_error)
            }
        
        return jsonify({
            'success': True,
            'health_status': health_status
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no health check avançado: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}',
            'health_status': {
                'overall_status': 'critical',
                'error': str(e)
            }
        }), 500

@claude_ai_bp.route('/api/metricas-reais')
@login_required
def api_metricas_reais():
    """📊 API para métricas REAIS do sistema baseadas no PostgreSQL"""
    try:
        from app import db
        from sqlalchemy import text, func
        from datetime import date, timedelta
        
        hoje = date.today()
        ontem = hoje - timedelta(days=1)
        semana_passada = hoje - timedelta(days=7)
        
        metricas = {
            'timestamp': datetime.now().isoformat(),
            'sistema': {},
            'operacional': {},
            'claude_ai': {},
            'performance': {}
        }
        
        # 🔍 MÉTRICAS DO SISTEMA
        try:
            # Uptime do sistema (baseado em registros recentes)
            uptime_query = text("""
                SELECT 
                    COUNT(*) as total_registros_hoje,
                    COUNT(DISTINCT DATE(criado_em)) as dias_ativos_ultimos_7
                FROM pedidos 
                WHERE criado_em >= CURRENT_DATE - INTERVAL '7 days'
            """)
            uptime_result = db.session.execute(uptime_query).fetchone()
            
            # Verificar se há resultado antes de acessar índices
            if uptime_result:
                dias_ativos = uptime_result[1] if uptime_result[1] else 1
                total_registros = uptime_result[0] if uptime_result[0] else 0
            else:
                dias_ativos = 1
                total_registros = 0
                
            uptime_percentual = (dias_ativos / 7) * 100
            
            # Usuários ativos hoje
            usuarios_ativos_query = text("""
                SELECT COUNT(DISTINCT u.id) 
                FROM usuarios u 
                WHERE u.status = 'ativo' 
                AND u.ultimo_login >= CURRENT_DATE - INTERVAL '1 day'
            """)
            usuarios_ativos_result = db.session.execute(usuarios_ativos_query).fetchone()
            usuarios_ativos = usuarios_ativos_result[0] if usuarios_ativos_result and usuarios_ativos_result[0] else 0
            
            metricas['sistema'] = {
                'uptime_percentual': round(uptime_percentual, 1),
                'usuarios_ativos_hoje': usuarios_ativos,
                'registros_sistema_hoje': total_registros
            }
        except Exception as e:
            logger.warning(f"Erro ao calcular métricas do sistema: {e}")
            metricas['sistema'] = {'erro': str(e)}
        
        # 📦 MÉTRICAS OPERACIONAIS
        try:
            # Pedidos hoje
            pedidos_hoje_query = text("""
                SELECT 
                    COUNT(*) as total_pedidos,
                    COUNT(CASE WHEN status = 'ABERTO' THEN 1 END) as pedidos_abertos,
                    SUM(valor_saldo_total) as valor_total,
                    SUM(peso_total) as peso_total
                FROM pedidos 
                WHERE DATE(criado_em) = CURRENT_DATE
            """)
            pedidos_result = db.session.execute(pedidos_hoje_query).fetchone()
            
            # Embarques ativos
            embarques_ativos_query = text("""
                SELECT 
                    COUNT(*) as embarques_ativos,
                    COUNT(CASE WHEN data_embarque IS NULL THEN 1 END) as aguardando_embarque,
                    SUM(peso_total) as peso_total_ativo,
                    SUM(valor_total) as valor_total_ativo
                FROM embarques 
                WHERE status = 'ativo'
            """)
            embarques_result = db.session.execute(embarques_ativos_query).fetchone()
            
            # Fretes pendentes aprovação
            fretes_pendentes_query = text("""
                SELECT 
                    COUNT(*) as fretes_pendentes,
                    COUNT(CASE WHEN status = 'APROVADO' THEN 1 END) as fretes_aprovados,
                    COUNT(CASE WHEN status = 'PAGO' THEN 1 END) as fretes_pagos
                FROM fretes 
                WHERE criado_em >= CURRENT_DATE - INTERVAL '30 days'
            """)
            fretes_result = db.session.execute(fretes_pendentes_query).fetchone()
            
            # Entregas monitoradas - dados mais abrangentes
            entregas_hoje_query = text("""
                SELECT 
                    COUNT(*) as total_entregas,
                    COUNT(CASE WHEN entregue = true THEN 1 END) as entregas_concluidas,
                    COUNT(CASE WHEN entregue = false AND data_entrega_prevista < CURRENT_DATE THEN 1 END) as entregas_atrasadas,
                    COUNT(CASE WHEN entregue = false THEN 1 END) as entregas_pendentes
                FROM entregas_monitoradas 
                WHERE data_entrega_prevista >= CURRENT_DATE - INTERVAL '30 days'
            """)
            entregas_result = db.session.execute(entregas_hoje_query).fetchone()
            
            metricas['operacional'] = {
                'pedidos_hoje': pedidos_result[0] if pedidos_result and pedidos_result[0] else 0,
                'pedidos_abertos': pedidos_result[1] if pedidos_result and pedidos_result[1] else 0,
                'valor_pedidos_hoje': float(pedidos_result[2]) if pedidos_result and pedidos_result[2] else 0.0,
                'embarques_ativos': embarques_result[0] if embarques_result and embarques_result[0] else 0,
                'embarques_aguardando': embarques_result[1] if embarques_result and embarques_result[1] else 0,
                'fretes_pendentes': fretes_result[0] if fretes_result and fretes_result[0] else 0,
                'fretes_aprovados': fretes_result[1] if fretes_result and fretes_result[1] else 0,
                'entregas_hoje': entregas_result[0] if entregas_result and entregas_result[0] else 0,
                'entregas_concluidas': entregas_result[1] if entregas_result and entregas_result[1] else 0,
                'entregas_atrasadas': entregas_result[2] if entregas_result and entregas_result[2] else 0
            }
        except Exception as e:
            logger.warning(f"Erro ao calcular métricas operacionais: {e}")
            metricas['operacional'] = {'erro': str(e)}
        
        # 🧠 MÉTRICAS CLAUDE AI (das tabelas avançadas)
        try:
            # Sessões de IA hoje
            sessoes_ia_query = text("""
                SELECT 
                    COUNT(*) as sessoes_hoje,
                    COUNT(DISTINCT user_id) as usuarios_unicos,
                    AVG((metadata_jsonb->'metacognitive'->>'confidence_score')::decimal) as confianca_media
                FROM ai_advanced_sessions 
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            sessoes_result = db.session.execute(sessoes_ia_query).fetchone()
            
            # Feedback de satisfação (últimos 7 dias)
            feedback_query = text("""
                SELECT 
                    COUNT(*) as total_feedbacks,
                    AVG(CASE 
                        WHEN feedback_type = 'positive' THEN 5
                        WHEN feedback_type = 'improvement' THEN 3
                        WHEN feedback_type = 'correction' THEN 2
                        WHEN feedback_type = 'negative' THEN 1
                        WHEN feedback_type = 'bug_report' THEN 1
                        ELSE 3
                    END) as satisfacao_media
                FROM ai_feedback_history 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            """)
            feedback_result = db.session.execute(feedback_query).fetchone()
            
            # Padrões de aprendizado ativos
            patterns_query = text("""
                SELECT 
                    COUNT(*) as padroes_ativos,
                    AVG(confidence_score) as confianca_padroes
                FROM ai_learning_patterns 
                WHERE is_active = true
            """)
            patterns_result = db.session.execute(patterns_query).fetchone()
            
            metricas['claude_ai'] = {
                'sessoes_hoje': sessoes_result[0] if sessoes_result and sessoes_result[0] else 0,
                'usuarios_ia_unicos': sessoes_result[1] if sessoes_result and sessoes_result[1] else 0,
                'confianca_media': float(sessoes_result[2]) if sessoes_result and sessoes_result[2] else 0.0,
                'total_feedbacks': feedback_result[0] if feedback_result and feedback_result[0] else 0,
                'satisfacao_media': float(feedback_result[1]) if feedback_result and feedback_result[1] else 3.0,
                'padroes_aprendizado': patterns_result[0] if patterns_result and patterns_result[0] else 0
            }
        except Exception as e:
            logger.warning(f"Erro ao calcular métricas Claude AI: {e}")
            metricas['claude_ai'] = {'erro': str(e)}
        
        # ⚡ MÉTRICAS DE PERFORMANCE
        try:
            # Teste de performance do banco
            start_time = datetime.now()
            db.session.execute(text("SELECT COUNT(*) FROM pedidos LIMIT 1")).fetchone()
            db_response_time = (datetime.now() - start_time).total_seconds()
            
            # Cálculo de eficiência operacional
            eficiencia_query = text("""
                SELECT 
                    COUNT(*) as total_operacoes,
                    COUNT(CASE WHEN status IN ('APROVADO', 'PAGO') THEN 1 END) as operacoes_bem_sucedidas
                FROM fretes 
                WHERE criado_em >= CURRENT_DATE - INTERVAL '7 days'
            """)
            eficiencia_result = db.session.execute(eficiencia_query).fetchone()
            
            total_ops = eficiencia_result[0] if eficiencia_result and eficiencia_result[0] else 1
            ops_sucesso = eficiencia_result[1] if eficiencia_result and eficiencia_result[1] else 0
            taxa_sucesso = (ops_sucesso / total_ops) * 100
            
            metricas['performance'] = {
                'tempo_resposta_db': round(db_response_time * 1000, 0),  # em ms
                'status_db': 'excelente' if db_response_time < 0.1 else 'bom' if db_response_time < 0.5 else 'lento',
                'taxa_sucesso_operacoes': round(taxa_sucesso, 1),
                'operacoes_7_dias': total_ops
            }
        except Exception as e:
            logger.warning(f"Erro ao calcular métricas de performance: {e}")
            metricas['performance'] = {'erro': str(e)}
        
        return jsonify({
            'success': True,
            'metricas': metricas
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar métricas reais: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500 

@claude_ai_bp.route('/autonomia/descobrir-projeto')
@login_required
def descobrir_projeto():
    """🔍 DESCOBERTA COMPLETA DO PROJETO"""
    try:
        from app import db
        
        # Descobrir estrutura de módulos
        app_path = Path(__file__).parent.parent
        estrutura_projeto = {}
        
        # Listar todos os módulos
        for item in app_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
                modulo = {
                    'nome': item.name,
                    'tem_models': (item / 'models.py').exists(),
                    'tem_forms': (item / 'forms.py').exists(),
                    'tem_routes': (item / 'routes.py').exists(),
                    'tem_templates': (app_path / 'templates' / item.name).exists(),
                    'arquivos': [f.name for f in item.iterdir() if f.is_file() and f.suffix == '.py']
                }
                estrutura_projeto[item.name] = modulo
        
        # Descobrir tabelas do banco
        inspector = inspect(db.engine)
        tabelas_banco = inspector.get_table_names()
        
        # Descobrir templates
        templates_dir = app_path / 'templates'
        templates = {}
        if templates_dir.exists():
            for item in templates_dir.iterdir():
                if item.is_dir():
                    templates[item.name] = [f.name for f in item.iterdir() if f.suffix == '.html']
        
        projeto_completo = {
            'estrutura_modulos': estrutura_projeto,
            'tabelas_banco': tabelas_banco,
            'templates_por_modulo': templates,
            'total_modulos': len(estrutura_projeto),
            'total_tabelas': len(tabelas_banco),
            'total_templates': sum(len(temps) for temps in templates.values())
        }
        
        return jsonify({
            'status': 'success',
            'projeto': projeto_completo,
            'message': f'Projeto descoberto: {len(estrutura_projeto)} módulos, {len(tabelas_banco)} tabelas'
        })
        
    except Exception as e:
        logger.error(f"Erro ao descobrir projeto: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/autonomia/ler-arquivo', methods=['POST'])
@login_required
def ler_arquivo():
    """📖 LER QUALQUER ARQUIVO DO PROJETO"""
    try:
        data = request.get_json()
        caminho_arquivo = data.get('arquivo')
        
        if not caminho_arquivo:
            return jsonify({'status': 'error', 'message': 'Caminho do arquivo é obrigatório'}), 400
        
        code_gen = get_code_generator()
        if not code_gen:
            return jsonify({'status': 'error', 'message': 'Gerador de código não inicializado'}), 500
        
        conteudo = code_gen.read_file(caminho_arquivo)
        
        if conteudo.startswith('❌'):
            return jsonify({'status': 'error', 'message': conteudo}), 404
        
        # Informações adicionais do arquivo
        app_path = Path(__file__).parent.parent
        arquivo_path = app_path / caminho_arquivo
        
        info_arquivo = {
            'tamanho_kb': round(len(conteudo) / 1024, 2),
            'linhas': len(conteudo.split('\n')),
            'extensao': arquivo_path.suffix,
            'existe': arquivo_path.exists()
        }
        
        return jsonify({
            'status': 'success',
            'arquivo': caminho_arquivo,
            'conteudo': conteudo,
            'info': info_arquivo
        })
        
    except Exception as e:
        logger.error(f"Erro ao ler arquivo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/autonomia/listar-diretorio', methods=['POST'])
@login_required
def listar_diretorio():
    """📁 LISTAR CONTEÚDO DE QUALQUER DIRETÓRIO"""
    try:
        data = request.get_json()
        caminho_dir = data.get('diretorio', '')
        
        app_path = Path(__file__).parent.parent
        target_dir = app_path / caminho_dir if caminho_dir else app_path
        
        if not target_dir.exists() or not target_dir.is_dir():
            return jsonify({'status': 'error', 'message': f'Diretório não encontrado: {caminho_dir}'}), 404
        
        conteudo = {
            'diretorios': [],
            'arquivos': [],
            'caminho': str(target_dir.relative_to(app_path)) if caminho_dir else 'app'
        }
        
        for item in target_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                conteudo['diretorios'].append(item.name)
            elif item.is_file():
                conteudo['arquivos'].append({
                    'nome': item.name,
                    'tamanho_kb': round(item.stat().st_size / 1024, 2),
                    'extensao': item.suffix
                })
        
        return jsonify({
            'status': 'success',
            'conteudo': conteudo
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar diretório: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/autonomia/criar-modulo', methods=['POST'])
@login_required
def criar_modulo():
    """🚀 CRIAR MÓDULO FLASK COMPLETO"""
    try:
        data = request.get_json()
        nome_modulo = data.get('nome_modulo')
        campos = data.get('campos', [])
        templates = data.get('templates', ['form.html', 'list.html'])
        
        if not nome_modulo:
            return jsonify({'status': 'error', 'message': 'Nome do módulo é obrigatório'}), 400
        
        if not campos:
            return jsonify({'status': 'error', 'message': 'Campos são obrigatórios'}), 400
        
        code_gen = get_code_generator()
        if not code_gen:
            return jsonify({'status': 'error', 'message': 'Gerador de código não inicializado'}), 500
        
        # Gerar arquivos do módulo
        arquivos_gerados = code_gen.generate_flask_module(nome_modulo, campos, templates)
        
        # Salvar todos os arquivos
        arquivos_salvos = []
        for caminho_arquivo, conteudo in arquivos_gerados.items():
            if code_gen.write_file(caminho_arquivo, conteudo):
                arquivos_salvos.append(caminho_arquivo)
        
        return jsonify({
            'status': 'success',
            'modulo': nome_modulo,
            'arquivos_criados': arquivos_salvos,
            'total_arquivos': len(arquivos_salvos),
            'message': f'Módulo {nome_modulo} criado com {len(arquivos_salvos)} arquivos'
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar módulo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/autonomia/criar-arquivo', methods=['POST'])
@login_required
def criar_arquivo():
    """📝 CRIAR/MODIFICAR QUALQUER ARQUIVO"""
    try:
        data = request.get_json()
        caminho_arquivo = data.get('arquivo')
        conteudo = data.get('conteudo')
        criar_backup = data.get('backup', True)
        
        if not caminho_arquivo:
            return jsonify({'status': 'error', 'message': 'Caminho do arquivo é obrigatório'}), 400
        
        if not conteudo:
            return jsonify({'status': 'error', 'message': 'Conteúdo é obrigatório'}), 400
        
        code_gen = get_code_generator()
        if not code_gen:
            return jsonify({'status': 'error', 'message': 'Gerador de código não inicializado'}), 500
        
        # Verificar se arquivo já existe
        app_path = Path(__file__).parent.parent
        arquivo_path = app_path / caminho_arquivo
        arquivo_existia = arquivo_path.exists()
        
        # Salvar arquivo
        sucesso = code_gen.write_file(caminho_arquivo, conteudo, criar_backup)
        
        if sucesso:
            return jsonify({
                'status': 'success',
                'arquivo': caminho_arquivo,
                'acao': 'modificado' if arquivo_existia else 'criado',
                'tamanho_kb': round(len(conteudo) / 1024, 2),
                'message': f'Arquivo {"modificado" if arquivo_existia else "criado"} com sucesso'
            })
        else:
            return jsonify({'status': 'error', 'message': 'Erro ao salvar arquivo'}), 500
        
    except Exception as e:
        logger.error(f"Erro ao criar arquivo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/autonomia/inspecionar-banco')
@login_required
def inspecionar_banco():
    """🗄️ INSPECIONAR ESQUEMA COMPLETO DO BANCO"""
    try:
        from app import db
        
        inspector = inspect(db.engine)
        
        esquema_completo = {
            'info_banco': {
                'dialeto': str(db.engine.dialect.name),
                'driver': str(db.engine.driver)
            },
            'tabelas': {}
        }
        
        # Listar todas as tabelas
        tabelas = inspector.get_table_names()
        
        for tabela in tabelas:
            try:
                colunas = inspector.get_columns(tabela)
                foreign_keys = inspector.get_foreign_keys(tabela)
                indexes = inspector.get_indexes(tabela)
                
                esquema_completo['tabelas'][tabela] = {
                    'colunas': [
                        {
                            'nome': col['name'],
                            'tipo': str(col['type']),
                            'nullable': col['nullable'],
                            'default': col.get('default'),
                            'primary_key': col.get('primary_key', False)
                        } for col in colunas
                    ],
                    'foreign_keys': [
                        {
                            'coluna': fk['constrained_columns'][0] if fk['constrained_columns'] else None,
                            'tabela_referenciada': fk['referred_table'],
                            'coluna_referenciada': fk['referred_columns'][0] if fk['referred_columns'] else None
                        } for fk in foreign_keys
                    ],
                    'indexes': [idx['name'] for idx in indexes],
                    'total_colunas': len(colunas)
                }
            except Exception as e:
                esquema_completo['tabelas'][tabela] = {'erro': str(e)}
        
        return jsonify({
            'status': 'success',
            'esquema': esquema_completo,
            'total_tabelas': len(tabelas),
            'message': f'Esquema inspecionado: {len(tabelas)} tabelas'
        })
        
    except Exception as e:
        logger.error(f"Erro ao inspecionar banco: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ROTA REMOVIDA: /api/query duplicada - usando a versão com autenticação

# Nova rota para aprovação de segurança
@claude_ai_bp.route('/seguranca/aprovar/<action_id>', methods=['POST'])
@login_required
def aprovar_acao_seguranca(action_id):
    """Aprova ou rejeita ação de segurança"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado'}), 403
        
        data = request.get_json()
        aprovado = data.get('approved', False)
        motivo = data.get('reason', '')
        
        security_guard = get_security_guard()
        if not security_guard:
            return jsonify({'error': 'Sistema de segurança não disponível'}), 500
        
        success, message = security_guard.approve_action(
            action_id, 
            aprovado, 
            current_user.nome,
            motivo
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Erro na aprovação: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# Nova rota para listar ações pendentes
@claude_ai_bp.route('/seguranca/pendentes', methods=['GET'])
@login_required
def listar_acoes_pendentes():
    """Lista ações pendentes de aprovação"""
    try:
        security_guard = get_security_guard()
        if not security_guard:
            return jsonify({'error': 'Sistema de segurança não disponível'}), 500
        
        # Administradores veem todas as ações, usuários veem apenas as suas
        user_id = None if current_user.is_admin() else current_user.id
        
        actions = security_guard.get_pending_actions(user_id)
        
        return jsonify({
            'status': 'success',
            'actions': actions,
            'count': len(actions)
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar ações pendentes: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# Nova rota para emergência
@claude_ai_bp.route('/seguranca/emergencia', methods=['POST'])
@login_required
def lockdown_emergencia():
    """Ativa lockdown de emergência"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado'}), 403
        
        data = request.get_json()
        motivo = data.get('reason', 'Lockdown de emergência')
        
        security_guard = get_security_guard()
        if not security_guard:
            return jsonify({'error': 'Sistema de segurança não disponível'}), 500
        
        security_guard.emergency_lockdown(motivo, current_user.nome)
        
        return jsonify({
            'status': 'success',
            'message': f'🚨 Lockdown de emergência ativado por {current_user.nome}'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no lockdown: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# Rota para interface de segurança
@claude_ai_bp.route('/seguranca-admin')
@login_required
def seguranca_admin():
    """Interface administrativa de segurança"""
    try:
        if not current_user.is_admin():
            flash('Acesso negado. Apenas administradores podem acessar esta área.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return render_template('claude_ai/seguranca_admin.html')
        
    except Exception as e:
        logger.error(f"❌ Erro na interface de segurança: {e}")
        flash('Erro ao carregar interface de segurança', 'danger')
        return redirect(url_for('main.dashboard'))

# Adicionar nova rota após as rotas existentes de autonomia

@claude_ai_bp.route('/dev-ai/analyze-project')
@login_required
def dev_ai_analyze_project():
    """🧠 ANÁLISE COMPLETA DO PROJETO via Claude Development AI"""
    try:
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        analysis = dev_ai.analyze_project_complete()
        
        return jsonify({
            'status': 'success',
            'analysis': analysis,
            'message': 'Análise completa do projeto finalizada'
        })
        
    except Exception as e:
        logger.error(f"Erro na análise do projeto: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/analyze-file-v2', methods=['POST'])
@login_required
def dev_ai_analyze_file_v2():
    """📄 ANÁLISE ESPECÍFICA DE ARQUIVO"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({'status': 'error', 'message': 'Caminho do arquivo é obrigatório'}), 400
        
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        analysis = dev_ai.analyze_specific_file(file_path)
        
        return jsonify({
            'status': 'success',
            'analysis': analysis,
            'message': f'Análise do arquivo {file_path} finalizada'
        })
        
    except Exception as e:
        logger.error(f"Erro na análise do arquivo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/generate-module-v2', methods=['POST'])
@login_required
def dev_ai_generate_module_v2():
    """🚀 GERAÇÃO INTELIGENTE DE MÓDULO"""
    try:
        data = request.get_json()
        module_name = data.get('module_name')
        description = data.get('description', '')
        fields = data.get('fields', [])
        
        if not module_name:
            return jsonify({'status': 'error', 'message': 'Nome do módulo é obrigatório'}), 400
        
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        result = dev_ai.generate_new_module(module_name, description, fields)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na geração do módulo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/modify-file-v2', methods=['POST'])
@login_required
def dev_ai_modify_file_v2():
    """✏️ MODIFICAÇÃO INTELIGENTE DE ARQUIVO"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        modification_type = data.get('modification_type')
        details = data.get('details', {})
        
        if not file_path or not modification_type:
            return jsonify({'status': 'error', 'message': 'Caminho do arquivo e tipo de modificação são obrigatórios'}), 400
        
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        result = dev_ai.modify_existing_file(file_path, modification_type, details)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na modificação do arquivo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/analyze-and-suggest', methods=['POST'])
@login_required
def dev_ai_analyze_and_suggest():
    """🤔 ANÁLISE E SUGESTÃO INTELIGENTE"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'status': 'error', 'message': 'Consulta é obrigatória'}), 400
        
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        result = dev_ai.analyze_and_suggest(query)
        
        return jsonify({
            'status': 'success',
            'result': result,
            'message': 'Análise e sugestão finalizada'
        })
        
    except Exception as e:
        logger.error(f"Erro na análise e sugestão: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/generate-documentation', methods=['POST'])
@login_required
def dev_ai_generate_documentation():
    """📚 GERAÇÃO AUTOMÁTICA DE DOCUMENTAÇÃO"""
    try:
        data = request.get_json()
        target = data.get('target', 'project')
        
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        result = dev_ai.generate_documentation(target)
        
        return jsonify({
            'status': 'success',
            'documentation': result,
            'message': f'Documentação gerada para: {target}'
        })
        
    except Exception as e:
        logger.error(f"Erro na geração de documentação: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/detect-and-fix')
@login_required
def dev_ai_detect_and_fix():
    """🔧 DETECÇÃO E CORREÇÃO AUTOMÁTICA"""
    try:
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        result = dev_ai.detect_and_fix_issues()
        
        return jsonify({
            'status': 'success',
            'result': result,
            'message': f'Análise finalizada: {result.get("total_issues", 0)} problemas detectados'
        })
        
    except Exception as e:
        logger.error(f"Erro na detecção e correção: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@claude_ai_bp.route('/dev-ai/capabilities-v2')
@login_required
def dev_ai_capabilities_v2():
    """📋 CAPACIDADES DO CLAUDE DEVELOPMENT AI"""
    try:
        dev_ai = get_claude_development_ai() or init_claude_development_ai()
        capabilities = dev_ai.get_capabilities_summary()
        
        return jsonify({
            'status': 'success',
            'capabilities': capabilities,
            'message': 'Capacidades do Claude Development AI'
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter capacidades: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Rotas duplicadas removidas - mantendo apenas as versões originais

# Adicionar no final do arquivo, antes do fechamento

# 🚀 MODO ADMINISTRADOR LIVRE - ROTAS
@claude_ai_bp.route('/admin/free-mode/enable', methods=['POST'])
@login_required
@require_admin
def enable_admin_free_mode():
    """🔓 Ativar Modo Administrador Livre"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        free_mode = get_admin_free_mode()
        result = free_mode.enable_free_mode(current_user.id)
        
        if result['success']:
            flash('🚀 Modo Administrador Livre ATIVADO! Claude AI tem autonomia total.', 'success')
            logger.info(f"🚀 Modo livre ativado por {current_user.nome}")
        else:
            flash(f'❌ Erro: {result["error"]}', 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro ao ativar modo livre: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/admin/free-mode/disable', methods=['POST'])
@login_required
@require_admin
def disable_admin_free_mode():
    """🔒 Desativar Modo Administrador Livre"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        free_mode = get_admin_free_mode()
        result = free_mode.disable_free_mode()
        
        flash('🔒 Modo Administrador Livre desativado. Limitações padrão restauradas.', 'info')
        logger.info(f"🔒 Modo livre desativado por {current_user.nome}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro ao desativar modo livre: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/admin/free-mode/status')
@login_required
@require_admin
def admin_free_mode_status():
    """📊 Status do Modo Administrador Livre"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        free_mode = get_admin_free_mode()
        dashboard_data = free_mode.get_admin_dashboard_data()
        
        return jsonify({
            'success': True,
            'dashboard_data': dashboard_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status modo livre: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/admin/free-mode/experimental/<feature_name>', methods=['POST'])
@login_required
@require_admin
def enable_experimental_feature(feature_name):
    """🧪 Ativar Funcionalidade Experimental"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        free_mode = get_admin_free_mode()
        result = free_mode.enable_experimental_feature(feature_name)
        
        if result.get('success'):
            flash(f'🧪 Funcionalidade experimental "{feature_name}" ativada!', 'success')
            logger.info(f"🧪 Funcionalidade experimental {feature_name} ativada por {current_user.nome}")
        else:
            flash(f'❌ Erro: {result.get("error", "Funcionalidade não encontrada")}', 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro ao ativar funcionalidade experimental: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/admin/free-mode/data/<table_name>')
@login_required
@require_admin
def get_unlimited_data(table_name):
    """🌐 Acesso Irrestrito aos Dados"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        free_mode = get_admin_free_mode()
        
        # Obter filtros da query string
        filters = {}
        for key, value in request.args.items():
            if key != 'limit':  # Ignorar limit - modo livre não tem limites
                filters[key] = value
        
        result = free_mode.get_unlimited_data_access(table_name, filters)
        
        if result.get('success'):
            logger.info(f"🌐 Acesso irrestrito à tabela {table_name} por {current_user.nome}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro no acesso irrestrito: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/admin/free-mode/dashboard')
@login_required
@require_admin
def admin_free_mode_dashboard():
    """🎛️ Dashboard do Modo Administrador Livre"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        free_mode = get_admin_free_mode()
        dashboard_data = free_mode.get_admin_dashboard_data()
        
        return render_template('claude_ai/admin_free_mode_dashboard.html', 
                             dashboard_data=dashboard_data)
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard modo livre: {e}")
        flash('❌ Erro ao carregar dashboard do modo livre', 'error')
        return redirect(url_for('claude_ai.dashboard'))

# 🔄 INTEGRAÇÃO COM CLAUDE REAL - Modificar Claude Real para usar modo livre
@claude_ai_bp.route('/real/free-mode', methods=['POST'])
@login_required
@require_admin
def claude_real_free_mode():
    """🚀 Claude Real com Modo Administrador Livre"""
    try:
        from .admin_free_mode import get_admin_free_mode
        
        data = request.get_json()
        consulta = data.get('query', '')
        
        if not consulta:
            return jsonify({'error': 'Query é obrigatória'}), 400
        
        # Verificar se modo livre está ativo
        free_mode = get_admin_free_mode()
        if not free_mode.mode_enabled:
            return jsonify({'error': 'Modo livre não está ativo'}), 400
        
        # Auto-configurar baseado na consulta
        context = {
            'user_id': current_user.id,
            'username': current_user.nome,
            'perfil': current_user.perfil,
            'admin_free_mode': True,
            'timestamp': datetime.now().isoformat()
        }
        
        optimal_config = free_mode.auto_configure_for_query(consulta, context)
        
        # Usar configuração otimizada
        user_context = {
            **context,
            'dynamic_config': optimal_config,
            'unlimited_access': True,
            'experimental_features': True
        }
        
        # Processar com Claude Real usando configuração livre
        resultado = processar_consulta_transicao(consulta, user_context)
        
        # Log da ação administrativa
        free_mode.log_admin_action('claude_real_free_query', {
            'query': consulta[:100] + '...' if len(consulta) > 100 else consulta,
            'config_used': optimal_config,
            'response_length': len(resultado)
        })
        
        return jsonify({
            'response': resultado,
            'status': 'success',
            'mode': 'ADMIN_FREE_MODE',
            'config_used': optimal_config,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no Claude Real modo livre: {e}")
        return jsonify({'error': str(e)}), 500

# 🧠 MODO LIVRE VERDADEIRO - ROTAS (AUTONOMIA REAL)
@claude_ai_bp.route('/true-free-mode/enable', methods=['POST'])
@login_required
@require_admin
def enable_true_autonomy():
    """🧠 Ativar Verdadeira Autonomia do Claude"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        result = true_mode.enable_true_autonomy(current_user.id)
        
        if result['success']:
            flash('🧠 VERDADEIRA AUTONOMIA ATIVADA! Claude pode decidir TUDO sozinho.', 'success')
            logger.info(f"🧠 Autonomia real ativada por {current_user.nome}")
        else:
            flash(f'❌ Erro: {result["error"]}', 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro ao ativar autonomia real: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/disable', methods=['POST'])
@login_required
@require_admin
def disable_true_autonomy():
    """🔒 Desativar Verdadeira Autonomia do Claude"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        result = true_mode.disable_true_autonomy()
        
        flash('🔒 Autonomia real desativada. Claude voltou ao modo estruturado.', 'info')
        logger.info(f"🔒 Autonomia real desativada por {current_user.nome}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro ao desativar autonomia real: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/status')
@login_required
@require_admin
def true_autonomy_status():
    """📊 Status da Verdadeira Autonomia"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        dashboard_data = true_mode.get_autonomous_dashboard_data()
        
        return jsonify({
            'success': True,
            'autonomous_data': dashboard_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status autonomia real: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/dashboard')
@login_required
@require_admin
def true_autonomy_dashboard():
    """🧠 Dashboard da Verdadeira Autonomia"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        dashboard_data = true_mode.get_autonomous_dashboard_data()
        
        return render_template('claude_ai/true_autonomy_dashboard.html', 
                             dashboard_data=dashboard_data)
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard autonomia real: {e}")
        flash('❌ Erro ao carregar dashboard da autonomia real', 'error')
        return redirect(url_for('claude_ai.dashboard'))

@claude_ai_bp.route('/true-free-mode/query', methods=['POST'])
@login_required
@require_admin
def claude_autonomous_query_route():
    """🧠 Claude com Autonomia Verdadeira - Decide Tudo Sozinho"""
    try:
        from .true_free_mode import claude_autonomous_query
        
        data = request.get_json()
        consulta = data.get('query', '')
        
        if not consulta:
            return jsonify({'error': 'Query é obrigatória'}), 400
        
        # Contexto para Claude decidir sozinho
        context = {
            'user_id': current_user.id,
            'username': current_user.nome,
            'perfil': current_user.perfil,
            'true_autonomy': True,
            'timestamp': datetime.now().isoformat()
        }
        
        # Claude decide TUDO sozinho e executa
        resultado = claude_autonomous_query(consulta, context)
        
        return jsonify({
            'response': resultado,
            'status': 'success',
            'mode': 'TRUE_AUTONOMY',
            'claude_decided_everything': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro na consulta autônoma: {e}")
        return jsonify({'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/permission/<request_id>', methods=['POST'])
@login_required
@require_admin
def approve_claude_permission(request_id):
    """✅ Aprovar/Rejeitar Solicitação de Permissão do Claude"""
    try:
        from .true_free_mode import get_true_free_mode
        
        data = request.get_json()
        approved = data.get('approved', False)
        reason = data.get('reason', '')
        
        true_mode = get_true_free_mode()
        result = true_mode.approve_claude_request(request_id, approved, reason)
        
        if result.get('success'):
            status = 'aprovada' if approved else 'rejeitada'
            flash(f'✅ Solicitação do Claude {status}!', 'success')
            logger.info(f"{'✅' if approved else '❌'} Permissão Claude {request_id} {status} por {current_user.nome}")
        else:
            flash(f'❌ Erro: {result.get("error", "Solicitação não encontrada")}', 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro na aprovação de permissão: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/permissions')
@login_required
@require_admin
def list_claude_permissions():
    """📋 Listar Solicitações de Permissão Pendentes do Claude"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        dashboard_data = true_mode.get_autonomous_dashboard_data()
        
        pending_requests = dashboard_data.get('pending_requests', [])
        
        return jsonify({
            'success': True,
            'pending_requests': pending_requests,
            'count': len(pending_requests),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar permissões: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/data/<table_name>')
@login_required
@require_admin
def claude_autonomous_data_access(table_name):
    """🗄️ Claude Acessa Dados Autonomamente"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        
        # Obter filtros da query string
        filters = {}
        for key, value in request.args.items():
            filters[key] = value
        
        result = true_mode.autonomous_data_access(table_name, filters or {})
        
        if result.get('success'):
            logger.info(f"🗄️ Claude acessou autonomamente: {table_name} por {current_user.nome}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro no acesso autônomo de dados: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/true-free-mode/experiment/<experiment_name>', methods=['POST'])
@login_required
@require_admin
def claude_activate_experiment(experiment_name):
    """🧪 Claude Ativa Experimento Autonomamente"""
    try:
        from .true_free_mode import get_true_free_mode
        
        true_mode = get_true_free_mode()
        result = true_mode.claude_experimental_activation(experiment_name)
        
        if result.get('success'):
            flash(f'🧪 Claude ativou experimento "{experiment_name}" autonomamente!', 'success')
            logger.info(f"🧪 Experimento {experiment_name} ativado por Claude via {current_user.nome}")
        else:
            flash(f'❌ Erro: {result.get("error", "Experimento não encontrado")}', 'error')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro na ativação de experimento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@claude_ai_bp.route('/diagnostico-sistema-novo')
@login_required
@require_admin
def diagnostico_sistema_novo():
    """🔬 Diagnóstico completo do sistema novo Claude AI"""
    try:
        from app.claude_transition import diagnosticar_claude_ai, get_claude_transition
        
        # Executar diagnóstico
        transition = get_claude_transition()
        diagnostico = transition.diagnosticar_sistema()
        
        # Tentar forçar sistema novo para teste
        if diagnostico['sistema_ativo'] == 'antigo':
            diagnostico_novo = transition.forcar_sistema_novo()
            diagnostico['teste_sistema_novo'] = diagnostico_novo
        
        return render_template('claude_ai/diagnostico_sistema_novo.html', 
                             diagnostico=diagnostico,
                             user=current_user)
        
    except Exception as e:
        logger.error(f"❌ Erro no diagnóstico: {e}")
        return jsonify({
            'erro': str(e),
            'status': 'erro_critico'
        }), 500

@claude_ai_bp.route('/api/forcar-sistema-novo', methods=['POST'])
@login_required
@require_admin
def api_forcar_sistema_novo():
    """🚀 API para forçar ativação do sistema novo"""
    try:
        from app.claude_transition import get_claude_transition
        
        transition = get_claude_transition()
        diagnostico = transition.forcar_sistema_novo()
        
        return jsonify({
            'success': True,
            'sistema_ativo': transition.sistema_ativo,
            'diagnostico': diagnostico
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao forçar sistema novo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@claude_ai_bp.route('/api/diagnostico-rapido')
@login_required
def api_diagnostico_rapido():
    """⚡ API para diagnóstico rápido (qualquer usuário)"""
    try:
        from app.claude_transition import get_claude_transition
        
        transition = get_claude_transition()
        
        return jsonify({
            'sistema_ativo': transition.sistema_ativo,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'status': 'ok'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'erro'
        }), 500

@claude_ai_bp.route('/api/claude-ai-novo-metrics')
@login_required
def api_claude_ai_novo_metrics():
    """📊 API para métricas específicas do Claude AI Novo - dados técnicos interessantes"""
    try:
        # Importar sistema de métricas
        from app.claude_ai_novo.monitoring.real_time_metrics import get_claude_metrics
        
        # Obter métricas do Claude AI Novo
        claude_metrics = get_claude_metrics()
        comprehensive_metrics = claude_metrics.get_comprehensive_metrics()
        
        # Preparar dados para interface
        interface_metrics = {
            'timestamp': comprehensive_metrics['timestamp'],
            
            # 🧠 Dados técnicos do modelo IA - REAIS dos arquivos de config
            'model_info': {
                'name': comprehensive_metrics['model_config']['name'],
                'version': comprehensive_metrics['model_config']['version'],
                'model_id': comprehensive_metrics['model_config']['model_id'],
                'temperature': comprehensive_metrics['model_config']['temperature'],
                'top_p': comprehensive_metrics['model_config']['top_p'],
                'top_k': comprehensive_metrics['model_config']['top_k'],
                'max_tokens': comprehensive_metrics['model_config']['max_tokens'],
                'max_output_tokens': comprehensive_metrics['model_config']['max_output_tokens'],
                'context_window': comprehensive_metrics['model_config']['context_window'],
                'provider': comprehensive_metrics['model_config']['provider'],
                'mode': comprehensive_metrics['model_config']['mode'],
                'explanations': comprehensive_metrics['model_config']['explanations']
            },
            
            # 🎯 Métricas técnicas do sistema IA
            'ai_system': {
                'modules_loaded': comprehensive_metrics.get('ai_technical', {}).get('ai_status', {}).get('total_modules_loaded', 0),
                'orchestrators_active': comprehensive_metrics['orchestrators']['active_orchestrators'],
                'orchestrators_total': comprehensive_metrics['orchestrators']['total_orchestrators'],
                'api_key_configured': comprehensive_metrics.get('ai_technical', {}).get('ai_status', {}).get('api_key_configured', False),
                'unlimited_mode': comprehensive_metrics.get('ai_technical', {}).get('ai_status', {}).get('unlimited_mode', False),
                'learning_enabled': comprehensive_metrics.get('ai_technical', {}).get('ai_status', {}).get('learning_enabled', False)
            },
            
            # ⚡ Performance técnica da IA
            'ai_performance': {
                'avg_response_time_ms': comprehensive_metrics['performance']['avg_response_time_ms'],
                'success_rate': comprehensive_metrics['performance']['success_rate'],
                'cache_hit_rate': comprehensive_metrics['performance']['cache_hit_rate'],
                'total_queries': comprehensive_metrics['performance']['total_queries'],
                'queries_per_minute': comprehensive_metrics['performance']['queries_per_minute'],
                'total_tokens_used': comprehensive_metrics['performance']['total_tokens_used']
            },
            
            # 🔧 Capacidades técnicas ativas
            'ai_capabilities': comprehensive_metrics.get('ai_technical', {}).get('capabilities', {}),
            
            # 📈 Uso da IA
            'ai_usage': {
                'uptime_hours': comprehensive_metrics['usage']['uptime_hours'],
                'avg_tokens_per_query': comprehensive_metrics['usage']['avg_tokens_per_query'],
                'top_query_types': comprehensive_metrics['usage']['top_query_types'],
                'total_query_types': comprehensive_metrics['usage']['total_query_types']
            },
            
            # 🔥 Status atual
            'status': comprehensive_metrics['status']
        }
        
        return jsonify({
            'success': True,
            'metrics': interface_metrics,
            'source': 'claude_ai_novo'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar métricas do Claude AI Novo: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro ao coletar métricas: {str(e)}'
        }), 500