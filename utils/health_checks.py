"""
Comprehensive health check utilities for MCP Sistema Frete.

Provides detailed health status for all system components with
actionable diagnostics and performance metrics.
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import redis
import aiohttp

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class ComponentHealth:
    """Health status for a single component."""
    
    def __init__(self, name: str, status: HealthStatus, 
                 response_time: float, details: Optional[Dict] = None):
        self.name = name
        self.status = status
        self.response_time = response_time
        self.details = details or {}
        self.checked_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'status': self.status.value,
            'response_time_ms': round(self.response_time * 1000, 2),
            'checked_at': self.checked_at.isoformat(),
            'details': self.details
        }


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.checks = []
        self.last_check_results = {}
        self.check_history = []
        self.max_history = 100
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        start_time = time.time()
        
        # Run all checks concurrently
        check_tasks = [
            self.check_database(),
            self.check_cache(),
            self.check_external_services(),
            self.check_system_resources(),
            self.check_application_metrics(),
            self.check_background_tasks(),
            self.check_security_components()
        ]
        
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        components = []
        overall_status = HealthStatus.HEALTHY
        failed_checks = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                component = ComponentHealth(
                    name="unknown",
                    status=HealthStatus.CRITICAL,
                    response_time=0,
                    details={'error': str(result)}
                )
            else:
                component = result
            
            components.append(component)
            
            # Update overall status
            if component.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif component.status == HealthStatus.UNHEALTHY and overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.UNHEALTHY
            elif component.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
            
            if component.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                failed_checks.append(component.name)
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Build response
        health_report = {
            'status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'version': self.config.get('app_version', 'unknown'),
            'total_check_time_ms': round(total_time * 1000, 2),
            'components': [c.to_dict() for c in components],
            'failed_checks': failed_checks,
            'summary': self._generate_summary(components, overall_status)
        }
        
        # Store in history
        self.last_check_results = health_report
        self.check_history.append(health_report)
        if len(self.check_history) > self.max_history:
            self.check_history.pop(0)
        
        return health_report
    
    async def check_database(self) -> ComponentHealth:
        """Check database health and performance."""
        start_time = time.time()
        details = {}
        
        try:
            # Get database connection from config
            db = self.config.get('database_connection')
            
            # Test basic connectivity
            async with db.acquire() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            
            # Check connection pool status
            pool_stats = {
                'size': db.pool.size(),
                'checked_in': db.pool.checkedin(),
                'checked_out': db.pool.checkedout(),
                'overflow': db.pool.overflow(),
                'total': db.pool.total()
            }
            
            details['pool_stats'] = pool_stats
            
            # Check for slow queries
            slow_queries = await self._check_slow_queries(db)
            if slow_queries:
                details['slow_queries'] = slow_queries
            
            # Determine status
            pool_usage = pool_stats['checked_out'] / pool_stats['size']
            if pool_usage > 0.9:
                status = HealthStatus.DEGRADED
                details['warning'] = 'High connection pool usage'
            elif pool_usage > 0.95:
                status = HealthStatus.UNHEALTHY
                details['error'] = 'Critical connection pool usage'
            else:
                status = HealthStatus.HEALTHY
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name='database',
                status=status,
                response_time=response_time,
                details=details
            )
            
        except OperationalError as e:
            return ComponentHealth(
                name='database',
                status=HealthStatus.CRITICAL,
                response_time=time.time() - start_time,
                details={'error': str(e), 'type': 'connection_failure'}
            )
        except Exception as e:
            return ComponentHealth(
                name='database',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={'error': str(e)}
            )
    
    async def check_cache(self) -> ComponentHealth:
        """Check cache system health."""
        start_time = time.time()
        details = {}
        
        try:
            # Get Redis connection from config
            cache = self.config.get('cache_connection')
            
            # Test basic operations
            test_key = 'health_check_test'
            test_value = str(time.time())
            
            # Set
            await cache.set(test_key, test_value, ex=10)
            
            # Get
            retrieved = await cache.get(test_key)
            
            if retrieved != test_value:
                raise ValueError("Cache read/write mismatch")
            
            # Get cache stats
            info = await cache.info()
            memory_info = info.get('memory', {})
            stats_info = info.get('stats', {})
            
            details['memory'] = {
                'used_memory_human': memory_info.get('used_memory_human'),
                'used_memory_peak_human': memory_info.get('used_memory_peak_human'),
                'mem_fragmentation_ratio': memory_info.get('mem_fragmentation_ratio')
            }
            
            details['stats'] = {
                'total_connections_received': stats_info.get('total_connections_received'),
                'total_commands_processed': stats_info.get('total_commands_processed'),
                'instantaneous_ops_per_sec': stats_info.get('instantaneous_ops_per_sec'),
                'keyspace_hits': stats_info.get('keyspace_hits'),
                'keyspace_misses': stats_info.get('keyspace_misses')
            }
            
            # Calculate hit rate
            hits = stats_info.get('keyspace_hits', 0)
            misses = stats_info.get('keyspace_misses', 0)
            if hits + misses > 0:
                hit_rate = hits / (hits + misses)
                details['hit_rate'] = round(hit_rate * 100, 2)
                
                if hit_rate < 0.5:
                    status = HealthStatus.DEGRADED
                    details['warning'] = 'Low cache hit rate'
                else:
                    status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.HEALTHY
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name='cache',
                status=status,
                response_time=response_time,
                details=details
            )
            
        except redis.ConnectionError as e:
            return ComponentHealth(
                name='cache',
                status=HealthStatus.CRITICAL,
                response_time=time.time() - start_time,
                details={'error': str(e), 'type': 'connection_failure'}
            )
        except Exception as e:
            return ComponentHealth(
                name='cache',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={'error': str(e)}
            )
    
    async def check_external_services(self) -> ComponentHealth:
        """Check health of external service dependencies."""
        start_time = time.time()
        services_status = {}
        overall_status = HealthStatus.HEALTHY
        
        external_services = self.config.get('external_services', {})
        
        async with aiohttp.ClientSession() as session:
            for service_name, service_config in external_services.items():
                service_start = time.time()
                
                try:
                    health_endpoint = f"{service_config['base_url']}/health"
                    timeout = aiohttp.ClientTimeout(total=5)
                    
                    async with session.get(health_endpoint, timeout=timeout) as response:
                        service_time = time.time() - service_start
                        
                        if response.status == 200:
                            services_status[service_name] = {
                                'status': 'healthy',
                                'response_time_ms': round(service_time * 1000, 2)
                            }
                        else:
                            services_status[service_name] = {
                                'status': 'unhealthy',
                                'response_time_ms': round(service_time * 1000, 2),
                                'http_status': response.status
                            }
                            overall_status = HealthStatus.DEGRADED
                            
                except asyncio.TimeoutError:
                    services_status[service_name] = {
                        'status': 'timeout',
                        'response_time_ms': 5000
                    }
                    if service_name in ['payment', 'correios']:  # Critical services
                        overall_status = HealthStatus.UNHEALTHY
                    else:
                        overall_status = HealthStatus.DEGRADED
                        
                except Exception as e:
                    services_status[service_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    overall_status = HealthStatus.DEGRADED
        
        response_time = time.time() - start_time
        
        return ComponentHealth(
            name='external_services',
            status=overall_status,
            response_time=response_time,
            details={'services': services_status}
        )
    
    async def check_system_resources(self) -> ComponentHealth:
        """Check system resource utilization."""
        start_time = time.time()
        details = {}
        status = HealthStatus.HEALTHY
        warnings = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            details['cpu'] = {
                'usage_percent': cpu_percent,
                'count': psutil.cpu_count()
            }
            
            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append('High CPU usage')
            elif cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append('Critical CPU usage')
            
            # Memory usage
            memory = psutil.virtual_memory()
            details['memory'] = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent
            }
            
            if memory.percent > 85:
                status = HealthStatus.DEGRADED
                warnings.append('High memory usage')
            elif memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                warnings.append('Critical memory usage')
            
            # Disk usage
            disk = psutil.disk_usage('/')
            details['disk'] = {
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'used_percent': disk.percent
            }
            
            if disk.percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append('High disk usage')
            elif disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append('Critical disk usage')
            
            # Network I/O
            net_io = psutil.net_io_counters()
            details['network'] = {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout
            }
            
            if warnings:
                details['warnings'] = warnings
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name='system_resources',
                status=status,
                response_time=response_time,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name='system_resources',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={'error': str(e)}
            )
    
    async def check_application_metrics(self) -> ComponentHealth:
        """Check application-specific metrics."""
        start_time = time.time()
        details = {}
        status = HealthStatus.HEALTHY
        
        try:
            metrics = self.config.get('metrics_collector')
            
            if metrics:
                # Get current metrics
                current_metrics = await metrics.get_current_metrics()
                
                details['requests'] = {
                    'total': current_metrics.get('total_requests', 0),
                    'success_rate': current_metrics.get('success_rate', 100),
                    'avg_response_time_ms': current_metrics.get('avg_response_time', 0),
                    'p95_response_time_ms': current_metrics.get('p95_response_time', 0),
                    'p99_response_time_ms': current_metrics.get('p99_response_time', 0)
                }
                
                details['errors'] = {
                    'rate': current_metrics.get('error_rate', 0),
                    'last_hour': current_metrics.get('errors_last_hour', 0)
                }
                
                # Check thresholds
                if current_metrics.get('error_rate', 0) > 5:
                    status = HealthStatus.DEGRADED
                    details['warning'] = 'High error rate'
                elif current_metrics.get('error_rate', 0) > 10:
                    status = HealthStatus.UNHEALTHY
                    details['error'] = 'Critical error rate'
                
                if current_metrics.get('p95_response_time', 0) > 2000:
                    if status == HealthStatus.HEALTHY:
                        status = HealthStatus.DEGRADED
                    details['warning'] = 'High response times'
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name='application_metrics',
                status=status,
                response_time=response_time,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name='application_metrics',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={'error': str(e)}
            )
    
    async def check_background_tasks(self) -> ComponentHealth:
        """Check background task health."""
        start_time = time.time()
        details = {}
        status = HealthStatus.HEALTHY
        
        try:
            task_manager = self.config.get('task_manager')
            
            if task_manager:
                task_status = await task_manager.get_status()
                
                details['tasks'] = {
                    'active': task_status.get('active_tasks', 0),
                    'pending': task_status.get('pending_tasks', 0),
                    'failed': task_status.get('failed_tasks', 0),
                    'completed_last_hour': task_status.get('completed_last_hour', 0)
                }
                
                # Check for stuck or failed tasks
                if task_status.get('failed_tasks', 0) > 10:
                    status = HealthStatus.DEGRADED
                    details['warning'] = 'High number of failed tasks'
                
                if task_status.get('pending_tasks', 0) > 100:
                    status = HealthStatus.DEGRADED
                    details['warning'] = 'Large task backlog'
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name='background_tasks',
                status=status,
                response_time=response_time,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name='background_tasks',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={'error': str(e)}
            )
    
    async def check_security_components(self) -> ComponentHealth:
        """Check security component health."""
        start_time = time.time()
        details = {}
        status = HealthStatus.HEALTHY
        
        try:
            # Check rate limiter
            rate_limiter = self.config.get('rate_limiter')
            if rate_limiter:
                details['rate_limiter'] = {
                    'active': True,
                    'backend': 'redis'
                }
            
            # Check authentication service
            auth_service = self.config.get('auth_service')
            if auth_service:
                auth_stats = await auth_service.get_stats()
                details['authentication'] = {
                    'active_sessions': auth_stats.get('active_sessions', 0),
                    'failed_attempts_last_hour': auth_stats.get('failed_attempts', 0)
                }
                
                if auth_stats.get('failed_attempts', 0) > 100:
                    status = HealthStatus.DEGRADED
                    details['warning'] = 'High number of failed auth attempts'
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name='security',
                status=status,
                response_time=response_time,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name='security',
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                details={'error': str(e)}
            )
    
    async def _check_slow_queries(self, db) -> List[Dict[str, Any]]:
        """Check for slow running queries."""
        try:
            # This is PostgreSQL specific, adjust for other databases
            query = text("""
                SELECT 
                    pid,
                    now() - pg_stat_activity.query_start AS duration,
                    query,
                    state
                FROM pg_stat_activity
                WHERE (now() - pg_stat_activity.query_start) > interval '1 second'
                AND state != 'idle'
                ORDER BY duration DESC
                LIMIT 5
            """)
            
            async with db.acquire() as conn:
                result = await conn.execute(query)
                rows = await result.fetchall()
                
                slow_queries = []
                for row in rows:
                    slow_queries.append({
                        'pid': row[0],
                        'duration_seconds': row[1].total_seconds() if row[1] else 0,
                        'query': row[2][:100] + '...' if len(row[2]) > 100 else row[2],
                        'state': row[3]
                    })
                
                return slow_queries
                
        except Exception as e:
            logger.error(f"Error checking slow queries: {e}")
            return []
    
    def _generate_summary(self, components: List[ComponentHealth], 
                         overall_status: HealthStatus) -> Dict[str, Any]:
        """Generate a summary of the health check results."""
        healthy_count = sum(1 for c in components if c.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for c in components if c.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        critical_count = sum(1 for c in components if c.status == HealthStatus.CRITICAL)
        
        return {
            'overall_status': overall_status.value,
            'component_count': len(components),
            'healthy': healthy_count,
            'degraded': degraded_count,
            'unhealthy': unhealthy_count,
            'critical': critical_count,
            'uptime_percentage': self._calculate_uptime()
        }
    
    def _calculate_uptime(self) -> float:
        """Calculate system uptime percentage based on health history."""
        if not self.check_history:
            return 100.0
        
        healthy_checks = sum(
            1 for check in self.check_history 
            if check['status'] == HealthStatus.HEALTHY.value
        )
        
        return round((healthy_checks / len(self.check_history)) * 100, 2)
    
    def get_health_trends(self) -> Dict[str, Any]:
        """Get health trends over time."""
        if not self.check_history:
            return {}
        
        # Analyze trends
        trends = {
            'checks_analyzed': len(self.check_history),
            'time_range': {
                'start': self.check_history[0]['timestamp'],
                'end': self.check_history[-1]['timestamp']
            },
            'status_distribution': {},
            'component_trends': {}
        }
        
        # Status distribution
        for check in self.check_history:
            status = check['status']
            trends['status_distribution'][status] = \
                trends['status_distribution'].get(status, 0) + 1
        
        # Component trends
        for check in self.check_history:
            for component in check['components']:
                comp_name = component['name']
                if comp_name not in trends['component_trends']:
                    trends['component_trends'][comp_name] = {
                        'healthy': 0,
                        'degraded': 0,
                        'unhealthy': 0,
                        'critical': 0
                    }
                
                comp_status = component['status']
                trends['component_trends'][comp_name][comp_status] += 1
        
        return trends


# Convenience functions for health check endpoints
async def liveness_check() -> Tuple[bool, str]:
    """Simple liveness check - is the application running?"""
    return True, "OK"


async def readiness_check(health_checker: HealthChecker) -> Tuple[bool, Dict[str, Any]]:
    """Readiness check - is the application ready to serve traffic?"""
    health_report = await health_checker.check_all()
    
    is_ready = health_report['status'] in [
        HealthStatus.HEALTHY.value,
        HealthStatus.DEGRADED.value
    ]
    
    return is_ready, health_report


async def deep_health_check(health_checker: HealthChecker) -> Dict[str, Any]:
    """Deep health check with full diagnostics."""
    health_report = await health_checker.check_all()
    health_report['trends'] = health_checker.get_health_trends()
    
    return health_report