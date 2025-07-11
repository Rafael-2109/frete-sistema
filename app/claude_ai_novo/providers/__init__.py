"""
🔗 PROVIDERS - Provedores de Dados
================================

Módulos responsáveis por fornecer dados e contexto.
Organizados com ProviderManager coordenando providers especializados.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Flask fallback para execução standalone
try:
    from app.claude_ai_novo.utils.flask_fallback import is_flask_available
    flask_available = is_flask_available()
except ImportError:
    flask_available = False
    logger.warning("Flask fallback não disponível")

# Imports principais
try:
    # Manager principal
    from .provider_manager import ProviderManager, get_provider_manager, ProviderRequest
    
    # Providers específicos
    from .context_provider import ContextProvider, get_context_provider
    from .data_provider import DataProvider, get_data_provider
    
    # Funções de conveniência do manager
    from .provider_manager import provide_data, provide_context
    
    logger.info("✅ Providers carregados com sucesso")
    
except ImportError as e:
    logger.warning(f"⚠️ Erro ao carregar providers: {e}")
    
    # Fallback básico
    class FallbackProvider:
        def __init__(self, provider_type="fallback"):
            self.provider_type = provider_type
        
        def get_context(self, query, context_type='basic', **kwargs):
            return {
                'query': query,
                'context_type': context_type,
                'status': 'fallback',
                'data': {}
            }
        
        def get_data_by_domain(self, domain, filters=None):
            return {
                'domain': domain,
                'total': 0,
                'data': [],
                'status': 'fallback'
            }
        
        def provide(self, request):
            return {
                'type': 'fallback',
                'request': str(request),
                'status': 'provider_unavailable'
            }
        
        def get_provider_status(self):
            return {
                'providers': {},
                'statistics': {'errors': 1},
                'status': 'fallback'
            }
    
    # Atribuir classes fallback
    ProviderManager = FallbackProvider
    ContextProvider = FallbackProvider
    DataProvider = FallbackProvider
    
    # Funções fallback
    def get_provider_manager(): return ProviderManager()
    def get_context_provider(): return ContextProvider()
    def get_data_provider(): return DataProvider()
    
    def provide_data(domain, filters=None, **kwargs):
        return {'domain': domain, 'data': [], 'status': 'fallback'}
    
    def provide_context(query, context_type='basic', **kwargs):
        return {'query': query, 'context': {}, 'status': 'fallback'}

# Funções de conveniência para uso direto
def provide_integrated_data(query: str, domain: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Função de conveniência para provisionamento integrado de dados.
    
    Args:
        query: Consulta do usuário
        domain: Domínio dos dados
        **kwargs: Parâmetros adicionais
        
    Returns:
        Dados provisionados pelo manager
    """
    manager = get_provider_manager()
    
    request = {
        'request_type': 'data',
        'query': query,
        'domain': domain,
        'filters': kwargs.get('filters'),
        'user_id': kwargs.get('user_id'),
        'session_id': kwargs.get('session_id')
    }
    
    return manager.provide(request)

def provide_integrated_context(query: str, context_type: str = 'basic', **kwargs) -> Dict[str, Any]:
    """
    Função de conveniência para provisionamento integrado de contexto.
    
    Args:
        query: Consulta do usuário
        context_type: Tipo de contexto
        **kwargs: Parâmetros adicionais
        
    Returns:
        Contexto provisionado pelo manager
    """
    manager = get_provider_manager()
    
    request = {
        'request_type': 'context',
        'query': query,
        'context_type': context_type,
        'domain': kwargs.get('domain'),
        'user_id': kwargs.get('user_id'),
        'session_id': kwargs.get('session_id')
    }
    
    return manager.provide(request)

def provide_mixed_intelligence(query: str, domain: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Função de conveniência para provisionamento misto inteligente.
    
    Args:
        query: Consulta do usuário
        domain: Domínio se conhecido
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resposta integrada de dados e contexto
    """
    manager = get_provider_manager()
    
    request = {
        'request_type': 'mixed',
        'query': query,
        'domain': domain,
        'context_type': kwargs.get('context_type', 'detailed'),
        'filters': kwargs.get('filters'),
        'user_id': kwargs.get('user_id'),
        'session_id': kwargs.get('session_id')
    }
    
    return manager.provide(request)

def get_best_provider_recommendation(query: str, domain: Optional[str] = None) -> str:
    """Recomenda o melhor provider para uma consulta"""
    manager = get_provider_manager()
    return manager.get_best_provider_for_query(query, domain)

def get_all_providers_status() -> Dict[str, Any]:
    """Retorna status completo de todos os providers"""
    manager = get_provider_manager()
    return manager.get_provider_status()

__all__ = [
    # Manager principal
    'ProviderManager',
    'get_provider_manager',
    
    # Providers específicos
    'ContextProvider',
    'DataProvider',
    'get_context_provider',
    'get_data_provider',
    
    # Classes auxiliares
    'ProviderRequest',
    
    # Funções básicas do manager
    'provide_data',
    'provide_context',
    
    # Funções de conveniência integradas
    'provide_integrated_data',
    'provide_integrated_context',
    'provide_mixed_intelligence',
    
    # Funções utilitárias
    'get_best_provider_recommendation',
    'get_all_providers_status'
] 