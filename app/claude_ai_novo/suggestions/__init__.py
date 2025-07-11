"""
💡 SUGGESTIONS - Sistema de Sugestões
===================================

Módulos responsáveis por geração e gerenciamento de sugestões inteligentes.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Importações com fallback robusto
try:
    from .suggestion_engine import SuggestionsEngine, get_suggestions_engine
    _suggestions_engine_available = True
except ImportError as e:
    logger.warning(f"⚠️ SuggestionsEngine não disponível: {e}")
    _suggestions_engine_available = False

try:
    from .suggestions_manager import SuggestionsManager, get_suggestions_manager
    _suggestions_manager_available = True
except ImportError as e:
    logger.warning(f"⚠️ SuggestionsManager não disponível: {e}")
    _suggestions_manager_available = False

# Instâncias globais
_suggestions_engine_instance = None
_suggestions_manager_instance = None

def get_suggestions_engine() -> Optional[object]:
    """
    Obtém instância do engine de sugestões.
    
    Returns:
        Instância do SuggestionsEngine ou None se não disponível
    """
    global _suggestions_engine_instance
    
    if not _suggestions_engine_available:
        logger.warning("⚠️ SuggestionsEngine não está disponível")
        return None
    
    if _suggestions_engine_instance is None:
        try:
            from .suggestion_engine import SuggestionsEngine
            _suggestions_engine_instance = SuggestionsEngine()
            logger.info("✅ SuggestionsEngine inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SuggestionsEngine: {e}")
            return None
    
    return _suggestions_engine_instance

def get_suggestions_manager() -> Optional[object]:
    """
    Obtém instância do gerenciador de sugestões.
    
    Returns:
        Instância do SuggestionsManager ou None se não disponível
    """
    global _suggestions_manager_instance
    
    if not _suggestions_manager_available:
        logger.warning("⚠️ SuggestionsManager não está disponível")
        return None
    
    if _suggestions_manager_instance is None:
        try:
            from .suggestions_manager import SuggestionsManager
            _suggestions_manager_instance = SuggestionsManager()
            logger.info("✅ SuggestionsManager inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SuggestionsManager: {e}")
            return None
    
    return _suggestions_manager_instance

def generate_suggestions(context: Dict[str, Any], suggestion_type: str = 'general', **kwargs) -> Dict[str, Any]:
    """
    Gera sugestões usando o gerenciador disponível.
    
    Args:
        context: Contexto para geração de sugestões
        suggestion_type: Tipo de sugestão
        **kwargs: Parâmetros adicionais
        
    Returns:
        Conjunto de sugestões geradas
    """
    try:
        # Tentar usar o gerenciador primeiro (mais avançado)
        manager = get_suggestions_manager()
        if manager and hasattr(manager, 'generate_suggestions'):
            return manager.generate_suggestions(context, suggestion_type, **kwargs)
        
        # Fallback para engine básico
        engine = get_suggestions_engine()
        if engine and hasattr(engine, 'generate_suggestions'):
            return engine.generate_suggestions(context, suggestion_type, **kwargs)
        
        # Fallback final
        return {
            'error': 'Nenhum sistema de sugestões disponível',
            'fallback_suggestions': [
                {
                    'text': 'Explorar funcionalidades do sistema',
                    'type': 'general',
                    'confidence': 0.5
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar sugestões: {e}")
        return {
            'error': str(e),
            'fallback_suggestions': []
        }

def register_suggestion_engine(engine_name: str, engine_callable, priority: int = 5) -> bool:
    """
    Registra um engine de sugestão no gerenciador.
    
    Args:
        engine_name: Nome do engine
        engine_callable: Função callable do engine
        priority: Prioridade do engine
        
    Returns:
        True se registrado com sucesso
    """
    try:
        manager = get_suggestions_manager()
        if manager and hasattr(manager, 'register_suggestion_engine'):
            return manager.register_suggestion_engine(engine_name, engine_callable, priority)
        
        logger.warning("⚠️ SuggestionsManager não disponível para registro")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar engine: {e}")
        return False

def submit_suggestion_feedback(suggestion_id: str, feedback_type: str, user_action: str, context: Optional[Dict] = None) -> bool:
    """
    Submete feedback sobre uma sugestão.
    
    Args:
        suggestion_id: ID da sugestão
        feedback_type: Tipo de feedback
        user_action: Ação do usuário
        context: Contexto adicional
        
    Returns:
        True se feedback processado com sucesso
    """
    try:
        manager = get_suggestions_manager()
        if manager and hasattr(manager, 'submit_feedback'):
            return manager.submit_feedback(suggestion_id, feedback_type, user_action, context)
        
        logger.warning("⚠️ SuggestionsManager não disponível para feedback")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao submeter feedback: {e}")
        return False

def get_suggestion_recommendations(user_profile: Dict[str, Any], session_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtém recomendações personalizadas.
    
    Args:
        user_profile: Perfil do usuário
        session_context: Contexto da sessão
        
    Returns:
        Recomendações personalizadas
    """
    try:
        manager = get_suggestions_manager()
        if manager and hasattr(manager, 'get_suggestion_recommendations'):
            return manager.get_suggestion_recommendations(user_profile, session_context)
        
        # Fallback básico
        return {
            'personalized_suggestions': [
                {
                    'text': f"Consulta recomendada para {user_profile.get('role', 'usuário')}",
                    'type': 'personalized',
                    'confidence': 0.6
                }
            ],
            'trending_suggestions': [
                {
                    'text': 'Verificar status das entregas',
                    'type': 'trending',
                    'confidence': 0.7
                }
            ],
            'contextual_suggestions': [],
            'quick_actions': [
                {
                    'text': 'Acessar dashboard principal',
                    'type': 'navigation',
                    'confidence': 0.8
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter recomendações: {e}")
        return {
            'error': str(e),
            'personalized_suggestions': [],
            'trending_suggestions': [],
            'contextual_suggestions': [],
            'quick_actions': []
        }

def optimize_suggestions_performance() -> Dict[str, Any]:
    """
    Otimiza performance do sistema de sugestões.
    
    Returns:
        Relatório de otimização
    """
    try:
        manager = get_suggestions_manager()
        if manager and hasattr(manager, 'optimize_suggestion_performance'):
            return manager.optimize_suggestion_performance()
        
        return {
            'message': 'SuggestionsManager não disponível para otimização',
            'actions_taken': []
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na otimização: {e}")
        return {
            'error': str(e),
            'actions_taken': []
        }

def get_suggestions_status() -> Dict[str, Any]:
    """
    Obtém status do sistema de sugestões.
    
    Returns:
        Status detalhado
    """
    return {
        'suggestions_engine': {
            'available': _suggestions_engine_available,
            'initialized': _suggestions_engine_instance is not None
        },
        'suggestions_manager': {
            'available': _suggestions_manager_available,
            'initialized': _suggestions_manager_instance is not None
        },
        'total_components': 2,
        'active_components': sum([
            _suggestions_engine_available,
            _suggestions_manager_available
        ]),
        'primary_system': 'manager' if _suggestions_manager_available else 'engine' if _suggestions_engine_available else 'none'
    }

# Exportações
__all__ = [
    'get_suggestions_engine',
    'get_suggestions_manager',
    'generate_suggestions',
    'register_suggestion_engine',
    'submit_suggestion_feedback',
    'get_suggestion_recommendations',
    'optimize_suggestions_performance',
    'get_suggestions_status'
]