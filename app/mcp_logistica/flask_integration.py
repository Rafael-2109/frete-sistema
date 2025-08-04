"""
Integração do MCP com Flask
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_login import login_required, current_user
from functools import wraps
import logging
from typing import Dict, Optional
from datetime import datetime
import json

from .query_processor import QueryProcessor
from .preference_manager import PreferenceManager
from .confirmation_system import ConfirmationSystem, ActionType
from .error_handler import ErrorHandler, ErrorCategory
from .models import db, UserPreference, ConfirmationRequest

logger = logging.getLogger(__name__)

# Cria blueprint
mcp_logistica_bp = Blueprint('mcp_logistica', __name__, url_prefix='/api/mcp/logistica')

# Inicializa componentes
query_processor = None
preference_manager = None
confirmation_system = None
error_handler = None

def init_mcp_logistica(app):
    """Inicializa o sistema MCP Logística"""
    global query_processor, preference_manager, confirmation_system, error_handler
    
    with app.app_context():
        # Inicializa componentes
        query_processor = QueryProcessor(db.session, api_key=app.config.get('ANTHROPIC_API_KEY'))
        preference_manager = PreferenceManager(storage_backend=app.config.get('REDIS_CLIENT'))
        confirmation_system = ConfirmationSystem(storage_backend=app.config.get('REDIS_CLIENT'))
        error_handler = ErrorHandler()
        
        # Registra handlers de confirmação
        register_confirmation_handlers()
        
        logger.info("MCP Logística inicializado com sucesso")

def register_confirmation_handlers():
    """Registra handlers para ações de confirmação"""
    
    def handle_reschedule(request):
        """Handler para reagendamento"""
        from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
        
        try:
            entrega = EntregaMonitorada.query.get(request.entity_id)
            if not entrega:
                return False
                
            # Cria novo agendamento
            agendamento = AgendamentoEntrega(
                entrega_id=entrega.id,
                data_agendada=request.details['nova_data'],
                motivo=request.details.get('motivo', 'Reagendamento via MCP'),
                autor=request.confirmed_by,
                forma_agendamento='MCP',
                protocolo_agendamento=f'MCP-{request.id}'
            )
            
            db.session.add(agendamento)
            db.session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Erro ao reagendar: {e}")
            return False
            
    def handle_cancel(request):
        """Handler para cancelamento"""
        # Implementar lógica de cancelamento
        return True
        
    def handle_approve(request):
        """Handler para aprovação"""
        # Implementar lógica de aprovação
        return True
        
    # Registra handlers
    confirmation_system.register_action_handler(ActionType.REAGENDAR, handle_reschedule)
    confirmation_system.register_action_handler(ActionType.CANCELAR, handle_cancel)
    confirmation_system.register_action_handler(ActionType.APROVAR, handle_approve)

def require_mcp_permission(f):
    """Decorator para verificar permissões MCP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Autenticação necessária'}), 401
            
        # Verifica permissões específicas se necessário
        # Por enquanto, apenas verifica autenticação
        
        return f(*args, **kwargs)
    return decorated_function

