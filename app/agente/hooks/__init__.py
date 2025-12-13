"""
Sistema de Hooks para o Agent SDK.

ARQUITETURA ROBUSTA:
- DB (agent_events) como fonte de verdade
- Lock distribuido via pg_advisory_xact_lock
- Separacao clara de responsabilidades
- Working set estruturado
- Write Policy explicito
- Scrubbing de dados sensiveis

Componentes:
- HookManager: Coordenador central
- MemoryRetriever: Recupera memorias (pre-hook)
- PatternDetector: Detecta padroes (post-hook)
- MemoryWritePolicy: Avalia candidatos
- MemoryWriter: Persiste memorias aprovadas
- EventLogger: Instrumentacao first-class
- LearningLoop: Processa feedback

Uso:
    from app.agente.hooks import get_hook_manager

    manager = get_hook_manager()

    # No inicio da sessao
    context = await manager.on_session_start(user_id, session_id)

    # Antes de enviar ao SDK
    result = await manager.on_pre_query(user_id, session_id, prompt)
    context_injection = result['context_injection']

    # Apos resposta
    await manager.on_post_response(user_id, session_id, prompt, response, tools)

    # Feedback do usuario
    await manager.on_feedback_received(user_id, session_id, 'positive', {})
"""

from .manager import (
    HookManager,
    get_hook_manager,
    reset_hook_manager,
    HookContext,
    WorkingSet,
    MemoryCandidate,
    MemoryScope,
    MemorySensitivity,
    EventType,
)
from .memory_retriever import MemoryRetriever
from .pattern_detector import PatternDetector
from .write_policy import MemoryWritePolicy
from .memory_writer import MemoryWriter
from .event_logger import EventLogger
from .learning_loop import LearningLoop

__all__ = [
    # Manager
    'HookManager',
    'get_hook_manager',
    'reset_hook_manager',

    # Data classes
    'HookContext',
    'WorkingSet',
    'MemoryCandidate',

    # Enums
    'MemoryScope',
    'MemorySensitivity',
    'EventType',

    # Componentes
    'MemoryRetriever',
    'PatternDetector',
    'MemoryWritePolicy',
    'MemoryWriter',
    'EventLogger',
    'LearningLoop',
]
