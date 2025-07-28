"""
Cache decorators for easy caching implementation
"""
import functools
import hashlib
import json
from typing import Any, Optional, Callable, Union, List
from datetime import datetime
import inspect
import structlog
import asyncio

from ..services.cache.redis_manager import redis_manager
from ..services.cache.cache_strategies import (
    CacheStrategy, TTLStrategy, AdaptiveTTLStrategy, HybridStrategy
)

logger = structlog.get_logger(__name__)


def _generate_cache_key(prefix: str, func: Callable, args: tuple, kwargs: dict,
                       include_args: Optional[List[int]] = None,
                       include_kwargs: Optional[List[str]] = None) -> str:
    """Generate cache key from function and arguments"""
    parts = [prefix, func.__module__, func.__name__]
    
    # Include specific args if specified
    if include_args:
        for idx in include_args:
            if idx < len(args):
                parts.append(str(args[idx]))
    else:
        # Include all args
        parts.extend(str(arg) for arg in args if not inspect.isclass(arg))
    
    # Include specific kwargs if specified
    if include_kwargs:
        for key in include_kwargs:
            if key in kwargs:
                parts.append(f"{key}={kwargs[key]}")
    else:
        # Include all kwargs
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    # Create hash for long keys
    key_string = ":".join(parts)
    if len(key_string) > 200:
        # Use hash for long keys
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{func.__name__}:{key_hash}"
    
    return key_string


def cache(prefix: str = "cache", 
          ttl: Optional[int] = None,
          strategy: Optional[CacheStrategy] = None,
          compress: bool = True,
          include_args: Optional[List[int]] = None,
          include_kwargs: Optional[List[str]] = None):
    """
    Generic cache decorator with flexible configuration
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        strategy: Cache strategy to use
        compress: Whether to compress cached values
        include_args: List of argument indices to include in cache key
        include_kwargs: List of kwarg names to include in cache key
    """
    if strategy is None:
        strategy = TTLStrategy()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(
                prefix, func, args, kwargs, include_args, include_kwargs
            )
            
            # Try to get from cache
            cached_value = redis_manager.get(cache_key)
            if cached_value is not None:
                strategy.on_hit(cache_key)
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_value
            
            # Cache miss
            strategy.on_miss(cache_key)
            logger.debug("Cache miss", function=func.__name__, key=cache_key)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Determine if we should cache
            if strategy.should_cache(cache_key, result):
                cache_ttl = ttl or strategy.get_ttl(cache_key, result)
                redis_manager.set(cache_key, result, ttl=cache_ttl, compress=compress)
                logger.debug("Cached result", function=func.__name__, 
                           key=cache_key, ttl=cache_ttl)
            
            return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(
                prefix, func, args, kwargs, include_args, include_kwargs
            )
            
            # Try to get from cache
            cached_value = redis_manager.get(cache_key)
            if cached_value is not None:
                strategy.on_hit(cache_key)
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_value
            
            # Cache miss
            strategy.on_miss(cache_key)
            logger.debug("Cache miss", function=func.__name__, key=cache_key)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Determine if we should cache
            if strategy.should_cache(cache_key, result):
                cache_ttl = ttl or strategy.get_ttl(cache_key, result)
                redis_manager.set(cache_key, result, ttl=cache_ttl, compress=compress)
                logger.debug("Cached result", function=func.__name__, 
                           key=cache_key, ttl=cache_ttl)
            
            return result
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_result(ttl: int = 300, compress: bool = True):
    """
    Simple result caching decorator
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        compress: Whether to compress cached values
    """
    return cache(prefix="result", ttl=ttl, compress=compress)


def cache_resource(ttl: int = 600):
    """
    Cache decorator for MCP resources
    
    Args:
        ttl: Time to live in seconds (default: 10 minutes)
    """
    return cache(
        prefix="resource",
        ttl=ttl,
        strategy=TTLStrategy(default_ttl=ttl),
        compress=True
    )


def cache_query(ttl: int = 300):
    """
    Cache decorator for database queries
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
    """
    return cache(
        prefix="query",
        ttl=ttl,
        strategy=AdaptiveTTLStrategy(min_ttl=60, max_ttl=ttl),
        compress=True
    )


def cache_analysis(ttl: int = 1800):
    """
    Cache decorator for analysis results
    
    Args:
        ttl: Time to live in seconds (default: 30 minutes)
    """
    return cache(
        prefix="analysis",
        ttl=ttl,
        strategy=TTLStrategy(default_ttl=ttl),
        compress=True
    )


def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache entries matching pattern after function execution
    
    Args:
        pattern: Cache key pattern to invalidate (supports wildcards)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache entries
            count = redis_manager.delete_pattern(pattern)
            logger.info("Cache invalidated", pattern=pattern, count=count)
            
            return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache entries
            count = redis_manager.delete_pattern(pattern)
            logger.info("Cache invalidated", pattern=pattern, count=count)
            
            return result
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def warmup_cache(*warmup_args, **warmup_kwargs):
    """
    Decorator to pre-warm cache on application startup
    
    The decorated function will be called with warmup_args and warmup_kwargs
    to populate the cache before serving requests.
    """
    def decorator(func: Callable) -> Callable:
        # Store original function
        wrapper = cache()(func)
        
        # Add warmup method
        def warmup():
            """Warmup cache by calling function with predefined args"""
            logger.info("Warming up cache", function=func.__name__)
            try:
                if asyncio.iscoroutinefunction(func):
                    # For async functions, create event loop if needed
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    loop.run_until_complete(wrapper(*warmup_args, **warmup_kwargs))
                else:
                    wrapper(*warmup_args, **warmup_kwargs)
                    
                logger.info("Cache warmup complete", function=func.__name__)
            except Exception as e:
                logger.error("Cache warmup failed", function=func.__name__, error=str(e))
        
        wrapper.warmup = warmup
        return wrapper
    
    return decorator


class CacheManager:
    """
    Context manager for batch cache operations
    """
    def __init__(self):
        self.operations = []
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Queue set operation"""
        self.operations.append(('set', key, value, ttl))
    
    def delete(self, key: str):
        """Queue delete operation"""
        self.operations.append(('delete', key))
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Execute all queued operations"""
        if exc_type is None:
            # Group operations by type
            sets = {}
            deletes = []
            
            for op in self.operations:
                if op[0] == 'set':
                    _, key, value, ttl = op
                    if ttl not in sets:
                        sets[ttl] = {}
                    sets[ttl][key] = value
                elif op[0] == 'delete':
                    deletes.append(op[1])
            
            # Execute batch operations
            for ttl, mapping in sets.items():
                redis_manager.mset(mapping, ttl=ttl)
            
            for key in deletes:
                redis_manager.delete(key)


# Usage example:
# @cache_result(ttl=300)
# def expensive_calculation(x, y):
#     return x ** y
#
# @cache_query(ttl=600)
# async def get_user_data(user_id: int):
#     # Database query
#     return user_data
#
# @invalidate_cache("resource:users:*")
# def update_user(user_id: int, data: dict):
#     # Update user and invalidate related caches
#     pass
#
# @warmup_cache(user_id=1)  # Pre-load user 1 on startup
# def get_user_profile(user_id: int):
#     return fetch_profile(user_id)