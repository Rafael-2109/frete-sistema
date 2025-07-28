"""
Unit tests for caching system
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
import json
import time
import hashlib
from src.cache.cache_manager import (
    CacheManager,
    CacheBackend,
    RedisCache,
    MemoryCache,
    CacheError,
    CacheMissError
)


class TestMemoryCache:
    """Test cases for in-memory cache implementation"""
    
    @pytest.fixture
    def memory_cache(self):
        """Create memory cache instance"""
        return MemoryCache(
            max_size=100,
            ttl_seconds=3600,
            eviction_policy="LRU"
        )
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for caching"""
        return {
            "simple": {"key": "value"},
            "complex": {
                "user": {"id": 123, "name": "Test User"},
                "data": [1, 2, 3, 4, 5],
                "nested": {"level1": {"level2": "deep"}}
            },
            "large": {"data": "x" * 1000}
        }
    
    def test_set_and_get_simple(self, memory_cache, sample_data):
        """Test basic set and get operations"""
        key = "test_key"
        value = sample_data["simple"]
        
        # Set
        memory_cache.set(key, value)
        
        # Get
        retrieved = memory_cache.get(key)
        assert retrieved == value
    
    def test_get_nonexistent_key(self, memory_cache):
        """Test getting non-existent key"""
        with pytest.raises(CacheMissError):
            memory_cache.get("nonexistent")
    
    def test_get_with_default(self, memory_cache):
        """Test get with default value"""
        default = {"default": "value"}
        result = memory_cache.get("nonexistent", default=default)
        assert result == default
    
    def test_ttl_expiration(self, memory_cache):
        """Test TTL expiration"""
        key = "expiring_key"
        value = {"data": "expires"}
        
        # Set with short TTL
        memory_cache.set(key, value, ttl=1)
        
        # Should exist immediately
        assert memory_cache.get(key) == value
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be expired
        with pytest.raises(CacheMissError):
            memory_cache.get(key)
    
    def test_delete_key(self, memory_cache, sample_data):
        """Test key deletion"""
        key = "delete_me"
        memory_cache.set(key, sample_data["simple"])
        
        # Verify exists
        assert memory_cache.exists(key)
        
        # Delete
        result = memory_cache.delete(key)
        assert result is True
        
        # Verify deleted
        assert not memory_cache.exists(key)
    
    def test_clear_cache(self, memory_cache, sample_data):
        """Test clearing entire cache"""
        # Add multiple items
        for key, value in sample_data.items():
            memory_cache.set(key, value)
        
        # Verify items exist
        assert memory_cache.size() == len(sample_data)
        
        # Clear
        memory_cache.clear()
        
        # Verify cleared
        assert memory_cache.size() == 0
        for key in sample_data:
            assert not memory_cache.exists(key)
    
    def test_lru_eviction(self, memory_cache):
        """Test LRU eviction policy"""
        memory_cache.max_size = 3
        
        # Fill cache
        memory_cache.set("key1", "value1")
        memory_cache.set("key2", "value2")
        memory_cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        memory_cache.get("key1")
        
        # Add new item, should evict key2 (least recently used)
        memory_cache.set("key4", "value4")
        
        assert memory_cache.exists("key1")
        assert not memory_cache.exists("key2")  # Evicted
        assert memory_cache.exists("key3")
        assert memory_cache.exists("key4")
    
    def test_update_existing_key(self, memory_cache):
        """Test updating existing key"""
        key = "update_me"
        
        memory_cache.set(key, {"version": 1})
        memory_cache.set(key, {"version": 2})
        
        result = memory_cache.get(key)
        assert result["version"] == 2
    
    def test_get_many(self, memory_cache, sample_data):
        """Test getting multiple keys at once"""
        # Set multiple
        for key, value in sample_data.items():
            memory_cache.set(key, value)
        
        # Get many
        keys = list(sample_data.keys())
        results = memory_cache.get_many(keys)
        
        assert len(results) == len(keys)
        for key in keys:
            assert results[key] == sample_data[key]
    
    def test_set_many(self, memory_cache, sample_data):
        """Test setting multiple keys at once"""
        memory_cache.set_many(sample_data)
        
        for key, value in sample_data.items():
            assert memory_cache.get(key) == value
    
    def test_cache_stats(self, memory_cache):
        """Test cache statistics"""
        # Perform operations
        memory_cache.set("key1", "value1")
        memory_cache.get("key1")  # Hit
        
        try:
            memory_cache.get("key2")  # Miss
        except CacheMissError:
            pass
        
        stats = memory_cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 1
        assert stats["evictions"] == 0


