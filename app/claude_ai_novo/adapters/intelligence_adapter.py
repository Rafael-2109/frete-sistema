"""
🧠 INTELLIGENCE ADAPTER
Adaptador para conectar com módulos de inteligência
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def get_conversation_context():
    """
    Adaptador para conversation_context que pode estar em diferentes locais
    """
    try:
        # Primeiro tentar na pasta intelligence (sistema novo)
        from ...intelligence.conversation_context import get_conversation_context as _get_context
        return _get_context()
    except ImportError:
        try:
            # Fallback para sistema antigo
            from ....claude_ai.conversation_context import get_conversation_context as _get_context_old
            return _get_context_old()
        except ImportError:
            logger.warning("⚠️ ConversationContext não disponível - criando mock")
            return MockConversationContext()

def get_db_session():
    """
    Adaptador para _get_db_session que pode estar em diferentes locais
    """
    try:
        # Primeiro tentar na pasta intelligence (sistema novo)
        from ...intelligence.lifelong_learning import _get_db_session
        return _get_db_session()
    except ImportError:
        try:
            # Fallback para sistema antigo
            from ....claude_ai.lifelong_learning import _get_db_session as _get_db_old
            return _get_db_old()
        except ImportError:
            logger.warning("⚠️ DB Session não disponível")
            return None

class MockConversationContext:
    """Mock para ConversationContext quando não disponível"""
    
    def __init__(self):
        self.context = {}
        
    def get_context(self, user_id: str) -> Dict[str, Any]:
        return self.context.get(user_id, {})
        
    def add_message(self, user_id: str, message: str, response: str):
        if user_id not in self.context:
            self.context[user_id] = []
        self.context[user_id].append({
            'message': message,
            'response': response
        })
        
    def clear_context(self, user_id: str):
        if user_id in self.context:
            del self.context[user_id] 