@mcp_logistica_bp.route('/query', methods=['POST'])
@login_required
@require_mcp_permission
def process_query():
    """Processa consulta em linguagem natural"""
    data = None  # Initialize data variable to avoid UnboundLocalError
    try:
        # Check if request is JSON or form data
        if request.is_json:
            data = request.get_json()
        else:
            # Handle form data from HTML form
            data = {
                'query': request.form.get('query'),
                'output_format': request.form.get('output_format', 'json'),
                'limit': request.form.get('limit', '100'),
                'enhance_with_claude': request.form.get('enhance_with_claude', 'false').lower() == 'true'
            }
        
        if not data or 'query' not in data or not data['query']:
            return jsonify({'error': 'Query não fornecida'}), 400
            
        # Obtém contexto do usuário
        user_context = {
            'user_id': str(current_user.id),
            'user_name': current_user.nome,
            'timestamp': datetime.now().isoformat(),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'session_id': request.headers.get('X-Session-Id', g.get('session_id', 'default')),
            'enhance_with_claude': data.get('enhance_with_claude', False)
        }
        
        # Aplica preferências do usuário
        user_prefs = preference_manager.get_user_preferences(str(current_user.id))
        enhanced_context = preference_manager.apply_user_context(
            str(current_user.id), 
            user_context
        )
        
        # Processa consulta
        result = query_processor.process(data['query'], enhanced_context)
        
        # Registra para aprendizado
        preference_manager.learn_from_query(str(current_user.id), {
            'original_query': data['query'],
            'entities': result.query.entities,
            'context': result.query.context,
            'intent': {'primary': result.intent.primary},
            'success': result.success,
            'response_format': result.query.response_format
        })
        
        # Verifica se ação requer confirmação
        if result.intent.action_required:
            # Cria requisição de confirmação
            confirmation = confirmation_system.create_confirmation_request(
                action_type=ActionType[result.intent.primary.upper()],
                entity_type=result.query.context.get('domain', 'geral'),
                entity_id=str(result.intent.parameters.get('entity_id', '')),
                user_id=str(current_user.id),
                description=f"Confirmar {result.intent.primary} - {data['query']}",
                details=result.intent.parameters
            )
            
            return jsonify({
                'success': True,
                'requires_confirmation': True,
                'confirmation_id': confirmation.id,
                'confirmation_details': confirmation.to_dict(),
                'query_result': {
                    'intent': result.intent.primary,
                    'confidence': result.intent.confidence,
                    'parameters': result.intent.parameters
                }
            })
        
        # Retorna resultado normal
        response = {
            'success': result.success,
            'data': result.data,
            'intent': {
                'primary': result.intent.primary,
                'secondary': result.intent.secondary,
                'confidence': result.intent.confidence
            },
            'suggestions': result.suggestions,
            'response_format': result.query.response_format,
            'metadata': result.metadata
        }
        
        # Adiciona resposta natural do Claude se disponível
        if result.natural_response:
            response['natural_response'] = result.natural_response
            
        # Adiciona informações do Claude se usado
        if result.claude_response:
            response['claude_insights'] = {
                'used': True,
                'response_type': result.claude_response.response_type,
                'confidence': result.claude_response.confidence
            }
            
            # Se foi fallback completo do Claude, adiciona a resposta direta
            if result.claude_response.response_type == 'direct':
                response['claude_answer'] = result.claude_response.direct_answer
                
        if result.error:
            response['error'] = result.error
            
        if current_app.config.get('DEBUG'):
            debug_info = {}
            if result.sql:
                debug_info['sql'] = result.sql
            if result.claude_response and result.claude_response.metadata:
                debug_info['claude_metadata'] = result.claude_response.metadata
            if debug_info:
                response['debug'] = debug_info
                
        return jsonify(response)
        
    except Exception as e:
        # Trata erro
        error = error_handler.handle_error(
            e, 
            ErrorCategory.SYSTEM,
            context={'endpoint': 'query', 'data': data if data else {}},
            user_id=str(current_user.id)
        )
        
        return jsonify({
            'success': False,
            'error': error.message,
            'error_code': error.code,
            'suggestions': error.recovery_suggestions
        }), 500

