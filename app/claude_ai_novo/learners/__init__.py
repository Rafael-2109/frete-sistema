"""
Módulo de aprendizado - Responsabilidade: APRENDER
Contém todos os componentes para aprendizado de padrões e comportamentos.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .human_in_loop_learning import HumanInLoopLearning
    from .lifelong_learning import LifelongLearningSystem
    from .adaptive_learning import AdaptiveLearning
    from .feedback_learning import FeedbackProcessor
    from .pattern_learning import PatternLearner
    from .learning_core import LearningCore

# Configuração de logging
logger = logging.getLogger(__name__)

# Import seguro dos componentes
_components = {}

try:
    from .learning_core import LearningCore
    _components['LearningCore'] = LearningCore
except ImportError as e:
    logger.warning(f"LearningCore não disponível: {e}")

try:
    from .human_in_loop_learning import HumanInLoopLearning
    _components['HumanInLoopLearning'] = HumanInLoopLearning
except ImportError as e:
    logger.warning(f"HumanInLoopLearning não disponível: {e}")

try:
    from .lifelong_learning import LifelongLearningSystem
    _components['LifelongLearningSystem'] = LifelongLearningSystem
except ImportError as e:
    logger.warning(f"LifelongLearning não disponível: {e}")

try:
    from .adaptive_learning import AdaptiveLearning
    _components['AdaptiveLearning'] = AdaptiveLearning
except ImportError as e:
    logger.warning(f"AdaptiveLearning não disponível: {e}")

try:
    from .feedback_learning import FeedbackProcessor
    _components['FeedbackProcessor'] = FeedbackProcessor
except ImportError as e:
    logger.warning(f"FeedbackProcessor não disponível: {e}")

try:
    from .pattern_learning import PatternLearner
    _components['PatternLearner'] = PatternLearner
except ImportError as e:
    logger.warning(f"PatternLearner não disponível: {e}")

# Funções de conveniência OBRIGATÓRIAS
def get_learning_core() -> Optional[Any]:
    """Retorna instância configurada do LearningCore (MANAGER PRINCIPAL)."""
    try:
        cls = _components.get('LearningCore')
        if cls:
            logger.info("Criando instância LearningCore (Manager Principal)")
            return cls()
        else:
            logger.warning("LearningCore não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar LearningCore: {e}")
        return None

def get_human_in_loop_learning() -> Optional[Any]:
    """Retorna instância configurada do HumanInLoopLearning."""
    try:
        cls = _components.get('HumanInLoopLearning')
        if cls:
            logger.info("Criando instância HumanInLoopLearning")
            return cls()
        else:
            logger.warning("HumanInLoopLearning não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar HumanInLoopLearning: {e}")
        return None

def get_lifelong_learning() -> Optional[Any]:
    """Retorna instância configurada do LifelongLearningSystem."""
    try:
        cls = _components.get('LifelongLearningSystem')
        if cls:
            logger.info("Criando instância LifelongLearningSystem")
            return cls()
        else:
            logger.warning("LifelongLearningSystem não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar LifelongLearningSystem: {e}")
        return None

def get_adaptive_learning() -> Optional[Any]:
    """Retorna instância configurada do AdaptiveLearning."""
    try:
        cls = _components.get('AdaptiveLearning')
        if cls:
            logger.info("Criando instância AdaptiveLearning")
            return cls()
        else:
            logger.warning("AdaptiveLearning não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar AdaptiveLearning: {e}")
        return None

def get_feedback_processor() -> Optional[Any]:
    """Retorna instância configurada do FeedbackProcessor."""
    try:
        cls = _components.get('FeedbackProcessor')
        if cls:
            logger.info("Criando instância FeedbackProcessor")
            return cls()
        else:
            logger.warning("FeedbackProcessor não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar FeedbackProcessor: {e}")
        return None

def get_pattern_learner() -> Optional[Any]:
    """Retorna instância configurada do PatternLearner."""
    try:
        cls = _components.get('PatternLearner')
        if cls:
            logger.info("Criando instância PatternLearner")
            return cls()
        else:
            logger.warning("PatternLearner não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar PatternLearner: {e}")
        return None

# Export explícito
__all__ = [
    'get_learning_core',
    'get_human_in_loop_learning',
    'get_lifelong_learning',
    'get_adaptive_learning',
    'get_feedback_processor',
    'get_pattern_learner'
]
