"""Connection Pool Optimizer - Optimizes database connection pooling."""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import psycopg2
from psycopg2 import pool
import statistics
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Statistics for a single connection."""
    connection_id: str
    created_at: datetime
    last_used_at: datetime
    total_queries: int = 0
    total_time: float = 0.0
    idle_time: float = 0.0
    active_time: float = 0.0
    error_count: int = 0
    
    @property
    def avg_query_time(self) -> float:
        """Average query execution time."""
        if self.total_queries == 0:
            return 0.0
        return self.total_time / self.total_queries
    
    @property
    def age(self) -> float:
        """Connection age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_percentage(self) -> float:
        """Percentage of time connection has been idle."""
        if self.age == 0:
            return 0.0
        return (self.idle_time / self.age) * 100


@dataclass
class PoolMetrics:
    """Metrics for the entire connection pool."""
    timestamp: datetime = field(default_factory=datetime.now)
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    waiting_requests: int = 0
    connection_wait_time: List[float] = field(default_factory=list)
    query_response_time: List[float] = field(default_factory=list)
    pool_utilization: float = 0.0
    
    @property
    def avg_wait_time(self) -> float:
        """Average connection wait time."""
        if not self.connection_wait_time:
            return 0.0
        return statistics.mean(self.connection_wait_time)
    
    @property
    def avg_response_time(self) -> float:
        """Average query response time."""
        if not self.query_response_time:
            return 0.0
        return statistics.mean(self.query_response_time)


