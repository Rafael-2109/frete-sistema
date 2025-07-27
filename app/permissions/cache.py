"""
Permission Cache Implementation
==============================

Provides caching functionality for permission checks to improve performance.
Supports multiple cache backends and automatic invalidation.
"""

import json
import time
from typing import Any, Optional, Dict, List
from flask import current_app
from app import db
from app.utils.timezone import agora_brasil
import logging
import redis
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheBackend:
    """Base class for cache backends"""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def delete_pattern(self, pattern: str) -> int:
        raise NotImplementedError
    
    def clear(self) -> bool:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """Simple in-memory cache for development/testing"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            else:
                # Expired, remove it
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def delete_pattern(self, pattern: str) -> int:
        # Simple pattern matching (supports * at end)
        deleted = 0
        pattern_prefix = pattern.rstrip('*')
        
        keys_to_delete = []
        for key in self._cache:
            if pattern.endswith('*') and key.startswith(pattern_prefix):
                keys_to_delete.append(key)
            elif key == pattern:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._cache[key]
            deleted += 1
        
        return deleted
    
    def clear(self) -> bool:
        self._cache.clear()
        return True


class RedisCache(CacheBackend):
    """Redis-based cache for production"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            serialized = json.dumps(value)
            return self.redis.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            return self.redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        try:
            deleted = 0
            for key in self.redis.scan_iter(match=pattern):
                if self.redis.delete(key):
                    deleted += 1
            return deleted
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    def clear(self) -> bool:
        try:
            self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


class DatabaseCache(CacheBackend):
    """Database-backed cache for persistent storage"""
    
    def get(self, key: str) -> Optional[Any]:
        from app.permissions.models import PermissionCache as PermCacheModel
        
        try:
            cache_entry = PermCacheModel.query.filter_by(
                cache_key=key
            ).filter(
                PermCacheModel.expires_at > agora_brasil()
            ).first()
            
            if cache_entry:
                return cache_entry.permission_data
        except Exception as e:
            logger.error(f"Database cache get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        from app.permissions.models import PermissionCache as PermCacheModel
        
        try:
            # Remove existing entry if exists
            PermCacheModel.query.filter_by(cache_key=key).delete()
            
            # Create new entry
            expires_at = agora_brasil() + timedelta(seconds=ttl)
            cache_entry = PermCacheModel(
                cache_key=key,
                permission_data=value,
                expires_at=expires_at
            )
            
            db.session.add(cache_entry)
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Database cache set error: {e}")
            db.session.rollback()
            return False
    
    def delete(self, key: str) -> bool:
        from app.permissions.models import PermissionCache as PermCacheModel
        
        try:
            deleted = PermCacheModel.query.filter_by(cache_key=key).delete()
            db.session.commit()
            return deleted > 0
        except Exception as e:
            logger.error(f"Database cache delete error: {e}")
            db.session.rollback()
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        from app.permissions.models import PermissionCache as PermCacheModel
        
        try:
            # Convert pattern to SQL LIKE pattern
            sql_pattern = pattern.replace('*', '%')
            
            deleted = PermCacheModel.query.filter(
                PermCacheModel.cache_key.like(sql_pattern)
            ).delete()
            
            db.session.commit()
            return deleted
            
        except Exception as e:
            logger.error(f"Database cache delete_pattern error: {e}")
            db.session.rollback()
            return 0
    
    def clear(self) -> bool:
        from app.permissions.models import PermissionCache as PermCacheModel
        
        try:
            PermCacheModel.query.delete()
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Database cache clear error: {e}")
            db.session.rollback()
            return False


class PermissionCache:
    """
    Main permission cache manager that coordinates different cache backends
    """
    
    def __init__(self):
        self.backends: List[CacheBackend] = []
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialize cache backends based on configuration"""
        # Always use in-memory cache as L1
        self.backends.append(InMemoryCache())
        
        # Add Redis if configured (check if in app context)
        try:
            from flask import current_app
            if current_app and current_app.config.get('REDIS_URL'):
                try:
                    redis_client = redis.from_url(current_app.config['REDIS_URL'])
                    self.backends.append(RedisCache(redis_client))
                except Exception as e:
                    logger.warning(f"Failed to initialize Redis cache: {e}")
        except RuntimeError:
            # Not in app context, skip Redis for now
            logger.debug("Not in app context, skipping Redis initialization")
        
        # Add database cache as L3
        self.backends.append(DatabaseCache())
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache, checking each backend in order
        """
        for i, backend in enumerate(self.backends):
            value = backend.get(key)
            if value is not None:
                # Found in this backend, update higher-level caches
                for j in range(i):
                    self.backends[j].set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in all cache backends
        """
        success = True
        for backend in self.backends:
            if not backend.set(key, value, ttl):
                success = False
        
        return success
    
    def delete(self, key: str) -> bool:
        """
        Delete key from all cache backends
        """
        success = True
        for backend in self.backends:
            if not backend.delete(key):
                success = False
        
        return success
    
    def invalidate_user(self, user_id: int):
        """
        Invalidate all cache entries for a specific user
        """
        pattern = f"perm:*:{user_id}:*"
        for backend in self.backends:
            backend.delete_pattern(pattern)
    
    def invalidate_module(self, module_name: str):
        """
        Invalidate all cache entries for a specific module
        """
        pattern = f"perm:*:{module_name}:*"
        for backend in self.backends:
            backend.delete_pattern(pattern)
    
    def invalidate_all(self):
        """
        Clear all permission cache
        """
        for backend in self.backends:
            backend.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        """
        stats = {
            'backends': len(self.backends),
            'backend_types': [type(b).__name__ for b in self.backends]
        }
        
        # Add backend-specific stats if available
        for i, backend in enumerate(self.backends):
            if isinstance(backend, InMemoryCache):
                stats[f'backend_{i}_size'] = len(backend._cache)
        
        return stats


# Cache invalidation helpers
def invalidate_user_permissions(user_id: int):
    """Invalidate all cached permissions for a user"""
    cache = PermissionCache()
    cache.invalidate_user(user_id)
    logger.info(f"Invalidated permission cache for user {user_id}")


def invalidate_module_permissions(module_name: str):
    """Invalidate all cached permissions for a module"""
    cache = PermissionCache()
    cache.invalidate_module(module_name)
    logger.info(f"Invalidated permission cache for module {module_name}")


def invalidate_all_permissions():
    """Invalidate all cached permissions"""
    cache = PermissionCache()
    cache.invalidate_all()
    logger.info("Invalidated all permission cache")


# Cleanup expired cache entries (for database backend)
def cleanup_expired_cache():
    """Remove expired cache entries from database"""
    from app.permissions.models import PermissionCache as PermCacheModel
    
    try:
        deleted = PermCacheModel.query.filter(
            PermCacheModel.expires_at < agora_brasil()
        ).delete()
        
        db.session.commit()
        logger.info(f"Cleaned up {deleted} expired cache entries")
        return deleted
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired cache: {e}")
        db.session.rollback()
        return 0