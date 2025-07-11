"""
Performance Cache - Cache otimizado para enrichers
================================================

Sistema de cache com monitoramento de performance para
acelerar operações de enriquecimento.
"""

import time
import logging
from typing import Any, Callable, Optional, Dict
from functools import wraps

logger = logging.getLogger(__name__)

# Cache simples em memória
_cache_store: Dict[str, Dict[str, Any]] = {}

def cached_result(cache_key: str, func: Callable, *args, **kwargs) -> Any:
    """
    Executa função com cache otimizado.
    
    Args:
        cache_key: Chave do cache
        func: Função a executar
        *args, **kwargs: Argumentos da função
        
    Returns:
        Resultado da função (do cache ou nova execução)
    """
    try:
        # Verificar se existe no cache
        if cache_key in _cache_store:
            cache_entry = _cache_store[cache_key]
            
            # Verificar se não expirou (30 minutos)
            if time.time() - cache_entry['timestamp'] < 1800:
                logger.debug(f"💾 Cache hit: {cache_key}")
                return cache_entry['result']
        
        # Executar função
        logger.debug(f"🔄 Cache miss: {cache_key}")
        result = func(*args, **kwargs)
        
        # Salvar no cache
        _cache_store[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Limitar tamanho do cache (últimos 100 itens)
        if len(_cache_store) > 100:
            # Remover o mais antigo
            oldest_key = min(_cache_store.keys(), 
                           key=lambda k: _cache_store[k]['timestamp'])
            del _cache_store[oldest_key]
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro no cached_result: {e}")
        # Fallback - executar função diretamente
        try:
            return func(*args, **kwargs)
        except:
            return None

def performance_monitor(func: Callable) -> Callable:
    """
    Decorator para monitorar performance de funções.
    
    Args:
        func: Função a monitorar
        
    Returns:
        Função decorada com monitoramento
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Log do tempo de execução
            execution_time = time.time() - start_time
            
            if execution_time > 2.0:  # Mais de 2 segundos
                logger.warning(f"🐌 Função lenta: {func.__name__} ({execution_time:.2f}s)")
            elif execution_time > 5.0:  # Mais de 5 segundos
                logger.error(f"🚨 Função muito lenta: {func.__name__} ({execution_time:.2f}s)")
            else:
                logger.debug(f"⚡ {func.__name__}: {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Erro em {func.__name__} após {execution_time:.2f}s: {e}")
            raise
    
    return wrapper

def clear_cache():
    """Limpa todo o cache de performance."""
    global _cache_store
    _cache_store = {}
    logger.info("🧹 Cache de performance limpo")

def get_cache_stats() -> Dict[str, Any]:
    """
    Obtém estatísticas do cache.
    
    Returns:
        Estatísticas do cache
    """
    return {
        'total_entries': len(_cache_store),
        'cache_keys': list(_cache_store.keys()),
        'oldest_timestamp': min([entry['timestamp'] for entry in _cache_store.values()]) if _cache_store else None,
        'newest_timestamp': max([entry['timestamp'] for entry in _cache_store.values()]) if _cache_store else None
    } 