"""
🔄 QUERY PROCESSOR
Processador principal de consultas do sistema
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Processador central de consultas"""
    
    def __init__(self, claude_client, context_manager, learning_system):
        self.claude_client = claude_client
        self.context_manager = context_manager
        self.learning_system = learning_system
        
    def process_query(self, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma consulta completa"""
        
        # 1. Aplicar contexto conversacional
        enriched_query = self.context_manager.enrich_query(query, user_context)
        
        # 2. Aplicar conhecimento aprendido
        learned_context = self.learning_system.get_relevant_knowledge(query)
        
        # 3. Processar com Claude
        response = self._process_with_claude(enriched_query, learned_context)
        
        # 4. Registrar para aprendizado futuro
        self.learning_system.record_interaction(query, response, user_context)
        
        return {
            'query': query,
            'response': response,
            'context_used': bool(enriched_query != query),
            'learning_applied': bool(learned_context),
            'timestamp': datetime.now().isoformat()
        }
    
    def _process_with_claude(self, query: str, context: Dict) -> str:
        """Processa consulta com Claude"""
        
        # Construir prompt do sistema
        system_prompt = self._build_system_prompt(context)
        
        # Enviar para Claude
        messages = [{"role": "user", "content": query}]
        response = self.claude_client.send_message(messages, system_prompt)
        
        return response
    
    def _build_system_prompt(self, context: Dict) -> str:
        """Constrói prompt do sistema baseado no contexto"""
        
        base_prompt = """Você é um assistente especializado em sistemas de frete e logística.
        Analise os dados fornecidos e responda de forma precisa e detalhada."""
        
        if context:
            base_prompt += f"\n\nContexto adicional: {context}"
            
        return base_prompt

# Instância global
_query_processor = None

def get_query_processor():
    """Retorna instância de QueryProcessor"""
    global _query_processor
    if _query_processor is None:
        # Para compatibilidade, criar com clients mock se necessário
        _query_processor = QueryProcessor(
            claude_client=None,
            context_manager=None,
            learning_system=None
        )
    return _query_processor
