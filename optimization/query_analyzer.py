"""Query Analyzer - Identifies slow queries and performance bottlenecks."""

import time
import logging
import statistics
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
from dataclasses import dataclass, field
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for a single query."""
    query: str
    execution_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    std_dev: float = 0.0
    execution_times: List[float] = field(default_factory=list)
    query_plan: Optional[Dict] = None
    table_scans: int = 0
    index_scans: int = 0
    rows_examined: int = 0
    rows_returned: int = 0
    
    def add_execution(self, duration: float, rows_examined: int = 0, rows_returned: int = 0):
        """Add a new execution time to the statistics."""
        self.execution_count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.execution_times.append(duration)
        self.avg_time = self.total_time / self.execution_count
        self.rows_examined += rows_examined
        self.rows_returned += rows_returned
        
        if len(self.execution_times) > 1:
            self.std_dev = statistics.stdev(self.execution_times)


class QueryAnalyzer:
    """Analyzes database queries for performance issues."""
    
    def __init__(self, connection_params: Dict[str, str]):
        self.connection_params = connection_params
        self.query_stats: Dict[str, QueryStats] = {}
        self.slow_query_threshold = 1.0  # seconds
        self.problematic_patterns = [
            (r'SELECT \* FROM', 'Avoid SELECT *, specify columns explicitly'),
            (r'NOT IN \(SELECT', 'Consider using NOT EXISTS or LEFT JOIN'),
            (r'LIKE \'%.*\'', 'Leading wildcard prevents index usage'),
            (r'OR\s+\w+\s*=', 'Multiple OR conditions may prevent index usage'),
            (r'DISTINCT', 'Consider if DISTINCT is necessary, may indicate missing JOIN'),
            (r'ORDER BY RAND\(\)', 'ORDER BY RAND() is very inefficient'),
            (r'OFFSET \d{4,}', 'Large OFFSET values are inefficient, consider keyset pagination'),
        ]
    
    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = psycopg2.connect(**self.connection_params)
        try:
            yield conn
        finally:
            conn.close()
    
    def analyze_query(self, query: str, params: Optional[Tuple] = None) -> Dict[str, Any]:
        """Analyze a single query for performance issues."""
        import re
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get query execution plan
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                
                start_time = time.time()
                try:
                    cursor.execute(explain_query, params)
                    plan = cursor.fetchone()[0][0]
                    execution_time = time.time() - start_time
                except Exception as e:
                    logger.error(f"Error analyzing query: {e}")
                    return {"error": str(e)}
                
                # Extract statistics from plan
                total_cost = plan.get('Plan', {}).get('Total Cost', 0)
                actual_time = plan.get('Plan', {}).get('Actual Total Time', 0)
                rows_examined = plan.get('Plan', {}).get('Actual Rows', 0)
                
                # Check for sequential scans
                seq_scans = self._count_node_types(plan.get('Plan', {}), 'Seq Scan')
                index_scans = self._count_node_types(plan.get('Plan', {}), 'Index Scan')
                
                # Check for problematic patterns
                issues = []
                for pattern, message in self.problematic_patterns:
                    if re.search(pattern, query, re.IGNORECASE):
                        issues.append(message)
                
                # Check for missing indexes
                if seq_scans > 0 and rows_examined > 1000:
                    issues.append(f"Sequential scan on large table ({rows_examined} rows)")
                
                # Check for inefficient joins
                nested_loops = self._count_node_types(plan.get('Plan', {}), 'Nested Loop')
                if nested_loops > 2:
                    issues.append("Multiple nested loops detected, consider optimizing joins")
                
                return {
                    'query': query,
                    'execution_time': actual_time / 1000.0,  # Convert to seconds
                    'total_cost': total_cost,
                    'rows_examined': rows_examined,
                    'seq_scans': seq_scans,
                    'index_scans': index_scans,
                    'issues': issues,
                    'plan': plan,
                    'recommendations': self._generate_recommendations(plan, issues)
                }
    
    def _count_node_types(self, plan: Dict, node_type: str) -> int:
        """Count occurrences of a specific node type in the query plan."""
        count = 0
        if plan.get('Node Type') == node_type:
            count += 1
        
        for child in plan.get('Plans', []):
            count += self._count_node_types(child, node_type)
        
        return count
    
    def _generate_recommendations(self, plan: Dict, issues: List[str]) -> List[str]:
        """Generate optimization recommendations based on the query plan."""
        recommendations = []
        
        # Check startup cost vs total cost
        if plan.get('Plan', {}).get('Startup Cost', 0) > plan.get('Plan', {}).get('Total Cost', 0) * 0.5:
            recommendations.append("High startup cost detected, consider adding appropriate indexes")
        
        # Check for sort operations
        if self._count_node_types(plan.get('Plan', {}), 'Sort') > 0:
            recommendations.append("Sort operation detected, consider adding an index on ORDER BY columns")
        
        # Check buffer usage
        shared_hit = plan.get('Plan', {}).get('Shared Hit Blocks', 0)
        shared_read = plan.get('Plan', {}).get('Shared Read Blocks', 0)
        if shared_read > 0 and shared_hit / (shared_read + shared_hit) < 0.9:
            recommendations.append("Low buffer cache hit ratio, consider increasing shared_buffers")
        
        return recommendations
    
    def monitor_queries(self, duration_minutes: int = 60) -> Dict[str, QueryStats]:
        """Monitor database queries for a specified duration."""
        logger.info(f"Starting query monitoring for {duration_minutes} minutes...")
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                while datetime.now() < end_time:
                    # Get current queries from pg_stat_statements
                    cursor.execute("""
                        SELECT 
                            query,
                            calls,
                            total_time,
                            mean_time,
                            min_time,
                            max_time,
                            stddev_time,
                            rows
                        FROM pg_stat_statements
                        WHERE query NOT LIKE '%pg_stat_statements%'
                        ORDER BY total_time DESC
                        LIMIT 100
                    """)
                    
                    for row in cursor:
                        query_hash = self._normalize_query(row['query'])
                        if query_hash not in self.query_stats:
                            self.query_stats[query_hash] = QueryStats(query=row['query'])
                        
                        stats = self.query_stats[query_hash]
                        stats.execution_count = row['calls']
                        stats.total_time = row['total_time'] / 1000.0  # Convert to seconds
                        stats.avg_time = row['mean_time'] / 1000.0
                        stats.min_time = row['min_time'] / 1000.0
                        stats.max_time = row['max_time'] / 1000.0
                        stats.std_dev = row['stddev_time'] / 1000.0
                        stats.rows_returned = row['rows']
                    
                    time.sleep(5)  # Check every 5 seconds
        
        return self.query_stats
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for comparison (remove literals)."""
        import re
        # Remove numeric literals
        query = re.sub(r'\b\d+\b', '?', query)
        # Remove string literals
        query = re.sub(r"\'[^\']*\'", '?', query)
        # Remove whitespace variations
        query = ' '.join(query.split())
        return query
    
    def identify_slow_queries(self, threshold_seconds: Optional[float] = None) -> List[Dict[str, Any]]:
        """Identify queries that exceed the slow query threshold."""
        threshold = threshold_seconds or self.slow_query_threshold
        slow_queries = []
        
        for query_hash, stats in self.query_stats.items():
            if stats.avg_time > threshold:
                analysis = self.analyze_query(stats.query)
                slow_queries.append({
                    'query': stats.query,
                    'avg_time': stats.avg_time,
                    'execution_count': stats.execution_count,
                    'total_time': stats.total_time,
                    'analysis': analysis
                })
        
        return sorted(slow_queries, key=lambda x: x['total_time'], reverse=True)
    
    def generate_report(self, output_file: str = 'query_analysis_report.json'):
        """Generate a comprehensive query analysis report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_queries_analyzed': len(self.query_stats),
                'slow_queries': len([s for s in self.query_stats.values() if s.avg_time > self.slow_query_threshold]),
                'total_execution_time': sum(s.total_time for s in self.query_stats.values()),
            },
            'slow_queries': self.identify_slow_queries(),
            'top_queries_by_time': self._get_top_queries_by_total_time(10),
            'top_queries_by_frequency': self._get_top_queries_by_frequency(10),
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Query analysis report generated: {output_file}")
        return report
    
    def _get_top_queries_by_total_time(self, limit: int) -> List[Dict[str, Any]]:
        """Get top queries by total execution time."""
        sorted_queries = sorted(self.query_stats.items(), 
                              key=lambda x: x[1].total_time, 
                              reverse=True)
        return [
            {
                'query': stats.query,
                'total_time': stats.total_time,
                'execution_count': stats.execution_count,
                'avg_time': stats.avg_time
            }
            for _, stats in sorted_queries[:limit]
        ]
    
    def _get_top_queries_by_frequency(self, limit: int) -> List[Dict[str, Any]]:
        """Get top queries by execution frequency."""
        sorted_queries = sorted(self.query_stats.items(), 
                              key=lambda x: x[1].execution_count, 
                              reverse=True)
        return [
            {
                'query': stats.query,
                'execution_count': stats.execution_count,
                'total_time': stats.total_time,
                'avg_time': stats.avg_time
            }
            for _, stats in sorted_queries[:limit]
        ]


if __name__ == "__main__":
    # Example usage
    analyzer = QueryAnalyzer({
        'host': 'localhost',
        'port': 5432,
        'database': 'frete_db',
        'user': 'postgres',
        'password': 'postgres'
    })
    
    # Analyze a specific query
    result = analyzer.analyze_query(
        "SELECT * FROM cotacoes WHERE status = %s ORDER BY data_criacao DESC",
        ('pendente',)
    )
    print(json.dumps(result, indent=2, default=str))
    
    # Monitor queries for 5 minutes
    # analyzer.monitor_queries(5)
    # analyzer.generate_report()