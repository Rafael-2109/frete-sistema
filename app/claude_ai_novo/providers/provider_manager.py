"""
🔗 PROVIDER MANAGER - Coordenador de Provedores
=============================================

Manager principal que coordena todos os providers de dados e contexto.

Responsabilidade: Coordenar ContextProvider e DataProvider para fornecer
dados e contexto de forma integrada e inteligente.

Função: MANAGER que orquestra providers especializados, não um provider individual.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProviderRequest:
    """Definição de uma solicitação para providers"""
    request_type: str  # 'data', 'context', 'mixed'
    query: str
    domain: Optional[str] = None
    context_type: str = 'basic'
    filters: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ProviderManager:
    """
    Manager principal que coordena todos os providers.
    
    NÃO apenas delega, mas tem lógica inteligente para:
    - Detectar que tipo de provider é necessário
    - Combinar dados de múltiplos providers
    - Otimizar performance com cache coordenado
    - Fornecer fallbacks robustos
    """
    
    def __init__(self):
        self.context_provider = None
        self.data_provider = None
        self.providers_cache = {}
        self.request_stats = {
            'data_requests': 0,
            'context_requests': 0,
            'mixed_requests': 0,
            'errors': 0
        }
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Inicializa providers com fallback robusto"""
        try:
            from .context_provider import ContextProvider
            self.context_provider = ContextProvider()
            logger.info("✅ ContextProvider inicializado no manager")
        except ImportError as e:
            logger.warning(f"⚠️ ContextProvider não disponível: {e}")
            
        try:
            from .data_provider import get_data_provider
            # Usar get_data_provider que agora tenta obter LoaderManager automaticamente
            self.data_provider = get_data_provider()
            logger.info("✅ DataProvider inicializado no manager (com LoaderManager se disponível)")
        except ImportError as e:
            logger.warning(f"⚠️ DataProvider não disponível: {e}")
    
    def provide(self, request: Union[ProviderRequest, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Método principal de provisionamento integrado.
        
        Args:
            request: Solicitação de dados/contexto
            
        Returns:
            Resposta integrada dos providers
        """
        try:
            # Normalizar request
            if isinstance(request, dict):
                request = self._dict_to_request(request)
            
            # Detectar tipo de provisionamento necessário
            provision_type = self._detect_provision_type(request)
            
            # Executar provisionamento baseado no tipo
            if provision_type == 'data_only':
                return self._provide_data_only(request)
            elif provision_type == 'context_only':
                return self._provide_context_only(request)
            elif provision_type == 'data_with_context':
                return self._provide_data_with_context(request)
            elif provision_type == 'context_with_data':
                return self._provide_context_with_data(request)
            else:
                return self._provide_mixed(request)
                
        except Exception as e:
            logger.error(f"❌ Erro no provisionamento: {e}")
            self.request_stats['errors'] += 1
            return {
                'error': str(e),
                'request_type': getattr(request, 'request_type', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'fallback': True
            }
    
    def _detect_provision_type(self, request: ProviderRequest) -> str:
        """
        Detecta que tipo de provisionamento é necessário.
        
        LÓGICA INTELIGENTE baseada na consulta e parâmetros.
        """
        query_lower = request.query.lower()
        
        # Palavras que indicam necessidade de dados específicos
        data_keywords = ['listar', 'mostrar', 'quantos', 'ver', 'buscar', 'encontrar', 
                        'relatório', 'exportar', 'dados', 'registros']
        
        # Palavras que indicam necessidade de contexto
        context_keywords = ['como', 'porque', 'quando', 'onde', 'explicar', 'analisar',
                           'sugerir', 'recomendar', 'comparar', 'tendência']
        
        has_data_intent = any(keyword in query_lower for keyword in data_keywords)
        has_context_intent = any(keyword in query_lower for keyword in context_keywords)
        has_domain = request.domain is not None
        has_filters = request.filters is not None
        
        # Lógica de decisão inteligente
        if has_domain and has_filters and not has_context_intent:
            return 'data_only'
        elif has_context_intent and not has_data_intent:
            return 'context_only'
        elif has_data_intent and has_context_intent:
            return 'data_with_context'
        elif has_context_intent and has_domain:
            return 'context_with_data'
        else:
            return 'mixed'
    
    def _provide_data_only(self, request: ProviderRequest) -> Dict[str, Any]:
        """Fornece apenas dados"""
        self.request_stats['data_requests'] += 1
        
        if not self.data_provider:
            return {'error': 'DataProvider não disponível', 'fallback': True}
        
        try:
            data = self.data_provider.get_data_by_domain(
                domain=request.domain or 'general',
                filters=request.filters
            )
            
            return {
                'type': 'data_only',
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'provider_used': 'data_provider'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no DataProvider: {e}")
            return {'error': str(e), 'provider': 'data_provider'}
    
    def _provide_context_only(self, request: ProviderRequest) -> Dict[str, Any]:
        """Fornece apenas contexto"""
        self.request_stats['context_requests'] += 1
        
        if not self.context_provider:
            return {'error': 'ContextProvider não disponível', 'fallback': True}
        
        try:
            context = self.context_provider.get_context(
                query=request.query,
                context_type=request.context_type,
                user_id=request.user_id,
                session_id=request.session_id
            )
            
            return {
                'type': 'context_only',
                'context': context,
                'timestamp': datetime.now().isoformat(),
                'provider_used': 'context_provider'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no ContextProvider: {e}")
            return {'error': str(e), 'provider': 'context_provider'}
    
    def _provide_data_with_context(self, request: ProviderRequest) -> Dict[str, Any]:
        """Fornece dados enriquecidos com contexto"""
        self.request_stats['mixed_requests'] += 1
        
        try:
            # Primeiro obter dados
            data_result = self._provide_data_only(request)
            
            # Depois enriquecer com contexto
            if 'error' not in data_result:
                context_request = ProviderRequest(
                    request_type='context',
                    query=f"Contexto para: {request.query}",
                    context_type='detailed',
                    user_id=request.user_id,
                    session_id=request.session_id,
                    metadata={'data_domain': request.domain}
                )
                
                context_result = self._provide_context_only(context_request)
                
                return {
                    'type': 'data_with_context',
                    'data': data_result.get('data'),
                    'context': context_result.get('context'),
                    'timestamp': datetime.now().isoformat(),
                    'providers_used': ['data_provider', 'context_provider']
                }
            
            return data_result
            
        except Exception as e:
            logger.error(f"❌ Erro na provisão mista: {e}")
            return {'error': str(e), 'type': 'data_with_context'}
    
    def _provide_context_with_data(self, request: ProviderRequest) -> Dict[str, Any]:
        """Fornece contexto enriquecido com dados"""
        self.request_stats['mixed_requests'] += 1
        
        try:
            # Primeiro obter contexto
            context_result = self._provide_context_only(request)
            
            # Depois enriquecer com dados relevantes se disponível
            if 'error' not in context_result and request.domain:
                data_request = ProviderRequest(
                    request_type='data',
                    query=request.query,
                    domain=request.domain,
                    filters=request.filters
                )
                
                data_result = self._provide_data_only(data_request)
                
                return {
                    'type': 'context_with_data',
                    'context': context_result.get('context'),
                    'supporting_data': data_result.get('data'),
                    'timestamp': datetime.now().isoformat(),
                    'providers_used': ['context_provider', 'data_provider']
                }
            
            return context_result
            
        except Exception as e:
            logger.error(f"❌ Erro na provisão mista: {e}")
            return {'error': str(e), 'type': 'context_with_data'}
    
    def _provide_mixed(self, request: ProviderRequest) -> Dict[str, Any]:
        """Provisão mista inteligente"""
        self.request_stats['mixed_requests'] += 1
        
        try:
            results = {}
            
            # Tentar ambos os providers
            if self.context_provider:
                try:
                    context = self.context_provider.get_context(
                        query=request.query,
                        context_type=request.context_type or 'basic'
                    )
                    results['context'] = context
                except Exception as e:
                    results['context_error'] = str(e)
            
            if self.data_provider and request.domain:
                try:
                    data = self.data_provider.get_data_by_domain(
                        domain=request.domain,
                        filters=request.filters
                    )
                    results['data'] = data
                except Exception as e:
                    results['data_error'] = str(e)
            
            return {
                'type': 'mixed',
                'results': results,
                'timestamp': datetime.now().isoformat(),
                'providers_attempted': ['context_provider', 'data_provider']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na provisão mista: {e}")
            return {'error': str(e), 'type': 'mixed'}
    
    def _dict_to_request(self, data: Dict[str, Any]) -> ProviderRequest:
        """Converte dict para ProviderRequest"""
        return ProviderRequest(
            request_type=data.get('request_type', 'mixed'),
            query=data.get('query', ''),
            domain=data.get('domain'),
            context_type=data.get('context_type', 'basic'),
            filters=data.get('filters'),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            metadata=data.get('metadata')
        )
    
    def get_best_provider_for_query(self, query: str, domain: Optional[str] = None) -> str:
        """
        Determina o melhor provider para uma consulta.
        
        Args:
            query: Consulta do usuário
            domain: Domínio se conhecido
            
        Returns:
            Nome do provider recomendado
        """
        query_lower = query.lower()
        
        # Consultas claramente de dados
        if any(word in query_lower for word in ['listar', 'quantos', 'mostrar dados']):
            return 'data_provider'
        
        # Consultas claramente de contexto
        if any(word in query_lower for word in ['como funciona', 'porque', 'explicar']):
            return 'context_provider'
        
        # Baseado no domínio
        if domain in ['entregas', 'pedidos', 'embarques', 'faturamento']:
            return 'data_provider'
        
        return 'mixed'
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Retorna status detalhado dos providers"""
        return {
            'providers': {
                'context_provider': {
                    'available': self.context_provider is not None,
                    'type': type(self.context_provider).__name__ if self.context_provider else None
                },
                'data_provider': {
                    'available': self.data_provider is not None,
                    'type': type(self.data_provider).__name__ if self.data_provider else None
                }
            },
            'statistics': self.request_stats.copy(),
            'cache_size': len(self.providers_cache),
            'timestamp': datetime.now().isoformat()
        }
    
    def clear_cache(self):
        """Limpa cache dos providers"""
        self.providers_cache.clear()
        if self.context_provider and hasattr(self.context_provider, 'clear_context_cache'):
            self.context_provider.clear_context_cache()
        logger.info("🧹 Cache dos providers limpo")

# Instância global
_provider_manager = None

def get_provider_manager() -> ProviderManager:
    """
    Retorna instância global do ProviderManager.
    
    Returns:
        ProviderManager: Instância do manager
    """
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
        logger.info("✅ ProviderManager inicializado")
    return _provider_manager

# Funções de conveniência
def provide_data(domain: str, filters: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """Função de conveniência para dados"""
    manager = get_provider_manager()
    request = ProviderRequest(
        request_type='data',
        query=kwargs.get('query', f'Dados do domínio {domain}'),
        domain=domain,
        filters=filters,
        **{k: v for k, v in kwargs.items() if k in ['user_id', 'session_id']}
    )
    return manager.provide(request)

def provide_context(query: str, context_type: str = 'basic', **kwargs) -> Dict[str, Any]:
    """Função de conveniência para contexto"""
    manager = get_provider_manager()
    request = ProviderRequest(
        request_type='context',
        query=query,
        context_type=context_type,
        **{k: v for k, v in kwargs.items() if k in ['user_id', 'session_id', 'domain']}
    )
    return manager.provide(request)

# Exports
__all__ = [
    'ProviderManager',
    'ProviderRequest',
    'get_provider_manager',
    'provide_data',
    'provide_context'
] 