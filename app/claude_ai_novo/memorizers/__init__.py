"""
Módulo de memorização - Responsabilidade: MEMORIZAR
Contém todos os componentes para memorização de contexto e conhecimento.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .context_memory import ContextMemory
    from .system_memory import SystemMemory
    from .knowledge_memory import KnowledgeMemory
    from .memory_manager import MemoryManager
    from .session_memory import SessionMemory
    from .conversation_memory import ConversationMemory

# Configuração de logging
logger = logging.getLogger(__name__)

# Import seguro dos componentes
_components = {}

try:
    from .context_memory import ContextMemory
    _components['ContextMemory'] = ContextMemory
except ImportError as e:
    logger.warning(f"ContextMemory não disponível: {e}")

try:
    from .system_memory import SystemMemory
    _components['SystemMemory'] = SystemMemory
except ImportError as e:
    logger.warning(f"SystemMemory não disponível: {e}")

try:
    from .knowledge_memory import KnowledgeMemory
    _components['KnowledgeMemory'] = KnowledgeMemory
except ImportError as e:
    logger.warning(f"KnowledgeMemory não disponível: {e}")

try:
    from .memory_manager import MemoryManager
    _components['MemoryManager'] = MemoryManager
except ImportError as e:
    logger.warning(f"MemoryManager não disponível: {e}")

try:
    from .conversation_memory import ConversationMemory
    _components['ConversationMemory'] = ConversationMemory
except ImportError as e:
    logger.warning(f"ConversationMemory não disponível: {e}")

try:
    from .session_memory import SessionMemory
    _components['SessionMemory'] = SessionMemory
except ImportError as e:
    logger.warning(f"SessionMemory não disponível: {e}")

# Funções de conveniência OBRIGATÓRIAS
def get_context_memory() -> Optional[Any]:
    """Retorna instância configurada do ContextMemory."""
    try:
        cls = _components.get('ContextMemory')
        if cls:
            logger.info("Criando instância ContextMemory")
            return cls()
        else:
            logger.warning("ContextMemory não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ContextMemory: {e}")
        return None

def get_system_memory() -> Optional[Any]:
    """Retorna instância configurada do SystemMemory."""
    try:
        cls = _components.get('SystemMemory')
        if cls:
            logger.info("Criando instância SystemMemory")
            return cls()
        else:
            logger.warning("SystemMemory não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar SystemMemory: {e}")
        return None

def get_knowledge_memory() -> Optional[Any]:
    """Retorna instância configurada do KnowledgeMemory."""
    try:
        cls = _components.get('KnowledgeMemory')
        if cls:
            logger.info("Criando instância KnowledgeMemory")
            return cls()
        else:
            logger.warning("KnowledgeMemory não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar KnowledgeMemory: {e}")
        return None

def get_memory_manager() -> Optional[Any]:
    """Retorna instância configurada do MemoryManager."""
    try:
        cls = _components.get('MemoryManager')
        if cls:
            logger.info("Criando instância MemoryManager")
            return cls()
        else:
            logger.warning("MemoryManager não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar MemoryManager: {e}")
        return None

def get_conversation_memory() -> Optional[Any]:
    """Retorna instância configurada do ConversationMemory."""
    try:
        cls = _components.get('ConversationMemory')
        if cls:
            logger.info("Criando instância ConversationMemory")
            return cls()
        else:
            logger.warning("ConversationMemory não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ConversationMemory: {e}")
        return None

def get_session_memory() -> Optional[Any]:
    """Retorna instância configurada do SessionMemory."""
    try:
        cls = _components.get('SessionMemory')
        if cls:
            logger.info("Criando instância SessionMemory")
            return cls()
        else:
            logger.warning("SessionMemory não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar SessionMemory: {e}")
        return None

# Flask fallback para execução standalone
def memorize_context(session_id: str, context: dict) -> bool:
    """Função de conveniência para memorizar contexto."""
    try:
        manager = get_memory_manager()
        if manager:
            return manager.store_conversation_context(session_id, context)
        return False
    except Exception as e:
        logger.error(f"Erro ao memorizar contexto: {e}")
        return False

def recall_context(session_id: str) -> Optional[dict]:
    """Função de conveniência para recuperar contexto."""
    try:
        manager = get_memory_manager()
        if manager:
            return manager.retrieve_conversation_context(session_id)
        return None
    except Exception as e:
        logger.error(f"Erro ao recuperar contexto: {e}")
        return None

def get_memory_status() -> dict:
    """Função de conveniência para status da memória."""
    try:
        manager = get_memory_manager()
        if manager:
            return manager.get_memory_health()
        return {'error': 'MemoryManager não disponível'}
    except Exception as e:
        logger.error(f"Erro ao obter status da memória: {e}")
        return {'error': str(e)}

# Export explícito
__all__ = [
    'get_context_memory',
    'get_system_memory',
    'get_knowledge_memory',
    'get_memory_manager',
    'get_conversation_memory',
    'get_session_memory',
    'memorize_context',
    'recall_context',
    'get_memory_status'
]

# Execução standalone
if __name__ == "__main__":
    print("🧠 MEMORIZERS - Testando componentes")
    
    # Teste do MemoryManager
    manager = get_memory_manager()
    if manager:
        print("✅ MemoryManager OK")
        health = manager.get_memory_health()
        print(f"📊 Status: {health.get('overall_status', 'unknown')}")
    else:
        print("❌ MemoryManager não disponível")
    
    # Teste dos componentes individuais
    components = ['ContextMemory', 'SystemMemory', 'KnowledgeMemory', 'ConversationMemory', 'SessionMemory']
    for component in components:
        if component in _components:
            print(f"✅ {component} OK")
        else:
            print(f"❌ {component} não disponível")
    
    # Teste específico SessionMemory
    session_mem = get_session_memory()
    if session_mem:
        print("✅ SessionMemory function OK")
    else:
        print("❌ SessionMemory function não disponível")
    
    print(" Teste concluído")
