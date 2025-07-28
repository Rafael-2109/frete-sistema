"""
Query Optimizer Utilities

Provides query optimization features including:
- Query plan analysis
- Index recommendations
- Query caching
- Connection pooling management
- Performance monitoring
"""

from typing import Dict, Any, List, Optional
from sqlalchemy import text, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from sqlalchemy.orm import Session
import time
import logging
from functools import wraps
from collections import defaultdict
import hashlib
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Query optimization utilities"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.query_cache = {}
        self.query_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'avg_time': 0})
        self.slow_query_threshold = 1.0  # seconds
        self._setup_listeners()
        
    def _setup_listeners(self):
        """Setup SQLAlchemy event listeners for query monitoring"""
        @event.listens_for(self.engine, "before_execute")
        def receive_before_execute(conn, clauseelement, multiparams, params, execution_options):
            conn.info.setdefault('query_start_time', []).append(time.time())
            
        @event.listens_for(self.engine, "after_execute")
        def receive_after_execute(conn, clauseelement, multiparams, params, execution_options, result):
            total_time = time.time() - conn.info['query_start_time'].pop(-1)
            
            # Log slow queries
            if total_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected ({total_time:.2f}s): {str(clauseelement)[:200]}")
                
            # Update stats
            query_key = self._get_query_key(str(clauseelement))
            self.query_stats[query_key]['count'] += 1
            self.query_stats[query_key]['total_time'] += total_time
            self.query_stats[query_key]['avg_time'] = (
                self.query_stats[query_key]['total_time'] / 
                self.query_stats[query_key]['count']
            )
            
    def _get_query_key(self, query: str) -> str:
        """Generate a key for query caching and stats"""
        # Remove specific values to group similar queries
        normalized = query.lower()
        # Replace numbers with placeholders
        import re
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        normalized = re.sub(r"'[^']*'", '?', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()
        
    def analyze_query_plan(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze query execution plan (PostgreSQL specific)"""
        if not self.engine.url.drivername.startswith('postgresql'):
            return {'error': 'Query plan analysis only available for PostgreSQL'}
            
        with self.engine.connect() as conn:
            # Get EXPLAIN ANALYZE output
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            result = conn.execute(text(explain_query), params or {})
            plan = result.fetchone()[0]
            
            # Extract key metrics
            analysis = {
                'execution_time': plan[0]['Execution Time'],
                'planning_time': plan[0]['Planning Time'],
                'total_cost': plan[0]['Plan']['Total Cost'],
                'actual_rows': plan[0]['Plan']['Actual Rows'],
                'shared_blocks': {
                    'hit': plan[0]['Plan'].get('Shared Hit Blocks', 0),
                    'read': plan[0]['Plan'].get('Shared Read Blocks', 0)
                }
            }
            
            # Check for potential issues
            issues = []
            if plan[0]['Plan'].get('Node Type') == 'Seq Scan':
                issues.append('Sequential scan detected - consider adding index')
                
            if analysis['shared_blocks']['read'] > analysis['shared_blocks']['hit']:
                issues.append('High disk reads - data not in cache')
                
            analysis['issues'] = issues
            analysis['full_plan'] = plan
            
            return analysis
            
    def recommend_indexes(self, table_name: str, min_usage: int = 10) -> List[Dict[str, Any]]:
        """Recommend indexes based on query patterns"""
        recommendations = []
        
        # Analyze frequently used WHERE clauses
        frequent_filters = self._analyze_filter_patterns(table_name)
        
        for column, usage_count in frequent_filters.items():
            if usage_count >= min_usage:
                recommendations.append({
                    'table': table_name,
                    'column': column,
                    'type': 'btree',
                    'reason': f'Column used in WHERE clause {usage_count} times',
                    'estimated_improvement': 'High',
                    'sql': f'CREATE INDEX idx_{table_name}_{column} ON {table_name}({column});'
                })
                
        # Check for composite index opportunities
        composite_patterns = self._analyze_composite_patterns(table_name)
        for columns, usage_count in composite_patterns.items():
            if usage_count >= min_usage:
                col_list = ', '.join(columns)
                recommendations.append({
                    'table': table_name,
                    'columns': columns,
                    'type': 'composite',
                    'reason': f'Columns used together {usage_count} times',
                    'estimated_improvement': 'Very High',
                    'sql': f'CREATE INDEX idx_{table_name}_{"_".join(columns)} ON {table_name}({col_list});'
                })
                
        return recommendations
        
    def _analyze_filter_patterns(self, table_name: str) -> Dict[str, int]:
        """Analyze WHERE clause patterns for a table"""
        # This would analyze query logs in production
        # For now, return common patterns
        common_patterns = {
            'fretes': {
                'numero_cte': 50,
                'transportadora_id': 100,
                'status': 80,
                'criado_em': 60
            },
            'pedidos': {
                'num_pedido': 120,
                'separacao_lote_id': 90,
                'cnpj_cpf': 70,
                'status': 85
            },
            'carteira_principal': {
                'num_pedido': 150,
                'cod_produto': 140,
                'cnpj_cpf': 100,
                'expedicao': 80
            }
        }
        
        return common_patterns.get(table_name, {})
        
    def _analyze_composite_patterns(self, table_name: str) -> Dict[tuple, int]:
        """Analyze composite index opportunities"""
        composite_patterns = {
            'fretes': {
                ('transportadora_id', 'status'): 40,
                ('criado_em', 'status'): 35
            },
            'pedidos': {
                ('separacao_lote_id', 'status'): 45,
                ('cnpj_cpf', 'expedicao'): 30
            },
            'carteira_principal': {
                ('num_pedido', 'cod_produto'): 200,
                ('cnpj_cpf', 'expedicao'): 60
            }
        }
        
        return composite_patterns.get(table_name, {})
        
    def optimize_connection_pool(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend optimal connection pool settings"""
        # Get current database statistics
        stats = self.get_connection_stats()
        
        recommendations = {
            'pool_size': current_config.get('pool_size', 5),
            'max_overflow': current_config.get('max_overflow', 10),
            'pool_timeout': current_config.get('pool_timeout', 30),
            'pool_recycle': current_config.get('pool_recycle', 300)
        }
        
        # Adjust based on usage patterns
        if stats['active_connections'] > recommendations['pool_size'] * 0.8:
            recommendations['pool_size'] = min(stats['active_connections'] + 5, 20)
            recommendations['max_overflow'] = recommendations['pool_size']
            
        if stats['wait_time_avg'] > 1.0:
            recommendations['pool_timeout'] = 60
            
        if stats['connection_errors'] > 0:
            recommendations['pool_recycle'] = 200
            
        recommendations['reasoning'] = self._explain_pool_recommendations(stats, recommendations)
        
        return recommendations
        
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics"""
        pool = self.engine.pool
        
        return {
            'size': pool.size() if hasattr(pool, 'size') else 0,
            'checked_in': pool.checkedin() if hasattr(pool, 'checkedin') else 0,
            'checked_out': pool.checkedout() if hasattr(pool, 'checkedout') else 0,
            'overflow': pool.overflow() if hasattr(pool, 'overflow') else 0,
            'total': pool.total() if hasattr(pool, 'total') else 0,
            'active_connections': self._get_active_connections(),
            'wait_time_avg': 0.5,  # Placeholder
            'connection_errors': 0  # Placeholder
        }
        
    def _get_active_connections(self) -> int:
        """Get active database connections"""
        if self.engine.url.drivername.startswith('postgresql'):
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                ))
                return result.scalar()
        return 0
        
    def _explain_pool_recommendations(self, stats: Dict[str, Any], 
                                    recommendations: Dict[str, Any]) -> List[str]:
        """Explain connection pool recommendations"""
        reasons = []
        
        if recommendations['pool_size'] > stats.get('size', 5):
            reasons.append(f"Increased pool size to {recommendations['pool_size']} due to high connection usage")
            
        if recommendations['pool_timeout'] > 30:
            reasons.append("Increased timeout to reduce connection wait errors")
            
        if recommendations['pool_recycle'] < 300:
            reasons.append("Decreased recycle time to prevent stale connections")
            
        return reasons
        
    def cache_query_result(self, query_key: str, result: Any, ttl: int = 300):
        """Cache query result with TTL"""
        self.query_cache[query_key] = {
            'result': result,
            'timestamp': datetime.now(),
            'ttl': ttl
        }
        
    def get_cached_result(self, query_key: str) -> Optional[Any]:
        """Get cached query result if valid"""
        if query_key not in self.query_cache:
            return None
            
        cached = self.query_cache[query_key]
        if datetime.now() - cached['timestamp'] > timedelta(seconds=cached['ttl']):
            del self.query_cache[query_key]
            return None
            
        return cached['result']
        
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear query cache"""
        if pattern:
            keys_to_remove = [k for k in self.query_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.query_cache[key]
        else:
            self.query_cache.clear()
            
    def get_slow_queries(self, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get queries slower than threshold"""
        threshold = threshold or self.slow_query_threshold
        
        slow_queries = []
        for query_key, stats in self.query_stats.items():
            if stats['avg_time'] > threshold:
                slow_queries.append({
                    'query_key': query_key,
                    'count': stats['count'],
                    'avg_time': round(stats['avg_time'], 3),
                    'total_time': round(stats['total_time'], 3)
                })
                
        return sorted(slow_queries, key=lambda x: x['avg_time'], reverse=True)
        
    def vacuum_analyze_tables(self, tables: Optional[List[str]] = None):
        """Run VACUUM ANALYZE on tables (PostgreSQL)"""
        if not self.engine.url.drivername.startswith('postgresql'):
            logger.warning("VACUUM ANALYZE only available for PostgreSQL")
            return
            
        tables = tables or ['fretes', 'pedidos', 'carteira_principal', 'embarques']
        
        with self.engine.connect() as conn:
            # Need to be outside transaction for VACUUM
            conn.execute(text("COMMIT"))
            for table in tables:
                try:
                    conn.execute(text(f"VACUUM ANALYZE {table}"))
                    logger.info(f"VACUUM ANALYZE completed for {table}")
                except Exception as e:
                    logger.error(f"Error running VACUUM ANALYZE on {table}: {str(e)}")
                    
    def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics"""
        with self.engine.connect() as conn:
            # Row count
            row_count = conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()
            
            # Table size (PostgreSQL specific)
            if self.engine.url.drivername.startswith('postgresql'):
                size_result = conn.execute(
                    text(f"SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))")
                ).scalar()
                
                # Index information
                index_result = conn.execute(text(f"""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = '{table_name}'
                """)).fetchall()
                
                indexes = [{'name': r[0], 'definition': r[1]} for r in index_result]
            else:
                size_result = 'N/A'
                indexes = []
                
            return {
                'table_name': table_name,
                'row_count': row_count,
                'size': size_result,
                'indexes': indexes,
                'last_analyzed': datetime.now().isoformat()
            }
            
    def create_missing_indexes(self, recommendations: List[Dict[str, Any]], 
                             dry_run: bool = True) -> List[Dict[str, Any]]:
        """Create recommended indexes"""
        results = []
        
        with self.engine.connect() as conn:
            for rec in recommendations:
                try:
                    if dry_run:
                        results.append({
                            'index': rec.get('sql', ''),
                            'status': 'dry_run',
                            'message': 'Would create index'
                        })
                    else:
                        conn.execute(text(rec['sql']))
                        conn.commit()
                        results.append({
                            'index': rec.get('sql', ''),
                            'status': 'created',
                            'message': 'Index created successfully'
                        })
                except Exception as e:
                    results.append({
                        'index': rec.get('sql', ''),
                        'status': 'error',
                        'message': str(e)
                    })
                    
        return results


def cached_query(ttl: int = 300):
    """Decorator for caching query results"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Check cache
            if hasattr(self, '_query_cache'):
                cached = self._query_cache.get(cache_key)
                if cached and datetime.now() - cached['timestamp'] < timedelta(seconds=ttl):
                    return cached['result']
                    
            # Execute query
            result = func(self, *args, **kwargs)
            
            # Cache result
            if not hasattr(self, '_query_cache'):
                self._query_cache = {}
                
            self._query_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.now()
            }
            
            return result
        return wrapper
    return decorator


def monitor_query_performance(func):
    """Decorator to monitor query performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Log slow queries
                logger.warning(f"Slow query in {func.__name__}: {execution_time:.2f}s")
                
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query error in {func.__name__} after {execution_time:.2f}s: {str(e)}")
            raise
            
    return wrapper