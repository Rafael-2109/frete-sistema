"""
Cache em memoria com TTL — utilitario leve para dados de configuracao.
=====================================================================

Uso:
    from app.utils.memory_cache import ttl_cache

    @ttl_cache(ttl=300)  # 5 minutos
    def get_transportadoras():
        return Transportadora.query.order_by(Transportadora.razao_social).all()

    # Ou uso direto:
    cache = TTLCache(ttl=300)
    dados = cache.get_or_set('chave', fetcher=lambda: query_pesada())

IMPORTANTE: Armazena dados simples (dicts, listas de dicts) em vez de
instancias ORM para evitar DetachedInstanceError entre requests.
Para dados ORM, o fetcher deve converter para dict antes de retornar.
"""

import time
import functools
from threading import Lock


class TTLCache:
    """Cache thread-safe com TTL em segundos."""

    def __init__(self, ttl=300):
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}
        self._lock = Lock()

    def get(self, key):
        """Retorna valor cacheado ou None se expirado/inexistente."""
        with self._lock:
            ts = self._timestamps.get(key, 0)
            if time.time() - ts < self.ttl:
                return self._cache.get(key)
            return None

    def set(self, key, value):
        """Define valor no cache."""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def get_or_set(self, key, fetcher):
        """Retorna valor cacheado ou executa fetcher, cacheia e retorna."""
        val = self.get(key)
        if val is not None:
            return val
        val = fetcher()
        self.set(key, val)
        return val

    def invalidate(self, key=None):
        """Invalida uma chave ou todo o cache."""
        with self._lock:
            if key is None:
                self._cache.clear()
                self._timestamps.clear()
            else:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)


def ttl_cache(ttl=300, key=None):
    """Decorator para cachear resultado de funcao com TTL.

    Args:
        ttl: Time-to-live em segundos (default 300 = 5 min)
        key: Chave do cache (default: nome da funcao)
    """
    _cache = TTLCache(ttl=ttl)

    def decorator(func):
        cache_key = key or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Se ha argumentos, inclui no cache key
            if args or kwargs:
                full_key = f"{cache_key}:{args}:{kwargs}"
            else:
                full_key = cache_key

            val = _cache.get(full_key)
            if val is not None:
                return val

            val = func(*args, **kwargs)
            _cache.set(full_key, val)
            return val

        wrapper.invalidate = _cache.invalidate
        wrapper.cache = _cache
        return wrapper

    return decorator
