from flask import render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
import subprocess
import json
import os
import sys
import logging
from datetime import datetime
from .mcp_connector import MCPSistemaOnline
from . import claude_ai_bp
from app.utils.auth_decorators import require_admin
from .claude_real_integration import processar_com_claude_real

# Configurar logger
logger = logging.getLogger(__name__)

# Importar sistema de sugestões inteligentes
try:
    from .suggestion_engine import get_suggestion_engine, init_suggestion_engine
    SUGGESTIONS_AVAILABLE = True
except ImportError:
    SUGGESTIONS_AVAILABLE = False
    logger.warning("Sistema de sugestões inteligentes não disponível")

# Importar contexto conversacional
try:
    from .conversation_context import get_conversation_context
    CONTEXT_AVAILABLE = True
except ImportError:
    CONTEXT_AVAILABLE = False
    logger.warning("Contexto conversacional não disponível")

# Importar MCP v4.0 Server
try:
    from .mcp_v4_server import mcp_v4_server, process_query
    MCP_V4_AVAILABLE = True
except ImportError:
    MCP_V4_AVAILABLE = False

# Importar Redis cache se disponível
try:
    from app.utils.redis_cache import redis_cache, REDIS_DISPONIVEL
except ImportError:
    REDIS_DISPONIVEL = False

@claude_ai_bp.route('/chat')
@login_required
def chat_page():
    """Redireciona para Claude 4 Sonnet (nova interface principal)"""
    from flask import redirect, url_for
    return redirect(url_for('claude_ai.claude_real'))

# ❌ REMOVIDO: Dashboard MCP antigo - substituído pelo Dashboard Executivo

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


@claude_ai_bp.route('/real', methods=['GET', 'POST'])
@login_required
def claude_real():
    """Interface com Claude REAL da Anthropic"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            consulta = data.get('query', '')
            
            if not consulta:
                return jsonify({'error': 'Query é obrigatória'}), 400
            
            # Usar Claude REAL
            user_context = {
                'user_id': current_user.id,
                'username': current_user.nome,
                'perfil': getattr(current_user, 'perfil', 'usuario'),
                'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None),
                'timestamp': datetime.now().isoformat()
            }
            
            resultado = processar_com_claude_real(consulta, user_context)
            
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
@require_admin()
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
@require_admin()
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
    """Processa consulta via API com contexto conversacional"""
    try:
        data = request.get_json()
        consulta = data.get('query', '').strip()
        
        if not consulta:
            return jsonify({'error': 'Consulta vazia'}), 400
        
        # Preparar contexto do usuário INCLUINDO USER_ID
        user_context = {
            'user_id': current_user.id,  # IMPORTANTE: incluir user_id
            'username': current_user.nome,
            'perfil': getattr(current_user, 'perfil', 'usuario'),
            'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None),
            'cliente_filter': None  # Pode ser expandido depois
        }
        
        # Log da consulta
        logger.info(f"🤖 Consulta Claude recebida de {current_user.nome}: '{consulta[:100]}...'")
        
        # Processar com Claude REAL
        resposta = processar_com_claude_real(consulta, user_context)
        
        return jsonify({
            'response': resposta,
            'timestamp': datetime.now().isoformat(),
            'user': current_user.nome,
            'context_enabled': True  # Indicar que contexto está ativo
        })
        
    except Exception as e:
        logger.error(f"❌ Erro na API query: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

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
                conversation_context = context_manager.get_context(str(current_user.id))
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
        })

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
        from .claude_real_integration import processar_com_claude_real
        
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
        relatorio = processar_com_claude_real(consulta_relatorio)
        
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
        comando = data.get('comando', '').lower()
        
        excel_generator = get_excel_generator()
        resultado = None
        
        # Analisar comando e determinar tipo de relatório
        if 'entregas atrasadas' in comando or 'atraso' in comando:
            # Detectar filtros no comando
            filtros = {}
            if 'cliente' in comando:
                # Extrair nome do cliente do comando
                import re
                match = re.search(r'cliente\s+([a-zA-Z\s]+)', comando)
                if match:
                    filtros['cliente'] = match.group(1).strip()
            
            resultado = excel_generator.gerar_relatorio_entregas_atrasadas(filtros)
            
        elif any(cliente in comando for cliente in ['assai', 'atacadão', 'carrefour', 'tenda']):
            # Relatório de cliente específico
            cliente = None
            for nome in ['assai', 'atacadão', 'carrefour', 'tenda']:
                if nome in comando:
                    cliente = nome.title()
                    break
            
            if cliente:
                resultado = excel_generator.gerar_relatorio_cliente_especifico(cliente)
        
        else:
            # Comando genérico - gerar entregas atrasadas
            resultado = excel_generator.gerar_relatorio_entregas_atrasadas()
        
        if resultado and resultado.get('success'):
            # Retornar resposta formatada para o Claude
            resposta_claude = f"""📊 **EXCEL GERADO COM SUCESSO!**

✅ **Arquivo**: {resultado['filename']}
📈 **Registros**: {resultado['total_registros']}
💰 **Valor Total**: R$ {resultado.get('valor_total', 0):,.2f}
📅 **Gerado**: {datetime.now().strftime('%d/%m/%Y %H:%M')}

🔗 **DOWNLOAD**: {resultado['file_url']}

📋 **Conteúdo do Relatório**:
• Aba "Entregas Atrasadas": Dados completos
• Aba "Resumo": Estatísticas principais  
• Aba "Ações Recomendadas": Lista de ações prioritárias

💡 **Como usar**: Clique no link acima para baixar o arquivo Excel."""

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