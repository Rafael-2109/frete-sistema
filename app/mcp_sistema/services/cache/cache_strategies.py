"""
Cache strategies for different use cases in MCP Sistema
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import heapq
from collections import OrderedDict, defaultdict
import structlog

logger = structlog.get_logger(__name__)


class CacheStrategy(ABC):
    """Abstract base class for cache strategies"""
    
    @abstractmethod
    def should_cache(self, key: str, value: Any) -> bool:
        """Determine if value should be cached"""
        pass
    
    @abstractmethod
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Get TTL for cache entry"""
        pass
    
    @abstractmethod
    def on_hit(self, key: str):
        """Called when cache hit occurs"""
        pass
    
    @abstractmethod
    def on_miss(self, key: str):
        """Called when cache miss occurs"""
        pass
    
    @abstractmethod
    def should_evict(self, key: str) -> bool:
        """Determine if key should be evicted"""
        pass


class TTLStrategy(CacheStrategy):
    """
    Time-based caching strategy with configurable TTL per pattern
    """
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self.ttl_patterns = {
            'query:*': 300,      # 5 minutes for queries
            'resource:*': 600,   # 10 minutes for resources
            'analysis:*': 1800,  # 30 minutes for analysis results
            'ml:*': 3600,        # 1 hour for ML predictions
            'static:*': 86400,   # 24 hours for static data
            'session:*': 1800,   # 30 minutes for sessions
            'temp:*': 60         # 1 minute for temporary data
        }
        self.access_times: Dict[str, datetime] = {}
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache based on key pattern and value size"""
        # Don't cache very large values (>10MB)
        if hasattr(value, '__sizeof__') and value.__sizeof__() > 10 * 1024 * 1024:
            return False
        
        # Don't cache None or empty values
        if value is None or (hasattr(value, '__len__') and len(value) == 0):
            return False
        
        return True
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Get TTL based on key pattern"""
        for pattern, ttl in self.ttl_patterns.items():
            if self._matches_pattern(key, pattern):
                return ttl
        return self.default_ttl
    
    def on_hit(self, key: str):
        """Update access time on hit"""
        self.access_times[key] = datetime.now()
    
    def on_miss(self, key: str):
        """Log miss for analysis"""
        logger.debug("Cache miss", key=key)
    
    def should_evict(self, key: str) -> bool:
        """Evict if not accessed recently"""
        if key not in self.access_times:
            return False
        
        last_access = self.access_times[key]
        inactive_time = datetime.now() - last_access
        
        # Evict if inactive for more than 2x the TTL
        ttl = self.get_ttl(key, None)
        return inactive_time.total_seconds() > (ttl * 2)
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching"""
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        return key == pattern


class LRUStrategy(CacheStrategy):
    """
    Least Recently Used caching strategy
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache_order = OrderedDict()
        self.cache_sizes: Dict[str, int] = {}
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache if under size limit"""
        value_size = self._estimate_size(value)
        
        # Check if we need to evict items
        current_size = sum(self.cache_sizes.values())
        if current_size + value_size > self.max_size * 1024 * 1024:  # MB to bytes
            # Would need to evict items
            return len(self.cache_order) < self.max_size
        
        return True
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Fixed TTL for LRU"""
        return self.default_ttl
    
    def on_hit(self, key: str):
        """Move to end (most recently used)"""
        if key in self.cache_order:
            self.cache_order.move_to_end(key)
    
    def on_miss(self, key: str):
        """Add to cache order"""
        self.cache_order[key] = datetime.now()
    
    def should_evict(self, key: str) -> bool:
        """Evict least recently used when at capacity"""
        if len(self.cache_order) >= self.max_size:
            # Get least recently used key
            lru_key = next(iter(self.cache_order))
            return key == lru_key
        return False
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """Get keys to evict"""
        return list(self.cache_order.keys())[:count]
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate object size in bytes"""
        if hasattr(value, '__sizeof__'):
            return value.__sizeof__()
        elif isinstance(value, (str, bytes)):
            return len(value)
        elif isinstance(value, (list, tuple)):
            return sum(self._estimate_size(item) for item in value)
        elif isinstance(value, dict):
            return sum(self._estimate_size(k) + self._estimate_size(v) 
                      for k, v in value.items())
        else:
            return 1024  # Default 1KB


class FIFOStrategy(CacheStrategy):
    """
    First In First Out caching strategy
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.queue: List[Tuple[datetime, str]] = []
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache if under size limit"""
        return len(self.queue) < self.max_size
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Fixed TTL for FIFO"""
        return self.default_ttl
    
    def on_hit(self, key: str):
        """No action on hit for FIFO"""
        pass
    
    def on_miss(self, key: str):
        """Add to queue"""
        heapq.heappush(self.queue, (datetime.now(), key))
    
    def should_evict(self, key: str) -> bool:
        """Evict oldest entry when at capacity"""
        if len(self.queue) >= self.max_size and self.queue:
            oldest_time, oldest_key = self.queue[0]
            return key == oldest_key
        return False
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """Get oldest keys"""
        candidates = []
        for i in range(min(count, len(self.queue))):
            if i < len(self.queue):
                candidates.append(self.queue[i][1])
        return candidates


