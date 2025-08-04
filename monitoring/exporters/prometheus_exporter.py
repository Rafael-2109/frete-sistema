#!/usr/bin/env python3
"""
MCP Frete Sistema - Prometheus Exporter
Exports metrics in Prometheus format
"""

from prometheus_client import (
    Counter, Gauge, Histogram, Summary, Info,
    CollectorRegistry, generate_latest, push_to_gateway,
    start_http_server, CONTENT_TYPE_LATEST
)
from flask import Flask, Response
import redis
import psycopg2
import psutil
import time
import threading
import logging
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app for metrics endpoint
app = Flask(__name__)

# Create custom registry
registry = CollectorRegistry()

# System metrics
cpu_usage_gauge = Gauge('mcp_system_cpu_usage_percent', 'CPU usage percentage', registry=registry)
memory_usage_gauge = Gauge('mcp_system_memory_usage_percent', 'Memory usage percentage', registry=registry)
memory_used_gauge = Gauge('mcp_system_memory_used_bytes', 'Memory used in bytes', registry=registry)
memory_available_gauge = Gauge('mcp_system_memory_available_bytes', 'Memory available in bytes', registry=registry)
disk_usage_gauge = Gauge('mcp_system_disk_usage_percent', 'Disk usage percentage', ['mountpoint'], registry=registry)
disk_free_gauge = Gauge('mcp_system_disk_free_bytes', 'Disk free space in bytes', ['mountpoint'], registry=registry)

# Process metrics
process_cpu_gauge = Gauge('mcp_process_cpu_percent', 'Process CPU usage percentage', registry=registry)
process_memory_gauge = Gauge('mcp_process_memory_rss_bytes', 'Process RSS memory in bytes', registry=registry)
process_threads_gauge = Gauge('mcp_process_threads', 'Number of process threads', registry=registry)
process_fds_gauge = Gauge('mcp_process_open_fds', 'Number of open file descriptors', registry=registry)

# API metrics
api_requests_total = Counter('mcp_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'], registry=registry)
api_request_duration = Histogram('mcp_api_request_duration_seconds', 'API request duration', ['method', 'endpoint'], registry=registry)
api_errors_total = Counter('mcp_api_errors_total', 'Total API errors', ['method', 'endpoint', 'error_type'], registry=registry)
api_active_requests = Gauge('mcp_api_active_requests', 'Number of active API requests', registry=registry)

# Database metrics
db_connections_total = Gauge('mcp_database_connections_total', 'Total database connections', registry=registry)
db_connections_active = Gauge('mcp_database_connections_active', 'Active database connections', registry=registry)
db_connections_idle = Gauge('mcp_database_connections_idle', 'Idle database connections', registry=registry)
db_size_bytes = Gauge('mcp_database_size_bytes', 'Database size in bytes', registry=registry)
db_query_duration = Histogram('mcp_database_query_duration_seconds', 'Database query duration', ['query_type'], registry=registry)
db_table_rows = Gauge('mcp_database_table_rows', 'Number of rows in table', ['schema', 'table'], registry=registry)

# Cache metrics
cache_hits_total = Counter('mcp_cache_hits_total', 'Total cache hits', registry=registry)
cache_misses_total = Counter('mcp_cache_misses_total', 'Total cache misses', registry=registry)
cache_hit_rate = Gauge('mcp_cache_hit_rate_percent', 'Cache hit rate percentage', registry=registry)
cache_memory_used_bytes = Gauge('mcp_cache_memory_used_bytes', 'Cache memory used in bytes', registry=registry)
cache_keys_total = Gauge('mcp_cache_keys_total', 'Total number of cache keys', ['db'], registry=registry)
cache_connections = Gauge('mcp_cache_connections', 'Number of cache connections', registry=registry)

# Business metrics
orders_created_total = Counter('mcp_orders_created_total', 'Total orders created', ['status'], registry=registry)
quotes_created_total = Counter('mcp_quotes_created_total', 'Total quotes created', registry=registry)
revenue_total = Counter('mcp_revenue_total_cents', 'Total revenue in cents', ['currency'], registry=registry)
active_users = Gauge('mcp_active_users', 'Number of active users', registry=registry)
user_sessions = Gauge('mcp_user_sessions', 'Number of active user sessions', registry=registry)

