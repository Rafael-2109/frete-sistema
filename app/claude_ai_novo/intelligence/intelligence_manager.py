"""
🧠 INTELLIGENCE MANAGER - Orquestrador Principal dos Sistemas de Inteligência

Este módulo gerencia todos os sistemas de inteligência artificial:
- Contexto conversacional
- Aprendizado vitalício  
- Aprendizado humano-no-loop
- Gestão de memória
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

# Imports das subpastas especializadas
from .conversation.conversation_context import ConversationContext
from .learning.lifelong_learning import LifelongLearningSystem
from .learning.human_in_loop_learning import HumanInLoopLearning
from .memory.context_manager import ContextManager

logger = logging.getLogger(__name__)

@dataclass
class IntelligenceResult:
    """Resultado processado pelos sistemas de inteligência"""
    success: bool
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    learning_feedback: Optional[Dict[str, Any]] = None
    memory_state: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)

class IntelligenceManager:
    """
    🧠 GERENCIADOR PRINCIPAL DOS SISTEMAS DE INTELIGÊNCIA
    
    Orquestra todos os sistemas de inteligência artificial:
    - Contexto conversacional
    - Aprendizado vitalício
    - Aprendizado humano-no-loop
    - Gestão de memória
    """
    
    def __init__(self):
        """Inicializa todos os sistemas de inteligência"""
        self.conversation = None
        self.lifelong_learning = None
        self.human_learning = None
        self.context_manager = None
        
        self._initialize_systems()
        
    def _initialize_systems(self):
        """Inicializa todos os sistemas de inteligência com tratamento de erros"""
        try:
            # 💬 Sistema de Contexto Conversacional
            self.conversation = ConversationContext()
            logger.info("💬 Sistema de Contexto Conversacional inicializado")
            
            # 🎓 Sistema de Aprendizado Vitalício
            self.lifelong_learning = LifelongLearningSystem()
            logger.info("🎓 Sistema de Aprendizado Vitalício inicializado")
            
            # 🧑‍🤝‍🧑 Sistema de Aprendizado Humano-no-Loop
            self.human_learning = HumanInLoopLearning()
            logger.info("🧑‍🤝‍🧑 Sistema de Aprendizado Humano-no-loop inicializado")
            
            # 💾 Gerenciador de Contexto/Memória
            self.context_manager = ContextManager()
            logger.info("💾 Gerenciador de Contexto/Memória inicializado")
            
            logger.info("🧠 Intelligence Manager inicializado com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Intelligence Manager: {str(e)}")
            raise
    
    def process_intelligence(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> IntelligenceResult:
        """
        Processa uma consulta através de todos os sistemas de inteligência
        
        Args:
            query: Consulta do usuário
            user_context: Contexto do usuário
            
        Returns:
            IntelligenceResult: Resultado processado
        """
        try:
            result = IntelligenceResult(success=False, data={})
            
            # 1. 💬 Processar contexto conversacional
            if self.conversation and user_context and user_context.get('user_id'):
                # Corrigir: garantir que user_id seja string não-nula
                user_id = str(user_context.get('user_id', ''))
                if user_id:
                    context_messages = self.conversation.get_context(user_id)
                    result.context = {'messages': context_messages}
                    logger.debug("💬 Contexto conversacional processado")
            
            # 2. 🎓 Aplicar aprendizado vitalício
            if self.lifelong_learning:
                learning_result = self.lifelong_learning.apply_learning(query, user_context or {})
                result.learning_feedback = learning_result
                logger.debug("🎓 Aprendizado vitalício aplicado")
            
            # 3. 💾 Gerenciar memória/contexto
            if self.context_manager:
                memory_result = self.context_manager.manage_context(query, user_context or {})
                result.memory_state = memory_result
                logger.debug("💾 Memória/contexto gerenciado")
            
            # 4. 🧑‍🤝‍🧑 Capturar feedback humano (se disponível)
            if self.human_learning and user_context and user_context.get('feedback'):
                # capture_feedback retorna string (feedback_id), não dict
                feedback_str = str(user_context.get('feedback', ''))
                feedback_id = self.human_learning.capture_feedback(
                    query, 
                    user_context.get('response', ''), 
                    feedback_str,
                    user_context.get('feedback_type', 'neutral'),
                    user_context.get('severity', 'medium'),
                    user_context
                )
                # Armazenar feedback_id no resultado
                if result.learning_feedback:
                    result.learning_feedback['feedback_id'] = feedback_id
                else:
                    result.learning_feedback = {'feedback_id': feedback_id}
                logger.debug("🧑‍🤝‍🧑 Feedback humano capturado")
            
            result.success = True
            logger.info("🧠 Intelligence processada com sucesso")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar intelligence: {str(e)}")
            result = IntelligenceResult(success=False, data={})
            result.errors.append(str(e))
            return result
    
    def get_conversation_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtém contexto conversacional para um usuário"""
        if self.conversation:
            # get_context retorna List[Dict], mas vamos encapsular em um Dict
            messages = self.conversation.get_context(user_id)
            return {'messages': messages, 'count': len(messages)}
        return None
    
    def update_conversation_context(self, user_id: str, message: str, response: str) -> bool:
        """Atualiza contexto conversacional"""
        if self.conversation:
            return self.conversation.add_message(user_id, message, response)
        return False
    
    def capture_human_feedback(self, query: str, response: str, feedback: str, 
                             feedback_type: str = 'neutral', severity: str = 'medium',
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Captura feedback humano para aprendizado
        
        Args:
            query: Consulta original
            response: Resposta dada
            feedback: Feedback do usuário (string)
            feedback_type: Tipo do feedback
            severity: Severidade do feedback
            context: Contexto adicional
            
        Returns:
            Dict com informações do feedback processado
        """
        if self.human_learning:
            # capture_feedback retorna string (feedback_id)
            feedback_id = self.human_learning.capture_feedback(
                query, response, feedback, feedback_type, severity, context or {}
            )
            # Retornar dict com informações do feedback
            return {
                'feedback_id': feedback_id,
                'status': 'captured',
                'feedback_type': feedback_type,
                'severity': severity
            }
        return {'status': 'failed', 'error': 'Human learning system not available'}
    
    def apply_lifelong_learning(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aplica aprendizado vitalício"""
        if self.lifelong_learning:
            return self.lifelong_learning.apply_learning(query, context or {})
        return {}
    
    def get_intelligence_status(self) -> Dict[str, Any]:
        """Retorna status de todos os sistemas de inteligência"""
        return {
            'conversation': self.conversation is not None,
            'lifelong_learning': self.lifelong_learning is not None,
            'human_learning': self.human_learning is not None,
            'context_manager': self.context_manager is not None,
            'total_systems': sum([
                self.conversation is not None,
                self.lifelong_learning is not None,
                self.human_learning is not None,
                self.context_manager is not None
            ]),
            'initialized': True
        }
    
    def __str__(self) -> str:
        status = self.get_intelligence_status()
        return f"IntelligenceManager(systems={status['total_systems']}/4, initialized={status['initialized']})"
    
    def __repr__(self) -> str:
        return self.__str__()

# Instância global para fácil acesso
intelligence_manager = IntelligenceManager()

# Função de conveniência para acesso rápido
def get_intelligence_manager() -> IntelligenceManager:
    """Retorna a instância global do Intelligence Manager"""
    return intelligence_manager

# Exportações principais
__all__ = [
    'IntelligenceManager',
    'IntelligenceResult',
    'intelligence_manager',
    'get_intelligence_manager'
] 