"""
🚀 PERFORMANCE CACHE - Sistema de Cache para Readers
==================================================

Módulo responsável por otimizar a performance dos readers através
de cache inteligente e reutilização de instâncias.

Funcionalidades:
- Singleton pattern para readers
- Cache de resultados com TTL
- Lazy loading de dados
- Pool de conexões
"""

import threading
import time
import weakref
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ReadersCache:
    """
    Sistema de cache global para otimização de performance dos readers.
    
    Implementa padrão Singleton para evitar múltiplas instâncias dos readers
    e cache de resultados para evitar reprocessamento desnecessário.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._readers_pool = {}
        self._results_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutos
        self._access_stats = {
            'hits': 0,
            'misses': 0,
            'readers_created': 0
        }
        self._initialized = True
        
        logger.info("🚀 ReadersCache inicializado")
    
    def get_readme_reader(self):
        """
        Obtém instância do ReadmeReader usando pool singleton.
        
        Returns:
            Instância cached do ReadmeReader ou None se não disponível
        """
        if 'readme_reader' not in self._readers_pool:
            try:
                from app.claude_ai_novo.readme_reader import ReadmeReader
                
                reader = ReadmeReader()
                if reader.esta_disponivel():
                    self._readers_pool['readme_reader'] = reader
                    self._access_stats['readers_created'] += 1
                    logger.debug("📄 ReadmeReader criado e adicionado ao pool")
                else:
                    logger.debug("📄 ReadmeReader não disponível")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Erro ao criar ReadmeReader: {e}")
                return None
        
        return self._readers_pool.get('readme_reader')
    
    def get_database_reader(self):
        """
        Obtém instância do DatabaseReader usando pool singleton.
        
        Returns:
            Instância cached do DatabaseReader ou None se não disponível
        """
        if 'database_reader' not in self._readers_pool:
            try:
                from app.claude_ai_novo.database_reader import DatabaseReader
                
                reader = DatabaseReader()
                if reader.esta_disponivel():
                    self._readers_pool['database_reader'] = reader
                    self._access_stats['readers_created'] += 1
                    logger.debug("📊 DatabaseReader criado e adicionado ao pool")
                else:
                    logger.debug("📊 DatabaseReader não disponível")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Erro ao criar DatabaseReader: {e}")
                return None
        
        return self._readers_pool.get('database_reader')
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        Obtém resultado do cache se ainda válido.
        
        Args:
            cache_key: Chave única do cache
            
        Returns:
            Resultado cached ou None se expirado/não existe
        """
        if cache_key not in self._results_cache:
            self._access_stats['misses'] += 1
            return None
        
        # Verificar TTL
        timestamp = self._cache_timestamps.get(cache_key, 0)
        if time.time() - timestamp > self._cache_ttl:
            # Cache expirado, remover
            self._remove_from_cache(cache_key)
            self._access_stats['misses'] += 1
            return None
        
        self._access_stats['hits'] += 1
        logger.debug(f"🎯 Cache hit: {cache_key}")
        return self._results_cache[cache_key]
    
    def set_cached_result(self, cache_key: str, result: Any) -> None:
        """
        Armazena resultado no cache.
        
        Args:
            cache_key: Chave única do cache
            result: Resultado a ser armazenado
        """
        self._results_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
        
        # Limpar cache antigo se muito grande
        if len(self._results_cache) > 100:
            self._cleanup_expired_cache()
        
        logger.debug(f"💾 Resultado cached: {cache_key}")
    
    def _remove_from_cache(self, cache_key: str) -> None:
        """Remove entrada específica do cache"""
        self._results_cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
    
    def _cleanup_expired_cache(self) -> None:
        """Remove entradas expiradas do cache"""
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self._cache_timestamps.items():
            if current_time - timestamp > self._cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_from_cache(key)
        
        if expired_keys:
            logger.debug(f"🧹 Removidas {len(expired_keys)} entradas expiradas do cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do cache.
        
        Returns:
            Dict com estatísticas de performance
        """
        total_requests = self._access_stats['hits'] + self._access_stats['misses']
        hit_rate = (self._access_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self._access_stats['hits'],
            'misses': self._access_stats['misses'],
            'hit_rate_percent': round(hit_rate, 1),
            'readers_in_pool': len(self._readers_pool),
            'cached_results': len(self._results_cache),
            'readers_created_total': self._access_stats['readers_created']
        }
    
    def clear_cache(self) -> None:
        """Limpa todo o cache de resultados"""
        cleared_count = len(self._results_cache)
        self._results_cache.clear()
        self._cache_timestamps.clear()
        
        logger.info(f"🧹 Cache limpo: {cleared_count} entradas removidas")
    
    def invalidate_reader(self, reader_type: str) -> None:
        """
        Invalida e remove reader específico do pool.
        
        Args:
            reader_type: Tipo do reader ('readme_reader' ou 'database_reader')
        """
        if reader_type in self._readers_pool:
            del self._readers_pool[reader_type]
            logger.debug(f"🔄 Reader {reader_type} invalidado e removido do pool")

# Instância global singleton
_cache_instance = ReadersCache()

def get_cache() -> ReadersCache:
    """
    Obtém instância global do cache.
    
    Returns:
        Instância singleton do ReadersCache
    """
    return _cache_instance

def cached_readme_reader():
    """
    Obtém ReadmeReader com cache otimizado.
    
    Returns:
        Instância cached do ReadmeReader
    """
    return get_cache().get_readme_reader()

def cached_database_reader():
    """
    Obtém DatabaseReader com cache otimizado.
    
    Returns:
        Instância cached do DatabaseReader  
    """
    return get_cache().get_database_reader()

def cached_result(cache_key: str, compute_func=None, *args, **kwargs):
    """
    Decorator/função para cache automático de resultados.
    
    Args:
        cache_key: Chave do cache
        compute_func: Função para calcular resultado se não em cache
        *args, **kwargs: Argumentos para a função
        
    Returns:
        Resultado cached ou calculado
    """
    cache = get_cache()
    
    # Tentar obter do cache primeiro
    result = cache.get_cached_result(cache_key)
    if result is not None:
        return result
    
    # Calcular resultado se função fornecida
    if compute_func:
        try:
            result = compute_func(*args, **kwargs)
            cache.set_cached_result(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao calcular resultado para cache {cache_key}: {e}")
            return None
    
    return None

def performance_monitor(func):
    """
    Decorator para monitorar performance de funções.
    
    Args:
        func: Função a ser monitorada
        
    Returns:
        Função decorada com monitoring
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Log apenas se > 1 segundo
                logger.warning(f"⏱️ {func.__name__} executou em {execution_time:.3f}s (lento)")
            elif execution_time > 0.1:
                logger.debug(f"⏱️ {func.__name__} executou em {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ {func.__name__} falhou após {execution_time:.3f}s: {e}")
            raise
    
    return wrapper 