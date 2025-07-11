"""
🔗 CONTEXT PROVIDER - Provedor de Contexto
=========================================

Módulo responsável por fornecimento e gerenciamento de contexto para análises.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)

class ContextProvider:
    """
    Provedor de contexto que gerencia e fornece informações contextuais.
    
    Responsabilidades:
    - Coleta de contexto de múltiplas fontes
    - Enriquecimento de contexto
    - Cache de contexto
    - Filtros de contexto
    - Contexto temporal
    """
    
    def __init__(self):
        """Inicializa o provedor de contexto."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔗 ContextProvider inicializado")
        
        # Cache de contexto
        self.context_cache = {}
        self.cache_ttl = timedelta(minutes=30)
        
        # Configurações de contexto
        self.config = {
            'max_context_size': 10000,  # Caracteres
            'max_history_items': 50,
            'include_metadata': True,
            'include_timestamps': True,
            'context_levels': ['basic', 'detailed', 'complete']
        }
        
        # Provedores de contexto registrados
        self.context_sources = {}
        
        # Inicializar provedores padrão
        self._initialize_default_sources()
    
    def get_context(self, query: str, context_type: str = 'basic', **kwargs) -> Dict[str, Any]:
        """
        Obtém contexto para uma consulta.
        
        Args:
            query: Consulta do usuário
            context_type: Tipo de contexto ('basic', 'detailed', 'complete')
            **kwargs: Parâmetros adicionais
            
        Returns:
            Contexto enriquecido
        """
        try:
            # Gerar chave de cache
            cache_key = self._generate_cache_key(query, context_type, kwargs)
            
            # Verificar cache
            cached_context = self._get_cached_context(cache_key)
            if cached_context:
                self.logger.debug(f"🎯 Contexto obtido do cache: {cache_key[:20]}...")
                return cached_context
            
            # Construir contexto
            context = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'context_type': context_type,
                'sources_used': [],
                'metadata': {},
                'data': {}
            }
            
            # Coletar contexto de diferentes fontes
            if context_type == 'basic':
                context = self._collect_basic_context(context, query, **kwargs)
            elif context_type == 'detailed':
                context = self._collect_detailed_context(context, query, **kwargs)
            elif context_type == 'complete':
                context = self._collect_complete_context(context, query, **kwargs)
            
            # Enriquecer contexto
            context = self._enrich_context(context, query, **kwargs)
            
            # Filtrar contexto se necessário
            context = self._filter_context(context)
            
            # Cachear resultado
            self._cache_context(cache_key, context)
            
            self.logger.info(f"✅ Contexto gerado: {len(context['sources_used'])} fontes, tipo: {context_type}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter contexto: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'context_type': context_type,
                'error': str(e),
                'sources_used': [],
                'data': {}
            }
    
    def provide_user_context(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fornece contexto específico do usuário.
        
        Args:
            user_id: ID do usuário
            session_id: ID da sessão
            
        Returns:
            Contexto do usuário
        """
        try:
            context = {
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'user_profile': {},
                'preferences': {},
                'history': [],
                'permissions': {}
            }
            
            # Coletar perfil do usuário
            context['user_profile'] = self._get_user_profile(user_id)
            
            # Coletar preferências
            context['preferences'] = self._get_user_preferences(user_id)
            
            # Coletar histórico limitado
            context['history'] = self._get_user_history(user_id, limit=10)
            
            # Coletar permissões
            context['permissions'] = self._get_user_permissions(user_id)
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter contexto do usuário: {e}")
            return {
                'user_id': user_id,
                'session_id': session_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def provide_temporal_context(self, reference_date: Optional[datetime] = None, window_days: int = 30) -> Dict[str, Any]:
        """
        Fornece contexto temporal.
        
        Args:
            reference_date: Data de referência
            window_days: Janela de dias para contexto
            
        Returns:
            Contexto temporal
        """
        try:
            if reference_date is None:
                reference_date = datetime.now()
            
            context = {
                'reference_date': reference_date.isoformat(),
                'window_days': window_days,
                'period_start': (reference_date - timedelta(days=window_days)).isoformat(),
                'period_end': reference_date.isoformat(),
                'temporal_data': {},
                'trends': {},
                'patterns': {}
            }
            
            # Coletar dados temporais
            context['temporal_data'] = self._collect_temporal_data(reference_date, window_days)
            
            # Analisar tendências
            context['trends'] = self._analyze_temporal_trends(context['temporal_data'])
            
            # Detectar padrões
            context['patterns'] = self._detect_temporal_patterns(context['temporal_data'])
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter contexto temporal: {e}")
            return {
                'reference_date': reference_date.isoformat() if reference_date else datetime.now().isoformat(),
                'error': str(e)
            }
    
    def register_context_source(self, source_name: str, provider_func, priority: int = 5) -> bool:
        """
        Registra uma fonte de contexto.
        
        Args:
            source_name: Nome da fonte
            provider_func: Função provedora de contexto
            priority: Prioridade (1-10, maior = mais importante)
            
        Returns:
            True se registrado com sucesso
        """
        try:
            self.context_sources[source_name] = {
                'provider': provider_func,
                'priority': priority,
                'registered_at': datetime.now().isoformat(),
                'calls_count': 0,
                'errors_count': 0
            }
            
            self.logger.info(f"✅ Fonte de contexto '{source_name}' registrada com prioridade {priority}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar fonte '{source_name}': {e}")
            return False
    
    def update_context_cache(self, query: str, context_data: Dict[str, Any], ttl_minutes: int = 30):
        """
        Atualiza cache de contexto manualmente.
        
        Args:
            query: Consulta
            context_data: Dados do contexto
            ttl_minutes: Tempo de vida em minutos
        """
        try:
            cache_key = self._generate_cache_key(query, 'manual', {})
            
            cache_entry = {
                'data': context_data,
                'created_at': datetime.now(),
                'ttl_minutes': ttl_minutes
            }
            
            self.context_cache[cache_key] = cache_entry
            self.logger.debug(f"💾 Contexto cacheado manualmente: {cache_key[:20]}...")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao cachear contexto: {e}")
    
    def clear_context_cache(self, pattern: Optional[str] = None):
        """
        Limpa cache de contexto.
        
        Args:
            pattern: Padrão para limpeza seletiva
        """
        try:
            if pattern is None:
                # Limpar tudo
                cleared_count = len(self.context_cache)
                self.context_cache.clear()
                self.logger.info(f"🧹 Cache limpo: {cleared_count} entradas removidas")
            else:
                # Limpeza seletiva
                keys_to_remove = [key for key in self.context_cache.keys() if pattern in key]
                for key in keys_to_remove:
                    del self.context_cache[key]
                self.logger.info(f"🧹 Cache limpo seletivamente: {len(keys_to_remove)} entradas removidas")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar cache: {e}")
    
    def _initialize_default_sources(self):
        """Inicializa fontes de contexto padrão."""
        # Fonte de contexto de sistema
        self.register_context_source(
            'system_context',
            self._provide_system_context,
            priority=8
        )
        
        # Fonte de contexto de sessão
        self.register_context_source(
            'session_context',
            self._provide_session_context,
            priority=7
        )
        
        # Fonte de contexto de consulta
        self.register_context_source(
            'query_context',
            self._provide_query_context,
            priority=6
        )
    
    def _collect_basic_context(self, context: Dict[str, Any], query: str, **kwargs) -> Dict[str, Any]:
        """Coleta contexto básico."""
        # Fontes prioritárias para contexto básico
        priority_sources = ['system_context', 'query_context']
        
        for source_name in priority_sources:
            if source_name in self.context_sources:
                try:
                    source_data = self._call_context_source(source_name, query, **kwargs)
                    context['data'][source_name] = source_data
                    context['sources_used'].append(source_name)
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro em fonte {source_name}: {e}")
        
        return context
    
    def _collect_detailed_context(self, context: Dict[str, Any], query: str, **kwargs) -> Dict[str, Any]:
        """Coleta contexto detalhado."""
        # Primeiro coletar contexto básico
        context = self._collect_basic_context(context, query, **kwargs)
        
        # Adicionar fontes detalhadas
        detailed_sources = ['session_context']
        
        for source_name in detailed_sources:
            if source_name in self.context_sources:
                try:
                    source_data = self._call_context_source(source_name, query, **kwargs)
                    context['data'][source_name] = source_data
                    if source_name not in context['sources_used']:
                        context['sources_used'].append(source_name)
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro em fonte {source_name}: {e}")
        
        return context
    
    def _collect_complete_context(self, context: Dict[str, Any], query: str, **kwargs) -> Dict[str, Any]:
        """Coleta contexto completo."""
        # Primeiro coletar contexto detalhado
        context = self._collect_detailed_context(context, query, **kwargs)
        
        # Adicionar todas as outras fontes disponíveis
        remaining_sources = [name for name in self.context_sources.keys() 
                           if name not in context['sources_used']]
        
        for source_name in remaining_sources:
            try:
                source_data = self._call_context_source(source_name, query, **kwargs)
                context['data'][source_name] = source_data
                context['sources_used'].append(source_name)
            except Exception as e:
                self.logger.warning(f"⚠️ Erro em fonte {source_name}: {e}")
        
        return context
    
    def _call_context_source(self, source_name: str, query: str, **kwargs) -> Dict[str, Any]:
        """Chama uma fonte de contexto."""
        source_info = self.context_sources[source_name]
        provider_func = source_info['provider']
        
        # Incrementar contador
        source_info['calls_count'] += 1
        
        try:
            result = provider_func(query, **kwargs)
            return result
        except Exception as e:
            source_info['errors_count'] += 1
            raise e
    
    def _enrich_context(self, context: Dict[str, Any], query: str, **kwargs) -> Dict[str, Any]:
        """Enriquece contexto com metadados."""
        if self.config['include_metadata']:
            context['metadata'] = {
                'query_length': len(query),
                'word_count': len(query.split()),
                'context_size': len(str(context)),
                'generation_time': datetime.now().isoformat(),
                'config_used': self.config.copy()
            }
        
        return context
    
    def _filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Filtra contexto baseado em configurações."""
        # Limitar tamanho do contexto
        context_str = str(context)
        if len(context_str) > self.config['max_context_size']:
            # Simplificar dados se muito grande
            for source_name in context['data']:
                if isinstance(context['data'][source_name], dict):
                    # Manter apenas campos essenciais
                    essential_fields = ['timestamp', 'type', 'summary', 'key_data']
                    filtered_data = {k: v for k, v in context['data'][source_name].items() 
                                   if k in essential_fields}
                    context['data'][source_name] = filtered_data
        
        return context
    
    def _generate_cache_key(self, query: str, context_type: str, kwargs: Dict[str, Any]) -> str:
        """Gera chave de cache."""
        content = f"{query}|{context_type}|{str(sorted(kwargs.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_context(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtém contexto do cache."""
        if cache_key not in self.context_cache:
            return None
        
        cache_entry = self.context_cache[cache_key]
        
        # Verificar TTL
        age = datetime.now() - cache_entry['created_at']
        if age > timedelta(minutes=cache_entry.get('ttl_minutes', 30)):
            del self.context_cache[cache_key]
            return None
        
        return cache_entry['data']
    
    def _cache_context(self, cache_key: str, context: Dict[str, Any]):
        """Armazena contexto no cache."""
        cache_entry = {
            'data': context,
            'created_at': datetime.now(),
            'ttl_minutes': 30
        }
        
        self.context_cache[cache_key] = cache_entry
    
    # Provedores de contexto padrão
    def _provide_system_context(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fornece contexto do sistema."""
        return {
            'timestamp': datetime.now().isoformat(),
            'system_status': 'operational',
            'available_sources': len(self.context_sources),
            'cache_size': len(self.context_cache),
            'query_received': query[:100] + '...' if len(query) > 100 else query
        }
    
    def _provide_session_context(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fornece contexto da sessão."""
        return {
            'timestamp': datetime.now().isoformat(),
            'session_id': kwargs.get('session_id', 'unknown'),
            'user_id': kwargs.get('user_id', 'anonymous'),
            'query_count': kwargs.get('query_count', 1),
            'session_duration': kwargs.get('session_duration', 0)
        }
    
    def _provide_query_context(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fornece contexto da consulta."""
        return {
            'timestamp': datetime.now().isoformat(),
            'query_type': self._detect_query_type(query),
            'complexity': self._assess_query_complexity(query),
            'entities': self._extract_simple_entities(query),
            'intent': self._detect_simple_intent(query)
        }
    
    def _detect_query_type(self, query: str) -> str:
        """Detecta tipo da consulta."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['listar', 'mostrar', 'ver', 'consultar']):
            return 'query'
        elif any(word in query_lower for word in ['criar', 'adicionar', 'inserir']):
            return 'create'
        elif any(word in query_lower for word in ['atualizar', 'modificar', 'alterar']):
            return 'update'
        elif any(word in query_lower for word in ['relatório', 'exportar', 'gerar']):
            return 'report'
        else:
            return 'general'
    
    def _assess_query_complexity(self, query: str) -> str:
        """Avalia complexidade da consulta."""
        word_count = len(query.split())
        
        if word_count <= 5:
            return 'simple'
        elif word_count <= 15:
            return 'medium'
        else:
            return 'complex'
    
    def _extract_simple_entities(self, query: str) -> List[str]:
        """Extrai entidades simples."""
        entities = []
        
        # Detectar datas
        import re
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', query)
        entities.extend(dates)
        
        # Detectar números
        numbers = re.findall(r'\b\d{3,}\b', query)
        entities.extend(numbers)
        
        return entities
    
    def _detect_simple_intent(self, query: str) -> str:
        """Detecta intenção simples."""
        query_lower = query.lower()
        
        if '?' in query:
            return 'question'
        elif any(word in query_lower for word in ['por favor', 'preciso', 'quero']):
            return 'request'
        elif any(word in query_lower for word in ['problema', 'erro', 'não funciona']):
            return 'help'
        else:
            return 'statement'
    
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Obtém perfil do usuário (placeholder)."""
        return {
            'user_id': user_id,
            'profile_type': 'standard',
            'created_at': datetime.now().isoformat(),
            'preferences_loaded': False
        }
    
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Obtém preferências do usuário (placeholder)."""
        return {
            'language': 'pt-BR',
            'detail_level': 'medium',
            'format_preference': 'text'
        }
    
    def _get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém histórico do usuário (placeholder)."""
        return [
            {
                'timestamp': datetime.now().isoformat(),
                'query': 'consulta exemplo',
                'type': 'query'
            }
        ]
    
    def _get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Obtém permissões do usuário (placeholder)."""
        return {
            'read': True,
            'write': False,
            'admin': False
        }
    
    def _collect_temporal_data(self, reference_date: datetime, window_days: int) -> Dict[str, Any]:
        """Coleta dados temporais (placeholder)."""
        return {
            'data_points': window_days,
            'period_type': 'daily',
            'availability': 'limited'
        }
    
    def _analyze_temporal_trends(self, temporal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa tendências temporais (placeholder)."""
        return {
            'trend_direction': 'stable',
            'confidence': 0.5,
            'patterns_found': 0
        }
    
    def _detect_temporal_patterns(self, temporal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detecta padrões temporais (placeholder)."""
        return {
            'weekly_patterns': False,
            'monthly_patterns': False,
            'seasonal_patterns': False
        }


def get_context_provider() -> ContextProvider:
    """
    Obtém instância do provedor de contexto.
    
    Returns:
        Instância do ContextProvider
    """
    return ContextProvider() 