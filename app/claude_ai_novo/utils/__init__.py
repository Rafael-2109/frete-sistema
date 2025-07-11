"""
🛠️ UTILS - Módulo de Utilitários
==============================

Módulo responsável por utilitários, classes base e funcionalidades auxiliares.
"""

import logging

logger = logging.getLogger(__name__)

# Flask fallback para execução standalone
try:
    from .flask_fallback import (
        FlaskFallback,
        get_flask_fallback,
        is_flask_available,
        get_app,
        get_model,
        get_db,
        get_current_user,
        get_config
    )
    _flask_fallback_available = True
except ImportError as e:
    logger.warning(f"⚠️ Flask fallback não disponível: {e}")
    _flask_fallback_available = False

# Managers principais
try:
    from .utils_manager import UtilsManager, get_utilsmanager
    _utils_manager_available = True
except ImportError as e:
    logger.warning(f"⚠️ UtilsManager não disponível: {e}")
    _utils_manager_available = False

try:
    from .data_manager import DataManager, get_datamanager
    _data_manager_available = True
except ImportError as e:
    logger.warning(f"⚠️ DataManager não disponível: {e}")
    _data_manager_available = False

try:
    from .base_context_manager import BaseContextManager
    _base_context_manager_available = True
except ImportError as e:
    logger.warning(f"⚠️ BaseContextManager não disponível: {e}")
    _base_context_manager_available = False

# Classes base
try:
    from .base_classes import BaseOrchestrator, BaseProcessor
    _base_classes_available = True
except ImportError as e:
    logger.warning(f"⚠️ Base classes não disponíveis: {e}")
    _base_classes_available = False

# Tipos e agentes
try:
    from .agent_types import AgentType, AgentResponse, ValidationResult, OperationRecord
    _agent_types_available = True
except ImportError as e:
    logger.warning(f"⚠️ Agent types não disponíveis: {e}")
    _agent_types_available = False

# Componentes auxiliares
try:
    from .response_utils import ResponseUtils
    _response_utils_available = True
except ImportError as e:
    logger.warning(f"⚠️ ResponseUtils não disponível: {e}")
    _response_utils_available = False

try:
    from .validation_utils import BaseValidationUtils, get_validation_utils
    _validation_utils_available = True
except ImportError as e:
    logger.warning(f"⚠️ ValidationUtils não disponível: {e}")
    _validation_utils_available = False

try:
    from .performance_cache import PerformanceCache
    _performance_cache_available = True
except ImportError as e:
    logger.warning(f"⚠️ PerformanceCache não disponível: {e}")
    _performance_cache_available = False

try:
    from .processor_registry import ProcessorRegistry
    _processor_registry_available = True
except ImportError as e:
    logger.warning(f"⚠️ ProcessorRegistry não disponível: {e}")
    _processor_registry_available = False

try:
    from .flask_context_wrapper import FlaskContextWrapper
    _flask_context_wrapper_available = True
except ImportError as e:
    logger.warning(f"⚠️ FlaskContextWrapper não disponível: {e}")
    _flask_context_wrapper_available = False

try:
    from .legacy_compatibility import LegacyCompatibility
    _legacy_compatibility_available = True
except ImportError as e:
    logger.warning(f"⚠️ LegacyCompatibility não disponível: {e}")
    _legacy_compatibility_available = False

logger.info("✅ Utils carregado com sucesso")

# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA PARA FLASK FALLBACK
# ============================================================================

def get_utils_manager():
    """Retorna instância do UtilsManager."""
    if _utils_manager_available:
        return get_utilsmanager()
    return None

def get_data_manager():
    """Retorna instância do DataManager."""
    if _data_manager_available:
        return get_datamanager()
    return None

def initialize_flask_fallback():
    """Inicializa o sistema de fallback do Flask."""
    if _flask_fallback_available:
        fallback = get_flask_fallback()
        logger.info(f"🔄 Flask fallback inicializado - disponível: {fallback.is_flask_available()}")
        return fallback
    return None

