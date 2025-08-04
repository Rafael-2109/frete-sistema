"""Cache Optimizer - Implements intelligent caching strategies."""

import time
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
import redis
import psycopg2
import pickle
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    size: int
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    @property
    def age(self) -> float:
        """Get age of cache entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    cache_size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'total_requests': self.total_requests,
            'hit_rate': self.hit_rate,
            'cache_size': self.cache_size,
            'max_size': self.max_size
        }


class CacheOptimizer:
    """Intelligent cache management system with multiple strategies."""
    
    def __init__(self, 
                 redis_config: Optional[Dict[str, Any]] = None,
                 max_memory_mb: int = 512,
                 default_ttl: int = 3600):
        self.redis_client = None
        if redis_config:
            self.redis_client = redis.Redis(**redis_config)
        
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.default_ttl = default_ttl
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats(max_size=self.max_memory)
        self.query_patterns: Dict[str, List[float]] = defaultdict(list)
        self.invalidation_rules: List[Callable] = []
    
    def _generate_key(self, query: str, params: Optional[Tuple] = None) -> str:
        """Generate a unique cache key for a query."""
        key_data = f"{query}:{params if params else ''}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate the size of an object in bytes."""
        try:
            return len(pickle.dumps(obj))
        except:
            return 1024  # Default size if serialization fails
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        self.stats.total_requests += 1
        
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    self.stats.hits += 1
                    return pickle.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Try memory cache
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not entry.is_expired:
                # Move to end (LRU)
                self.memory_cache.move_to_end(key)
                entry.accessed_at = datetime.now()
                entry.access_count += 1
                self.stats.hits += 1
                return entry.value
            else:
                # Remove expired entry
                del self.memory_cache[key]
        
        self.stats.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None):
        """Set value in cache with TTL and tags."""
        ttl = ttl or self.default_ttl
        size = self._estimate_size(value)
        
        # Store in Redis if available
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, pickle.dumps(value))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        # Store in memory cache
        entry = CacheEntry(
            key=key,
            value=value,
            size=size,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl=ttl,
            tags=tags or []
        )
        
        # Evict entries if necessary
        self._evict_if_needed(size)
        
        self.memory_cache[key] = entry
        self.stats.cache_size += size
    
    def _evict_if_needed(self, required_size: int):
        """Evict cache entries if memory limit exceeded."""
        while self.stats.cache_size + required_size > self.max_memory and self.memory_cache:
            # LRU eviction
            key, entry = self.memory_cache.popitem(last=False)
            self.stats.cache_size -= entry.size
            self.stats.evictions += 1
            
            # Also remove from Redis
            if self.redis_client:
                try:
                    self.redis_client.delete(key)
                except:
                    pass
    
    def invalidate_by_tags(self, tags: List[str]):
        """Invalidate all cache entries with specified tags."""
        keys_to_remove = []
        
        for key, entry in self.memory_cache.items():
            if any(tag in entry.tags for tag in tags):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            entry = self.memory_cache.pop(key)
            self.stats.cache_size -= entry.size
            
            if self.redis_client:
                try:
                    self.redis_client.delete(key)
                except:
                    pass
    
    def cache_query(self, ttl: Optional[int] = None, tags: Optional[List[str]] = None):
        """Decorator for caching database queries."""
        def decorator(func):
            @wraps(func)
            def wrapper(query: str, params: Optional[Tuple] = None, *args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(query, params)
                
                # Track query pattern
                pattern = self._extract_pattern(query)
                self.query_patterns[pattern].append(time.time())
                
                # Check cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute query
                result = func(query, params, *args, **kwargs)
                
                # Cache result
                self.set(cache_key, result, ttl=ttl, tags=tags)
                
                return result
            return wrapper
        return decorator
    
    def _extract_pattern(self, query: str) -> str:
        """Extract query pattern for analysis."""
        import re
        # Remove literals to get query pattern
        pattern = re.sub(r'\b\d+\b', '?', query)
        pattern = re.sub(r"\'[^\']*\'", '?', pattern)
        pattern = ' '.join(pattern.split())
        return pattern
    
    def analyze_cache_performance(self) -> Dict[str, Any]:
        """Analyze cache performance and provide recommendations."""
        analysis = {
            'stats': self.stats.to_dict(),
            'memory_usage': {
                'used_mb': self.stats.cache_size / (1024 * 1024),
                'max_mb': self.max_memory / (1024 * 1024),
                'usage_percent': (self.stats.cache_size / self.max_memory) * 100
            },
            'recommendations': []
        }
        
        # Analyze hit rate
        if self.stats.hit_rate < 0.5:
            analysis['recommendations'].append({
                'type': 'low_hit_rate',
                'message': f"Cache hit rate is {self.stats.hit_rate:.2%}. Consider adjusting TTL or cache size.",
                'severity': 'high'
            })
        
        # Analyze eviction rate
        if self.stats.evictions > self.stats.hits * 0.1:
            analysis['recommendations'].append({
                'type': 'high_evictions',
                'message': "High eviction rate detected. Consider increasing cache size.",
                'severity': 'medium'
            })
        
        # Analyze query patterns
        hot_patterns = self._identify_hot_patterns()
        if hot_patterns:
            analysis['hot_patterns'] = hot_patterns
            analysis['recommendations'].append({
                'type': 'hot_patterns',
                'message': f"Found {len(hot_patterns)} frequently accessed query patterns.",
                'severity': 'info'
            })
        
        return analysis
    
    def _identify_hot_patterns(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Identify frequently accessed query patterns."""
        hot_patterns = []
        current_time = time.time()
        
        for pattern, timestamps in self.query_patterns.items():
            # Count recent accesses (last hour)
            recent_accesses = [t for t in timestamps if current_time - t < 3600]
            
            if len(recent_accesses) >= threshold:
                hot_patterns.append({
                    'pattern': pattern,
                    'access_count': len(recent_accesses),
                    'avg_interval': self._calculate_avg_interval(recent_accesses)
                })
        
        return sorted(hot_patterns, key=lambda x: x['access_count'], reverse=True)
    
    def _calculate_avg_interval(self, timestamps: List[float]) -> float:
        """Calculate average interval between accesses."""
        if len(timestamps) < 2:
            return 0.0
        
        intervals = []
        for i in range(1, len(timestamps)):
            intervals.append(timestamps[i] - timestamps[i-1])
        
        return sum(intervals) / len(intervals)
    
    def optimize_ttl(self, pattern: str, target_hit_rate: float = 0.8) -> int:
        """Recommend optimal TTL for a query pattern."""
        timestamps = self.query_patterns.get(pattern, [])
        
        if len(timestamps) < 2:
            return self.default_ttl
        
        # Calculate access intervals
        intervals = []
        for i in range(1, len(timestamps)):
            intervals.append(timestamps[i] - timestamps[i-1])
        
        # Use percentile to determine TTL
        intervals.sort()
        percentile_index = int(len(intervals) * target_hit_rate)
        recommended_ttl = int(intervals[percentile_index]) if percentile_index < len(intervals) else self.default_ttl
        
        # Apply bounds
        return max(60, min(recommended_ttl, 86400))  # Between 1 minute and 24 hours
    
    def create_cache_warmer(self, db_connection_params: Dict[str, str]):
        """Create a cache warmer for pre-loading frequently accessed data."""
        def warm_cache():
            """Pre-load frequently accessed data into cache."""
            conn = psycopg2.connect(**db_connection_params)
            cursor = conn.cursor()
            
            # Get hot patterns
            hot_patterns = self._identify_hot_patterns()
            
            for pattern_info in hot_patterns[:10]:  # Top 10 patterns
                pattern = pattern_info['pattern']
                
                # Skip if pattern has parameters
                if '?' in pattern:
                    continue
                
                try:
                    # Execute query
                    cursor.execute(pattern)
                    result = cursor.fetchall()
                    
                    # Cache result with optimized TTL
                    cache_key = self._generate_key(pattern)
                    optimal_ttl = self.optimize_ttl(pattern)
                    self.set(cache_key, result, ttl=optimal_ttl)
                    
                    logger.info(f"Warmed cache for pattern: {pattern[:50]}...")
                except Exception as e:
                    logger.error(f"Error warming cache for pattern: {e}")
            
            cursor.close()
            conn.close()
        
        return warm_cache
    
    def get_cache_report(self) -> str:
        """Generate a detailed cache performance report."""
        analysis = self.analyze_cache_performance()
        
        report = [
            "Cache Performance Report",
            "=" * 50,
            f"\nCache Statistics:",
            f"  Hit Rate: {self.stats.hit_rate:.2%}",
            f"  Total Requests: {self.stats.total_requests:,}",
            f"  Hits: {self.stats.hits:,}",
            f"  Misses: {self.stats.misses:,}",
            f"  Evictions: {self.stats.evictions:,}",
            f"\nMemory Usage:",
            f"  Used: {analysis['memory_usage']['used_mb']:.2f} MB",
            f"  Max: {analysis['memory_usage']['max_mb']:.2f} MB",
            f"  Usage: {analysis['memory_usage']['usage_percent']:.1f}%",
        ]
        
        if analysis.get('hot_patterns'):
            report.append("\nHot Query Patterns:")
            for i, pattern in enumerate(analysis['hot_patterns'][:5], 1):
                report.append(f"  {i}. {pattern['pattern'][:60]}...")
                report.append(f"     Accesses: {pattern['access_count']}, Avg Interval: {pattern['avg_interval']:.1f}s")
        
        if analysis['recommendations']:
            report.append("\nRecommendations:")
            for rec in analysis['recommendations']:
                report.append(f"  [{rec['severity'].upper()}] {rec['message']}")
        
        return "\n".join(report)


class QueryCacheMiddleware:
    """Middleware for automatic query caching."""
    
    def __init__(self, cache_optimizer: CacheOptimizer):
        self.cache = cache_optimizer
    
    def execute_query(self, conn, query: str, params: Optional[Tuple] = None, 
                     cache_ttl: Optional[int] = None, cache_tags: Optional[List[str]] = None):
        """Execute query with automatic caching."""
        # Check if query should be cached
        if self._should_cache(query):
            cache_key = self.cache._generate_key(query, params)
            
            # Try cache first
            result = self.cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute query
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            
            # Cache result
            self.cache.set(cache_key, result, ttl=cache_ttl, tags=cache_tags)
            
            return result
        else:
            # Execute without caching
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
    
    def _should_cache(self, query: str) -> bool:
        """Determine if a query should be cached."""
        query_upper = query.upper().strip()
        
        # Don't cache write operations
        if any(query_upper.startswith(op) for op in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']):
            return False
        
        # Don't cache transactions
        if any(word in query_upper for word in ['BEGIN', 'COMMIT', 'ROLLBACK']):
            return False
        
        return True


if __name__ == "__main__":
    # Example usage
    cache = CacheOptimizer(
        redis_config={'host': 'localhost', 'port': 6379, 'db': 0},
        max_memory_mb=256,
        default_ttl=1800
    )
    
    # Simulate some cache operations
    for i in range(100):
        key = f"query_{i % 10}"
        if i % 3 == 0:
            cache.set(key, f"result_{i}", tags=['table_users'])
        else:
            cache.get(key)
    
    # Print performance report
    print(cache.get_cache_report())