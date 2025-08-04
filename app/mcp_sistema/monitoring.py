"""
Monitoring and metrics collection for MCP Sistema Frete.

Provides real-time metrics collection, performance tracking,
and system monitoring capabilities.
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import threading

import psutil
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, generate_latest
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and manage application metrics."""
    
    def __init__(self, retention_minutes: int = 60):
        self.retention_minutes = retention_minutes
        self.metrics = defaultdict(lambda: deque(maxlen=retention_minutes * 60))
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = threading.Lock()
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()
        
        # Start background cleanup
        self._start_cleanup_task()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics collectors."""
        # Request metrics
        self.request_count = Counter(
            'mcp_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'mcp_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_query_count = Counter(
            'mcp_db_queries_total',
            'Total number of database queries',
            ['operation'],
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'mcp_db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        self.db_connection_pool = Gauge(
            'mcp_db_connection_pool_size',
            'Database connection pool metrics',
            ['state'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations = Counter(
            'mcp_cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'mcp_cache_hit_rate',
            'Cache hit rate percentage',
            registry=self.registry
        )
        
        # System metrics
        self.cpu_usage = Gauge(
            'mcp_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'mcp_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        # Business metrics
        self.freight_calculations = Counter(
            'mcp_freight_calculations_total',
            'Total freight calculations',
            ['status'],
            registry=self.registry
        )
        
        self.active_shipments = Gauge(
            'mcp_active_shipments',
            'Number of active shipments',
            registry=self.registry
        )
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment a counter metric."""
        with self.lock:
            self.counters[name] += value
            
            # Update Prometheus counter if mapped
            if name == 'requests' and labels:
                self.request_count.labels(**labels).inc(value)
            elif name == 'db_queries' and labels:
                self.db_query_count.labels(**labels).inc(value)
            elif name == 'cache_operations' and labels:
                self.cache_operations.labels(**labels).inc(value)
            elif name == 'freight_calculations' and labels:
                self.freight_calculations.labels(**labels).inc(value)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge metric."""
        with self.lock:
            self.gauges[name] = value
            
            # Update Prometheus gauge if mapped
            if name == 'cache_hit_rate':
                self.cache_hit_rate.set(value)
            elif name == 'active_shipments':
                self.active_shipments.set(value)
            elif name == 'cpu_usage':
                self.cpu_usage.set(value)
            elif name == 'memory_usage' and labels:
                self.memory_usage.labels(**labels).set(value)
            elif name == 'db_pool' and labels:
                self.db_connection_pool.labels(**labels).set(value)
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record a histogram metric."""
        with self.lock:
            if name not in self.histograms:
                self.histograms[name] = []
            self.histograms[name].append(value)
            
            # Keep only recent values
            if len(self.histograms[name]) > 10000:
                self.histograms[name] = self.histograms[name][-5000:]
            
            # Update Prometheus histogram if mapped
            if name == 'request_duration' and labels:
                self.request_duration.labels(**labels).observe(value)
            elif name == 'db_query_duration' and labels:
                self.db_query_duration.labels(**labels).observe(value)
    
    @contextmanager
    def timer(self, name: str, labels: Optional[Dict] = None):
        """Context manager to time operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram(name, duration, labels)
    
    def record_event(self, event_type: str, data: Dict[str, Any]):
        """Record a timestamped event."""
        timestamp = datetime.utcnow()
        with self.lock:
            self.metrics[event_type].append({
                'timestamp': timestamp,
                'data': data
            })
    
    def get_counter(self, name: str) -> int:
        """Get current counter value."""
        with self.lock:
            return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Get current gauge value."""
        with self.lock:
            return self.gauges.get(name, 0.0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        with self.lock:
            values = self.histograms.get(name, [])
            if not values:
                return {
                    'count': 0,
                    'mean': 0,
                    'min': 0,
                    'max': 0,
                    'p50': 0,
                    'p95': 0,
                    'p99': 0
                }
            
            sorted_values = sorted(values)
            count = len(sorted_values)
            
            return {
                'count': count,
                'mean': sum(sorted_values) / count,
                'min': sorted_values[0],
                'max': sorted_values[-1],
                'p50': sorted_values[int(count * 0.5)],
                'p95': sorted_values[int(count * 0.95)],
                'p99': sorted_values[int(count * 0.99)]
            }
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        # Collect system metrics
        self._update_system_metrics()
        
        # Calculate derived metrics
        total_requests = self.get_counter('requests')
        failed_requests = self.get_counter('failed_requests')
        success_rate = ((total_requests - failed_requests) / total_requests * 100) if total_requests > 0 else 100
        
        request_stats = self.get_histogram_stats('request_duration')
        db_stats = self.get_histogram_stats('db_query_duration')
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'requests': {
                'total': total_requests,
                'failed': failed_requests,
                'success_rate': round(success_rate, 2),
                'avg_duration_ms': round(request_stats['mean'] * 1000, 2),
                'p95_duration_ms': round(request_stats['p95'] * 1000, 2),
                'p99_duration_ms': round(request_stats['p99'] * 1000, 2)
            },
            'database': {
                'queries': self.get_counter('db_queries'),
                'avg_duration_ms': round(db_stats['mean'] * 1000, 2),
                'p95_duration_ms': round(db_stats['p95'] * 1000, 2),
                'connection_pool': {
                    'active': self.get_gauge('db_pool_active'),
                    'idle': self.get_gauge('db_pool_idle'),
                    'total': self.get_gauge('db_pool_total')
                }
            },
            'cache': {
                'operations': self.get_counter('cache_operations'),
                'hits': self.get_counter('cache_hits'),
                'misses': self.get_counter('cache_misses'),
                'hit_rate': round(self.get_gauge('cache_hit_rate'), 2)
            },
            'system': {
                'cpu_usage': round(self.get_gauge('cpu_usage'), 2),
                'memory_usage_mb': round(self.get_gauge('memory_usage') / (1024 * 1024), 2),
                'active_connections': self.get_gauge('active_connections')
            },
            'business': {
                'freight_calculations': self.get_counter('freight_calculations'),
                'active_shipments': int(self.get_gauge('active_shipments'))
            }
        }
    
    def _update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.set_gauge('cpu_usage', cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.set_gauge('memory_usage', memory.used, {'type': 'used'})
            self.set_gauge('memory_available', memory.available, {'type': 'available'})
            
            # Network connections
            connections = len(psutil.net_connections())
            self.set_gauge('active_connections', connections)
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def get_prometheus_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()
    
    def get_final_metrics(self) -> Dict[str, Any]:
        """Get final metrics for shutdown."""
        return {
            'shutdown_time': self.get_current_timestamp(),
            'total_requests': self.get_counter('requests'),
            'total_errors': self.get_counter('failed_requests'),
            'final_snapshot': asyncio.run(self.get_current_metrics())
        }
    
    def _start_cleanup_task(self):
        """Start background task to clean old metrics."""
        def cleanup():
            while True:
                time.sleep(300)  # Every 5 minutes
                self._cleanup_old_metrics()
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
        
        with self.lock:
            for event_type, events in self.metrics.items():
                # Remove old events
                while events and events[0]['timestamp'] < cutoff_time:
                    events.popleft()


class PerformanceMonitor:
    """Monitor application performance."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.slow_query_threshold = 1.0  # seconds
        self.slow_request_threshold = 2.0  # seconds
    
    async def monitor_request(self, request_info: Dict[str, Any]):
        """Monitor a request."""
        duration = request_info.get('duration', 0)
        
        # Record metrics
        self.metrics.increment_counter('requests', labels={
            'method': request_info.get('method', 'GET'),
            'endpoint': request_info.get('endpoint', '/'),
            'status': request_info.get('status', 200)
        })
        
        self.metrics.record_histogram('request_duration', duration, labels={
            'method': request_info.get('method', 'GET'),
            'endpoint': request_info.get('endpoint', '/')
        })
        
        # Check for slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request_info.get('method')} "
                f"{request_info.get('endpoint')} took {duration:.2f}s"
            )
            self.metrics.increment_counter('slow_requests')
        
        # Track errors
        if request_info.get('status', 200) >= 400:
            self.metrics.increment_counter('failed_requests')
    
    async def monitor_database_query(self, query_info: Dict[str, Any]):
        """Monitor a database query."""
        duration = query_info.get('duration', 0)
        
        # Record metrics
        self.metrics.increment_counter('db_queries', labels={
            'operation': query_info.get('operation', 'select')
        })
        
        self.metrics.record_histogram('db_query_duration', duration, labels={
            'operation': query_info.get('operation', 'select')
        })
        
        # Check for slow queries
        if duration > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected: {query_info.get('operation')} "
                f"took {duration:.2f}s"
            )
            self.metrics.increment_counter('slow_queries')
    
    async def monitor_cache_operation(self, operation: str, hit: bool):
        """Monitor cache operations."""
        self.metrics.increment_counter('cache_operations', labels={
            'operation': operation,
            'result': 'hit' if hit else 'miss'
        })
        
        if hit:
            self.metrics.increment_counter('cache_hits')
        else:
            self.metrics.increment_counter('cache_misses')
        
        # Update hit rate
        total_ops = self.metrics.get_counter('cache_hits') + self.metrics.get_counter('cache_misses')
        if total_ops > 0:
            hit_rate = self.metrics.get_counter('cache_hits') / total_ops * 100
            self.metrics.set_gauge('cache_hit_rate', hit_rate)


# Global instances
_metrics_collector = None
_performance_monitor = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(get_metrics_collector())
    return _performance_monitor


# Convenience functions
def start_monitoring():
    """Initialize monitoring systems."""
    collector = get_metrics_collector()
    monitor = get_performance_monitor()
    logger.info("Monitoring systems initialized")
    return collector, monitor


def stop_monitoring():
    """Stop monitoring systems."""
    if _metrics_collector:
        final_metrics = _metrics_collector.get_final_metrics()
        logger.info(f"Final metrics: {final_metrics}")
    
    logger.info("Monitoring systems stopped")