def get_base_processor_class():
    """Retorna classe BaseProcessor se disponível."""
    if _base_classes_available:
        return BaseProcessor
    return None

def get_base_orchestrator_class():
    """Retorna classe BaseOrchestrator se disponível."""
    if _base_classes_available:
        return BaseOrchestrator
    return None

def validate_flask_dependencies():
    """
    Valida se dependências do Flask estão disponíveis.
    
    Returns:
        dict: Status das dependências
    """
    status = {
        'flask_fallback': _flask_fallback_available,
        'utils_manager': _utils_manager_available,
        'data_manager': _data_manager_available,
        'base_classes': _base_classes_available,
        'agent_types': _agent_types_available,
        'response_utils': _response_utils_available,
        'performance_cache': _performance_cache_available,
        'processor_registry': _processor_registry_available,
        'flask_context_wrapper': _flask_context_wrapper_available,
        'legacy_compatibility': _legacy_compatibility_available
    }
    
    available_count = sum(1 for available in status.values() if available)
    total_count = len(status)
    
    logger.info(f"📊 Utils status: {available_count}/{total_count} componentes disponíveis")
    
    return {
        'status': status,
        'available_count': available_count,
        'total_count': total_count,
        'percentage': (available_count / total_count) * 100
    }

# ============================================================================
# INSTÂNCIAS GLOBAIS PARA CONVENIÊNCIA
# ============================================================================

# Instâncias globais lazy-loaded
_global_utils_manager = None
_global_data_manager = None
_global_flask_fallback = None

def get_global_utils_manager():
    """Retorna instância global do UtilsManager."""
    global _global_utils_manager
    if _global_utils_manager is None and _utils_manager_available:
        _global_utils_manager = get_utilsmanager()
    return _global_utils_manager

def get_global_data_manager():
    """Retorna instância global do DataManager."""
    global _global_data_manager
    if _global_data_manager is None and _data_manager_available:
        _global_data_manager = get_datamanager()
    return _global_data_manager

def get_global_flask_fallback():
    """Retorna instância global do FlaskFallback."""
    global _global_flask_fallback
    if _global_flask_fallback is None and _flask_fallback_available:
        _global_flask_fallback = get_flask_fallback()
    return _global_flask_fallback

# ============================================================================
# EXPORTS PRINCIPAIS
# ============================================================================

__all__ = [
    # Managers
    'UtilsManager', 'get_utilsmanager', 'get_utils_manager', 'get_global_utils_manager',
    'DataManager', 'get_datamanager', 'get_data_manager', 'get_global_data_manager',
    'BaseContextManager',
    
    # Classes base
    'BaseOrchestrator', 'BaseProcessor',
    'get_base_processor_class', 'get_base_orchestrator_class',
    
    # Tipos e agentes
    'AgentType', 'AgentResponse', 'ValidationResult', 'OperationRecord',
    
    # Flask fallback
    'FlaskFallback', 'get_flask_fallback', 'get_global_flask_fallback',
    'is_flask_available', 'get_app', 'get_model', 'get_db', 
    'get_current_user', 'get_config', 'initialize_flask_fallback',
    
    # Componentes auxiliares
    'ResponseUtils', 'PerformanceCache', 'ProcessorRegistry',
    'FlaskContextWrapper', 'LegacyCompatibility',
    
    # Utilitários
    'validate_flask_dependencies'
]

# Execução standalone para testes
if __name__ == "__main__":
    print("🛠️ UTILS - Módulo de Utilitários")
    print("=" * 50)
    
    status = validate_flask_dependencies()
    print(f"Status: {status['available_count']}/{status['total_count']} ({status['percentage']:.1f}%)")
    
    # Testar managers se disponíveis
    utils_manager = get_global_utils_manager()
    if utils_manager:
        print(f"✅ UtilsManager: {utils_manager}")
    
    data_manager = get_global_data_manager()
    if data_manager:
        print(f"✅ DataManager: {data_manager}")
    
    flask_fallback = get_global_flask_fallback()
    if flask_fallback:
        print(f"✅ FlaskFallback: disponível={flask_fallback.is_flask_available()}")