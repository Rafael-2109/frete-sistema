#!/usr/bin/env python3
"""
MCP Frete Sistema - Metrics Collector
Collects and aggregates system and application metrics
"""

import time
import threading
import psutil
import redis
import psycopg2
import requests
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging
from typing import Dict, List, Any, Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Main metrics collection service"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = self._connect_redis()
        self.db_config = config.get('database', {})
        self.collectors = []
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.aggregated_metrics = {}
        self.running = False
        self.lock = threading.Lock()
        
        # Initialize collectors
        self._init_collectors()
    
    def _connect_redis(self) -> redis.Redis:
        """Connect to Redis"""
        return redis.Redis(
            host=self.config.get('redis_host', 'localhost'),
            port=self.config.get('redis_port', 6379),
            decode_responses=True
        )
    
    def _init_collectors(self):
        """Initialize all metric collectors"""
        self.collectors = [
            SystemMetricsCollector(self),
            DatabaseMetricsCollector(self),
            APIMetricsCollector(self),
            CacheMetricsCollector(self),
            ApplicationMetricsCollector(self),
            CustomMetricsCollector(self)
        ]
    
    def start(self):
        """Start metrics collection"""
        self.running = True
        
        # Start collector threads
        for collector in self.collectors:
            thread = threading.Thread(target=collector.collect_loop, daemon=True)
            thread.start()
        
        # Start aggregation thread
        aggregation_thread = threading.Thread(target=self._aggregation_loop, daemon=True)
        aggregation_thread.start()
        
        logger.info("Metrics collector started")
    
    def stop(self):
        """Stop metrics collection"""
        self.running = False
        logger.info("Metrics collector stopped")
    
    def add_metric(self, name: str, value: float, tags: Dict[str, str] = None, timestamp: float = None):
        """Add a metric to the buffer"""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            metric_key = self._make_metric_key(name, tags)
            self.metrics_buffer[metric_key].append({
                'value': value,
                'timestamp': timestamp,
                'tags': tags or {}
            })
            
            # Store in Redis for real-time access
            self._store_redis_metric(name, value, tags)
    
    def _make_metric_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create a unique key for a metric"""
        if not tags:
            return name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name},{tag_str}"
    
    def _store_redis_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Store metric in Redis"""
        try:
            key = f"mcp:metrics:{name}"
            if tags:
                key += f":{','.join(f'{k}={v}' for k, v in tags.items())}"
            
            # Store current value
            self.redis_client.set(key, value, ex=300)  # 5 minute expiry
            
            # Store in time series
            ts_key = f"{key}:ts"
            self.redis_client.zadd(ts_key, {json.dumps({'value': value, 'tags': tags}): time.time()})
            
            # Trim old entries (keep last 1000)
            self.redis_client.zremrangebyrank(ts_key, 0, -1001)
            
        except Exception as e:
            logger.error(f"Error storing metric in Redis: {e}")
    
    def _aggregation_loop(self):
        """Periodically aggregate metrics"""
        while self.running:
            try:
                self._aggregate_metrics()
                time.sleep(60)  # Aggregate every minute
            except Exception as e:
                logger.error(f"Aggregation error: {e}")
                time.sleep(5)
    
    def _aggregate_metrics(self):
        """Aggregate metrics for different time windows"""
        with self.lock:
            current_time = time.time()
            
            for metric_key, values in self.metrics_buffer.items():
                if not values:
                    continue
                
                # Calculate aggregations
                recent_values = [v for v in values if current_time - v['timestamp'] < 300]  # Last 5 minutes
                
                if recent_values:
                    metric_values = [v['value'] for v in recent_values]
                    
                    aggregations = {
                        'count': len(metric_values),
                        'sum': sum(metric_values),
                        'avg': sum(metric_values) / len(metric_values),
                        'min': min(metric_values),
                        'max': max(metric_values),
                        'p50': self._percentile(metric_values, 50),
                        'p95': self._percentile(metric_values, 95),
                        'p99': self._percentile(metric_values, 99)
                    }
                    
                    self.aggregated_metrics[metric_key] = {
                        'aggregations': aggregations,
                        'last_update': current_time
                    }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_metric(self, name: str, tags: Dict[str, str] = None, window: int = 300) -> Dict[str, Any]:
        """Get metric data for a time window"""
        metric_key = self._make_metric_key(name, tags)
        current_time = time.time()
        
        with self.lock:
            if metric_key in self.metrics_buffer:
                values = [v for v in self.metrics_buffer[metric_key] 
                         if current_time - v['timestamp'] < window]
                
                if values:
                    return {
                        'name': name,
                        'tags': tags,
                        'values': values,
                        'aggregations': self.aggregated_metrics.get(metric_key, {}).get('aggregations', {})
                    }
        
        return {'name': name, 'tags': tags, 'values': [], 'aggregations': {}}


