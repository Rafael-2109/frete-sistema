"""
🚀 PERFORMANCE CACHE - Sistema de Cache para Scanners
==================================================

Módulo responsável por otimizar a performance dos scanners através
de cache inteligente e reutilização de instâncias.

Funcionalidades:
- Singleton pattern para scanners
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

class ScannersCache:
    """
    Sistema de cache global para otimização de performance dos scanners.
    
    Implementa padrão Singleton para evitar múltiplas instâncias dos scanners
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
            
        self._scanners_pool = {}
        self._results_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutos
        self._access_stats = {
            'hits': 0,
            'misses': 0,
            'scanners_created': 0
        }
        self._initialized = True
        
        logger.info("🚀 ScannersCache inicializado")
    
    def get_readme_scanner(self):
        """
        Obtém instância do ReadmeScanner usando pool singleton.
        
        Returns:
            Instância cached do ReadmeScanner ou None se não disponível
        """
        if 'readme_scanner' not in self._scanners_pool:
            try:
                from app.claude_ai_novo.scanning.readme_scanner import ReadmeScanner
                
                scanner = ReadmeScanner()
                if scanner.esta_disponivel():
                    self._scanners_pool['readme_scanner'] = scanner
                    self._access_stats['scanners_created'] += 1
                    logger.debug("📄 ReadmeScanner criado e adicionado ao pool")
                else:
                    logger.debug("📄 ReadmeScanner não disponível")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Erro ao criar ReadmeScanner: {e}")
                return None
        
        return self._scanners_pool.get('readme_scanner')
    
    def get_database_scanner(self):
        """
        Obtém instância do DatabaseScanner usando pool singleton.
        
        Returns:
            Instância cached do DatabaseScanner ou None se não disponível
        """
        if 'database_scanner' not in self._scanners_pool:
            try:
                from app.claude_ai_novo.scanning.database_scanner import DatabaseScanner
                
                scanner = DatabaseScanner()
                if scanner.esta_disponivel():
                    self._scanners_pool['database_scanner'] = scanner
                    self._access_stats['scanners_created'] += 1
                    logger.debug("📊 DatabaseScanner criado e adicionado ao pool")
                else:
                    logger.debug("📊 DatabaseScanner não disponível")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Erro ao criar DatabaseScanner: {e}")
                return None
        
        return self._scanners_pool.get('database_scanner')
    
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
            'scanners_in_pool': len(self._scanners_pool),
            'cached_results': len(self._results_cache),
            'scanners_created_total': self._access_stats['scanners_created']
        }
    
    def clear_cache(self) -> None:
        """Limpa todo o cache de resultados"""
        cleared_count = len(self._results_cache)
        self._results_cache.clear()
        self._cache_timestamps.clear()
        
        logger.info(f"🧹 Cache limpo: {cleared_count} entradas removidas")
    
    def invalidate_scanner(self, scanner_type: str) -> None:
        """
        Invalida e remove scanner específico do pool.
        
        Args:
            scanner_type: Tipo do scanner ('readme_scanner' ou 'database_scanner')
        """
        if scanner_type in self._scanners_pool:
            del self._scanners_pool[scanner_type]
            logger.debug(f"🔄 Scanner {scanner_type} invalidado e removido do pool")

# Instância global singleton
_cache_instance = ScannersCache()

# Alias para compatibilidade
PerformanceCache = ScannersCache

def get_cache() -> ScannersCache:
    """
    Obtém instância global do cache.
    
    Returns:
        Instância singleton do ScannersCache
    """
    return _cache_instance

def cached_readme_scanner():
    """
    Obtém ReadmeScanner com cache otimizado.
    
    Returns:
        Instância cached do ReadmeScanner
    """
    return get_cache().get_readme_scanner

def cached_database_scanner():
    """
    Obtém DatabaseScanner com cache otimizado.
    
    Returns:
        Instância cached do DatabaseScanner  
    """
    return get_cache().get_database_scanner()

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