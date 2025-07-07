"""
🤖 CLAUDE AI - MÓDULO PRINCIPAL
Sistema de IA avançado para análise de fretes e logística
"""

from .integration.claude_client import ClaudeClient
from .integration.query_processor import QueryProcessor
from .integration.response_formatter import ResponseFormatter

from .intelligence.context_manager import ContextManager
from .intelligence.learning_system import LearningSystem

# Versão do módulo
__version__ = "2.0.0"

# Configuração padrão
DEFAULT_CONFIG = {
    'model': 'claude-sonnet-4-20250514',
    'max_tokens': 8192,
    'temperature': 0.7,
    'context_max_messages': 20,
    'context_ttl_hours': 1
}

class ClaudeAI:
    """Classe principal do sistema Claude AI"""
    
    def __init__(self, api_key: str, db_session=None, redis_client=None):
        self.claude_client = ClaudeClient(api_key)
        self.context_manager = ContextManager(redis_client)
        self.learning_system = LearningSystem(db_session)
        self.query_processor = QueryProcessor(
            self.claude_client,
            self.context_manager, 
            self.learning_system
        )
        self.response_formatter = ResponseFormatter()
    
    def process_query(self, query: str, user_context: dict) -> str:
        """Interface principal para processar consultas"""
        
        try:
            # Processar consulta
            result = self.query_processor.process_query(query, user_context)
            
            # Formatar resposta
            response = self.response_formatter.format_standard_response(
                result['response'], 
                result
            )
            
            # Adicionar ao contexto conversacional
            user_id = user_context.get('user_id', 'anonymous')
            self.context_manager.add_message(user_id, 'user', query)
            self.context_manager.add_message(user_id, 'assistant', response)
            
            return response
            
        except Exception as e:
            return self.response_formatter.format_error_response(str(e))
    
    def clear_context(self, user_id: str):
        """Limpa contexto conversacional do usuário"""
        self.context_manager.clear_context(user_id)
    
    def record_feedback(self, query: str, response: str, feedback: dict):
        """Registra feedback do usuário"""
        self.learning_system.learn_from_feedback(query, response, feedback)

# Instância global (será inicializada nas rotas)
claude_ai_instance = None

def get_claude_ai_instance():
    """Obtém instância global do Claude AI"""
    return claude_ai_instance

def initialize_claude_ai(api_key: str, db_session=None, redis_client=None):
    """Inicializa instância global"""
    global claude_ai_instance
    claude_ai_instance = ClaudeAI(api_key, db_session, redis_client)
    return claude_ai_instance