class ConnectionPoolOptimizer:
    """Optimizes database connection pool configuration and performance."""
    
    def __init__(self, connection_params: Dict[str, str], 
                 initial_pool_size: int = 5,
                 max_pool_size: int = 20):
        self.connection_params = connection_params
        self.initial_pool_size = initial_pool_size
        self.max_pool_size = max_pool_size
        
        # Create connection pool
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            self.initial_pool_size,
            self.max_pool_size,
            **connection_params
        )
        
        # Tracking
        self.connection_stats: Dict[str, ConnectionStats] = {}
        self.metrics_history: deque = deque(maxlen=1000)
        self.current_metrics = PoolMetrics()
        self.lock = threading.Lock()
        
        # Configuration
        self.idle_timeout = 300  # 5 minutes
        self.max_connection_age = 3600  # 1 hour
        self.target_utilization = 0.7  # 70%
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_pool)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def get_connection(self) -> Tuple[Any, str]:
        """Get a connection from the pool with tracking."""
        wait_start = time.time()
        
        with self.lock:
            self.current_metrics.waiting_requests += 1
        
        try:
            conn = self.pool.getconn()
            wait_time = time.time() - wait_start
            
            # Track connection stats
            conn_id = str(id(conn))
            
            with self.lock:
                self.current_metrics.waiting_requests -= 1
                self.current_metrics.connection_wait_time.append(wait_time)
                
                if conn_id not in self.connection_stats:
                    self.connection_stats[conn_id] = ConnectionStats(
                        connection_id=conn_id,
                        created_at=datetime.now(),
                        last_used_at=datetime.now()
                    )
                else:
                    self.connection_stats[conn_id].last_used_at = datetime.now()
            
            return conn, conn_id
        
        except pool.PoolError as e:
            with self.lock:
                self.current_metrics.waiting_requests -= 1
            logger.error(f"Failed to get connection: {e}")
            raise
    
    def return_connection(self, conn: Any, conn_id: str, had_error: bool = False):
        """Return a connection to the pool."""
        with self.lock:
            if conn_id in self.connection_stats:
                stats = self.connection_stats[conn_id]
                if had_error:
                    stats.error_count += 1
        
        self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a query with connection pool optimization."""
        conn, conn_id = self.get_connection()
        
        try:
            start_time = time.time()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.rowcount
            
            cursor.close()
            
            # Track query metrics
            query_time = time.time() - start_time
            
            with self.lock:
                self.current_metrics.query_response_time.append(query_time)
                if conn_id in self.connection_stats:
                    stats = self.connection_stats[conn_id]
                    stats.total_queries += 1
                    stats.total_time += query_time
                    stats.active_time += query_time
            
            self.return_connection(conn, conn_id)
            return result
            
        except Exception as e:
            self.return_connection(conn, conn_id, had_error=True)
            raise
    
    def _monitor_pool(self):
        """Monitor pool performance and adjust configuration."""
        while self.monitoring_active:
            try:
                # Collect current metrics
                metrics = self._collect_metrics()
                
                with self.lock:
                    self.metrics_history.append(metrics)
                    self.current_metrics = metrics
                
                # Analyze and optimize
                self._analyze_and_optimize()
                
                # Clean up old connections
                self._cleanup_connections()
                
            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
            
            time.sleep(10)  # Monitor every 10 seconds
    
    def _collect_metrics(self) -> PoolMetrics:
        """Collect current pool metrics."""
        metrics = PoolMetrics()
        
        with self.lock:
            # Get pool status
            metrics.total_connections = len(self.pool._used) + len(self.pool._pool)
            metrics.active_connections = len(self.pool._used)
            metrics.idle_connections = len(self.pool._pool)
            metrics.waiting_requests = self.current_metrics.waiting_requests
            
            # Copy recent performance data
            metrics.connection_wait_time = self.current_metrics.connection_wait_time[-100:]
            metrics.query_response_time = self.current_metrics.query_response_time[-100:]
            
            # Calculate utilization
            if metrics.total_connections > 0:
                metrics.pool_utilization = metrics.active_connections / metrics.total_connections
            
            # Update idle times
            now = datetime.now()
            for conn_id, stats in self.connection_stats.items():
                idle_duration = (now - stats.last_used_at).total_seconds()
                stats.idle_time += idle_duration
        
        return metrics
    
    def _analyze_and_optimize(self):
        """Analyze metrics and optimize pool configuration."""
        if len(self.metrics_history) < 10:
            return  # Not enough data
        
        # Calculate recent averages
        recent_metrics = list(self.metrics_history)[-30:]
        avg_utilization = statistics.mean(m.pool_utilization for m in recent_metrics)
        avg_wait_time = statistics.mean(m.avg_wait_time for m in recent_metrics if m.connection_wait_time)
        
        recommendations = []
        
        # Check if pool size should be adjusted
        if avg_utilization > 0.8 and avg_wait_time > 0.1:
            recommendations.append({
                'type': 'increase_pool_size',
                'reason': f'High utilization ({avg_utilization:.1%}) and wait time ({avg_wait_time:.3f}s)',
                'action': 'Consider increasing max pool size'
            })
        elif avg_utilization < 0.3:
            recommendations.append({
                'type': 'decrease_pool_size',
                'reason': f'Low utilization ({avg_utilization:.1%})',
                'action': 'Consider decreasing pool size to save resources'
            })
        
        # Check response times
        if recent_metrics[-1].avg_response_time > 1.0:
            recommendations.append({
                'type': 'slow_queries',
                'reason': f'High average response time ({recent_metrics[-1].avg_response_time:.2f}s)',
                'action': 'Investigate slow queries or database performance'
            })
        
        # Log recommendations
        for rec in recommendations:
            logger.info(f"Pool optimization recommendation: {rec['action']} - {rec['reason']}")
    
    def _cleanup_connections(self):
        """Clean up idle or old connections."""
        now = datetime.now()
        connections_to_close = []
        
        with self.lock:
            for conn_id, stats in self.connection_stats.items():
                # Check if connection is too old
                if stats.age > self.max_connection_age:
                    connections_to_close.append(conn_id)
                    logger.info(f"Closing old connection {conn_id} (age: {stats.age:.0f}s)")
                
                # Check if connection has too many errors
                elif stats.error_count > 5:
                    connections_to_close.append(conn_id)
                    logger.info(f"Closing connection {conn_id} due to errors ({stats.error_count})")
        
        # Note: Actual connection closing would require pool modification
        # This is a simplified version for demonstration
        for conn_id in connections_to_close:
            del self.connection_stats[conn_id]
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate a comprehensive optimization report."""
        if not self.metrics_history:
            return {"error": "No metrics available yet"}
        
        recent_metrics = list(self.metrics_history)[-60:]  # Last 10 minutes
        
        report = {
            'current_status': {
                'total_connections': self.current_metrics.total_connections,
                'active_connections': self.current_metrics.active_connections,
                'idle_connections': self.current_metrics.idle_connections,
                'pool_utilization': f"{self.current_metrics.pool_utilization:.1%}",
                'waiting_requests': self.current_metrics.waiting_requests
            },
            'performance_metrics': {
                'avg_wait_time': f"{statistics.mean(m.avg_wait_time for m in recent_metrics if m.connection_wait_time):.3f}s",
                'avg_response_time': f"{statistics.mean(m.avg_response_time for m in recent_metrics if m.query_response_time):.3f}s",
                'max_wait_time': f"{max((m.avg_wait_time for m in recent_metrics if m.connection_wait_time), default=0):.3f}s",
                'max_response_time': f"{max((m.avg_response_time for m in recent_metrics if m.query_response_time), default=0):.3f}s"
            },
            'connection_analysis': self._analyze_connections(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _analyze_connections(self) -> Dict[str, Any]:
        """Analyze individual connection performance."""
        if not self.connection_stats:
            return {"message": "No connection data available"}
        
        stats_list = list(self.connection_stats.values())
        
        return {
            'total_connections_tracked': len(stats_list),
            'avg_queries_per_connection': statistics.mean(s.total_queries for s in stats_list),
            'avg_connection_age': f"{statistics.mean(s.age for s in stats_list):.0f}s",
            'avg_idle_percentage': f"{statistics.mean(s.idle_percentage for s in stats_list):.1f}%",
            'connections_with_errors': sum(1 for s in stats_list if s.error_count > 0)
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate optimization recommendations based on current metrics."""
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        recent_metrics = list(self.metrics_history)[-30:]
        avg_utilization = statistics.mean(m.pool_utilization for m in recent_metrics)
        avg_wait_time = statistics.mean(m.avg_wait_time for m in recent_metrics if m.connection_wait_time)
        
        # Pool size recommendations
        if avg_utilization > 0.8:
            current_size = self.current_metrics.total_connections
            recommended_size = int(current_size * 1.5)
            recommendations.append({
                'category': 'Pool Size',
                'recommendation': f"Increase pool size from {current_size} to {recommended_size}",
                'reason': f"High average utilization ({avg_utilization:.1%})"
            })
        elif avg_utilization < 0.3 and self.current_metrics.total_connections > self.initial_pool_size:
            recommendations.append({
                'category': 'Pool Size',
                'recommendation': f"Reduce pool size to {self.initial_pool_size}",
                'reason': f"Low average utilization ({avg_utilization:.1%})"
            })
        
        # Connection timeout recommendations
        idle_connections = [s for s in self.connection_stats.values() if s.idle_percentage > 80]
        if len(idle_connections) > self.current_metrics.total_connections * 0.5:
            recommendations.append({
                'category': 'Connection Management',
                'recommendation': "Implement connection timeout for idle connections",
                'reason': f"{len(idle_connections)} connections are idle >80% of the time"
            })
        
        # Performance recommendations
        if avg_wait_time > 0.5:
            recommendations.append({
                'category': 'Performance',
                'recommendation': "Consider using connection pooling middleware or pgBouncer",
                'reason': f"High average connection wait time ({avg_wait_time:.2f}s)"
            })
        
        return recommendations
    
    def export_metrics(self, output_file: str = 'pool_metrics.json'):
        """Export detailed metrics for analysis."""
        metrics_data = {
            'export_time': datetime.now().isoformat(),
            'configuration': {
                'initial_pool_size': self.initial_pool_size,
                'max_pool_size': self.max_pool_size,
                'idle_timeout': self.idle_timeout,
                'max_connection_age': self.max_connection_age
            },
            'current_metrics': {
                'total_connections': self.current_metrics.total_connections,
                'active_connections': self.current_metrics.active_connections,
                'pool_utilization': self.current_metrics.pool_utilization,
                'avg_wait_time': self.current_metrics.avg_wait_time,
                'avg_response_time': self.current_metrics.avg_response_time
            },
            'historical_metrics': [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'utilization': m.pool_utilization,
                    'active_connections': m.active_connections,
                    'waiting_requests': m.waiting_requests,
                    'avg_wait_time': m.avg_wait_time,
                    'avg_response_time': m.avg_response_time
                }
                for m in list(self.metrics_history)[-100:]
            ],
            'recommendations': self._generate_recommendations()
        }
        
        with open(output_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Metrics exported to {output_file}")
        return output_file
    
    def shutdown(self):
        """Gracefully shutdown the connection pool."""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.pool.closeall()
        logger.info("Connection pool shut down")


if __name__ == "__main__":
    # Example usage
    optimizer = ConnectionPoolOptimizer(
        connection_params={
            'host': 'localhost',
            'port': 5432,
            'database': 'frete_db',
            'user': 'postgres',
            'password': 'postgres'
        },
        initial_pool_size=5,
        max_pool_size=20
    )
    
    try:
        # Simulate some database operations
        import random
        for i in range(50):
            try:
                result = optimizer.execute_query(
                    "SELECT pg_sleep(%s)",
                    (random.uniform(0.01, 0.1),)
                )
            except Exception as e:
                logger.error(f"Query error: {e}")
            
            time.sleep(random.uniform(0.1, 0.5))
        
        # Generate report
        report = optimizer.get_optimization_report()
        print(json.dumps(report, indent=2))
        
        # Export metrics
        optimizer.export_metrics()
        
    finally:
        optimizer.shutdown()