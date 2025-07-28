"""
Monitoring and metrics collection for MCP Sistema
"""
import time
import psutil
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from functools import wraps

from .logging import get_logger, PerformanceLogger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Base metric class"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "labels": self.labels
        }


class MetricsCollector:
    """
    Centralized metrics collector
    """
    
    def __init__(self, flush_interval: int = 60):
        """
        Initialize metrics collector
        
        Args:
            flush_interval: Seconds between metric flushes
        """
        self.flush_interval = flush_interval
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
        self._running = False
        self._flush_thread = None
        self._metrics_queue = queue.Queue()
        
    def start(self):
        """Start metrics collection"""
        if self._running:
            return
            
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        logger.info("Metrics collector started")
        
    def stop(self):
        """Stop metrics collection"""
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
        logger.info("Metrics collector stopped")
        
    def _flush_loop(self):
        """Background thread for flushing metrics"""
        while self._running:
            try:
                time.sleep(self.flush_interval)
                self.flush()
            except Exception as e:
                logger.error(f"Error in metrics flush loop: {e}")
                
    def increment(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            
            metric = Metric(
                name=name,
                type=MetricType.COUNTER,
                value=self.counters[key],
                timestamp=datetime.utcnow(),
                labels=labels or {}
            )
            self.metrics[name].append(metric)
            
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            
            metric = Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {}
            )
            self.metrics[name].append(metric)
            
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a value to histogram"""
        with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            
            # Keep only last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
                
            metric = Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {}
            )
            self.metrics[name].append(metric)
            
    def timing(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Record timing metric"""
        self.histogram(name, duration_ms, labels)
        
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create unique key for metric"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
        
    def get_metrics(self, name: Optional[str] = None) -> List[Metric]:
        """Get collected metrics"""
        with self._lock:
            if name:
                return list(self.metrics.get(name, []))
            
            all_metrics = []
            for metric_list in self.metrics.values():
                all_metrics.extend(metric_list)
            return all_metrics
            
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        with self._lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {}
            }
            
            # Calculate histogram summaries
            for key, values in self.histograms.items():
                if values:
                    sorted_values = sorted(values)
                    summary["histograms"][key] = {
                        "count": len(values),
                        "min": sorted_values[0],
                        "max": sorted_values[-1],
                        "mean": sum(values) / len(values),
                        "p50": sorted_values[len(values) // 2],
                        "p95": sorted_values[int(len(values) * 0.95)],
                        "p99": sorted_values[int(len(values) * 0.99)]
                    }
                    
            return summary
            
    def flush(self):
        """Flush metrics to storage/external system"""
        try:
            metrics = self.get_metrics()
            if metrics:
                logger.info(
                    "Flushing metrics",
                    extra={
                        "metric_count": len(metrics),
                        "summary": self.get_summary()
                    }
                )
                # Here you would send metrics to monitoring system
                # For now, we just log them
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")


class SystemMonitor:
    """
    System resource monitor
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self._running = False
        self._monitor_thread = None
        
    def start(self, interval: int = 30):
        """Start system monitoring"""
        if self._running:
            return
            
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("System monitor started")
        
    def stop(self):
        """Stop system monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("System monitor stopped")
        
    def _monitor_loop(self, interval: int):
        """Background monitoring loop"""
        while self._running:
            try:
                self.collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in system monitor: {e}")
                
    def collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.collector.gauge("system.cpu.usage", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.collector.gauge("system.memory.usage", memory.percent)
            self.collector.gauge("system.memory.available", memory.available)
            self.collector.gauge("system.memory.total", memory.total)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.collector.gauge("system.disk.usage", disk.percent)
            self.collector.gauge("system.disk.free", disk.free)
            self.collector.gauge("system.disk.total", disk.total)
            
            # Process metrics
            process = psutil.Process()
            self.collector.gauge("process.cpu.usage", process.cpu_percent())
            self.collector.gauge("process.memory.rss", process.memory_info().rss)
            self.collector.gauge("process.threads", process.num_threads())
            
            # Network metrics (if available)
            try:
                net_io = psutil.net_io_counters()
                self.collector.gauge("system.network.bytes_sent", net_io.bytes_sent)
                self.collector.gauge("system.network.bytes_recv", net_io.bytes_recv)
                self.collector.gauge("system.network.packets_sent", net_io.packets_sent)
                self.collector.gauge("system.network.packets_recv", net_io.packets_recv)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")


class MCPMetrics:
    """
    MCP-specific metrics
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        
    def track_tool_execution(self, tool_name: str):
        """Track tool execution"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                labels = {"tool": tool_name}
                
                self.collector.increment("mcp.tool.calls", labels=labels)
                
                try:
                    result = await func(*args, **kwargs)
                    self.collector.increment("mcp.tool.success", labels=labels)
                    return result
                except Exception as e:
                    self.collector.increment("mcp.tool.errors", labels=labels)
                    self.collector.increment(
                        "mcp.tool.errors_by_type",
                        labels={**labels, "error_type": type(e).__name__}
                    )
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000
                    self.collector.timing("mcp.tool.duration_ms", duration, labels=labels)
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                labels = {"tool": tool_name}
                
                self.collector.increment("mcp.tool.calls", labels=labels)
                
                try:
                    result = func(*args, **kwargs)
                    self.collector.increment("mcp.tool.success", labels=labels)
                    return result
                except Exception as e:
                    self.collector.increment("mcp.tool.errors", labels=labels)
                    self.collector.increment(
                        "mcp.tool.errors_by_type",
                        labels={**labels, "error_type": type(e).__name__}
                    )
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000
                    self.collector.timing("mcp.tool.duration_ms", duration, labels=labels)
                    
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return decorator
        
    def track_resource_access(self, resource_name: str):
        """Track resource access"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                labels = {"resource": resource_name}
                self.collector.increment("mcp.resource.access", labels=labels)
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.collector.increment("mcp.resource.errors", labels=labels)
                    raise
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                labels = {"resource": resource_name}
                self.collector.increment("mcp.resource.access", labels=labels)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.collector.increment("mcp.resource.errors", labels=labels)
                    raise
                    
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return decorator
        
    def track_request(self, request_type: str = "mcp"):
        """Track MCP request"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                labels = {"type": request_type}
                
                self.collector.increment("mcp.requests.total", labels=labels)
                self.collector.gauge(
                    "mcp.requests.active",
                    self.collector.gauges.get("mcp.requests.active", 0) + 1
                )
                
                try:
                    result = await func(*args, **kwargs)
                    self.collector.increment("mcp.requests.success", labels=labels)
                    return result
                except Exception as e:
                    self.collector.increment("mcp.requests.errors", labels=labels)
                    raise
                finally:
                    self.collector.gauge(
                        "mcp.requests.active",
                        max(0, self.collector.gauges.get("mcp.requests.active", 0) - 1)
                    )
                    duration = (time.time() - start_time) * 1000
                    self.collector.timing("mcp.requests.duration_ms", duration, labels=labels)
                    
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                # Similar sync version...
                return func
        return decorator


# Global instances
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
mcp_metrics = MCPMetrics(metrics_collector)


def start_monitoring():
    """Start all monitoring components"""
    metrics_collector.start()
    system_monitor.start()
    logger.info("Monitoring started")
    

def stop_monitoring():
    """Stop all monitoring components"""
    system_monitor.stop()
    metrics_collector.stop()
    logger.info("Monitoring stopped")
    

def get_metrics_summary() -> Dict[str, Any]:
    """Get current metrics summary"""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metrics": metrics_collector.get_summary(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }


# Convenience decorators
track_tool = mcp_metrics.track_tool_execution
track_resource = mcp_metrics.track_resource_access
track_request = mcp_metrics.track_request