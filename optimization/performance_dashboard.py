"""Performance Monitoring Dashboard - Real-time database performance monitoring."""

import time
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
from flask import Flask, render_template_string, jsonify
import threading
from collections import deque
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our optimization modules
from query_analyzer import QueryAnalyzer
from index_optimizer import IndexOptimizer
from cache_optimizer import CacheOptimizer
from connection_pool_optimizer import ConnectionPoolOptimizer


class PerformanceDashboard:
    """Real-time performance monitoring dashboard."""
    
    def __init__(self, connection_params: Dict[str, str]):
        self.connection_params = connection_params
        
        # Initialize optimizers
        self.query_analyzer = QueryAnalyzer(connection_params)
        self.index_optimizer = IndexOptimizer(connection_params)
        self.cache_optimizer = CacheOptimizer(max_memory_mb=256)
        self.pool_optimizer = ConnectionPoolOptimizer(connection_params)
        
        # Metrics storage
        self.metrics_buffer = deque(maxlen=300)  # 5 minutes at 1 sample/sec
        self.alerts = deque(maxlen=100)
        
        # Monitoring configuration
        self.monitoring_active = True
        self.alert_thresholds = {
            'query_time': 1.0,  # seconds
            'connection_wait': 0.5,  # seconds
            'cache_hit_rate': 0.5,  # minimum hit rate
            'pool_utilization': 0.9,  # maximum utilization
            'error_rate': 0.05  # maximum error rate
        }
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._continuous_monitoring)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _continuous_monitoring(self):
        """Continuously monitor database performance."""
        while self.monitoring_active:
            try:
                metrics = self._collect_real_time_metrics()
                self.metrics_buffer.append(metrics)
                self._check_alerts(metrics)
                time.sleep(1)  # Collect metrics every second
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(5)
    
    def _collect_real_time_metrics(self) -> Dict[str, Any]:
        """Collect real-time performance metrics."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'database': {},
            'queries': {},
            'connections': {},
            'cache': {},
            'system': {}
        }
        
        with psycopg2.connect(**self.connection_params) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Database statistics
                cursor.execute("""
                    SELECT 
                        numbackends as active_connections,
                        xact_commit as transactions_committed,
                        xact_rollback as transactions_rolled_back,
                        blks_read as blocks_read,
                        blks_hit as blocks_hit,
                        tup_returned as tuples_returned,
                        tup_fetched as tuples_fetched,
                        tup_inserted as tuples_inserted,
                        tup_updated as tuples_updated,
                        tup_deleted as tuples_deleted
                    FROM pg_stat_database
                    WHERE datname = current_database()
                """)
                
                db_stats = cursor.fetchone()
                metrics['database'] = dict(db_stats)
                
                # Calculate cache hit ratio
                if db_stats['blocks_read'] + db_stats['blocks_hit'] > 0:
                    metrics['database']['cache_hit_ratio'] = \
                        db_stats['blocks_hit'] / (db_stats['blocks_read'] + db_stats['blocks_hit'])
                
                # Active queries
                cursor.execute("""
                    SELECT 
                        pid,
                        usename,
                        application_name,
                        client_addr,
                        backend_start,
                        state,
                        wait_event_type,
                        wait_event,
                        query,
                        extract(epoch from (now() - query_start)) as query_duration
                    FROM pg_stat_activity
                    WHERE state != 'idle'
                    AND query NOT LIKE '%pg_stat_activity%'
                    ORDER BY query_start
                """)
                
                active_queries = []
                for row in cursor:
                    active_queries.append({
                        'pid': row['pid'],
                        'user': row['usename'],
                        'duration': row['query_duration'],
                        'state': row['state'],
                        'wait_event': f"{row['wait_event_type']}:{row['wait_event']}" if row['wait_event_type'] else None,
                        'query': row['query'][:100] + '...' if len(row['query']) > 100 else row['query']
                    })
                
                metrics['queries']['active'] = active_queries
                metrics['queries']['count'] = len(active_queries)
                
                # Lock statistics
                cursor.execute("""
                    SELECT 
                        mode,
                        COUNT(*) as count
                    FROM pg_locks
                    WHERE NOT granted
                    GROUP BY mode
                """)
                
                blocked_locks = {row['mode']: row['count'] for row in cursor}
                metrics['database']['blocked_locks'] = blocked_locks
                
                # Table statistics
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins + n_tup_upd + n_tup_del as write_activity,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY write_activity DESC
                    LIMIT 10
                """)
                
                hot_tables = []
                for row in cursor:
                    hot_tables.append({
                        'table': row['tablename'],
                        'write_activity': row['write_activity'],
                        'seq_scans': row['seq_scan'],
                        'index_scans': row['idx_scan'],
                        'scan_ratio': row['idx_scan'] / (row['seq_scan'] + row['idx_scan']) 
                                      if (row['seq_scan'] + row['idx_scan']) > 0 else 0
                    })
                
                metrics['database']['hot_tables'] = hot_tables
        
        # Connection pool metrics
        pool_report = self.pool_optimizer.get_optimization_report()
        metrics['connections'] = pool_report.get('current_status', {})
        
        # Cache metrics
        cache_analysis = self.cache_optimizer.analyze_cache_performance()
        metrics['cache'] = cache_analysis.get('stats', {})
        
        # System metrics
        metrics['system'] = {
            'timestamp': datetime.now().isoformat(),
            'alerts_count': len(self.alerts),
            'monitoring_uptime': self._get_monitoring_uptime()
        }
        
        return metrics
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against alert thresholds."""
        alerts = []
        
        # Check active query duration
        for query in metrics['queries'].get('active', []):
            if query['duration'] and query['duration'] > self.alert_thresholds['query_time']:
                alerts.append({
                    'type': 'slow_query',
                    'severity': 'high',
                    'message': f"Slow query detected (PID: {query['pid']}, Duration: {query['duration']:.1f}s)",
                    'details': query
                })
        
        # Check cache hit rate
        cache_hit_rate = metrics['cache'].get('hit_rate', 1.0)
        if cache_hit_rate < self.alert_thresholds['cache_hit_rate']:
            alerts.append({
                'type': 'low_cache_hit',
                'severity': 'medium',
                'message': f"Low cache hit rate: {cache_hit_rate:.1%}",
                'details': {'hit_rate': cache_hit_rate}
            })
        
        # Check connection pool utilization
        pool_util = metrics['connections'].get('pool_utilization', '0%')
        if isinstance(pool_util, str):
            pool_util = float(pool_util.strip('%')) / 100
        if pool_util > self.alert_thresholds['pool_utilization']:
            alerts.append({
                'type': 'high_pool_utilization',
                'severity': 'high',
                'message': f"High connection pool utilization: {pool_util:.1%}",
                'details': metrics['connections']
            })
        
        # Check for blocked locks
        blocked_locks = metrics['database'].get('blocked_locks', {})
        if blocked_locks:
            alerts.append({
                'type': 'blocked_locks',
                'severity': 'high',
                'message': f"Blocked locks detected: {sum(blocked_locks.values())} total",
                'details': blocked_locks
            })
        
        # Add alerts to buffer
        for alert in alerts:
            alert['timestamp'] = datetime.now().isoformat()
            self.alerts.append(alert)
    
    def _get_monitoring_uptime(self) -> str:
        """Get monitoring uptime."""
        if not self.metrics_buffer:
            return "0s"
        
        first_metric = self.metrics_buffer[0]
        first_time = datetime.fromisoformat(first_metric['timestamp'])
        uptime = datetime.now() - first_time
        
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}h {minutes}m {seconds}s"
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data."""
        if not self.metrics_buffer:
            return {'error': 'No metrics available yet'}
        
        current_metrics = self.metrics_buffer[-1]
        recent_metrics = list(self.metrics_buffer)[-60:]  # Last minute
        
        # Calculate trends
        query_counts = [m['queries']['count'] for m in recent_metrics]
        cache_hit_rates = [m['cache'].get('hit_rate', 0) for m in recent_metrics]
        
        return {
            'current': current_metrics,
            'trends': {
                'query_count': {
                    'current': query_counts[-1] if query_counts else 0,
                    'avg': statistics.mean(query_counts) if query_counts else 0,
                    'max': max(query_counts) if query_counts else 0
                },
                'cache_hit_rate': {
                    'current': cache_hit_rates[-1] if cache_hit_rates else 0,
                    'avg': statistics.mean(cache_hit_rates) if cache_hit_rates else 0,
                    'min': min(cache_hit_rates) if cache_hit_rates else 0
                }
            },
            'alerts': list(self.alerts)[-10:],  # Last 10 alerts
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate performance recommendations based on current metrics."""
        recommendations = []
        
        if not self.metrics_buffer:
            return recommendations
        
        recent_metrics = list(self.metrics_buffer)[-60:]
        
        # Analyze query performance
        slow_queries = []
        for m in recent_metrics:
            for q in m['queries'].get('active', []):
                if q['duration'] and q['duration'] > 1.0:
                    slow_queries.append(q)
        
        if len(slow_queries) > 5:
            recommendations.append({
                'category': 'Query Performance',
                'recommendation': 'Multiple slow queries detected',
                'action': 'Run query analyzer to identify optimization opportunities'
            })
        
        # Analyze cache performance
        avg_hit_rate = statistics.mean([m['cache'].get('hit_rate', 0) for m in recent_metrics])
        if avg_hit_rate < 0.7:
            recommendations.append({
                'category': 'Cache Performance',
                'recommendation': f'Low cache hit rate ({avg_hit_rate:.1%})',
                'action': 'Increase cache size or optimize cache strategy'
            })
        
        # Analyze table scans
        current = recent_metrics[-1]
        for table in current['database'].get('hot_tables', []):
            if table['scan_ratio'] < 0.5 and table['seq_scans'] > 100:
                recommendations.append({
                    'category': 'Index Usage',
                    'recommendation': f"High sequential scans on {table['table']}",
                    'action': 'Consider adding indexes for frequently queried columns'
                })
        
        return recommendations[:5]  # Top 5 recommendations
    
    def create_web_dashboard(self, port: int = 5000):
        """Create a web-based dashboard."""
        app = Flask(__name__)
        
        @app.route('/')
        def dashboard():
            return render_template_string(DASHBOARD_TEMPLATE)
        
        @app.route('/api/metrics')
        def metrics():
            return jsonify(self.get_dashboard_data())
        
        @app.route('/api/analyze/queries')
        def analyze_queries():
            slow_queries = self.query_analyzer.identify_slow_queries()
            return jsonify(slow_queries[:10])  # Top 10 slow queries
        
        @app.route('/api/analyze/indexes')
        def analyze_indexes():
            missing = self.index_optimizer.analyze_missing_indexes()
            unused = self.index_optimizer.analyze_unused_indexes()
            return jsonify({
                'missing': missing[:10],
                'unused': unused[:10]
            })
        
        @app.route('/api/report/performance')
        def performance_report():
            report = {
                'timestamp': datetime.now().isoformat(),
                'query_analysis': self.query_analyzer.generate_report(),
                'pool_optimization': self.pool_optimizer.get_optimization_report(),
                'cache_performance': self.cache_optimizer.get_cache_report()
            }
            return jsonify(report)
        
        logger.info(f"Starting web dashboard on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    
    def shutdown(self):
        """Shutdown monitoring."""
        self.monitoring_active = False
        self.pool_optimizer.shutdown()
        logger.info("Performance dashboard shut down")


# HTML template for the web dashboard
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Database Performance Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { display: inline-block; margin: 10px 20px; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { color: #666; font-size: 14px; }
        .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .alert-high { background: #ffebee; color: #c62828; }
        .alert-medium { background: #fff3e0; color: #e65100; }
        .alert-low { background: #e8f5e9; color: #2e7d32; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; font-weight: bold; }
        .refresh-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; 
                       border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Database Performance Dashboard</h1>
        <button class="refresh-btn" onclick="refreshData()">Refresh</button>
        
        <div class="card">
            <h2>System Overview</h2>
            <div id="overview-metrics"></div>
        </div>
        
        <div class="card">
            <h2>Active Queries</h2>
            <div id="active-queries"></div>
        </div>
        
        <div class="card">
            <h2>Recent Alerts</h2>
            <div id="alerts"></div>
        </div>
        
        <div class="card">
            <h2>Performance Recommendations</h2>
            <div id="recommendations"></div>
        </div>
        
        <div class="card">
            <h2>Hot Tables</h2>
            <div id="hot-tables"></div>
        </div>
    </div>
    
    <script>
        function refreshData() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => updateDashboard(data));
        }
        
        function updateDashboard(data) {
            // Update overview metrics
            const overview = document.getElementById('overview-metrics');
            const current = data.current;
            overview.innerHTML = `
                <div class="metric">
                    <div class="metric-value">${current.database.active_connections || 0}</div>
                    <div class="metric-label">Active Connections</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${current.queries.count || 0}</div>
                    <div class="metric-label">Active Queries</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${(current.cache.hit_rate * 100).toFixed(1)}%</div>
                    <div class="metric-label">Cache Hit Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${current.connections.pool_utilization || '0%'}</div>
                    <div class="metric-label">Pool Utilization</div>
                </div>
            `;
            
            // Update active queries
            const queries = document.getElementById('active-queries');
            if (current.queries.active && current.queries.active.length > 0) {
                queries.innerHTML = '<table><tr><th>PID</th><th>User</th><th>Duration</th><th>Query</th></tr>' +
                    current.queries.active.map(q => 
                        `<tr><td>${q.pid}</td><td>${q.user}</td><td>${q.duration ? q.duration.toFixed(1) + 's' : '-'}</td><td>${q.query}</td></tr>`
                    ).join('') + '</table>';
            } else {
                queries.innerHTML = '<p>No active queries</p>';
            }
            
            // Update alerts
            const alerts = document.getElementById('alerts');
            if (data.alerts && data.alerts.length > 0) {
                alerts.innerHTML = data.alerts.map(a => 
                    `<div class="alert alert-${a.severity}">${a.message}</div>`
                ).join('');
            } else {
                alerts.innerHTML = '<p>No recent alerts</p>';
            }
            
            // Update recommendations
            const recommendations = document.getElementById('recommendations');
            if (data.recommendations && data.recommendations.length > 0) {
                recommendations.innerHTML = '<ul>' + data.recommendations.map(r => 
                    `<li><strong>${r.category}:</strong> ${r.recommendation} - <em>${r.action}</em></li>`
                ).join('') + '</ul>';
            } else {
                recommendations.innerHTML = '<p>No recommendations at this time</p>';
            }
            
            // Update hot tables
            const hotTables = document.getElementById('hot-tables');
            if (current.database.hot_tables && current.database.hot_tables.length > 0) {
                hotTables.innerHTML = '<table><tr><th>Table</th><th>Write Activity</th><th>Seq Scans</th><th>Index Scans</th><th>Index Usage</th></tr>' +
                    current.database.hot_tables.map(t => 
                        `<tr><td>${t.table}</td><td>${t.write_activity}</td><td>${t.seq_scans}</td><td>${t.index_scans}</td><td>${(t.scan_ratio * 100).toFixed(1)}%</td></tr>`
                    ).join('') + '</table>';
            }
        }
        
        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);
        refreshData();
    </script>
</body>
</html>
'''


if __name__ == "__main__":
    # Example usage
    dashboard = PerformanceDashboard({
        'host': 'localhost',
        'port': 5432,
        'database': 'frete_db',
        'user': 'postgres',
        'password': 'postgres'
    })
    
    try:
        # Start web dashboard
        dashboard.create_web_dashboard(port=5000)
    except KeyboardInterrupt:
        dashboard.shutdown()