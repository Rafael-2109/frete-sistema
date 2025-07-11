"""
📁 LOADERS - Módulos de Carregamento
====================================

Módulos responsáveis por carregar dados de diferentes fontes.
Organização: Manager + micro-loaders especializados por domínio.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def get_context_loader() -> Optional[Any]:
    """
    Obtém carregador de contexto.
    
    Returns:
        Instância do ContextLoader ou None
    """
    try:
        from .context_loader import ContextLoader
        return ContextLoader()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar context_loader: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar context_loader: {e}")
        return None

def get_database_loader() -> Optional[Any]:
    """
    Obtém carregador de banco de dados.
    
    Returns:
        Instância do DatabaseLoader ou None
    """
    try:
        from .database_loader import DatabaseLoader
        return DatabaseLoader()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar database_loader: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar database_loader: {e}")
        return None

def get_loader_manager() -> Optional[Any]:
    """
    Obtém manager de loaders (coordenador principal).
    
    Returns:
        Instância do LoaderManager ou None
    """
    try:
        from .loader_manager import get_loader_manager as get_manager
        return get_manager()
    except ImportError as e:
        logger.warning(f"⚠️ Não foi possível carregar loader_manager: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar loader_manager: {e}")
        return None

def get_data_manager() -> Optional[Any]:
    """
    Obtém gerenciador de dados (movido para utils/).
    
    Returns:
        Instância do DataManager ou None
    """
    try:
        # data_manager foi movido para utils/
        from ..utils.data_manager import get_datamanager
        return get_datamanager()
    except ImportError as e:
        logger.warning(f"⚠️ data_manager foi movido para utils/: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao carregar data_manager: {e}")
        return None

def get_domain_loaders() -> dict:
    """
    Obtém todos os micro-loaders de domínio.
    
    Returns:
        Dicionário com micro-loaders especializados
    """
    domain_loaders = {}
    
    try:
        from .domain import (
            get_pedidos_loader, get_entregas_loader, get_fretes_loader,
            get_embarques_loader, get_faturamento_loader, get_agendamentos_loader
        )
        
        domain_loaders.update({
            'pedidos': get_pedidos_loader(),
            'entregas': get_entregas_loader(),
            'fretes': get_fretes_loader(),
            'embarques': get_embarques_loader(),
            'faturamento': get_faturamento_loader(),
            'agendamentos': get_agendamentos_loader()
        })
        
    except ImportError as e:
        logger.warning(f"⚠️ Erro ao importar micro-loaders: {e}")
    
    return domain_loaders

def get_all_loaders() -> dict:
    """
    Obtém todos os carregadores disponíveis.
    
    Returns:
        Dicionário com todos os carregadores
    """
    loaders = {}
    
    # Carregar manager principal
    loader_manager = get_loader_manager()
    if loader_manager:
        loaders['manager'] = loader_manager
    
    # Carregar loaders básicos
    context_loader = get_context_loader()
    if context_loader:
        loaders['context'] = context_loader
    
    database_loader = get_database_loader()
    if database_loader:
        loaders['database'] = database_loader
    
    # Carregar micro-loaders de domínio
    domain_loaders = get_domain_loaders()
    if domain_loaders:
        loaders['domain'] = domain_loaders
    
    return loaders

# Convenience functions
def load_context(query: Any, **kwargs) -> dict:
    """
    Carrega contexto.
    
    Args:
        query: Consulta para carregamento
        **kwargs: Parâmetros adicionais
        
    Returns:
        Contexto carregado
    """
    loader = get_context_loader()
    if loader:
        return loader.load_context(query, **kwargs)
    return {'status': 'error', 'error': 'Context loader not available'}

def load_database(query: Any, **kwargs) -> dict:
    """
    Carrega dados do banco.
    
    Args:
        query: Consulta SQL ou critério
        **kwargs: Parâmetros adicionais
        
    Returns:
        Dados carregados
    """
    loader = get_database_loader()
    if loader:
        return loader.load_database(query, **kwargs)
    return {'status': 'error', 'error': 'Database loader not available'}

def load_data(consulta: str, user_context: Optional[dict] = None, **kwargs) -> dict:
    """
    Carrega dados usando o LoaderManager (recomendado).
    
    Args:
        consulta: Consulta do usuário
        user_context: Contexto do usuário
        **kwargs: Parâmetros adicionais
        
    Returns:
        Dados carregados
    """
    # Tentar usar LoaderManager primeiro
    manager = get_loader_manager()
    if manager:
        # Determinar melhor domínio para a consulta
        domain = manager.get_best_loader_for_query(consulta, user_context)
        filters = kwargs.copy()
        if user_context:
            filters.update(user_context)
        return manager.load_data_by_domain(domain, filters)
    
    # Fallback: data_manager (movido para utils/)
    data_manager = get_data_manager()
    if data_manager:
        return data_manager.load_data(consulta, user_context)
    
    return {'status': 'error', 'error': 'No loader manager available'}

def load_domain_data(domain: str, filters: dict) -> dict:
    """
    Carrega dados de um domínio específico usando micro-loaders.
    
    Args:
        domain: Nome do domínio (pedidos, entregas, fretes, etc.)
        filters: Filtros específicos
        
    Returns:
        Dados do domínio carregados
    """
    manager = get_loader_manager()
    if manager:
        return manager.load_data_by_domain(domain, filters)
    return {'status': 'error', 'error': 'Loader manager not available'}

# Aliases para compatibilidade
ContextLoader = get_context_loader
DatabaseLoader = get_database_loader
LoaderManager = get_loader_manager
DataManager = get_data_manager  # Movido para utils/

# Exports
__all__ = [
    'get_context_loader',
    'get_database_loader',
    'get_loader_manager',
    'get_domain_loaders', 
    'get_data_manager',
    'get_all_loaders',
    'load_context',
    'load_database',
    'load_data',
    'load_domain_data',
    'ContextLoader',
    'DatabaseLoader',
    'LoaderManager',
    'DataManager'
] 