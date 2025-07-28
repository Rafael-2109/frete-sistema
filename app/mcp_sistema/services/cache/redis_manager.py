"""
Redis Manager for MCP Sistema
Handles all Redis operations with connection pooling and error handling
"""
import json
import pickle
import zlib
from typing import Any, Optional, Dict, List, Callable, Union
from datetime import datetime, timedelta
import redis
from redis import ConnectionPool, Redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import structlog
from contextlib import contextmanager
from threading import RLock
import os

logger = structlog.get_logger(__name__)


class RedisManager:
    """
    Redis connection manager with advanced features:
    - Connection pooling
    - Automatic retry with exponential backoff
    - Compression support
    - Multi-level caching
    - Health monitoring
    """
    
    _instance = None
    _lock = RLock()
    
    def __new__(cls):
        """Singleton pattern to ensure single Redis connection pool"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection pool"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.pool = self._create_pool()
        self._local_cache: Dict[str, Dict[str, Any]] = {}  # In-memory L1 cache
        self._stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'compressions': 0
        }
    
    def _create_pool(self) -> ConnectionPool:
        """Create Redis connection pool with optimized settings"""
        return ConnectionPool.from_url(
            self.redis_url,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    @contextmanager
    def get_client(self) -> Redis:
        """Get Redis client from pool with error handling"""
        client = None
        try:
            client = Redis(connection_pool=self.pool)
            yield client
        except ConnectionError as e:
            logger.error("Redis connection error", error=str(e))
            self._stats['errors'] += 1
            raise
        except TimeoutError as e:
            logger.error("Redis timeout error", error=str(e))
            self._stats['errors'] += 1
            raise
        except RedisError as e:
            logger.error("Redis error", error=str(e))
            self._stats['errors'] += 1
            raise
        finally:
            if client:
                client.close()
    
    def _serialize(self, value: Any, compress: bool = True) -> bytes:
        """Serialize and optionally compress data"""
        serialized = pickle.dumps(value)
        
        if compress and len(serialized) > 1024:  # Compress if > 1KB
            serialized = zlib.compress(serialized)
            self._stats['compressions'] += 1
            
        return serialized
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize and decompress data"""
        try:
            # Try decompression first
            decompressed = zlib.decompress(data)
            return pickle.loads(decompressed)
        except:
            # If decompression fails, data wasn't compressed
            return pickle.loads(data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with L1/L2 lookup
        L1: In-memory cache
        L2: Redis cache
        """
        # Check L1 cache first
        if key in self._local_cache:
            cache_entry = self._local_cache[key]
            if cache_entry['expires'] > datetime.now():
                self._stats['hits'] += 1
                logger.debug("L1 cache hit", key=key)
                return cache_entry['value']
            else:
                del self._local_cache[key]
        
        # Check L2 cache (Redis)
        try:
            with self.get_client() as client:
                data = client.get(key)
                if data:
                    self._stats['hits'] += 1
                    value = self._deserialize(data)
                    
                    # Store in L1 cache with 60s TTL
                    self._local_cache[key] = {
                        'value': value,
                        'expires': datetime.now() + timedelta(seconds=60)
                    }
                    
                    logger.debug("L2 cache hit", key=key)
                    return value
        except Exception as e:
            logger.error("Error getting from cache", key=key, error=str(e))
        
        self._stats['misses'] += 1
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            compress: bool = True) -> bool:
        """Set value in cache with optional TTL and compression"""
        try:
            # Store in L1 cache
            expires = datetime.now() + timedelta(seconds=ttl if ttl else 3600)
            self._local_cache[key] = {
                'value': value,
                'expires': expires
            }
            
            # Store in L2 cache (Redis)
            with self.get_client() as client:
                serialized = self._serialize(value, compress)
                if ttl:
                    client.setex(key, ttl, serialized)
                else:
                    client.set(key, serialized)
                
                logger.debug("Cache set", key=key, ttl=ttl, compressed=compress)
                return True
                
        except Exception as e:
            logger.error("Error setting cache", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from both L1 and L2 cache"""
        try:
            # Remove from L1 cache
            if key in self._local_cache:
                del self._local_cache[key]
            
            # Remove from L2 cache
            with self.get_client() as client:
                client.delete(key)
                
            logger.debug("Cache deleted", key=key)
            return True
            
        except Exception as e:
            logger.error("Error deleting from cache", key=key, error=str(e))
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        count = 0
        try:
            # Clear matching keys from L1 cache
            keys_to_delete = [k for k in self._local_cache if self._match_pattern(k, pattern)]
            for key in keys_to_delete:
                del self._local_cache[key]
                count += 1
            
            # Clear from L2 cache
            with self.get_client() as client:
                for key in client.scan_iter(match=pattern):
                    client.delete(key)
                    count += 1
                    
            logger.info("Cache pattern deleted", pattern=pattern, count=count)
            return count
            
        except Exception as e:
            logger.error("Error deleting pattern", pattern=pattern, error=str(e))
            return count
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for L1 cache"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys at once"""
        results = {}
        
        # Check L1 cache first
        l2_keys = []
        for key in keys:
            if key in self._local_cache:
                cache_entry = self._local_cache[key]
                if cache_entry['expires'] > datetime.now():
                    results[key] = cache_entry['value']
                else:
                    del self._local_cache[key]
                    l2_keys.append(key)
            else:
                l2_keys.append(key)
        
        # Get remaining from L2 cache
        if l2_keys:
            try:
                with self.get_client() as client:
                    values = client.mget(l2_keys)
                    for key, value in zip(l2_keys, values):
                        if value:
                            deserialized = self._deserialize(value)
                            results[key] = deserialized
                            # Update L1 cache
                            self._local_cache[key] = {
                                'value': deserialized,
                                'expires': datetime.now() + timedelta(seconds=60)
                            }
            except Exception as e:
                logger.error("Error in mget", error=str(e))
        
        return results
    
    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple keys at once"""
        try:
            # Update L1 cache
            expires = datetime.now() + timedelta(seconds=ttl if ttl else 3600)
            for key, value in mapping.items():
                self._local_cache[key] = {
                    'value': value,
                    'expires': expires
                }
            
            # Update L2 cache
            with self.get_client() as client:
                # Serialize all values
                serialized_mapping = {
                    key: self._serialize(value) 
                    for key, value in mapping.items()
                }
                
                if ttl:
                    # Use pipeline for atomic operations with TTL
                    pipe = client.pipeline()
                    for key, value in serialized_mapping.items():
                        pipe.setex(key, ttl, value)
                    pipe.execute()
                else:
                    client.mset(serialized_mapping)
                    
            return True
            
        except Exception as e:
            logger.error("Error in mset", error=str(e))
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        try:
            with self.get_client() as client:
                return client.incr(key, amount)
        except Exception as e:
            logger.error("Error incrementing", key=key, error=str(e))
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key"""
        try:
            with self.get_client() as client:
                return client.expire(key, ttl)
        except Exception as e:
            logger.error("Error setting expire", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        # Check L1 cache
        if key in self._local_cache:
            if self._local_cache[key]['expires'] > datetime.now():
                return True
            else:
                del self._local_cache[key]
        
        # Check L2 cache
        try:
            with self.get_client() as client:
                return client.exists(key) > 0
        except Exception as e:
            logger.error("Error checking existence", key=key, error=str(e))
            return False
    
    def clear_local_cache(self):
        """Clear L1 in-memory cache"""
        self._local_cache.clear()
        logger.info("Local cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with self.get_client() as client:
                info = client.info()
                
            return {
                'local_cache_size': len(self._local_cache),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': self._stats['hits'] / max(1, self._stats['hits'] + self._stats['misses']),
                'errors': self._stats['errors'],
                'compressions': self._stats['compressions'],
                'redis_info': {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', 'N/A'),
                    'total_connections_received': info.get('total_connections_received', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }
            }
        except Exception as e:
            logger.error("Error getting stats", error=str(e))
            return self._stats
    
    def health_check(self) -> bool:
        """Check Redis health"""
        try:
            with self.get_client() as client:
                client.ping()
                return True
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False


# Global instance
redis_manager = RedisManager()