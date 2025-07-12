"""
Módulo de orquestração - Responsabilidade: ORQUESTRAR
Contém apenas os orquestradores essenciais para processos complexos.
"""

import logging
from typing import Optional, Any, Dict

# Configuração de logging
logger = logging.getLogger(__name__)

# Import seguro dos componentes ESSENCIAIS
_components = {}

# Import dos tipos compartilhados para facilitar acesso
from .types import (
    OrchestrationMode,
    OrchestratorType,
    OrchestrationStep,
    OrchestrationTask,
    SessionStatus,
    SessionPriority
)

# ================================
# ORQUESTRADORES ESSENCIAIS (4)
# ================================

try:
    from .orchestrator_manager import (
        OrchestratorManager, 
        get_orchestrator_manager,
        orchestrate_system_operation,
        get_orchestration_status
    )
    _components['OrchestratorManager'] = OrchestratorManager
    logger.info("🎭 OrchestratorManager (MAESTRO) carregado")
except ImportError as e:
    logger.warning(f"❌ OrchestratorManager não disponível: {e}")

try:
    from .main_orchestrator import MainOrchestrator
    _components['MainOrchestrator'] = MainOrchestrator
    logger.info("🎯 MainOrchestrator carregado")
except ImportError as e:
    logger.warning(f"❌ MainOrchestrator não disponível: {e}")

try:
    from .session_orchestrator import SessionOrchestrator, get_session_orchestrator
    _components['SessionOrchestrator'] = SessionOrchestrator
    logger.info("🔄 SessionOrchestrator carregado")
except ImportError as e:
    logger.warning(f"❌ SessionOrchestrator não disponível: {e}")

try:
    from .workflow_orchestrator import WorkflowOrchestrator  
    _components['WorkflowOrchestrator'] = WorkflowOrchestrator
    logger.info("⚙️ WorkflowOrchestrator carregado")
except ImportError as e:
    logger.warning(f"❌ WorkflowOrchestrator não disponível: {e}")

# ================================
# FUNÇÕES DE CONVENIÊNCIA ESSENCIAIS
# ================================

def get_orchestrator_manager() -> Optional[Any]:
    """Retorna instância configurada do OrchestratorManager (MAESTRO)."""
    try:
        if 'OrchestratorManager' in _components:
            from .orchestrator_manager import get_orchestrator_manager as _get_manager
            return _get_manager()
        else:
            logger.warning("❌ OrchestratorManager não disponível")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao criar OrchestratorManager: {e}")
        return None

def get_main_orchestrator() -> Optional[Any]:
    """Retorna instância configurada do MainOrchestrator."""
    try:
        cls = _components.get('MainOrchestrator')
        if cls:
            logger.info("🎯 Criando instância MainOrchestrator")
            return cls()
        else:
            logger.warning("❌ MainOrchestrator não disponível")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao criar MainOrchestrator: {e}")
        return None

def get_session_orchestrator() -> Optional[Any]:
    """Retorna instância configurada do SessionOrchestrator."""
    try:
        if 'SessionOrchestrator' in _components:
            from .session_orchestrator import get_session_orchestrator as _get_session
            return _get_session()
        else:
            logger.warning("❌ SessionOrchestrator não disponível")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao criar SessionOrchestrator: {e}")
        return None

def get_workflow_orchestrator() -> Optional[Any]:
    """Retorna instância configurada do WorkflowOrchestrator."""
    try:
        cls = _components.get('WorkflowOrchestrator')
        if cls:
            logger.info("⚙️ Criando instância WorkflowOrchestrator")
            return cls()
        else:
            logger.warning("❌ WorkflowOrchestrator não disponível")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao criar WorkflowOrchestrator: {e}")
        return None

# ================================
# FUNÇÕES DE CONVENIÊNCIA DO MAESTRO
# ================================

async def orchestrate_operation(operation_type: str, data: dict, **kwargs) -> Dict[str, Any]:
    """
    Função de conveniência para orquestrar operações via OrchestratorManager.
    
    Args:
        operation_type: Tipo da operação
        data: Dados da operação
        **kwargs: Argumentos adicionais
        
    Returns:
        Resultado da orquestração
    """
    try:
        if 'orchestrate_system_operation' in globals():
            return await orchestrate_system_operation(operation_type, data, **kwargs)
        else:
            manager = get_orchestrator_manager()
            if manager:
                return await manager.orchestrate_operation(operation_type, data, **kwargs)
            else:
                return {
                    'success': False,
                    'error': 'OrchestratorManager não disponível',
                    'fallback_used': True
                }
    except Exception as e:
        logger.error(f"❌ Erro na orquestração: {e}")
        return {
            'success': False,
            'error': str(e),
            'operation_type': operation_type
        }