class TestRedisCache:
    """Test cases for Redis cache implementation"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        return MagicMock()
    
    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create Redis cache instance with mocked client"""
        cache = RedisCache(
            host="localhost",
            port=6379,
            db=0,
            ttl_seconds=3600
        )
        cache.client = mock_redis
        return cache
    
    def test_set_with_serialization(self, redis_cache, mock_redis):
        """Test set with JSON serialization"""
        key = "test_key"
        value = {"data": "test", "number": 42}
        
        redis_cache.set(key, value)
        
        # Verify Redis set was called with serialized data
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        
        assert call_args[0][0] == key
        assert call_args[0][1] == 3600  # TTL
        assert json.loads(call_args[0][2]) == value
    
    def test_get_with_deserialization(self, redis_cache, mock_redis):
        """Test get with JSON deserialization"""
        key = "test_key"
        value = {"data": "test"}
        
        mock_redis.get.return_value = json.dumps(value).encode()
        
        result = redis_cache.get(key)
        
        assert result == value
        mock_redis.get.assert_called_once_with(key)
    
    def test_get_cache_miss(self, redis_cache, mock_redis):
        """Test cache miss in Redis"""
        mock_redis.get.return_value = None
        
        with pytest.raises(CacheMissError):
            redis_cache.get("missing_key")
    
    def test_delete_from_redis(self, redis_cache, mock_redis):
        """Test deletion from Redis"""
        key = "delete_me"
        mock_redis.delete.return_value = 1
        
        result = redis_cache.delete(key)
        
        assert result is True
        mock_redis.delete.assert_called_once_with(key)
    
    def test_exists_in_redis(self, redis_cache, mock_redis):
        """Test key existence check"""
        mock_redis.exists.return_value = True
        
        assert redis_cache.exists("existing_key") is True
        
        mock_redis.exists.return_value = False
        assert redis_cache.exists("missing_key") is False
    
    def test_clear_with_pattern(self, redis_cache, mock_redis):
        """Test clearing cache with pattern"""
        mock_redis.scan_iter.return_value = ["key1", "key2", "key3"]
        
        redis_cache.clear(pattern="prefix:*")
        
        mock_redis.scan_iter.assert_called_once_with(match="prefix:*")
        assert mock_redis.delete.call_count == 3
    
    def test_pipeline_operations(self, redis_cache, mock_redis):
        """Test pipeline for batch operations"""
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline
        
        data = {"key1": "value1", "key2": "value2"}
        redis_cache.set_many(data)
        
        mock_redis.pipeline.assert_called_once()
        assert mock_pipeline.setex.call_count == 2
        mock_pipeline.execute.assert_called_once()
    
    def test_connection_error_handling(self, redis_cache, mock_redis):
        """Test Redis connection error handling"""
        mock_redis.get.side_effect = Exception("Connection refused")
        
        with pytest.raises(CacheError) as exc_info:
            redis_cache.get("key")
        
        assert "Redis operation failed" in str(exc_info.value)
    
    def test_get_ttl(self, redis_cache, mock_redis):
        """Test getting remaining TTL"""
        mock_redis.ttl.return_value = 1800  # 30 minutes
        
        ttl = redis_cache.get_ttl("key")
        
        assert ttl == 1800
        mock_redis.ttl.assert_called_once_with("key")
    
    def test_extend_ttl(self, redis_cache, mock_redis):
        """Test extending key TTL"""
        mock_redis.expire.return_value = True
        
        result = redis_cache.extend_ttl("key", 7200)
        
        assert result is True
        mock_redis.expire.assert_called_once_with("key", 7200)


