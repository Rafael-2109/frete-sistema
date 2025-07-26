"""
🗄️ DATABASE LOADER - Carregador de Dados do Banco
==============================================

Módulo responsável por carregar dados do banco de dados PostgreSQL
para o sistema Claude AI Novo.

Função: Abstrair acesso ao banco de dados e fornecer interface
consistente para carregamento de dados.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, date

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Configuração do banco de dados"""
    host: str = "localhost"
    port: int = 5432
    database: str = "sistema_fretes"
    username: str = "postgres"
    password: str = ""
    
class DatabaseLoader:
    """
    Carregador de dados do banco de dados.
    
    Responsável por conectar ao PostgreSQL e carregar dados
    para o sistema Claude AI de forma otimizada.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Inicializa o carregador de banco de dados.
        
        Args:
            config: Configuração do banco de dados
        """
        self.config = config or DatabaseConfig()
        self._connection = None
        self._session = None
        self._available = False
        
        # Tentar inicializar conexão
        self._initialize_connection()
        
    def _initialize_connection(self):
        """Inicializa conexão com o banco de dados"""
        try:
            # Tentar importar SQLAlchemy
            import sqlalchemy as sa
        except Exception as e:
            logger.error(f'Erro: {e}')
            pass
try:
    from sqlalchemy import create_engine
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    create_engine = None
    SQLALCHEMY_AVAILABLE = False
            from sqlalchemy.orm import sessionmaker
            
            # Construir URL de conexão
            db_url = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
            
            # Criar engine
            self._engine = create_engine(db_url, echo=False)
            
            # Criar session factory
            Session = sessionmaker(bind=self._engine)
            self._session_factory = Session
            
            # Testar conexão
            with self._engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
                
            self._available = True
            logger.info("🗄️ DatabaseLoader inicializado com sucesso")
            
        except ImportError:
            logger.warning("📦 SQLAlchemy não disponível - usando modo mock")
            self._available = False
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao conectar ao banco: {e} - usando modo mock")
            self._available = False
    
    def is_available(self) -> bool:
        """
        Verifica se o carregador está disponível.
        
        Returns:
            True se conexão com banco está ativa
        """
        return self._available
    
    def load_data(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados usando query SQL.
        
        Args:
            query: Query SQL a ser executada
            parameters: Parâmetros para a query
            
        Returns:
            Lista de registros como dicionários
        """
        if not self.is_available():
            logger.warning("🔌 Banco não disponível - retornando dados mock")
            return self._get_mock_data()
        
        try:
            import sqlalchemy as sa
            
            with self._engine.connect() as conn:
                result = conn.execute(sa.text(query), parameters or {})
                rows = result.fetchall()
                
                # Converter para dicionários
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")
            return []
    
    def load_table_data(self, table_name: str, filters: Optional[Dict[str, Any]] = None, 
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Carrega dados de uma tabela específica.
        
        Args:
            table_name: Nome da tabela
            filters: Filtros a serem aplicados
            limit: Limite de registros
            
        Returns:
            Lista de registros da tabela
        """
        if not self.is_available():
            return self._get_mock_data()
        
        try:
            # Construir query base
            query = f"SELECT * FROM {table_name}"
            parameters = {}
            
            # Aplicar filtros
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = :{key}")
                    parameters[key] = value
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            # Aplicar limite
            if limit:
                query += f" LIMIT {limit}"
            
            return self.load_data(query, parameters)
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar tabela {table_name}: {e}")
            return []
    
    # Métodos específicos de domínio removidos - use micro-loaders em domain/
    # Para carregar dados especializados, use:
    # from .domain.pedidos_loader import get_pedidos_loader
    # from .domain.entregas_loader import get_entregas_loader
    # etc.
    
    def _get_mock_data(self) -> List[Dict[str, Any]]:
        """
        Retorna dados mock para teste quando banco não está disponível.
        
        Returns:
            Lista de dados mock
        """
        return [
            {
                'id': 1,
                'nome': 'Dados Mock',
                'status': 'ativo',
                'created_at': datetime.now(),
                'observacao': 'Dados simulados - banco não disponível'
            },
            {
                'id': 2,
                'nome': 'Teste Database Loader',
                'status': 'mock',
                'created_at': datetime.now(),
                'observacao': 'Teste de funcionamento do carregador'
            }
        ]
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Obtém informações sobre a conexão.
        
        Returns:
            Dict com informações da conexão
        """
        return {
            'available': self._available,
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'username': self.config.username,
            'status': 'connected' if self._available else 'disconnected'
        }
    
    def close(self):
        """Fecha conexão com o banco de dados"""
        if self._session:
            self._session.close()
            self._session = None
            
        if hasattr(self, '_engine') and self._engine:
            self._engine.dispose()
            
        self._available = False
        logger.info("🔌 DatabaseLoader desconectado")
    
    def __del__(self):
        """Destrutor para garantir que conexão seja fechada"""
        try:
            self.close()
        except:
            pass

# Instância global
_database_loader = None

def get_database_loader(config: Optional[DatabaseConfig] = None) -> DatabaseLoader:
    """
    Retorna instância global do DatabaseLoader.
    
    Args:
        config: Configuração do banco (opcional)
        
    Returns:
        DatabaseLoader: Instância do carregador
    """
    global _database_loader
    if _database_loader is None:
        _database_loader = DatabaseLoader(config)
    return _database_loader

# Funções de conveniência específicas removidas - use o LoaderManager:
# from .loader_manager import get_loader_manager
# manager = get_loader_manager()
# dados = manager.load_data_by_domain('pedidos', filters)

# Exports
__all__ = [
    'DatabaseLoader',
    'DatabaseConfig',
    'get_database_loader'
    # Funções específicas de domínio foram movidas para LoaderManager
] 