class BaseCollector:
    """Base class for metric collectors"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.interval = 10  # Default collection interval
    
    def collect_loop(self):
        """Main collection loop"""
        while self.metrics_collector.running:
            try:
                self.collect()
            except Exception as e:
                logger.error(f"{self.__class__.__name__} error: {e}")
            
            time.sleep(self.interval)
    
    def collect(self):
        """Collect metrics - to be implemented by subclasses"""
        raise NotImplementedError
    
    def add_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Add a metric"""
        self.metrics_collector.add_metric(name, value, tags)


class SystemMetricsCollector(BaseCollector):
    """Collects system-level metrics"""
    
    def collect(self):
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self.add_metric('system.cpu.usage', cpu_percent)
        
        # Per-CPU metrics
        for i, cpu in enumerate(psutil.cpu_percent(interval=1, percpu=True)):
            self.add_metric('system.cpu.usage', cpu, {'cpu': str(i)})
        
        # Memory metrics
        memory = psutil.virtual_memory()
        self.add_metric('system.memory.usage', memory.percent)
        self.add_metric('system.memory.used', memory.used)
        self.add_metric('system.memory.available', memory.available)
        
        # Swap metrics
        swap = psutil.swap_memory()
        self.add_metric('system.swap.usage', swap.percent)
        self.add_metric('system.swap.used', swap.used)
        
        # Disk metrics
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                tags = {'mountpoint': partition.mountpoint, 'device': partition.device}
                
                self.add_metric('system.disk.usage', usage.percent, tags)
                self.add_metric('system.disk.used', usage.used, tags)
                self.add_metric('system.disk.free', usage.free, tags)
            except PermissionError:
                continue
        
        # Network metrics
        net_io = psutil.net_io_counters()
        self.add_metric('system.network.bytes_sent', net_io.bytes_sent)
        self.add_metric('system.network.bytes_recv', net_io.bytes_recv)
        self.add_metric('system.network.packets_sent', net_io.packets_sent)
        self.add_metric('system.network.packets_recv', net_io.packets_recv)
        
        # Process metrics
        process = psutil.Process()
        self.add_metric('process.cpu.usage', process.cpu_percent())
        self.add_metric('process.memory.rss', process.memory_info().rss)
        self.add_metric('process.memory.vms', process.memory_info().vms)
        self.add_metric('process.threads', process.num_threads())
        self.add_metric('process.fds', process.num_fds() if hasattr(process, 'num_fds') else 0)


