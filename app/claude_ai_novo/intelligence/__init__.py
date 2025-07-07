"""
🧠 MÓDULO DE INTELIGÊNCIA
Sistemas de contexto, aprendizado e feedback
"""

try:
    from .conversation_context import ConversationContext, get_conversation_context
    from .human_in_loop_learning import HumanInLoopLearning, get_human_learning_system, capture_user_feedback
    from .lifelong_learning import LifelongLearning, get_lifelong_learning_system
except ImportError:
    pass

__all__ = [
    'ConversationContext',
    'get_conversation_context'
]
