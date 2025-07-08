"""
🧠 INTELLIGENCE MODULE - Sistemas de Inteligência Artificial

Este módulo contém todos os sistemas de inteligência artificial:
- Intelligence Manager (orquestrador principal)
- Conversation (contexto conversacional)
- Learning (sistemas de aprendizado)
- Memory (gestão de memória)
"""

# Imports do manager principal
from .intelligence_manager import (
    IntelligenceManager,
    IntelligenceResult,
    intelligence_manager,
    get_intelligence_manager
)

# Imports das subpastas especializadas
from .conversation.conversation_context import ConversationContext
from .learning.learning_core import LearningCore, get_learning_core
from .learning.human_in_loop_learning import HumanInLoopLearning
from .learning.pattern_learner import PatternLearner
from .memory.context_manager import ContextManager

# Exportações principais
__all__ = [
    # Manager principal
    'IntelligenceManager',
    'IntelligenceResult',
    'intelligence_manager',
    'get_intelligence_manager',
    
    # Sistemas especializados
    'ConversationContext',
    'LearningCore',
    'get_learning_core',
    'HumanInLoopLearning',
    'PatternLearner',
    'ContextManager',
]
