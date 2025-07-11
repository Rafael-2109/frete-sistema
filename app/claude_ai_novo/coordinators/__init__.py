"""
🔧 COORDINATORS - Módulos de Coordenação
========================================

Módulos responsáveis por coordenar diferentes aspectos do sistema.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def get_coordinator_manager() -> Optional[Any]:
    """
    Obtém o gerenciador central de coordenadores.
    
    Returns:
        Instância do CoordinatorManager ou None
    """
    try:
        from .coordinator_manager import get_coordinator_manager
        return get_coordinator_manager()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar coordinator_manager: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar coordinator_manager: {e}")
        return None

def get_intelligence_coordinator() -> Optional[Any]:
    """
    Obtém coordenador de inteligência.
    
    Returns:
        Instância do IntelligenceCoordinator ou None
    """
    try:
        from .intelligence_coordinator import get_intelligence_coordinator
        return get_intelligence_coordinator()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar intelligence_coordinator: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar intelligence_coordinator: {e}")
        return None

def get_processor_coordinator() -> Optional[Any]:
    """
    Obtém coordenador de processadores.
    
    Returns:
        Instância do ProcessorCoordinator ou None
    """
    try:
        from .processor_coordinator import ProcessorCoordinator
        return ProcessorCoordinator()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar processor_coordinator: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar processor_coordinator: {e}")
        return None

def get_specialist_coordinator() -> Optional[Any]:
    """
    Obtém coordenador de especialistas.
    
    Returns:
        Instância do SpecialistCoordinator ou None
    """
    try:
        from .specialist_agents import SpecialistAgents
        return SpecialistAgents()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar specialist_coordinator: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar specialist_coordinator: {e}")
        return None

def get_all_coordinators() -> dict:
    """
    Obtém todos os coordenadores disponíveis.
    
    Returns:
        Dicionário com todos os coordenadores
    """
    coordinators = {}
    
    # Carregar coordenador central
    coordinator_manager = get_coordinator_manager()
    if coordinator_manager:
        coordinators['manager'] = coordinator_manager
    
    # Carregar coordenadores individuais
    intelligence_coordinator = get_intelligence_coordinator()
    if intelligence_coordinator:
        coordinators['intelligence'] = intelligence_coordinator
    
    processor_coordinator = get_processor_coordinator()
    if processor_coordinator:
        coordinators['processor'] = processor_coordinator
    
    specialist_coordinator = get_specialist_coordinator()
    if specialist_coordinator:
        coordinators['specialist'] = specialist_coordinator
    
    return coordinators

# Convenience functions usando CoordinatorManager
def coordinate_smart_query(query: str, context: Optional[dict] = None) -> dict:
    """
    Coordena consulta usando o gerenciador inteligente.
    
    Args:
        query: Consulta a ser processada
        context: Contexto da consulta
        
    Returns:
        Resultado da coordenação inteligente
    """
    manager = get_coordinator_manager()
    if manager:
        return manager.coordinate_query(query, context)
    return {'status': 'error', 'error': 'Coordinator manager not available'}

def get_domain_agent(domain: str) -> Optional[Any]:
    """
    Obtém agente de domínio específico via manager.
    
    Args:
        domain: Nome do domínio
        
    Returns:
        Instância do agente ou None
    """
    manager = get_coordinator_manager()
    if manager:
        return manager.domain_agents.get(domain)
    return None

def get_coordination_status() -> dict:
    """
    Obtém status completo do sistema de coordenação.
    
    Returns:
        Status de todos os coordenadores
    """
    manager = get_coordinator_manager()
    if manager:
        return manager.get_coordinator_status()
    return {'status': 'error', 'error': 'Coordinator manager not available'}

# Convenience functions originais (mantidas para compatibilidade)
def coordinate_intelligence(operation_type: str, data: Any, **kwargs) -> dict:
    """
    Coordena operação de inteligência.
    
    Args:
        operation_type: Tipo de operação
        data: Dados para processamento
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado da coordenação
    """
    coordinator = get_intelligence_coordinator()
    if coordinator:
        return coordinator.coordinate_intelligence_operation(operation_type, data, **kwargs)
    return {'status': 'error', 'error': 'Intelligence coordinator not available'}

def coordinate_processors(processors: list, data: Any, **kwargs) -> dict:
    """
    Coordena operação de processadores.
    
    Args:
        processors: Lista de processadores
        data: Dados para processamento
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado da coordenação
    """
    coordinator = get_processor_coordinator()
    if coordinator:
        return coordinator.coordinate_processors(processors, data, **kwargs)
    return {'status': 'error', 'error': 'Processor coordinator not available'}

# Aliases para compatibilidade
IntelligenceCoordinator = get_intelligence_coordinator
ProcessorCoordinator = get_processor_coordinator
CoordinatorManager = get_coordinator_manager

# Exports
__all__ = [
    # Manager central
    'get_coordinator_manager',
    'CoordinatorManager',
    
    # Coordinators individuais
    'get_intelligence_coordinator',
    'get_processor_coordinator',
    'get_specialist_coordinator',
    'get_all_coordinators',
    
    # Funções inteligentes (novas)
    'coordinate_smart_query',
    'get_domain_agent',
    'get_coordination_status',
    
    # Funções originais (compatibilidade)
    'coordinate_intelligence',
    'coordinate_processors',
    'IntelligenceCoordinator',
    'ProcessorCoordinator'
] 