@mcp_logistica_bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """Obtém sugestões de consultas"""
    try:
        partial_query = request.args.get('q', '')
        
        suggestions = preference_manager.get_query_suggestions(
            str(current_user.id),
            partial_query
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter sugestões: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """Obtém preferências do usuário"""
    try:
        prefs = preference_manager.get_user_preferences(str(current_user.id))
        insights = preference_manager.get_preference_insights(str(current_user.id))
        
        return jsonify({
            'success': True,
            'preferences': prefs,
            'insights': insights
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter preferências: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/preferences', methods=['PUT'])
@login_required
def update_preferences():
    """Atualiza preferências do usuário"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
            
        # Atualiza cada preferência
        for key, value in data.items():
            preference_manager.update_preference(
                str(current_user.id),
                'manual',
                key,
                value
            )
            
        return jsonify({
            'success': True,
            'message': 'Preferências atualizadas'
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar preferências: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/confirmations', methods=['GET'])
@login_required
def get_pending_confirmations():
    """Obtém confirmações pendentes"""
    try:
        # Filtros opcionais
        entity_type = request.args.get('entity_type')
        action_type = request.args.get('action_type')
        
        confirmations = confirmation_system.get_pending_confirmations(
            user_id=str(current_user.id),
            entity_type=entity_type,
            action_type=ActionType[action_type.upper()] if action_type else None
        )
        
        return jsonify({
            'success': True,
            'confirmations': [c.to_dict() for c in confirmations]
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter confirmações: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/confirmations/<confirmation_id>/confirm', methods=['POST'])
@login_required
def confirm_action(confirmation_id):
    """Confirma uma ação pendente"""
    try:
        data = request.get_json() or {}
        
        success = confirmation_system.confirm_action(
            confirmation_id,
            current_user.nome,
            data.get('details')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Ação confirmada com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Não foi possível confirmar a ação'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao confirmar ação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/confirmations/<confirmation_id>/reject', methods=['POST'])
@login_required
def reject_action(confirmation_id):
    """Rejeita uma ação pendente"""
    try:
        data = request.get_json() or {}
        
        success = confirmation_system.reject_action(
            confirmation_id,
            current_user.nome,
            data.get('reason')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Ação rejeitada'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Não foi possível rejeitar a ação'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao rejeitar ação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submete feedback sobre resultado"""
    try:
        data = request.get_json()
        
        if not data or 'query_id' not in data:
            return jsonify({'error': 'ID da consulta não fornecido'}), 400
            
        # Processa feedback para aprendizado
        query_processor.nlp_engine.learn_from_feedback(
            data['query_id'],
            data.get('feedback', {})
        )
        
        return jsonify({
            'success': True,
            'message': 'Feedback registrado'
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/test/query', methods=['POST'])
def test_query():
    """Endpoint de teste sem autenticação"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query não fornecida'}), 400
            
        # Contexto de teste
        user_context = {
            'user_id': 'test_user',
            'user_name': 'Test User',
            'timestamp': datetime.now().isoformat(),
            'output_format': data.get('output_format', 'json'),
            'enhance_with_claude': data.get('enhance_with_claude', False)
        }
        
        # Processa query
        result = query_processor.process(data['query'], user_context)
        
        # Prepara resposta
        response = {
            'success': result.success,
            'intent': {
                'primary': result.intent.primary,
                'confidence': result.intent.confidence,
                'entities': result.intent.entities
            },
            'metadata': result.metadata
        }
        
        if result.natural_response:
            response['response'] = result.natural_response
            
        if result.sql_query:
            response['sql'] = result.sql_query
            
        if result.suggestions:
            response['suggestions'] = result.suggestions[:5]
            
        if result.error:
            response['error'] = result.error
            
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erro no endpoint de teste: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/', methods=['GET'])
@login_required
def index():
    """Página principal do MCP Logística"""
    from flask import render_template
    return render_template('mcp_logistica/index.html')

@mcp_logistica_bp.route('/health', methods=['GET'])
def health_check():
    """Verifica saúde do sistema MCP"""
    try:
        # Verifica componentes
        health = {
            'status': 'healthy',
            'components': {
                'query_processor': query_processor is not None,
                'preference_manager': preference_manager is not None,
                'confirmation_system': confirmation_system is not None,
                'error_handler': error_handler is not None
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Verifica banco de dados
        try:
            db.session.execute('SELECT 1')
            health['database'] = 'connected'
        except:
            health['database'] = 'disconnected'
            health['status'] = 'degraded'
            
        return jsonify(health)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/stats', methods=['GET'])
@login_required
@require_mcp_permission
def get_statistics():
    """Obtém estatísticas do sistema"""
    try:
        # Estatísticas de erro
        error_stats = error_handler.get_error_statistics(hours=24)
        
        # Estatísticas de confirmações
        pending_confirmations = len(confirmation_system.get_pending_confirmations())
        
        return jsonify({
            'success': True,
            'statistics': {
                'errors': error_stats,
                'pending_confirmations': pending_confirmations,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/session/summary', methods=['GET'])
@login_required
def get_session_summary():
    """Obtém resumo da sessão atual"""
    try:
        session_id = request.headers.get('X-Session-Id', g.get('session_id', 'default'))
        
        summary = query_processor.claude_integration.get_session_summary(
            str(current_user.id),
            session_id
        )
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo da sessão: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/session/clear', methods=['POST'])
@login_required
def clear_session():
    """Limpa contexto da sessão atual"""
    try:
        session_id = request.headers.get('X-Session-Id', g.get('session_id', 'default'))
        
        query_processor.claude_integration.clear_session_context(
            str(current_user.id),
            session_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Contexto da sessão limpo'
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_logistica_bp.route('/claude/config', methods=['GET'])
@login_required
@require_mcp_permission
def get_claude_config():
    """Obtém configuração do Claude"""
    try:
        config = {
            'enabled': query_processor.claude_integration.client is not None,
            'model': 'claude-3-5-sonnet-20241022',
            'max_context_queries': query_processor.claude_integration.max_context_queries,
            'features': {
                'fallback': True,
                'insights': True,
                'session_context': True,
                'natural_language': True
            }
        }
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter configuração do Claude: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Registra blueprint na aplicação Flask
def register_blueprint(app):
    """Registra o blueprint MCP na aplicação"""
    app.register_blueprint(mcp_logistica_bp)
    init_mcp_logistica(app)
    logger.info("Blueprint MCP Logística registrado")