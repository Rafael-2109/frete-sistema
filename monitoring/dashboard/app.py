#!/usr/bin/env python3
"""
MCP Frete Sistema - Monitoring Dashboard
Real-time system monitoring and performance tracking
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import json
import datetime
import threading
import time
from collections import deque, defaultdict
import psutil
import redis
import psycopg2
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import logging

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=True
)

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        database=os.environ.get('DB_NAME', 'frete_sistema'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', '')
    )

# Metrics storage
class MetricsStore:
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.metrics = defaultdict(lambda: deque(maxlen=max_size))
        self.alerts = deque(maxlen=100)
        self.lock = threading.Lock()
    
    def add_metric(self, metric_name, value, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        with self.lock:
            self.metrics[metric_name].append({
                'value': value,
                'timestamp': timestamp.isoformat()
            })
    
    def get_metrics(self, metric_name, limit=100):
        with self.lock:
            data = list(self.metrics[metric_name])
            return data[-limit:] if len(data) > limit else data
    
    def add_alert(self, alert_data):
        with self.lock:
            self.alerts.append({
                **alert_data,
                'timestamp': datetime.datetime.now().isoformat()
            })
    
    def get_alerts(self, limit=50):
        with self.lock:
            return list(self.alerts)[-limit:]

# Initialize metrics store
metrics_store = MetricsStore()

# Prometheus metrics
request_count = Counter('mcp_requests_total', 'Total number of requests', ['method', 'endpoint'])
request_duration = Histogram('mcp_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_users = Gauge('mcp_active_users', 'Number of active users')
db_connections = Gauge('mcp_db_connections', 'Number of database connections')
cache_hit_rate = Gauge('mcp_cache_hit_rate', 'Cache hit rate percentage')
error_rate = Gauge('mcp_error_rate', 'Error rate per minute')

# Background metrics collector
class MetricsCollector(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                metrics_store.add_metric('cpu_usage', cpu_percent)
                metrics_store.add_metric('memory_usage', memory.percent)
                metrics_store.add_metric('disk_usage', disk.percent)
                
                # Collect process metrics
                process = psutil.Process()
                metrics_store.add_metric('process_cpu', process.cpu_percent())
                metrics_store.add_metric('process_memory', process.memory_info().rss / 1024 / 1024)  # MB
                
                # Database metrics
                try:
                    with get_db_connection() as conn:
                        with conn.cursor() as cur:
                            # Query performance
                            cur.execute("""
                                SELECT 
                                    COUNT(*) as count,
                                    AVG(duration) as avg_duration
                                FROM pg_stat_statements
                                WHERE query NOT LIKE '%pg_stat_statements%'
                                LIMIT 1
                            """)
                            result = cur.fetchone()
                            if result:
                                metrics_store.add_metric('db_query_count', result[0] or 0)
                                metrics_store.add_metric('db_query_avg_duration', result[1] or 0)
                            
                            # Connection count
                            cur.execute("SELECT COUNT(*) FROM pg_stat_activity")
                            conn_count = cur.fetchone()[0]
                            metrics_store.add_metric('db_connections', conn_count)
                            db_connections.set(conn_count)
                except Exception as e:
                    logger.error(f"Database metrics error: {e}")
                
                # Redis metrics
                try:
                    info = redis_client.info()
                    hits = info.get('keyspace_hits', 0)
                    misses = info.get('keyspace_misses', 0)
                    total = hits + misses
                    hit_rate = (hits / total * 100) if total > 0 else 0
                    
                    metrics_store.add_metric('cache_hit_rate', hit_rate)
                    cache_hit_rate.set(hit_rate)
                    
                    metrics_store.add_metric('redis_memory', info.get('used_memory_rss', 0) / 1024 / 1024)  # MB
                    metrics_store.add_metric('redis_connections', info.get('connected_clients', 0))
                except Exception as e:
                    logger.error(f"Redis metrics error: {e}")
                
                # API metrics from Redis
                try:
                    # Get recent request counts
                    request_count_val = redis_client.get('mcp:metrics:request_count') or 0
                    error_count_val = redis_client.get('mcp:metrics:error_count') or 0
                    
                    metrics_store.add_metric('api_requests', int(request_count_val))
                    metrics_store.add_metric('api_errors', int(error_count_val))
                    
                    # Calculate error rate
                    if int(request_count_val) > 0:
                        error_rate_val = (int(error_count_val) / int(request_count_val)) * 100
                        metrics_store.add_metric('error_rate', error_rate_val)
                        error_rate.set(error_rate_val)
                except Exception as e:
                    logger.error(f"API metrics error: {e}")
                
                # Emit metrics via WebSocket
                socketio.emit('metrics_update', {
                    'cpu_usage': cpu_percent,
                    'memory_usage': memory.percent,
                    'disk_usage': disk.percent,
                    'timestamp': datetime.datetime.now().isoformat()
                })
                
                # Check for alerts
                self.check_alerts({
                    'cpu_usage': cpu_percent,
                    'memory_usage': memory.percent,
                    'disk_usage': disk.percent,
                    'error_rate': metrics_store.get_metrics('error_rate', 1)[0]['value'] if metrics_store.get_metrics('error_rate', 1) else 0
                })
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            
            time.sleep(5)  # Collect every 5 seconds
    
    def check_alerts(self, current_metrics):
        """Check metrics against alert thresholds"""
        thresholds = {
            'cpu_usage': {'warning': 70, 'critical': 90},
            'memory_usage': {'warning': 80, 'critical': 95},
            'disk_usage': {'warning': 85, 'critical': 95},
            'error_rate': {'warning': 5, 'critical': 10}
        }
        
        for metric, value in current_metrics.items():
            if metric in thresholds:
                threshold = thresholds[metric]
                
                if value >= threshold['critical']:
                    alert = {
                        'level': 'critical',
                        'metric': metric,
                        'value': value,
                        'threshold': threshold['critical'],
                        'message': f"Critical: {metric} is at {value:.1f}% (threshold: {threshold['critical']}%)"
                    }
                    metrics_store.add_alert(alert)
                    socketio.emit('alert', alert)
                
                elif value >= threshold['warning']:
                    alert = {
                        'level': 'warning',
                        'metric': metric,
                        'value': value,
                        'threshold': threshold['warning'],
                        'message': f"Warning: {metric} is at {value:.1f}% (threshold: {threshold['warning']}%)"
                    }
                    metrics_store.add_alert(alert)
                    socketio.emit('alert', alert)

# Routes
@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html')

@app.route('/api/metrics/<metric_name>')
def get_metric(metric_name):
    """Get historical data for a specific metric"""
    limit = int(request.args.get('limit', 100))
    data = metrics_store.get_metrics(metric_name, limit)
    return jsonify(data)

@app.route('/api/metrics/current')
def get_current_metrics():
    """Get current values for all metrics"""
    metrics = {}
    for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage', 'api_requests', 
                       'api_errors', 'error_rate', 'cache_hit_rate', 'db_connections']:
        data = metrics_store.get_metrics(metric_name, 1)
        if data:
            metrics[metric_name] = data[0]['value']
        else:
            metrics[metric_name] = 0
    
    return jsonify(metrics)

@app.route('/api/alerts')
def get_alerts():
    """Get recent alerts"""
    limit = int(request.args.get('limit', 50))
    alerts = metrics_store.get_alerts(limit)
    return jsonify(alerts)

@app.route('/api/system/info')
def get_system_info():
    """Get system information"""
    return jsonify({
        'cpu_count': psutil.cpu_count(),
        'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
        'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
        'disk_total': psutil.disk_usage('/').total / 1024 / 1024 / 1024,  # GB
        'python_version': os.sys.version,
        'platform': os.sys.platform
    })

@app.route('/api/user/activity')
def get_user_activity():
    """Get user activity data"""
    try:
        # Get from Redis
        active_users_count = redis_client.scard('mcp:active_users') or 0
        recent_actions = redis_client.lrange('mcp:user_actions', 0, 50)
        
        return jsonify({
            'active_users': active_users_count,
            'recent_actions': [json.loads(action) for action in recent_actions]
        })
    except Exception as e:
        logger.error(f"User activity error: {e}")
        return jsonify({'active_users': 0, 'recent_actions': []})

@app.route('/metrics')
def prometheus_metrics():
    """Expose metrics for Prometheus"""
    return generate_latest()

@app.route('/health')
def health_check():
    """Health check endpoint"""
    checks = {
        'database': False,
        'redis': False,
        'monitoring': True
    }
    
    # Check database
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                checks['database'] = True
    except:
        pass
    
    # Check Redis
    try:
        redis_client.ping()
        checks['redis'] = True
    except:
        pass
    
    status = 'healthy' if all(checks.values()) else 'degraded'
    return jsonify({
        'status': status,
        'checks': checks,
        'timestamp': datetime.datetime.now().isoformat()
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to monitoring dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_metrics')
def handle_metrics_request(data):
    """Handle metrics request from client"""
    metric_name = data.get('metric')
    limit = data.get('limit', 100)
    
    if metric_name:
        metrics = metrics_store.get_metrics(metric_name, limit)
        emit('metrics_data', {
            'metric': metric_name,
            'data': metrics
        })

# Start metrics collector
if __name__ == '__main__':
    collector = MetricsCollector()
    collector.start()
    
    # Run the app
    port = int(os.environ.get('MONITORING_PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)