class TestCacheManager:
    """Test cases for cache manager with multiple backends"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager with multiple backends"""
        return CacheManager(
            default_backend="memory",
            backends={
                "memory": MemoryCache(max_size=100),
                "redis": MagicMock(spec=RedisCache)
            }
        )
    
    @pytest.fixture
    def freight_data(self):
        """Sample freight calculation data"""
        return {
            "route": "SP-RJ",
            "distance": 430,
            "weight": 1000,
            "service": "express",
            "cost": 250.00,
            "currency": "BRL"
        }
    
    def test_cache_key_generation(self, cache_manager):
        """Test cache key generation"""
        params = {
            "origin": "São Paulo",
            "destination": "Rio de Janeiro",
            "weight": 1000,
            "service": "express"
        }
        
        key = cache_manager.generate_key("freight_calc", **params)
        
        # Key should be deterministic
        key2 = cache_manager.generate_key("freight_calc", **params)
        assert key == key2
        
        # Different params should generate different key
        params["weight"] = 2000
        key3 = cache_manager.generate_key("freight_calc", **params)
        assert key != key3
    
    def test_cache_with_tags(self, cache_manager, freight_data):
        """Test caching with tags"""
        key = "freight:sp-rj:express"
        tags = ["freight", "route:sp-rj", "service:express"]
        
        cache_manager.set(key, freight_data, tags=tags)
        
        # Get by key
        result = cache_manager.get(key)
        assert result == freight_data
        
        # Invalidate by tag
        cache_manager.invalidate_by_tag("route:sp-rj")
        
        # Should be invalidated
        result = cache_manager.get(key, default=None)
        assert result is None
    
    def test_cache_decorator(self, cache_manager):
        """Test cache decorator functionality"""
        call_count = 0
        
        @cache_manager.cache(ttl=60, tags=["calculation"])
        def expensive_calculation(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call - cache miss
        result1 = expensive_calculation(10, 20)
        assert result1 == 30
        assert call_count == 1
        
        # Second call - cache hit
        result2 = expensive_calculation(10, 20)
        assert result2 == 30
        assert call_count == 1  # Not called again
        
        # Different args - cache miss
        result3 = expensive_calculation(20, 30)
        assert result3 == 50
        assert call_count == 2
    
    def test_multi_backend_fallback(self, cache_manager):
        """Test fallback between backends"""
        # Configure Redis to fail
        cache_manager.backends["redis"].get.side_effect = CacheError("Redis down")
        
        # Set in memory backend
        cache_manager.set("key", "value", backend="memory")
        
        # Try to get from Redis first, should fallback to memory
        result = cache_manager.get("key", backends=["redis", "memory"])
        assert result == "value"
    
    def test_cache_warming(self, cache_manager):
        """Test cache warming functionality"""
        data_to_warm = {
            "route:sp-rj": {"distance": 430, "toll": 50},
            "route:sp-mg": {"distance": 580, "toll": 70},
            "route:rj-mg": {"distance": 430, "toll": 40}
        }
        
        # Warm cache
        cache_manager.warm_cache(data_to_warm, ttl=3600, tags=["routes"])
        
        # Verify all warmed
        for key, value in data_to_warm.items():
            assert cache_manager.get(key) == value
    
    def test_cache_compression(self, cache_manager):
        """Test compression for large values"""
        large_data = {
            "data": "x" * 10000,
            "array": list(range(1000))
        }
        
        cache_manager.set(
            "large_key",
            large_data,
            compress=True,
            compression_threshold=1024
        )
        
        # Should retrieve correctly
        result = cache_manager.get("large_key")
        assert result == large_data
    
    def test_conditional_caching(self, cache_manager):
        """Test conditional caching based on response"""
        @cache_manager.cache(
            condition=lambda result: result.get("success", False)
        )
        def api_call(status):
            return {"success": status, "data": "result"}
        
        # Successful call - should cache
        result1 = api_call(True)
        assert cache_manager.exists(cache_manager.generate_key("api_call", True))
        
        # Failed call - should not cache
        result2 = api_call(False)
        assert not cache_manager.exists(cache_manager.generate_key("api_call", False))
    
    def test_cache_invalidation_patterns(self, cache_manager):
        """Test various cache invalidation patterns"""
        # Set multiple related keys
        cache_manager.set("user:123:profile", {"name": "Test"})
        cache_manager.set("user:123:settings", {"theme": "dark"})
        cache_manager.set("user:456:profile", {"name": "Other"})
        
        # Invalidate by pattern
        cache_manager.invalidate_pattern("user:123:*")
        
        # User 123 data should be gone
        assert cache_manager.get("user:123:profile", default=None) is None
        assert cache_manager.get("user:123:settings", default=None) is None
        
        # User 456 data should remain
        assert cache_manager.get("user:456:profile") is not None
    
    def test_cache_metrics(self, cache_manager, freight_data):
        """Test cache metrics collection"""
        # Perform various operations
        cache_manager.set("key1", freight_data)
        cache_manager.get("key1")  # Hit
        cache_manager.get("key2", default=None)  # Miss
        cache_manager.delete("key1")
        
        # Get metrics
        metrics = cache_manager.get_metrics()
        
        assert metrics["total_operations"] > 0
        assert metrics["hit_rate"] > 0
        assert "backend_stats" in metrics
        assert "memory" in metrics["backend_stats"]
    
    def test_async_cache_operations(self, cache_manager):
        """Test async cache operations"""
        import asyncio
        
        async def async_operation():
            # Set async
            await cache_manager.set_async("async_key", {"async": True})
            
            # Get async
            result = await cache_manager.get_async("async_key")
            return result
        
        # Run async operation
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(async_operation())
        loop.close()
        
        assert result["async"] is True
    
    def test_cache_namespace(self, cache_manager):
        """Test cache namespacing"""
        # Set in different namespaces
        cache_manager.set("key", "value1", namespace="app1")
        cache_manager.set("key", "value2", namespace="app2")
        
        # Get from different namespaces
        assert cache_manager.get("key", namespace="app1") == "value1"
        assert cache_manager.get("key", namespace="app2") == "value2"
    
    def test_cache_serialization_options(self, cache_manager):
        """Test different serialization options"""
        import pickle
        
        # JSON serialization (default)
        cache_manager.set("json_key", {"data": "value"})
        
        # Pickle serialization for complex objects
        complex_obj = {
            "function": lambda x: x * 2,
            "class": type("TestClass", (), {})
        }
        
        cache_manager.set(
            "pickle_key",
            complex_obj,
            serializer="pickle"
        )
        
        # Should handle both
        json_result = cache_manager.get("json_key")
        assert json_result["data"] == "value"
        
        pickle_result = cache_manager.get("pickle_key", serializer="pickle")
        assert callable(pickle_result["function"])
    
    def test_cache_versioning(self, cache_manager):
        """Test cache versioning for invalidation"""
        version = "v1"
        
        # Set with version
        cache_manager.set("api_response", {"data": "old"}, version=version)
        
        # Get with same version
        result = cache_manager.get("api_response", version=version)
        assert result["data"] == "old"
        
        # Get with different version - cache miss
        result = cache_manager.get("api_response", version="v2", default=None)
        assert result is None