class DatabaseMetricsCollector(BaseCollector):
    """Collects database metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        super().__init__(metrics_collector)
        self.interval = 30  # Collect every 30 seconds
    
    def collect(self):
        try:
            conn = psycopg2.connect(
                host=self.metrics_collector.db_config.get('host', 'localhost'),
                database=self.metrics_collector.db_config.get('database', 'frete_sistema'),
                user=self.metrics_collector.db_config.get('user', 'postgres'),
                password=self.metrics_collector.db_config.get('password', '')
            )
            
            with conn.cursor() as cur:
                # Connection metrics
                cur.execute("""
                    SELECT 
                        count(*) as total,
                        count(*) FILTER (WHERE state = 'active') as active,
                        count(*) FILTER (WHERE state = 'idle') as idle,
                        count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)
                result = cur.fetchone()
                if result:
                    self.add_metric('database.connections.total', result[0])
                    self.add_metric('database.connections.active', result[1])
                    self.add_metric('database.connections.idle', result[2])
                    self.add_metric('database.connections.idle_in_transaction', result[3])
                
                # Database size
                cur.execute("""
                    SELECT pg_database_size(current_database())
                """)
                db_size = cur.fetchone()[0]
                self.add_metric('database.size', db_size)
                
                # Table statistics
                cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del,
                        n_live_tup,
                        n_dead_tup
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                """)
                
                for row in cur.fetchall():
                    tags = {'schema': row[0], 'table': row[1]}
                    self.add_metric('database.table.inserts', row[2], tags)
                    self.add_metric('database.table.updates', row[3], tags)
                    self.add_metric('database.table.deletes', row[4], tags)
                    self.add_metric('database.table.live_tuples', row[5], tags)
                    self.add_metric('database.table.dead_tuples', row[6], tags)
                
                # Query performance (if pg_stat_statements is available)
                try:
                    cur.execute("""
                        SELECT 
                            count(*) as query_count,
                            sum(calls) as total_calls,
                            avg(mean_exec_time) as avg_exec_time,
                            max(mean_exec_time) as max_exec_time
                        FROM pg_stat_statements
                        WHERE query NOT LIKE '%pg_stat_statements%'
                    """)
                    result = cur.fetchone()
                    if result:
                        self.add_metric('database.queries.count', result[0])
                        self.add_metric('database.queries.calls', result[1] or 0)
                        self.add_metric('database.queries.avg_time', result[2] or 0)
                        self.add_metric('database.queries.max_time', result[3] or 0)
                except:
                    pass  # pg_stat_statements might not be available
                
            conn.close()
            
        except Exception as e:
            logger.error(f"Database metrics collection error: {e}")


class APIMetricsCollector(BaseCollector):
    """Collects API metrics from application logs and Redis"""
    
    def collect(self):
        try:
            redis_client = self.metrics_collector.redis_client
            
            # Request metrics
            request_count = redis_client.get('mcp:metrics:request_count') or 0
            self.add_metric('api.requests.total', int(request_count))
            
            # Error metrics
            error_count = redis_client.get('mcp:metrics:error_count') or 0
            self.add_metric('api.errors.total', int(error_count))
            
            # Response time metrics
            response_times = redis_client.lrange('mcp:metrics:response_times', 0, -1)
            if response_times:
                times = [float(t) for t in response_times]
                self.add_metric('api.response_time.avg', sum(times) / len(times))
                self.add_metric('api.response_time.min', min(times))
                self.add_metric('api.response_time.max', max(times))
                self.add_metric('api.response_time.p95', self.metrics_collector._percentile(times, 95))
            
            # Endpoint-specific metrics
            endpoints = redis_client.smembers('mcp:metrics:endpoints')
            for endpoint in endpoints:
                endpoint_key = f'mcp:metrics:endpoint:{endpoint}'
                count = redis_client.hget(endpoint_key, 'count') or 0
                errors = redis_client.hget(endpoint_key, 'errors') or 0
                avg_time = redis_client.hget(endpoint_key, 'avg_time') or 0
                
                tags = {'endpoint': endpoint}
                self.add_metric('api.endpoint.requests', int(count), tags)
                self.add_metric('api.endpoint.errors', int(errors), tags)
                self.add_metric('api.endpoint.response_time', float(avg_time), tags)
            
        except Exception as e:
            logger.error(f"API metrics collection error: {e}")


class CacheMetricsCollector(BaseCollector):
    """Collects cache metrics from Redis"""
    
    def collect(self):
        try:
            redis_client = self.metrics_collector.redis_client
            info = redis_client.info()
            
            # Memory metrics
            self.add_metric('cache.memory.used', info.get('used_memory', 0))
            self.add_metric('cache.memory.rss', info.get('used_memory_rss', 0))
            self.add_metric('cache.memory.peak', info.get('used_memory_peak', 0))
            
            # Performance metrics
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            self.add_metric('cache.hits', hits)
            self.add_metric('cache.misses', misses)
            self.add_metric('cache.hit_rate', hit_rate)
            
            # Connection metrics
            self.add_metric('cache.connections.current', info.get('connected_clients', 0))
            self.add_metric('cache.connections.blocked', info.get('blocked_clients', 0))
            
            # Command statistics
            self.add_metric('cache.commands.processed', info.get('total_commands_processed', 0))
            self.add_metric('cache.operations.per_sec', info.get('instantaneous_ops_per_sec', 0))
            
            # Keyspace metrics
            for db_index in range(16):  # Check first 16 databases
                db_key = f'db{db_index}'
                if db_key in info:
                    db_info = info[db_key]
                    # Parse 'keys=X,expires=Y,avg_ttl=Z'
                    parts = db_info.split(',')
                    metrics = {}
                    for part in parts:
                        key, value = part.split('=')
                        metrics[key] = int(value)
                    
                    tags = {'db': str(db_index)}
                    self.add_metric('cache.keys', metrics.get('keys', 0), tags)
                    self.add_metric('cache.expires', metrics.get('expires', 0), tags)
                    
        except Exception as e:
            logger.error(f"Cache metrics collection error: {e}")


class ApplicationMetricsCollector(BaseCollector):
    """Collects application-specific metrics"""
    
    def collect(self):
        try:
            redis_client = self.metrics_collector.redis_client
            
            # User metrics
            active_users = redis_client.scard('mcp:active_users') or 0
            self.add_metric('app.users.active', active_users)
            
            # Session metrics
            session_count = redis_client.get('mcp:metrics:sessions') or 0
            self.add_metric('app.sessions.active', int(session_count))
            
            # Business metrics
            orders_today = redis_client.get('mcp:metrics:orders:today') or 0
            quotes_today = redis_client.get('mcp:metrics:quotes:today') or 0
            revenue_today = redis_client.get('mcp:metrics:revenue:today') or 0
            
            self.add_metric('app.orders.today', int(orders_today))
            self.add_metric('app.quotes.today', int(quotes_today))
            self.add_metric('app.revenue.today', float(revenue_today))
            
            # Queue metrics
            queues = ['email', 'notifications', 'reports', 'integrations']
            for queue in queues:
                queue_size = redis_client.llen(f'mcp:queue:{queue}') or 0
                self.add_metric('app.queue.size', queue_size, {'queue': queue})
            
            # Feature usage metrics
            features = redis_client.smembers('mcp:features') or []
            for feature in features:
                usage_count = redis_client.get(f'mcp:feature:{feature}:usage') or 0
                self.add_metric('app.feature.usage', int(usage_count), {'feature': feature})
                
        except Exception as e:
            logger.error(f"Application metrics collection error: {e}")


class CustomMetricsCollector(BaseCollector):
    """Collects custom metrics defined by the application"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        super().__init__(metrics_collector)
        self.interval = 5  # Check for custom metrics more frequently
    
    def collect(self):
        try:
            redis_client = self.metrics_collector.redis_client
            
            # Check for custom metrics in Redis
            custom_metrics = redis_client.smembers('mcp:custom_metrics') or []
            
            for metric_name in custom_metrics:
                metric_data = redis_client.hgetall(f'mcp:custom_metric:{metric_name}')
                
                if metric_data:
                    value = float(metric_data.get('value', 0))
                    tags = json.loads(metric_data.get('tags', '{}'))
                    
                    self.add_metric(f'custom.{metric_name}', value, tags)
                    
                    # Remove processed metric
                    redis_client.delete(f'mcp:custom_metric:{metric_name}')
                    redis_client.srem('mcp:custom_metrics', metric_name)
                    
        except Exception as e:
            logger.error(f"Custom metrics collection error: {e}")


# Standalone runner
if __name__ == '__main__':
    config = {
        'redis_host': os.environ.get('REDIS_HOST', 'localhost'),
        'redis_port': int(os.environ.get('REDIS_PORT', 6379)),
        'database': {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'database': os.environ.get('DB_NAME', 'frete_sistema'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', '')
        }
    }
    
    collector = MetricsCollector(config)
    collector.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        collector.stop()
        print("Metrics collector stopped")