class AdaptiveTTLStrategy(CacheStrategy):
    """
    Adaptive TTL strategy that adjusts based on access patterns
    """
    def __init__(self, min_ttl: int = 60, max_ttl: int = 3600):
        self.min_ttl = min_ttl
        self.max_ttl = max_ttl
        self.access_counts: Dict[str, int] = defaultdict(int)
        self.last_access: Dict[str, datetime] = {}
        self.ttl_history: Dict[str, List[int]] = defaultdict(list)
        self.hit_rates: Dict[str, float] = defaultdict(float)
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Cache based on predicted value"""
        # Always cache first time
        if key not in self.access_counts:
            return True
        
        # Cache if hit rate is good
        hit_rate = self.hit_rates.get(key, 0)
        return hit_rate > 0.3  # 30% hit rate threshold
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Adaptive TTL based on access patterns"""
        access_count = self.access_counts[key]
        
        if access_count == 0:
            # First time, use minimum TTL
            ttl = self.min_ttl
        else:
            # Calculate based on access frequency
            if key in self.last_access:
                time_since_last = (datetime.now() - self.last_access[key]).total_seconds()
                
                # More frequent access = longer TTL
                if time_since_last < 60:  # Accessed within 1 minute
                    ttl = min(self.max_ttl, self.min_ttl * 10)
                elif time_since_last < 300:  # Accessed within 5 minutes
                    ttl = min(self.max_ttl, self.min_ttl * 5)
                else:
                    ttl = self.min_ttl
            else:
                ttl = self.min_ttl
        
        # Store TTL history for analysis
        self.ttl_history[key].append(ttl)
        if len(self.ttl_history[key]) > 10:
            self.ttl_history[key].pop(0)
        
        return ttl
    
    def on_hit(self, key: str):
        """Update access patterns on hit"""
        self.access_counts[key] += 1
        self.last_access[key] = datetime.now()
        
        # Update hit rate
        total_requests = self.access_counts[key]
        hits = total_requests * self.hit_rates.get(key, 0) + 1
        self.hit_rates[key] = hits / total_requests
        
        logger.debug("Cache hit", key=key, 
                    access_count=self.access_counts[key],
                    hit_rate=self.hit_rates[key])
    
    def on_miss(self, key: str):
        """Update miss statistics"""
        if key in self.access_counts:
            total_requests = self.access_counts[key] + 1
            hits = total_requests * self.hit_rates.get(key, 0)
            self.hit_rates[key] = hits / total_requests
    
    def should_evict(self, key: str) -> bool:
        """Evict based on predicted value"""
        # Evict if hit rate is very low
        if self.hit_rates.get(key, 1) < 0.1:  # Less than 10% hit rate
            return True
        
        # Evict if not accessed recently
        if key in self.last_access:
            time_since_last = (datetime.now() - self.last_access[key]).total_seconds()
            avg_ttl = sum(self.ttl_history.get(key, [self.min_ttl])) / len(self.ttl_history.get(key, [1]))
            return time_since_last > avg_ttl * 3
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'total_keys': len(self.access_counts),
            'avg_hit_rate': sum(self.hit_rates.values()) / max(1, len(self.hit_rates)),
            'most_accessed': sorted(self.access_counts.items(), 
                                  key=lambda x: x[1], reverse=True)[:10],
            'best_hit_rates': sorted(self.hit_rates.items(), 
                                   key=lambda x: x[1], reverse=True)[:10]
        }


class HybridStrategy(CacheStrategy):
    """
    Hybrid strategy combining multiple strategies based on key patterns
    """
    def __init__(self):
        self.strategies = {
            'query': AdaptiveTTLStrategy(),
            'resource': TTLStrategy(default_ttl=600),
            'ml': LRUStrategy(max_size=100, default_ttl=3600),
            'session': TTLStrategy(default_ttl=1800),
            'default': TTLStrategy(default_ttl=300)
        }
    
    def _get_strategy(self, key: str) -> CacheStrategy:
        """Get appropriate strategy based on key prefix"""
        prefix = key.split(':')[0] if ':' in key else 'default'
        return self.strategies.get(prefix, self.strategies['default'])
    
    def should_cache(self, key: str, value: Any) -> bool:
        """Delegate to appropriate strategy"""
        return self._get_strategy(key).should_cache(key, value)
    
    def get_ttl(self, key: str, value: Any) -> Optional[int]:
        """Delegate to appropriate strategy"""
        return self._get_strategy(key).get_ttl(key, value)
    
    def on_hit(self, key: str):
        """Delegate to appropriate strategy"""
        self._get_strategy(key).on_hit(key)
    
    def on_miss(self, key: str):
        """Delegate to appropriate strategy"""
        self._get_strategy(key).on_miss(key)
    
    def should_evict(self, key: str) -> bool:
        """Delegate to appropriate strategy"""
        return self._get_strategy(key).should_evict(key)