# Application info
app_info = Info('mcp_app', 'Application information', registry=registry)
app_info.info({
    'version': os.environ.get('APP_VERSION', '1.0.0'),
    'environment': os.environ.get('ENVIRONMENT', 'production'),
    'instance': os.environ.get('INSTANCE_ID', 'default')
})


class MetricsExporter:
    """Prometheus metrics exporter"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = self._connect_redis()
        self.db_config = config.get('database', {})
        self.running = False
        self.update_interval = config.get('update_interval', 10)
    
    def _connect_redis(self) -> redis.Redis:
        """Connect to Redis"""
        return redis.Redis(
            host=self.config.get('redis_host', 'localhost'),
            port=self.config.get('redis_port', 6379),
            decode_responses=True
        )
    
    def start(self):
        """Start metrics exporter"""
        self.running = True
        
        # Start update thread
        update_thread = threading.Thread(target=self._update_loop, daemon=True)
        update_thread.start()
        
        logger.info("Prometheus exporter started")
    
    def stop(self):
        """Stop metrics exporter"""
        self.running = False
        logger.info("Prometheus exporter stopped")
    
    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                self._update_metrics()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Metrics update error: {e}")
                time.sleep(5)
    
    def _update_metrics(self):
        """Update all metrics"""
        self._update_system_metrics()
        self._update_process_metrics()
        self._update_database_metrics()
        self._update_cache_metrics()
        self._update_api_metrics()
        self._update_business_metrics()
    
    def _update_system_metrics(self):
        """Update system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage_gauge.set(cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_usage_gauge.set(memory.percent)
            memory_used_gauge.set(memory.used)
            memory_available_gauge.set(memory.available)
            
            # Disk metrics
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage_gauge.labels(mountpoint=partition.mountpoint).set(usage.percent)
                    disk_free_gauge.labels(mountpoint=partition.mountpoint).set(usage.free)
                except PermissionError:
                    continue
                    
        except Exception as e:
            logger.error(f"System metrics error: {e}")
    
    def _update_process_metrics(self):
        """Update process-level metrics"""
        try:
            process = psutil.Process()
            
            # CPU usage
            process_cpu_gauge.set(process.cpu_percent())
            
            # Memory usage
            memory_info = process.memory_info()
            process_memory_gauge.set(memory_info.rss)
            
            # Thread count
            process_threads_gauge.set(process.num_threads())
            
            # File descriptors
            if hasattr(process, 'num_fds'):
                process_fds_gauge.set(process.num_fds())
                
        except Exception as e:
            logger.error(f"Process metrics error: {e}")
    
    def _update_database_metrics(self):
        """Update database metrics"""
        try:
            conn = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                database=self.db_config.get('database', 'frete_sistema'),
                user=self.db_config.get('user', 'postgres'),
                password=self.db_config.get('password', '')
            )
            
            with conn.cursor() as cur:
                # Connection metrics
                cur.execute("""
                    SELECT 
                        count(*) as total,
                        count(*) FILTER (WHERE state = 'active') as active,
                        count(*) FILTER (WHERE state = 'idle') as idle
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)
                result = cur.fetchone()
                if result:
                    db_connections_total.set(result[0])
                    db_connections_active.set(result[1])
                    db_connections_idle.set(result[2])
                
                # Database size
                cur.execute("SELECT pg_database_size(current_database())")
                db_size = cur.fetchone()[0]
                db_size_bytes.set(db_size)
                
                # Table metrics
                cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_live_tup
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC
                    LIMIT 20
                """)
                
                for row in cur.fetchall():
                    db_table_rows.labels(
                        schema=row[0],
                        table=row[1]
                    ).set(row[2])
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Database metrics error: {e}")
    
    def _update_cache_metrics(self):
        """Update cache metrics"""
        try:
            info = self.redis_client.info()
            
            # Hit/miss metrics
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            
            if total > 0:
                hit_rate = (hits / total) * 100
                cache_hit_rate.set(hit_rate)
            
            # Memory metrics
            cache_memory_used_bytes.set(info.get('used_memory', 0))
            
            # Connection metrics
            cache_connections.set(info.get('connected_clients', 0))
            
            # Keyspace metrics
            for db_index in range(16):
                db_key = f'db{db_index}'
                if db_key in info:
                    db_info = info[db_key]
                    # Parse 'keys=X,expires=Y'
                    keys_count = int(db_info.split(',')[0].split('=')[1])
                    cache_keys_total.labels(db=str(db_index)).set(keys_count)
                    
        except Exception as e:
            logger.error(f"Cache metrics error: {e}")
    
    def _update_api_metrics(self):
        """Update API metrics from Redis"""
        try:
            # Get API metrics stored by the application
            request_count = self.redis_client.get('mcp:metrics:request_count')
            if request_count:
                # This is a simplified example - in practice, you'd track by method/endpoint
                api_requests_total.labels(
                    method='GET',
                    endpoint='/api/v1',
                    status='200'
                ).inc(int(request_count))
            
            # Active requests
            active_requests = self.redis_client.get('mcp:metrics:active_requests')
            if active_requests:
                api_active_requests.set(int(active_requests))
            
            # Error count
            error_count = self.redis_client.get('mcp:metrics:error_count')
            if error_count:
                api_errors_total.labels(
                    method='GET',
                    endpoint='/api/v1',
                    error_type='500'
                ).inc(int(error_count))
                
        except Exception as e:
            logger.error(f"API metrics error: {e}")
    
    def _update_business_metrics(self):
        """Update business metrics"""
        try:
            # Active users
            active_users_count = self.redis_client.scard('mcp:active_users') or 0
            active_users.set(active_users_count)
            
            # User sessions
            session_count = self.redis_client.get('mcp:metrics:sessions') or 0
            user_sessions.set(int(session_count))
            
            # Orders
            orders_today = self.redis_client.get('mcp:metrics:orders:today') or 0
            if int(orders_today) > 0:
                orders_created_total.labels(status='completed').inc(int(orders_today))
            
            # Quotes
            quotes_today = self.redis_client.get('mcp:metrics:quotes:today') or 0
            if int(quotes_today) > 0:
                quotes_created_total.inc(int(quotes_today))
            
            # Revenue
            revenue_today = self.redis_client.get('mcp:metrics:revenue:today') or 0
            if float(revenue_today) > 0:
                # Convert to cents to avoid floating point in counter
                revenue_cents = int(float(revenue_today) * 100)
                revenue_total.labels(currency='BRL').inc(revenue_cents)
                
        except Exception as e:
            logger.error(f"Business metrics error: {e}")


