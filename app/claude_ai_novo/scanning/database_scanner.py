"""
🗄️ DATABASE SCANNER - Escaneamento de Banco de Dados
===================================================

Especialista em descoberta e análise de esquema
de banco de dados e estatísticas.

Responsabilidades:
- Descoberta de esquema do banco
- Análise de relacionamentos
- Estatísticas de tabelas
- Informações de índices
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import inspect as sql_inspect, text
from flask import current_app
from datetime import datetime
from app.claude_ai_novo.utils.flask_fallback import get_db

logger = logging.getLogger(__name__)

class DatabaseScanner:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """
    Especialista em escaneamento de banco de dados.
    
    Descobre esquema completo, relacionamentos e
    estatísticas do banco de dados da aplicação.
    """
    
    def __init__(self):
        """Inicializa o scanner de banco de dados"""
        logger.info("🗄️ DatabaseScanner inicializado")
    
    def discover_database_schema(self) -> Dict[str, Any]:
        """
        Descobre esquema completo do banco de dados dinamicamente.
        
        Returns:
            Dict com esquema completo
        """
        schema = {}
        
        try:
            inspector = sql_inspect(self.db.engine)
            
            # Informações gerais do banco
            schema['database_info'] = {
                'dialect': str(self.db.engine.dialect.name),
                'driver': str(self.db.engine.driver),
                'server_version': self._get_database_version()
            }
            
            # Todas as tabelas
            table_names = inspector.get_table_names()
            schema['tables'] = {}
            
            for table_name in table_names:
                try:
                    schema['tables'][table_name] = {
                        'columns': inspector.get_columns(table_name),
                        'primary_keys': inspector.get_pk_constraint(table_name),
                        'foreign_keys': inspector.get_foreign_keys(table_name),
                        'indexes': inspector.get_indexes(table_name),
                        'unique_constraints': inspector.get_unique_constraints(table_name),
                        'check_constraints': self._get_check_constraints(inspector, table_name)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao inspecionar tabela {table_name}: {e}")
                    schema['tables'][table_name] = {'error': str(e)}
            
            # Estatísticas de tabelas
            schema['table_statistics'] = self._get_table_statistics()
            
            # Análise de relacionamentos
            schema['relationships_analysis'] = self._analyze_relationships(schema['tables'])
            
            # Informações de performance
            schema['performance_info'] = self._get_performance_info()
            
            logger.info(f"🗄️ Esquema do banco descoberto: {len(schema['tables'])} tabelas")
            return schema
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir esquema do banco: {e}")
            return {
                'error': str(e),
                'database_info': {},
                'tables': {},
                'table_statistics': {},
                'relationships_analysis': {},
                'performance_info': {}
            }
    
    def _get_database_version(self) -> str:
        """Obtém versão do banco de dados"""
        try:
            dialect_name = str(self.db.engine.dialect.name).lower()
            
            if 'postgresql' in dialect_name:
                result = self.db.session.execute(text("SELECT version();")).fetchone()
                return result[0] if result else "PostgreSQL - versão desconhecida"
            elif 'mysql' in dialect_name:
                result = self.db.session.execute(text("SELECT version();")).fetchone()
                return result[0] if result else "MySQL - versão desconhecida"
            elif 'sqlite' in dialect_name:
                result = self.db.session.execute(text("SELECT sqlite_version();")).fetchone()
                return f"SQLite {result[0]}" if result else "SQLite - versão desconhecida"
            else:
                return f"{dialect_name} - versão desconhecida"
                
        except Exception as e:
            logger.debug(f"Erro ao obter versão do banco: {e}")
            return "Versão desconhecida"
    
    def _get_check_constraints(self, inspector, table_name: str) -> List[Dict]:
        """Obtém check constraints da tabela"""
        try:
            if hasattr(inspector, 'get_check_constraints'):
                return inspector.get_check_constraints(table_name)
        except Exception as e:
            logger.debug(f"Erro ao obter check constraints: {e}")
        return []
    
    def _get_table_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas das tabelas"""
        try:
            dialect_name = str(self.db.engine.dialect.name).lower()
            
            if 'postgresql' in dialect_name:
                return self._get_postgresql_statistics()
            elif 'mysql' in dialect_name:
                return self._get_mysql_statistics()
            elif 'sqlite' in dialect_name:
                return self._get_sqlite_statistics()
            else:
                return {'message': 'Estatísticas não disponíveis para este banco'}
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter estatísticas: {e}")
            return {'error': str(e)}
    
    def _get_postgresql_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas específicas do PostgreSQL"""
        try:
            # Tamanho das tabelas
            result = self.db.session.execute(text("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 50
            """)).fetchall()
            
            table_sizes = [
                {
                    'table': row[0], 
                    'size_pretty': row[1], 
                    'size_bytes': row[2]
                } 
                for row in result
            ]
            
            # Estatísticas de índices
            index_stats = self.db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_tup_read DESC
                LIMIT 20
            """)).fetchall()
            
            index_usage = [
                {
                    'table': row[1],
                    'index': row[2],
                    'reads': row[3],
                    'fetches': row[4]
                }
                for row in index_stats
            ]
            
            return {
                'dialect': 'postgresql',
                'table_sizes': table_sizes,
                'index_usage': index_usage,
                'total_tables': len(table_sizes)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter estatísticas PostgreSQL: {e}")
            return {'error': str(e)}
    
    def _get_mysql_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas específicas do MySQL"""
        try:
            # Tamanho das tabelas
            result = self.db.session.execute(text("""
                SELECT 
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) as size_mb,
                    table_rows
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                ORDER BY (data_length + index_length) DESC
                LIMIT 50
            """)).fetchall()
            
            table_sizes = [
                {
                    'table': row[0], 
                    'size_mb': row[1],
                    'rows': row[2]
                } 
                for row in result
            ]
            
            return {
                'dialect': 'mysql',
                'table_sizes': table_sizes,
                'total_tables': len(table_sizes)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter estatísticas MySQL: {e}")
            return {'error': str(e)}
    
    def _get_sqlite_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas específicas do SQLite"""
        try:
            # Informações das tabelas
            result = self.db.session.execute(text("""
                SELECT 
                    name,
                    sql
                FROM sqlite_master 
                WHERE type = 'table'
                ORDER BY name
            """)).fetchall()
            
            tables_info = [
                {
                    'table': row[0],
                    'create_sql': row[1]
                }
                for row in result
            ]
            
            return {
                'dialect': 'sqlite',
                'tables_info': tables_info,
                'total_tables': len(tables_info)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter estatísticas SQLite: {e}")
            return {'error': str(e)}
    
    def _analyze_relationships(self, tables: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa relacionamentos entre tabelas"""
        analysis = {
            'total_foreign_keys': 0,
            'relationships_map': {},
            'orphaned_tables': [],
            'highly_connected_tables': []
        }
        
        try:
            connection_count = {}
            
            for table_name, table_info in tables.items():
                if isinstance(table_info, dict) and 'foreign_keys' in table_info:
                    fks = table_info['foreign_keys']
                    analysis['total_foreign_keys'] += len(fks)
                    
                    connection_count[table_name] = len(fks)
                    
                    # Mapear relacionamentos
                    for fk in fks:
                        if fk.get('referred_table'):
                            rel_key = f"{table_name} -> {fk['referred_table']}"
                            analysis['relationships_map'][rel_key] = {
                                'from_table': table_name,
                                'to_table': fk['referred_table'],
                                'foreign_key_column': fk.get('constrained_columns', []),
                                'referenced_column': fk.get('referred_columns', [])
                            }
            
            # Identificar tabelas órfãs (sem FKs)
            analysis['orphaned_tables'] = [
                table for table, count in connection_count.items() 
                if count == 0
            ]
            
            # Identificar tabelas altamente conectadas
            analysis['highly_connected_tables'] = [
                {'table': table, 'connections': count}
                for table, count in connection_count.items()
                if count > 3
            ]
            
            analysis['connection_summary'] = {
                'total_connections': len(analysis['relationships_map']),
                'avg_connections_per_table': round(
                    sum(connection_count.values()) / len(connection_count), 2
                ) if connection_count else 0
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao analisar relacionamentos: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _get_performance_info(self) -> Dict[str, Any]:
        """Obtém informações de performance do banco"""
        try:
            dialect_name = str(self.db.engine.dialect.name).lower()
            
            performance_info = {
                'dialect': dialect_name,
                'connection_pool_size': getattr(self.db.engine.pool, 'size', 'unknown'),
                'connection_pool_checked_out': getattr(self.db.engine.pool, 'checked_out', 'unknown'),
                'connection_pool_overflow': getattr(self.db.engine.pool, 'overflow', 'unknown'),
                'connection_pool_checked_in': getattr(self.db.engine.pool, 'checked_in', 'unknown')
            }
            
            # Informações específicas por dialect
            if 'postgresql' in dialect_name:
                performance_info.update(self._get_postgresql_performance())
            elif 'mysql' in dialect_name:
                performance_info.update(self._get_mysql_performance())
            
            return performance_info
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter informações de performance: {e}")
            return {'error': str(e)}
    
    def _get_postgresql_performance(self) -> Dict[str, Any]:
        """Obtém informações de performance do PostgreSQL"""
        try:
            # Conexões ativas
            result = self.db.session.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
            """)).fetchone()
            
            return {
                'total_connections': result[0] if result else 0,
                'active_connections': result[1] if result else 0,
                'idle_connections': result[2] if result else 0
            }
            
        except Exception as e:
            logger.debug(f"Erro ao obter performance PostgreSQL: {e}")
            return {}
    
    def _get_mysql_performance(self) -> Dict[str, Any]:
        """Obtém informações de performance do MySQL"""
        try:
            # Conexões ativas
            result = self.db.session.execute(text("SHOW STATUS LIKE 'Threads_connected'")).fetchone()
            
            return {
                'threads_connected': result[1] if result else 0
            }
            
        except Exception as e:
            logger.debug(f"Erro ao obter performance MySQL: {e}")
            return {}
    
    def obter_estatisticas_gerais(self) -> Dict[str, Any]:
        """
        Obtém estatísticas gerais do banco de dados.
        
        Returns:
            Dict com estatísticas gerais
        """
        try:
            inspector = sql_inspect(self.db.engine)
            table_names = inspector.get_table_names()
            
            # Estatísticas básicas
            estatisticas = {
                'total_tabelas': len(table_names),
                'tabelas': table_names,
                'dialect': str(self.db.engine.dialect.name),
                'driver': str(self.db.engine.driver),
                'timestamp': datetime.now().isoformat()
            }
            
            # Adicionar estatísticas detalhadas se disponíveis
            detailed_stats = self._get_table_statistics()
            if detailed_stats and 'error' not in detailed_stats:
                estatisticas.update(detailed_stats)
            
            # Análise de relacionamentos
            schema = {'tables': {}}
            for table_name in table_names[:10]:  # Limitar para performance
                try:
                    schema['tables'][table_name] = {
                        'columns': inspector.get_columns(table_name),
                        'foreign_keys': inspector.get_foreign_keys(table_name)
                    }
                except Exception as e:
                    logger.debug(f"Erro ao inspecionar {table_name}: {e}")
            
            relationships = self._analyze_relationships(schema['tables'])
            estatisticas['relacionamentos'] = relationships
            
            logger.info(f"📊 Estatísticas gerais: {estatisticas['total_tabelas']} tabelas")
            return estatisticas
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas gerais: {e}")
            return {
                'error': str(e),
                'total_tabelas': 0,
                'tabelas': []
            }


# Singleton para uso global
_database_scanner = None

def get_database_scanner() -> DatabaseScanner:
    """
    Obtém instância do scanner de banco de dados.
    
    Returns:
        Instância do DatabaseScanner
    """
    global _database_scanner
    if _database_scanner is None:
        _database_scanner = DatabaseScanner()
    return _database_scanner 
