"""
Módulo de conversação - Responsabilidade: GERENCIAR
Contém todos os componentes para gerenciamento de conversas e diálogos.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.claude_ai_novo.conversers.conversation_manager import ConversationManager
    from app.claude_ai_novo.conversers.context_converser import ConversationContext

# Configuração de logging
logger = logging.getLogger(__name__)

# Import seguro dos componentes
_components = {}

try:
    from app.claude_ai_novo.conversers.conversation_manager import ConversationManager
    _components['ConversationManager'] = ConversationManager
except ImportError as e:
    logger.warning(f"ConversationManager não disponível: {e}")

try:
    from app.claude_ai_novo.conversers.context_converser import ConversationContext
    _components['ConversationContext'] = ConversationContext
except ImportError as e:
    logger.warning(f"ConversationContext não disponível: {e}")

# Funções de conveniência OBRIGATÓRIAS
def get_conversation_manager() -> Optional[Any]:
    """Retorna instância configurada do ConversationManager."""
    try:
        cls = _components.get('ConversationManager')
        if cls:
            logger.info("Criando instância ConversationManager")
            return cls()
        else:
            logger.warning("ConversationManager não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ConversationManager: {e}")
        return None

def get_conversation_context() -> Optional[Any]:
    """Retorna instância configurada do ConversationContext."""
    try:
        cls = _components.get('ConversationContext')
        if cls:
            logger.info("Criando instância ConversationContext")
            return cls()
        else:
            logger.warning("ConversationContext não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ConversationContext: {e}")
        return None

# Export explícito
__all__ = [
    'get_conversation_manager',
    'get_conversation_context'
]
