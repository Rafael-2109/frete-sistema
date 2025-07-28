"""
Performance utilities for MCP Sistema
"""
import time
import asyncio
import functools
import psutil
import threading
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
import structlog
from contextlib import contextmanager
import tracemalloc

logger = structlog.get_logger(__name__)


def measure_time(func: Callable) -> Callable:
    """Decorator to measure function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.info("Function executed", 
                       function=func.__name__,
                       duration_ms=round(elapsed * 1000, 2))
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error("Function failed",
                        function=func.__name__,
                        duration_ms=round(elapsed * 1000, 2),
                        error=str(e))
            raise
    return wrapper


def async_measure_time(func: Callable) -> Callable:
    """Decorator to measure async function execution time"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.info("Async function executed",
                       function=func.__name__,
                       duration_ms=round(elapsed * 1000, 2))
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error("Async function failed",
                        function=func.__name__,
                        duration_ms=round(elapsed * 1000, 2),
                        error=str(e))
            raise
    return wrapper


def profile_memory(func: Callable) -> Callable:
    """Decorator to profile memory usage"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = func(*args, **kwargs)
            
            # Get memory stats
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            logger.info("Memory profile",
                       function=func.__name__,
                       current_mb=round(current / 1024 / 1024, 2),
                       peak_mb=round(peak / 1024 / 1024, 2),
                       delta_mb=round(final_memory - initial_memory, 2))
            
            return result
        except Exception as e:
            tracemalloc.stop()
            logger.error("Function failed", function=func.__name__, error=str(e))
            raise
    
    return wrapper


def log_performance(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to log custom performance metrics"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            # Get system metrics before
            process = psutil.Process()
            cpu_before = process.cpu_percent()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            try:
                result = func(*args, **kwargs)
                
                # Calculate metrics
                elapsed = time.perf_counter() - start_time
                cpu_after = process.cpu_percent()
                memory_after = process.memory_info().rss / 1024 / 1024
                
                metrics = {
                    'duration_ms': round(elapsed * 1000, 2),
                    'cpu_usage': round((cpu_after + cpu_before) / 2, 2),
                    'memory_delta_mb': round(memory_after - memory_before, 2),
                    'function': func.__name__,
                    'metric': metric_name
                }
                
                if labels:
                    metrics.update(labels)
                
                logger.info("Performance metric", **metrics)
                
                # Store in performance monitor
                PerformanceMonitor.instance().record_metric(metric_name, elapsed, labels)
                
                return result
                
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error("Performance metric error",
                           metric=metric_name,
                           function=func.__name__,
                           duration_ms=round(elapsed * 1000, 2),
                           error=str(e))
                raise
        
        return wrapper
    return decorator


class PerformanceMonitor:
    """Singleton performance monitoring system"""
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self._start_time = time.time()
    
    @classmethod
    def instance(cls):
        """Get singleton instance"""
        return cls()
    
    def record_metric(self, name: str, value: float, 
                     labels: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        entry = {
            'timestamp': datetime.now(),
            'value': value,
            'labels': labels or {}
        }
        self.metrics[name].append(entry)
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter"""
        self.counters[name] += value
    
    def set_gauge(self, name: str, value: float):
        """Set a gauge value"""
        self.gauges[name] = value
    
    def get_stats(self, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if metric_name:
            if metric_name not in self.metrics:
                return {}
            
            values = [entry['value'] for entry in self.metrics[metric_name]]
            if not values:
                return {}
            
            return {
                'name': metric_name,
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'last': values[-1] if values else None,
                'last_timestamp': self.metrics[metric_name][-1]['timestamp'] if self.metrics[metric_name] else None
            }
        
        # Get all stats
        stats = {
            'uptime_seconds': time.time() - self._start_time,
            'metrics': {},
            'counters': dict(self.counters),
            'gauges': dict(self.gauges)
        }
        
        for name, entries in self.metrics.items():
            values = [entry['value'] for entry in entries]
            if values:
                stats['metrics'][name] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'last': values[-1]
                }
        
        return stats
    
    def get_recent_metrics(self, metric_name: str, 
                          seconds: int = 60) -> List[Dict[str, Any]]:
        """Get recent metric values"""
        cutoff = datetime.now() - timedelta(seconds=seconds)
        return [
            entry for entry in self.metrics.get(metric_name, [])
            if entry['timestamp'] >= cutoff
        ]
    
    def reset(self, metric_name: Optional[str] = None):
        """Reset metrics"""
        if metric_name:
            if metric_name in self.metrics:
                self.metrics[metric_name].clear()
            if metric_name in self.counters:
                self.counters[metric_name] = 0
            if metric_name in self.gauges:
                del self.gauges[metric_name]
        else:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()


