"""Index Optimizer - Recommends and creates optimal database indexes."""

import logging
from typing import Dict, List, Tuple, Optional, Set
import psycopg2
import psycopg2.extras
from dataclasses import dataclass
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IndexRecommendation:
    """Represents an index recommendation."""
    table_name: str
    columns: List[str]
    index_type: str = 'btree'
    reason: str = ''
    estimated_improvement: float = 0.0
    create_statement: str = ''
    size_estimate: int = 0
    
    def __post_init__(self):
        if not self.create_statement:
            columns_str = ', '.join(self.columns)
            index_name = f"idx_{self.table_name}_{'_'.join(self.columns)}"
            self.create_statement = f"CREATE INDEX {index_name} ON {self.table_name} ({columns_str})"


class IndexOptimizer:
    """Analyzes database and recommends optimal indexes."""
    
    def __init__(self, connection_params: Dict[str, str]):
        self.connection_params = connection_params
        self.existing_indexes: Dict[str, List[Dict]] = {}
        self.table_stats: Dict[str, Dict] = {}
        self.missing_indexes: List[IndexRecommendation] = []
        self.unused_indexes: List[Dict] = []
        self.duplicate_indexes: List[Tuple[Dict, Dict]] = []
    
    def get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(**self.connection_params)
    
    def analyze_missing_indexes(self) -> List[IndexRecommendation]:
        """Identify missing indexes based on query patterns."""
        recommendations = []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Analyze foreign key columns without indexes
                cursor.execute("""
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM pg_indexes
                        WHERE schemaname = 'public'
                        AND tablename = tc.table_name
                        AND indexdef LIKE '%' || kcu.column_name || '%'
                    )
                """)
                
                for row in cursor:
                    recommendations.append(IndexRecommendation(
                        table_name=row['table_name'],
                        columns=[row['column_name']],
                        reason=f"Foreign key to {row['foreign_table_name']} without index",
                        estimated_improvement=0.3
                    ))
                
                # Analyze frequently filtered columns from pg_stat_user_tables
                cursor.execute("""
                    WITH table_scans AS (
                        SELECT 
                            schemaname,
                            tablename,
                            seq_scan,
                            seq_tup_read,
                            idx_scan,
                            idx_tup_fetch,
                            n_tup_ins + n_tup_upd + n_tup_del as write_activity
                        FROM pg_stat_user_tables
                        WHERE schemaname = 'public'
                    )
                    SELECT 
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        CASE 
                            WHEN seq_scan > 0 THEN seq_tup_read::float / seq_scan
                            ELSE 0
                        END as avg_tuples_per_scan
                    FROM table_scans
                    WHERE seq_scan > 100
                    AND seq_tup_read > 10000
                    ORDER BY seq_tup_read DESC
                """)
                
                high_scan_tables = []
                for row in cursor:
                    if row['avg_tuples_per_scan'] > 1000:
                        high_scan_tables.append(row['tablename'])
                
                # Analyze WHERE clauses from pg_stat_statements
                try:
                    cursor.execute("""
                        SELECT 
                            query,
                            calls,
                            total_time,
                            mean_time
                        FROM pg_stat_statements
                        WHERE query LIKE '%WHERE%'
                        AND calls > 10
                        ORDER BY total_time DESC
                        LIMIT 100
                    """)
                    
                    # Parse queries to find frequently filtered columns
                    column_usage = self._analyze_where_clauses(cursor.fetchall())
                    
                    for table, columns in column_usage.items():
                        if table in high_scan_tables:
                            for column, usage_count in columns.items():
                                if usage_count > 50:
                                    recommendations.append(IndexRecommendation(
                                        table_name=table,
                                        columns=[column],
                                        reason=f"Frequently filtered column (used {usage_count} times)",
                                        estimated_improvement=0.5
                                    ))
                except psycopg2.ProgrammingError:
                    logger.warning("pg_stat_statements not available")
        
        self.missing_indexes = recommendations
        return recommendations
    
    def _analyze_where_clauses(self, queries: List) -> Dict[str, Dict[str, int]]:
        """Parse queries to find frequently filtered columns."""
        import re
        column_usage = {}
        
        for query_row in queries:
            query = query_row[0]
            calls = query_row[1]
            
            # Simple regex to extract table.column or column patterns from WHERE
            where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
            if where_match:
                where_clause = where_match.group(1)
                
                # Extract column references
                column_patterns = re.findall(r'(\w+)\.(\w+)\s*[=<>!]|\b(\w+)\s*[=<>!]', where_clause)
                
                for pattern in column_patterns:
                    if pattern[0] and pattern[1]:  # table.column format
                        table = pattern[0]
                        column = pattern[1]
                    elif pattern[2]:  # column only format
                        # Try to infer table from FROM clause
                        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
                        if from_match:
                            table = from_match.group(1)
                            column = pattern[2]
                        else:
                            continue
                    else:
                        continue
                    
                    if table not in column_usage:
                        column_usage[table] = {}
                    column_usage[table][column] = column_usage[table].get(column, 0) + calls
        
        return column_usage
    
    def analyze_unused_indexes(self) -> List[Dict]:
        """Identify indexes that are rarely or never used."""
        unused = []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                        pg_relation_size(indexrelid) as index_size_bytes
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    AND indexrelname NOT LIKE '%_pkey'
                    ORDER BY idx_scan
                """)
                
                for row in cursor:
                    if row['idx_scan'] < 10:
                        unused.append({
                            'schema': row['schemaname'],
                            'table': row['tablename'],
                            'index': row['indexname'],
                            'scans': row['idx_scan'],
                            'size': row['index_size'],
                            'size_bytes': row['index_size_bytes'],
                            'drop_statement': f"DROP INDEX {row['indexname']};"
                        })
        
        self.unused_indexes = unused
        return unused
    
    def analyze_duplicate_indexes(self) -> List[Tuple[Dict, Dict]]:
        """Identify duplicate or redundant indexes."""
        duplicates = []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Get all indexes with their columns
                cursor.execute("""
                    SELECT 
                        t.relname as table_name,
                        i.relname as index_name,
                        array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns,
                        pg_size_pretty(pg_relation_size(i.oid)) as index_size,
                        ix.indisunique as is_unique,
                        ix.indisprimary as is_primary
                    FROM pg_index ix
                    JOIN pg_class t ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    WHERE t.relkind = 'r'
                    AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                    GROUP BY t.relname, i.relname, i.oid, ix.indisunique, ix.indisprimary
                    ORDER BY t.relname, array_length(ix.indkey, 1) DESC
                """)
                
                indexes_by_table = {}
                for row in cursor:
                    table = row['table_name']
                    if table not in indexes_by_table:
                        indexes_by_table[table] = []
                    indexes_by_table[table].append(row)
                
                # Check for duplicates within each table
                for table, indexes in indexes_by_table.items():
                    for i in range(len(indexes)):
                        for j in range(i + 1, len(indexes)):
                            idx1 = indexes[i]
                            idx2 = indexes[j]
                            
                            # Check if idx2 columns are a prefix of idx1 columns
                            if self._is_index_redundant(idx1['columns'], idx2['columns']):
                                duplicates.append((dict(idx1), dict(idx2)))
        
        self.duplicate_indexes = duplicates
        return duplicates
    
    def _is_index_redundant(self, columns1: List[str], columns2: List[str]) -> bool:
        """Check if one index makes another redundant."""
        # If columns2 is a prefix of columns1, then columns1 can serve queries that columns2 serves
        if len(columns2) <= len(columns1):
            return columns2 == columns1[:len(columns2)]
        return False
    
    def analyze_index_bloat(self) -> List[Dict]:
        """Identify bloated indexes that need rebuilding."""
        bloated = []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    WITH index_bloat AS (
                        SELECT
                            schemaname,
                            tablename,
                            indexname,
                            pg_size_pretty(real_size) as real_size,
                            pg_size_pretty(extra_size) as bloat_size,
                            round(100 * extra_ratio)::text || '%' as bloat_ratio,
                            real_size,
                            extra_size,
                            extra_ratio
                        FROM (
                            SELECT
                                schemaname, tablename, indexname,
                                pg_relation_size(schemaname||'.'||indexname) as real_size,
                                pg_relation_size(schemaname||'.'||indexname) - 
                                pg_relation_size(schemaname||'.'||indexname) * 
                                (1 - avg_leaf_density) as extra_size,
                                (1 - avg_leaf_density) as extra_ratio
                            FROM (
                                SELECT
                                    schemaname, tablename, indexname,
                                    CASE WHEN indexpages = 0 THEN 0.0
                                         ELSE round(100.0 * relpages / indexpages) / 100.0
                                    END AS avg_leaf_density
                                FROM (
                                    SELECT
                                        schemaname,
                                        tablename,
                                        indexname,
                                        reltuples,
                                        relpages,
                                        reltuples / (relpages + 1) AS tuples_per_page,
                                        CASE WHEN reltuples > 0 THEN
                                            relpages * 100 / (reltuples * 16 / 1024 + 1)
                                        ELSE 0 END AS indexpages
                                    FROM pg_stat_user_indexes i
                                    JOIN pg_class c ON c.relname = i.indexrelname
                                    WHERE schemaname = 'public'
                                ) AS index_atts
                            ) AS index_density
                        ) AS index_bloat_details
                        WHERE real_size > 1024 * 1024  -- Only indexes > 1MB
                        AND extra_ratio > 0.2  -- More than 20% bloat
                    )
                    SELECT * FROM index_bloat
                    ORDER BY extra_size DESC
                """)
                
                for row in cursor:
                    bloated.append({
                        'schema': row['schemaname'],
                        'table': row['tablename'],
                        'index': row['indexname'],
                        'real_size': row['real_size'],
                        'bloat_size': row['bloat_size'],
                        'bloat_ratio': row['bloat_ratio'],
                        'rebuild_statement': f"REINDEX INDEX {row['schemaname']}.{row['indexname']};"
                    })
        
        return bloated
    
    def generate_optimization_script(self, output_file: str = 'index_optimization.sql'):
        """Generate SQL script with all optimization recommendations."""
        script_lines = [
            "-- Index Optimization Script",
            "-- Generated by IndexOptimizer",
            f"-- Database: {self.connection_params.get('database')}",
            "-- " + "=" * 50,
            ""
        ]
        
        # Missing indexes
        if self.missing_indexes:
            script_lines.append("-- Missing Indexes")
            script_lines.append("-- " + "-" * 30)
            for idx in self.missing_indexes:
                script_lines.append(f"-- Reason: {idx.reason}")
                script_lines.append(f"-- Estimated improvement: {idx.estimated_improvement * 100:.0f}%")
                script_lines.append(f"{idx.create_statement};")
                script_lines.append("")
        
        # Unused indexes
        if self.unused_indexes:
            script_lines.append("\n-- Unused Indexes (consider dropping)")
            script_lines.append("-- " + "-" * 30)
            for idx in self.unused_indexes:
                script_lines.append(f"-- Index: {idx['index']} on {idx['table']}")
                script_lines.append(f"-- Size: {idx['size']}, Scans: {idx['scans']}")
                script_lines.append(f"-- {idx['drop_statement']}")
                script_lines.append("")
        
        # Duplicate indexes
        if self.duplicate_indexes:
            script_lines.append("\n-- Duplicate/Redundant Indexes")
            script_lines.append("-- " + "-" * 30)
            for idx1, idx2 in self.duplicate_indexes:
                script_lines.append(f"-- {idx1['index_name']} covers {idx2['index_name']}")
                script_lines.append(f"-- Consider dropping: DROP INDEX {idx2['index_name']};")
                script_lines.append("")
        
        # Bloated indexes
        bloated = self.analyze_index_bloat()
        if bloated:
            script_lines.append("\n-- Bloated Indexes (consider rebuilding)")
            script_lines.append("-- " + "-" * 30)
            for idx in bloated:
                script_lines.append(f"-- Index: {idx['index']} ({idx['bloat_ratio']} bloat)")
                script_lines.append(f"{idx['rebuild_statement']}")
                script_lines.append("")
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(script_lines))
        
        logger.info(f"Optimization script generated: {output_file}")
        return output_file
    
    def apply_recommendations(self, dry_run: bool = True):
        """Apply index recommendations to the database."""
        if dry_run:
            logger.info("DRY RUN - No changes will be made")
        
        results = []
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for idx in self.missing_indexes:
                    try:
                        if dry_run:
                            logger.info(f"Would create: {idx.create_statement}")
                        else:
                            cursor.execute(idx.create_statement)
                            conn.commit()
                            logger.info(f"Created index: {idx.create_statement}")
                        results.append({'action': 'create', 'index': idx.create_statement, 'status': 'success'})
                    except Exception as e:
                        logger.error(f"Error creating index: {e}")
                        results.append({'action': 'create', 'index': idx.create_statement, 'status': 'error', 'error': str(e)})
                
                # Don't auto-drop indexes in production
                if not dry_run:
                    logger.warning("Skipping automatic index drops - review manually")
        
        return results


if __name__ == "__main__":
    # Example usage
    optimizer = IndexOptimizer({
        'host': 'localhost',
        'port': 5432,
        'database': 'frete_db',
        'user': 'postgres',
        'password': 'postgres'
    })
    
    # Analyze missing indexes
    missing = optimizer.analyze_missing_indexes()
    print(f"Found {len(missing)} missing indexes")
    
    # Analyze unused indexes
    unused = optimizer.analyze_unused_indexes()
    print(f"Found {len(unused)} unused indexes")
    
    # Generate optimization script
    optimizer.generate_optimization_script()