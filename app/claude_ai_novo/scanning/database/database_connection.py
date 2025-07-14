"""
🔌 DATABASE CONNECTION - Gestão de Conexões com Banco de Dados

Módulo responsável por gerenciar conexões com o banco de dados PostgreSQL.
Suporta múltiplas formas de conexão (Flask, direta, etc.).
"""

import logging
from typing import Optional, Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session
from sqlalchemy.engine.reflection import Inspector
import os
import sys

# Adicionar path para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Gerenciador de conexões com banco de dados.
    
    Responsável por estabelecer e manter conexões com o banco
    através de diferentes métodos (Flask, direto, etc.).
    """
    
    def __init__(self, db_engine: Optional[Engine] = None, db_session: Optional[Session] = None):
        """
        Inicializa o gerenciador de conexões.
        
        Args:
            db_engine: Engine do SQLAlchemy (opcional)
            db_session: Sessão do SQLAlchemy (opcional)
        """
        self.db_engine = db_engine
        self.db_session = db_session
        self.inspector: Optional[Inspector] = None
        self.connection_method = "none"
        
        # Tentar obter conexão se não fornecida
        if not self.db_engine or not self.db_session:
            self._establish_connection()
        
        # Inicializar inspector se engine disponível
        if self.db_engine:
            self._initialize_inspector()
    
    def _establish_connection(self) -> None:
        """
        Estabelece conexão com o banco usando diferentes métodos.
        """
        # Método 1: Tentar via Flask
        if self._try_flask_connection():
            self.connection_method = "flask"
            return
        
        # Método 2: Tentar conexão direta
        if self._try_direct_connection():
            self.connection_method = "direct"
            return
        
        # Método 3: Tentar variáveis de ambiente
        if self._try_env_connection():
            self.connection_method = "environment"
            return
        
        logger.warning("⚠️ Nenhuma conexão com banco estabelecida")
        self.connection_method = "none"
    
    def _try_flask_connection(self) -> bool:
        """
        Tenta obter conexão através do Flask app.
        
        Returns:
            True se conexão foi estabelecida
        """
        try:
            # Usar flask_fallback para obter db
            from app.claude_ai_novo.utils.flask_fallback import get_db
            
            db_obj = get_db()
            if db_obj and hasattr(db_obj, 'engine') and hasattr(db_obj, 'session'):
                self.db_engine = db_obj.engine
                self.db_session = db_obj.session
                logger.info("✅ Conexão Flask estabelecida")
                return True
            else:
                return False
            
        except Exception as e:
            logger.debug(f"🔄 Conexão Flask falhou: {e}")
            return False
    
    def _try_direct_connection(self) -> bool:
        """
        Tenta conexão direta com o banco.
        
        Returns:
            True se conexão foi estabelecida
        """
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return False
            
            # Corrigir URL para SQLAlchemy 1.4+
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            # Parse e encode a URL corretamente para evitar problemas de UTF-8
            try:
                from urllib.parse import urlparse, urlunparse, quote
                
                parsed = urlparse(database_url)
                
                # Encode username e password se existirem
                if parsed.username:
                    username = quote(parsed.username, safe='')
                else:
                    username = parsed.username
                    
                if parsed.password:
                    password = quote(parsed.password, safe='')
                else:
                    password = parsed.password
                
                # Reconstruir netloc
                hostname = parsed.hostname or 'localhost'  # Fallback para localhost se hostname for None
                
                if username and password:
                    netloc = f"{username}:{password}@{hostname}"
                elif username:
                    netloc = f"{username}@{hostname}"
                else:
                    netloc = hostname
                
                if parsed.port:
                    netloc += f":{parsed.port}"
                
                # Adicionar parâmetros de encoding
                if parsed.query:
                    query = parsed.query + '&client_encoding=utf8'
                else:
                    query = 'client_encoding=utf8'
                
                # Reconstruir URL
                database_url = urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    query,
                    parsed.fragment
                ))
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar URL: {e}")
                # Tentar adicionar encoding simples
                if 'postgresql://' in database_url:
                    if '?' in database_url:
                        database_url += '&client_encoding=utf8'
                    else:
                        database_url += '?client_encoding=utf8'
            
            # Criar engine com configurações adicionais para evitar problemas de encoding
            self.db_engine = create_engine(
                database_url,
                connect_args={
                    'client_encoding': 'utf8',
                    'connect_timeout': 10
                },
                pool_pre_ping=True,  # Verificar conexão antes de usar
                pool_size=5,
                max_overflow=10,
                # Adicionar echo para debug temporário
                echo=False
            )
            
            # Criar session maker
            session_maker = sessionmaker(bind=self.db_engine)
            self.db_session = session_maker()
            
            logger.info("✅ Conexão direta estabelecida")
            return True
            
        except Exception as e:
            logger.debug(f"🔄 Conexão direta falhou: {e}")
            return False
    
    def _try_env_connection(self) -> bool:
        """
        Tenta conexão usando variáveis de ambiente específicas.
        
        Returns:
            True se conexão foi estabelecida
        """
        try:
            # Buscar variáveis de ambiente
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'sistema_fretes')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', '')
            
            if not db_password:
                return False
            
            # Construir URL de conexão com encoding UTF-8
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?client_encoding=utf8"
            
            # Criar engine com configurações adicionais
            self.db_engine = create_engine(
                database_url,
                connect_args={
                    'client_encoding': 'utf8',
                    'connect_timeout': 10
                },
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            
            # Criar session maker
            session_maker = sessionmaker(bind=self.db_engine)
            self.db_session = session_maker()
            
            logger.info("✅ Conexão por variáveis de ambiente estabelecida")
            return True
            
        except Exception as e:
            logger.debug(f"🔄 Conexão por env falhou: {e}")
            return False
    
    def _initialize_inspector(self) -> None:
        """
        Inicializa o inspector do SQLAlchemy.
        """
        try:
            if self.db_engine:
                self.inspector = inspect(self.db_engine)
                logger.debug("🔍 Inspector do banco inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar inspector: {e}")
            self.inspector = None
    
    def is_connected(self) -> bool:
        """
        Verifica se há conexão ativa com o banco.
        
        Returns:
            True se conectado
        """
        return self.db_engine is not None and self.db_session is not None
    
    def is_inspector_available(self) -> bool:
        """
        Verifica se o inspector está disponível.
        
        Returns:
            True se inspector está disponível
        """
        return self.inspector is not None
    
    def get_engine(self) -> Optional[Engine]:
        """
        Retorna o engine do banco.
        
        Returns:
            Engine ou None se não disponível
        """
        return self.db_engine
    
    def get_session(self) -> Optional[Any]:
        """
        Retorna a sessão do banco.
        
        Returns:
            Session ou None se não disponível
        """
        return self.db_session
    
    def get_inspector(self) -> Optional[Inspector]:
        """
        Retorna o inspector do banco.
        
        Returns:
            Inspector ou None se não disponível
        """
        return self.inspector
    
    def test_connection(self) -> bool:
        """
        Testa se a conexão está funcionando.
        
        Returns:
            True se conexão funciona
        """
        if not self.db_engine:
            return False
        
        try:
            with self.db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"❌ Teste de conexão falhou: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """
        Retorna informações sobre a conexão.
        
        Returns:
            Dict com informações da conexão
        """
        return {
            'connected': self.is_connected(),
            'inspector_available': self.is_inspector_available(),
            'connection_method': self.connection_method,
            'engine_available': self.db_engine is not None,
            'session_available': self.db_session is not None,
            'test_result': self.test_connection() if self.is_connected() else False
        }
    
    def close_connection(self) -> None:
        """
        Fecha a conexão com o banco.
        """
        try:
            if self.db_session:
                self.db_session.close()
                self.db_session = None
            
            if self.db_engine:
                self.db_engine.dispose()
                self.db_engine = None
            
            self.inspector = None
            self.connection_method = "none"
            
            logger.info("🔒 Conexão com banco fechada")
        except Exception as e:
            logger.error(f"❌ Erro ao fechar conexão: {e}")
    
    def __del__(self):
        """
        Destrutor - fecha conexão ao destruir objeto.
        """
        try:
            self.close_connection()
        except:
            pass  # Ignorar erros no destrutor


# Exportações principais
__all__ = [
    'DatabaseConnection'
] 