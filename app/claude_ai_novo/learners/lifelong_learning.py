"""
🧠 LIFELONG LEARNING SYSTEM - Sistema de Aprendizado Vitalício

Este é o wrapper que integra todos os módulos modularizados de aprendizado:
- learning_core.py (núcleo principal)
- pattern_learner.py (aprendizado de padrões)
- human_in_loop_learning.py (aprendizado humano)
- feedback_processor.py (processamento de feedback)
- knowledge_manager.py (gestão de conhecimento)
"""

import logging
from typing import Dict, List, Any, Optional

# Imports dos módulos modularizados
from .learning_core import LearningCore
from .pattern_learning import PatternLearner
from .human_in_loop_learning import HumanInLoopLearning
from .feedback_learning import FeedbackProcessor
from ..memorizers.knowledge_memory import KnowledgeMemory

logger = logging.getLogger(__name__)


class LifelongLearningSystem:
    """
    Sistema de Aprendizado Vitalício - Wrapper dos módulos modularizados
    
    Integra:
    - LearningCore: Núcleo principal de aprendizado
    - PatternLearner: Aprendizado de padrões
    - HumanInLoopLearning: Aprendizado com humanos
    - FeedbackProcessor: Processamento de feedback
    - KnowledgeManager: Gestão de conhecimento
    """
    
    def __init__(self):
        """Inicializa todos os módulos especializados"""
        self.learning_core = LearningCore()
        self.pattern_learner = PatternLearner()
        self.human_learning = HumanInLoopLearning()
        self.feedback_processor = FeedbackProcessor()
        self.knowledge_memory = KnowledgeMemory()
        
        logger.info("🧠 Sistema de Aprendizado Vitalício (modularizado) inicializado")
    
    def aprender_com_interacao(self, consulta: str, interpretacao: Dict[str, Any], 
                               resposta: str, feedback: Optional[Dict[str, Any]] = None,
                               usuario_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Aprende com cada interação do usuário usando módulos especializados
        
        Args:
            consulta: Consulta original do usuário
            interpretacao: Como o sistema interpretou
            resposta: Resposta dada
            feedback: Feedback do usuário (se houver)
            usuario_id: ID do usuário
            
        Returns:
            Dict com aprendizados extraídos
        """
        try:
            # Usar learning_core como coordenador principal
            return self.learning_core.aprender_com_interacao(
                consulta, interpretacao, resposta, feedback, usuario_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no aprendizado: {e}")
            return {"erro": str(e)}
    
    def aplicar_conhecimento(self, consulta: str) -> Dict[str, Any]:
        """
        Aplica conhecimento aprendido para melhorar interpretação
        
        Returns:
            Dict com padrões e conhecimentos aplicáveis
        """
        try:
            # Usar learning_core como coordenador principal
            return self.learning_core.aplicar_conhecimento(consulta)
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar conhecimento: {e}")
            return {}
    
    def apply_learning(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método de compatibilidade com intelligence_manager
        
        Args:
            query: Consulta do usuário
            context: Contexto da consulta
            
        Returns:
            Dict com aprendizados aplicados
        """
        try:
            # Usar learning_core como coordenador principal
            return self.learning_core.apply_learning(query, context)
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar aprendizado: {e}")
            return {}
    
    def obter_estatisticas_aprendizado(self) -> Dict[str, Any]:
        """
        Obtém estatísticas de aprendizado de todos os módulos
        
        Returns:
            Dict com estatísticas completas
        """
        try:
            # Usar learning_core como coordenador principal
            return self.learning_core.obter_estatisticas_aprendizado()
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}


# Instância global para compatibilidade
_lifelong_learning = None


def get_lifelong_learning() -> LifelongLearningSystem:
    """
    Função de conveniência para obter instância global
    
    Returns:
        LifelongLearningSystem: Instância do sistema
    """
    global _lifelong_learning
    if _lifelong_learning is None:
        _lifelong_learning = LifelongLearningSystem()
    return _lifelong_learning


# Exportações principais
__all__ = [
    'LifelongLearningSystem',
    'get_lifelong_learning'
]

# Alias para compatibilidade
LifelongLearning = LifelongLearningSystem 