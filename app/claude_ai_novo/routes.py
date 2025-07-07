"""
🛣️ ROTAS CLAUDE AI
Rotas principais simplificadas e organizadas
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from . import get_claude_ai_instance
import logging

logger = logging.getLogger(__name__)

# Blueprint
claude_ai_bp = Blueprint('claude_ai', __name__, url_prefix='/claude-ai')

@claude_ai_bp.route('/chat')
@login_required
def chat_page():
    """Página principal do chat"""
    return render_template('claude_ai/chat.html', user=current_user)

@claude_ai_bp.route('/api/query', methods=['POST'])
@login_required
def api_query():
    """API principal para consultas"""
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vazia'})
        
        # Contexto do usuário
        user_context = {
            'user_id': current_user.id,
            'user_name': current_user.nome,
            'user_profile': getattr(current_user, 'perfil', 'user'),
            'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None)
        }
        
        # Processar consulta
        claude_ai = get_claude_ai_instance()
        response = claude_ai.process_query(query, user_context)
        
        return jsonify({
            'success': True,
            'response': response,
            'context_available': True
        })
        
    except Exception as e:
        logger.error(f"Erro na API de consulta: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@claude_ai_bp.route('/api/feedback', methods=['POST'])
@login_required
def api_feedback():
    """API para feedback do usuário"""
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        response = data.get('response', '')
        feedback_type = data.get('feedback_type', 'positive')
        feedback_text = data.get('feedback_text', '')
        
        feedback = {
            'type': feedback_type,
            'text': feedback_text,
            'user_id': current_user.id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Registrar feedback
        claude_ai = get_claude_ai_instance()
        claude_ai.record_feedback(query, response, feedback)
        
        return jsonify({
            'success': True,
            'message': 'Feedback registrado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao registrar feedback: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@claude_ai_bp.route('/clear-context')
@login_required
def clear_context():
    """Limpa contexto conversacional"""
    
    try:
        claude_ai = get_claude_ai_instance()
        claude_ai.clear_context(str(current_user.id))
        
        return jsonify({
            'success': True,
            'message': 'Contexto limpo com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar contexto: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@claude_ai_bp.route('/health')
@login_required
def health_check():
    """Health check do sistema"""
    
    try:
        claude_ai = get_claude_ai_instance()
        
        if not claude_ai:
            return jsonify({
                'status': 'error',
                'message': 'Claude AI não inicializado'
            }), 500
        
        # Testar conexão
        is_healthy = claude_ai.claude_client.validate_connection()
        
        return jsonify({
            'status': 'healthy' if is_healthy else 'degraded',
            'claude_api': 'ok' if is_healthy else 'error',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