class BatchProcessor:
    """Process items in batches for better performance"""
    
    def __init__(self, batch_size: int = 100, 
                 flush_interval: float = 1.0,
                 processor: Optional[Callable] = None):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.processor = processor
        self.items: List[Any] = []
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._closed = False
    
    def add(self, item: Any):
        """Add item to batch"""
        if self._closed:
            raise RuntimeError("BatchProcessor is closed")
        
        with self._lock:
            self.items.append(item)
            
            if len(self.items) >= self.batch_size:
                self._flush()
            elif self._timer is None:
                self._schedule_flush()
    
    def _schedule_flush(self):
        """Schedule automatic flush"""
        if self._timer:
            self._timer.cancel()
        
        self._timer = threading.Timer(self.flush_interval, self._flush)
        self._timer.start()
    
    def _flush(self):
        """Flush current batch"""
        with self._lock:
            if not self.items:
                return
            
            batch = self.items[:]
            self.items.clear()
            
            if self._timer:
                self._timer.cancel()
                self._timer = None
        
        # Process batch
        if self.processor:
            try:
                self.processor(batch)
            except Exception as e:
                logger.error("Batch processing failed", 
                           batch_size=len(batch), 
                           error=str(e))
    
    def flush(self):
        """Manually flush current batch"""
        self._flush()
    
    def close(self):
        """Close processor and flush remaining items"""
        self._closed = True
        
        if self._timer:
            self._timer.cancel()
            self._timer = None
        
        self._flush()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


@contextmanager
def performance_context(name: str, log_threshold_ms: float = 100):
    """Context manager for performance monitoring"""
    start_time = time.perf_counter()
    monitor = PerformanceMonitor.instance()
    
    # Get initial system state
    process = psutil.Process()
    initial_cpu = process.cpu_percent()
    initial_memory = process.memory_info().rss / 1024 / 1024
    
    try:
        yield monitor
    finally:
        # Calculate metrics
        elapsed = time.perf_counter() - start_time
        elapsed_ms = elapsed * 1000
        
        final_cpu = process.cpu_percent()
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Record metrics
        monitor.record_metric(f"{name}_duration", elapsed)
        monitor.increment_counter(f"{name}_count")
        
        # Log if above threshold
        if elapsed_ms > log_threshold_ms:
            logger.warning("Slow operation detected",
                         operation=name,
                         duration_ms=round(elapsed_ms, 2),
                         cpu_avg=round((initial_cpu + final_cpu) / 2, 2),
                         memory_delta_mb=round(final_memory - initial_memory, 2))
        else:
            logger.debug("Operation completed",
                        operation=name,
                        duration_ms=round(elapsed_ms, 2))


# Usage examples:
# 
# @measure_time
# def slow_function():
#     time.sleep(1)
#
# @profile_memory
# def memory_intensive():
#     data = [i for i in range(1000000)]
#     return sum(data)
#
# @log_performance("api_call", labels={"endpoint": "/users"})
# def api_handler():
#     # Handle API request
#     pass
#
# with performance_context("database_query") as monitor:
#     # Perform database operations
#     monitor.increment_counter("queries_executed", 5)
#
# # Batch processing
# def process_batch(items):
#     print(f"Processing {len(items)} items")
#
# with BatchProcessor(batch_size=50, processor=process_batch) as processor:
#     for i in range(200):
#         processor.add(f"item_{i}")