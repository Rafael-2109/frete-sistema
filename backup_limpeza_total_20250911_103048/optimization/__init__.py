"""Database Performance Optimization Module."""

from .query_analyzer import QueryAnalyzer, QueryStats
from .index_optimizer import IndexOptimizer, IndexRecommendation
from .cache_optimizer import CacheOptimizer, CacheEntry, CacheStats, QueryCacheMiddleware
from .connection_pool_optimizer import ConnectionPoolOptimizer, ConnectionStats, PoolMetrics
from .performance_dashboard import PerformanceDashboard

__version__ = '1.0.0'
__author__ = 'Database Performance Analyst'

__all__ = [
    'QueryAnalyzer',
    'QueryStats',
    'IndexOptimizer', 
    'IndexRecommendation',
    'CacheOptimizer',
    'CacheEntry',
    'CacheStats',
    'QueryCacheMiddleware',
    'ConnectionPoolOptimizer',
    'ConnectionStats',
    'PoolMetrics',
    'PerformanceDashboard'
]