# Flask routes
@app.route('/metrics')
def metrics():
    """Expose metrics endpoint"""
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy'}


# Custom metric recording functions
def record_api_request(method: str, endpoint: str, status: int, duration: float):
    """Record an API request"""
    api_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

def record_api_error(method: str, endpoint: str, error_type: str):
    """Record an API error"""
    api_errors_total.labels(method=method, endpoint=endpoint, error_type=error_type).inc()

def record_db_query(query_type: str, duration: float):
    """Record a database query"""
    db_query_duration.labels(query_type=query_type).observe(duration)

def record_cache_hit():
    """Record a cache hit"""
    cache_hits_total.inc()

def record_cache_miss():
    """Record a cache miss"""
    cache_misses_total.inc()

def record_order_created(status: str = 'completed'):
    """Record an order creation"""
    orders_created_total.labels(status=status).inc()

def record_quote_created():
    """Record a quote creation"""
    quotes_created_total.inc()

def record_revenue(amount_cents: int, currency: str = 'BRL'):
    """Record revenue"""
    revenue_total.labels(currency=currency).inc(amount_cents)


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
        },
        'update_interval': int(os.environ.get('METRICS_UPDATE_INTERVAL', 10))
    }
    
    # Initialize exporter
    exporter = MetricsExporter(config)
    exporter.start()
    
    # Start Flask app
    port = int(os.environ.get('PROMETHEUS_PORT', 9090))
    app.run(host='0.0.0.0', port=port)