def get_system_status() -> dict:
    """
    Função de conveniência para obter status do sistema de orquestração.
    
    Returns:
        Status completo dos orquestradores
    """
    try:
        if 'get_orchestration_status' in globals():
            return get_orchestration_status()
        else:
            manager = get_orchestrator_manager()
            if manager:
                return manager.get_orchestrator_status()
            else:
                return {
                    'error': 'OrchestratorManager não disponível',
                    'components_available': len(_components),
                    'components': list(_components.keys())
                }
    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return {
            'error': str(e),
            'components_available': len(_components)
        }

# ================================
# DIAGNÓSTICO LIMPO
# ================================

def diagnose_orchestrator_module() -> dict:
    """
    Diagnóstica o módulo de orquestração limpo.
    
    Returns:
        Relatório de diagnóstico
    """
    from datetime import datetime
    
    diagnosis = {
        'timestamp': datetime.now().isoformat(),
        'total_components': len(_components),
        'components_loaded': list(_components.keys()),
        'problems': [],
        'recommendations': [],
        'architecture_status': 'CLEAN'
    }
    
    # Verificar se maestro está disponível
    if 'OrchestratorManager' not in _components:
        diagnosis['problems'].append("❌ OrchestratorManager (MAESTRO) não disponível")
        diagnosis['recommendations'].append("Corrigir imports do OrchestratorManager")
    
    # Verificar orquestradores essenciais
    essential_orchestrators = ['OrchestratorManager', 'MainOrchestrator', 'SessionOrchestrator', 'WorkflowOrchestrator']
    missing_essential = [comp for comp in essential_orchestrators if comp not in _components]
    
    if missing_essential:
        diagnosis['problems'].append(f"❌ Orquestradores essenciais ausentes: {missing_essential}")
        diagnosis['recommendations'].append("Verificar imports dos orquestradores essenciais")
    else:
        diagnosis['problems'].append("✅ Todos os 4 orquestradores essenciais presentes")
    
    # Verificar limpeza
    if len(_components) == 4:
        diagnosis['problems'].append("✅ Módulo limpo - apenas orquestradores essenciais")
    elif len(_components) < 4:
        diagnosis['problems'].append(f"⚠️ Poucos componentes: {len(_components)}/4")
    else:
        diagnosis['problems'].append(f"⚠️ Muitos componentes: {len(_components)}/4 - verificar limpeza")
    
    return diagnosis

# ================================
# EXPORT EXPLÍCITO LIMPO
# ================================

__all__ = [
    # Função principal (MAESTRO)
    'get_orchestrator_manager',
    'orchestrate_operation',
    'get_system_status',
    
    # Orquestradores essenciais (4)
    'get_main_orchestrator',
    'get_session_orchestrator',
    'get_workflow_orchestrator',
    
    # Diagnóstico
    'diagnose_orchestrator_module'
]

# ================================
# LOG DE INICIALIZAÇÃO LIMPO
# ================================

logger.info(f"🎭 Módulo ORCHESTRATORS LIMPO inicializado")
logger.info(f"📊 Componentes essenciais: {len(_components)}/4")
logger.info(f"🎯 Maestro disponível: {'OrchestratorManager' in _components}")

# Executar diagnóstico automático
try:
    diagnosis = diagnose_orchestrator_module()
    if diagnosis['problems']:
        # Mostrar apenas os primeiros 3 problemas/status
        for problem in diagnosis['problems'][:3]:
            if problem.startswith('✅'):
                logger.info(f"   {problem}")
            elif problem.startswith('⚠️'):
                logger.warning(f"   {problem}")
            else:
                logger.error(f"   {problem}")
except Exception as e:
    logger.error(f"❌ Erro no diagnóstico automático: {e}")

logger.info("✅ Módulo ORCHESTRATORS LIMPO carregado com arquitetura industrial") 