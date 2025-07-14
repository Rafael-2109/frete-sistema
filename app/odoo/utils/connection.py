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
import socket

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
                # Configurar timeout global para socket
                socket.setdefaulttimeout(self.timeout)
                
                self._common = xmlrpc.client.ServerProxy(
                    f'{self.url}/xmlrpc/2/common',
                    context=self.ssl_context
                )
                logger.info("✅ Conexão common estabelecida com Odoo")
            except Exception as e:
                logger.error(f"Erro ao conectar no common: {e}")
                raise
        return self._common
    
    def _get_models(self):
        """Obtém conexão models do Odoo"""
        if self._models is None:
            try:
                # Configurar timeout global para socket
                socket.setdefaulttimeout(self.timeout)
                
                self._models = xmlrpc.client.ServerProxy(
                    f'{self.url}/xmlrpc/2/object',
                    context=self.ssl_context
                )
                logger.info("✅ Conexão models estabelecida com Odoo")
            except Exception as e:
                logger.error(f"Erro ao conectar no models: {e}")
                raise
        return self._models
    
    def authenticate(self) -> bool:
        """Autentica no Odoo e obtém UID"""
        try:
            common = self._get_common()
            
            # Autenticação com retry
            for attempt in range(self.retry_attempts):
                try:
                    self._uid = common.authenticate(
                        self.database,
                        self.username,
                        self.api_key,
                        {}
                    )
                    
                    if self._uid:
                        logger.info(f"✅ Autenticado no Odoo com UID: {self._uid}")
                        return True
                    else:
                        logger.warning(f"Falha na autenticação - tentativa {attempt + 1}/{self.retry_attempts}")
                        
                except Exception as e:
                    logger.error(f"Erro na autenticação (tentativa {attempt + 1}): {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(2 ** attempt)  # Backoff exponencial
                    else:
                        raise
            
            logger.error("❌ Falha na autenticação após todas as tentativas")
            return False
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return False
    
    def execute_kw(self, model: str, method: str, args: list, kwargs: Optional[dict] = None) -> Any:
        """Executa método no Odoo com retry automático"""
        if not self._uid:
            if not self.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        
        models = self._get_models()
        kwargs = kwargs or {}
        
        for attempt in range(self.retry_attempts):
            try:
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
                logger.error(f"Erro na execução (tentativa {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                    # Tentar reautenticar
                    self._uid = None
                    if not self.authenticate():
                        raise Exception("Falha na reautenticação")
                else:
                    raise
    
    def search_read(self, model: str, domain: list, fields: Optional[list] = None, limit: Optional[int] = None) -> list:
        """Busca registros no Odoo"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        
        return self.execute_kw(model, 'search_read', [domain], kwargs)
    
    def search(self, model: str, domain: list, limit: Optional[int] = None) -> list:
        """Busca IDs de registros no Odoo"""
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        
        return self.execute_kw(model, 'search', [domain], kwargs)
    
    def read(self, model: str, ids: list, fields: Optional[list] = None) -> list:
        """Lê registros do Odoo por IDs"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        
        return self.execute_kw(model, 'read', [ids], kwargs)
    
    def test_connection(self) -> Dict[str, Any]:
        """Testa conexão com Odoo"""
        try:
            # Testar conexão common
            common = self._get_common()
            version = common.version()
            
            # Testar autenticação
            if not self.authenticate():
                return {
                    'success': False,
                    'message': 'Falha na autenticação',
                    'error': 'Credenciais inválidas'
                }
            
            # Testar busca simples
            models = self._get_models()
            test_result = models.execute_kw(
                self.database,
                self._uid,
                self.api_key,
                'res.users',
                'search_read',
                [[['id', '=', self._uid]]],
                {'fields': ['name', 'login'], 'limit': 1}
            )
            
            user_data = None
            if test_result and isinstance(test_result, list) and len(test_result) > 0:
                user_data = test_result[0]
            
            return {
                'success': True,
                'message': 'Conexão estabelecida com sucesso',
                'data': {
                    'version': version,
                    'database': self.database,
                    'user': user_data,
                    'uid': self._uid
                }
            }
            
        except Exception as e:
            logger.error(f"Erro no teste de conexão: {e}")
            return {
                'success': False,
                'message': 'Erro na conexão',
                'error': str(e)
            }


def get_odoo_connection():
    """Retorna instância de conexão com Odoo"""
    from ..config.odoo_config import ODOO_CONFIG
    return OdooConnection(ODOO_CONFIG) 