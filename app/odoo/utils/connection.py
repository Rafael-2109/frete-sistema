"""
Utilitário de Conexão com Odoo
==============================

Sistema de conexão e autenticação com o Odoo ERP via XML-RPC.
Gerencia autenticação, timeouts e retry automático.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

import xmlrpc.client
import ssl
import logging
from typing import Optional, Dict, Any
from functools import wraps
import time

logger = logging.getLogger(__name__)

class OdooConnection:
    """Classe para gerenciar conexão com Odoo"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config['url']
        self.database = config['database']
        self.username = config['username']
        self.api_key = config['api_key']
        self.timeout = config.get('timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
        # Configurar SSL para produção
        self.ssl_context = ssl.create_default_context()
        if 'localhost' in self.url or '127.0.0.1' in self.url:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Conexões XML-RPC
        self._common = None
        self._models = None
        self._uid = None
        
    def _get_common(self):
        """Obtém conexão common do Odoo"""
        if self._common is None:
            try:
                self._common = xmlrpc.client.ServerProxy(
                    f'{self.url}/xmlrpc/2/common',
                    context=self.ssl_context,
                    timeout=self.timeout
                )
            except Exception as e:
                logger.error(f"Erro ao conectar no common: {e}")
                raise
        return self._common
    
    def _get_models(self):
        """Obtém conexão models do Odoo"""
        if self._models is None:
            try:
                self._models = xmlrpc.client.ServerProxy(
                    f'{self.url}/xmlrpc/2/object',
                    context=self.ssl_context,
                    timeout=self.timeout
                )
            except Exception as e:
                logger.error(f"Erro ao conectar no models: {e}")
                raise
        return self._models
    
    def authenticate(self) -> bool:
        """Autentica no Odoo e obtém UID"""
        try:
            common = self._get_common()
            
            # Verificar versão do Odoo
            version = common.version()
            logger.info(f"Conectando ao Odoo versão: {version}")
            
            # Autenticar
            self._uid = common.authenticate(
                self.database,
                self.username,
                self.api_key,
                {}
            )
            
            if self._uid:
                logger.info(f"Autenticação bem-sucedida. UID: {self._uid}")
                return True
            else:
                logger.error("Falha na autenticação")
                return False
                
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return False
    
    def execute_kw(self, model: str, method: str, args: list, kwargs: Optional[dict] = None) -> Any:
        """Executa método no Odoo com retry automático"""
        if not self._uid:
            if not self.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        
        kwargs = kwargs or {}
        
        for attempt in range(self.retry_attempts):
            try:
                models = self._get_models()
                result = models.execute_kw(
                    self.database,
                    self._uid,
                    self.api_key,
                    model,
                    method,
                    args,
                    kwargs
                )
                return result
                
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                    # Resetar conexões para tentar novamente
                    self._common = None
                    self._models = None
                    self._uid = None
                else:
                    raise
    
    def search_read(self, model: str, domain: Optional[list] = None, fields: Optional[list] = None, limit: Optional[int] = None) -> list:
        """Busca e lê registros do Odoo"""
        domain = domain or []
        fields = fields or []
        
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
            
        return self.execute_kw(model, 'search_read', [domain], kwargs)
    
    def search(self, model: str, domain: Optional[list] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> list:
        """Busca IDs de registros no Odoo"""
        domain = domain or []
        
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
            
        return self.execute_kw(model, 'search', [domain], kwargs)
    
    def read(self, model: str, ids: list, fields: Optional[list] = None) -> list:
        """Lê registros específicos do Odoo"""
        fields = fields or []
        
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
            
        return self.execute_kw(model, 'read', [ids], kwargs)
    
    def fields_get(self, model: str, fields: Optional[list] = None) -> dict:
        """Obtém definição de campos do modelo"""
        fields = fields or []
        
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
            
        return self.execute_kw(model, 'fields_get', [], kwargs)

# Instância global da conexão
_connection = None

def get_odoo_connection(config: Optional[Dict[str, Any]] = None) -> OdooConnection:
    """Obtém instância da conexão com Odoo (singleton)"""
    global _connection
    
    if _connection is None:
        if config is None:
            # Usar configuração padrão se não fornecida
            from app.odoo.config.odoo_config import ODOO_CONFIG
            config = ODOO_CONFIG
        
        _connection = OdooConnection(config)
    
    return _connection

def with_odoo_connection(func):
    """Decorator para garantir conexão com Odoo"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            connection = get_odoo_connection()
            return func(connection, *args, **kwargs)
        except Exception as e:
            logger.error(f"Erro na conexão com Odoo: {e}")
            raise
    
    return wrapper

# Funções de conveniência
def test_connection(config: Optional[Dict[str, Any]] = None) -> bool:
    """Testa conexão com Odoo"""
    try:
        connection = get_odoo_connection(config)
        return connection.authenticate()
    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        return False

def get_odoo_version(config: Optional[Dict[str, Any]] = None) -> str:
    """Obtém versão do Odoo"""
    try:
        connection = get_odoo_connection(config)
        common = connection._get_common()
        version = common.version()
        return version.get('server_version', 'Desconhecida')
    except Exception as e:
        logger.error(f"Erro ao obter versão: {e}")
        return 'Erro' 