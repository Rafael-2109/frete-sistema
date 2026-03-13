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
from .circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)

class OdooConnection:
    """Classe para gerenciar conexão com Odoo"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config['url']
        self.database = config['database']
        self.username = config['username']
        self.api_key = config['api_key']

        # 🔧 Timeout aumentado para 90s para suportar operações longas
        # A etapa 6 (action_gerar_po_dfe) pode demorar mais de 30s
        # Autenticação pode demorar mais quando Odoo está ocupado
        self.timeout = config.get('timeout', 90)

        # 🔧 Retry reduzido: Circuit Breaker gerencia tentativas
        # Com Circuit Breaker, não precisa de muitas tentativas internas
        self.retry_attempts = config.get('retry_attempts', 3)

        # 🔧 Circuit Breaker para proteger sistema
        self.circuit_breaker = get_circuit_breaker()

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
                    context=self.ssl_context,
                    allow_none=True  # ✅ Permite None nos retornos do Odoo
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
                    context=self.ssl_context,
                    allow_none=True  # ✅ Permite None nos retornos do Odoo
                )
                logger.info("✅ Conexão models estabelecida com Odoo")
            except Exception as e:
                logger.error(f"Erro ao conectar no models: {e}")
                raise
        return self._models
    
    def authenticate(self) -> bool:
        """
        Autentica no Odoo e obtém UID
        Protegido por Circuit Breaker
        """
        def _do_authenticate():
            """Função interna para autenticação"""
            # 🔧 CORREÇÃO 15/12/2025: Garantir timeout configurado ANTES da autenticação
            # Isso evita que a primeira conexão use o timeout padrão do Python (None/indefinido)
            current_timeout = socket.getdefaulttimeout()
            if current_timeout != self.timeout:
                logger.info(
                    f"⏱️ Configurando timeout inicial: {self.timeout}s (atual: {current_timeout}s)"
                )
                socket.setdefaulttimeout(self.timeout)
                # Forçar reconexão para aplicar novo timeout
                self._common = None

            common = self._get_common()

            # ✅ CORRIGIDO: Sem retry interno - Circuit Breaker gerencia tentativas
            # Falhar rápido para o Circuit Breaker detectar problemas imediatamente
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
                    error_msg = "Credenciais inválidas ou UID não retornado"
                    logger.error(f"❌ Falha na autenticação: {error_msg}")
                    raise Exception(error_msg)

            except socket.timeout as e:
                logger.error(f"⏰ TIMEOUT na autenticação após {self.timeout}s: {e}")
                raise Exception(f"Timeout de {self.timeout}s excedido na autenticação")

            except Exception as e:
                # ✅ Lançar exceção imediatamente para Circuit Breaker detectar
                logger.error(f"❌ Erro na autenticação: {e}")
                raise

            logger.error("❌ Falha na autenticação após todas as tentativas")
            return False

        try:
            # 🔧 Usar Circuit Breaker para proteger autenticação
            return self.circuit_breaker.call(_do_authenticate)

        except Exception as e:
            error_msg = str(e)

            # Mensagens amigáveis para diferentes estados do Circuit Breaker
            if "Circuit Breaker ABERTO" in error_msg:
                logger.warning(f"⚠️ Circuit Breaker bloqueou autenticação: Odoo indisponível")
            else:
                logger.error(f"Erro na autenticação: {e}")

            return False
    
    def execute_kw(self, model: str, method: str, args: list, kwargs: Optional[dict] = None, timeout_override: Optional[int] = None) -> Any:
        """
        Executa método no Odoo com retry automático
        Protegido por Circuit Breaker

        Args:
            model: Nome do modelo Odoo
            method: Nome do método a executar
            args: Argumentos posicionais
            kwargs: Argumentos nomeados
            timeout_override: Timeout específico em segundos (sobrescreve o padrão para operações longas)
        """
        # 🔧 CORREÇÃO 15/12/2025: Determinar timeout efetivo ANTES da execução
        # O timeout_override SEMPRE deve ser aplicado quando especificado,
        # independentemente de ser maior ou menor que o padrão
        timeout_efetivo = timeout_override if timeout_override else self.timeout
        usar_timeout_customizado = timeout_override is not None

        def _do_execute():
            """Função interna para execução"""
            if not self._uid:
                if not self.authenticate():
                    raise Exception("Falha na autenticação com Odoo")

            kwargs_resolved = kwargs or {}

            # 🔧 CORREÇÃO: Timeout específico para operações longas
            # socket.setdefaulttimeout() só afeta sockets NOVOS, não conexões já estabelecidas
            # Por isso, SEMPRE forçamos reconexão quando há timeout_override especificado
            if usar_timeout_customizado:
                logger.info(
                    f"⏱️ Aplicando timeout customizado: {timeout_efetivo}s para {model}.{method} "
                    f"(padrão seria {self.timeout}s)"
                )
                self._models = None  # Força reconexão com novo timeout
                socket.setdefaulttimeout(timeout_efetivo)

            models = self._get_models()

            try:
                logger.debug(f"🔌 Executando {model}.{method} com timeout={timeout_efetivo}s...")
                result = models.execute_kw(
                    self.database,
                    self._uid,
                    self.api_key,
                    model,
                    method,
                    args,
                    kwargs_resolved
                )
                return result

            except socket.timeout as e:
                # ✅ Log específico para timeout de socket
                logger.error(
                    f"⏰ TIMEOUT de socket após {timeout_efetivo}s em {model}.{method}: {e}"
                )
                raise Exception(f"Timeout de {timeout_efetivo}s excedido em {model}.{method}")

            except Exception as e:
                error_str = str(e).lower()

                # Erro conhecido: métodos Odoo que retornam None (reconcile, button_validate, etc.)
                # O servidor Odoo não tem allow_none=True, então Fault é gerado na serialização
                # Mas a operação FOI executada com sucesso antes do retorno
                if "cannot marshal none" in error_str:
                    logger.debug(
                        f"✓ {model}.{method} executado com sucesso (retorno None é esperado)"
                    )
                    return None  # Retorna None normalmente, operação foi bem-sucedida

                # SSL transiente: retry 1x com reconexão. Fixes PYTHON-FLASK-20/21/22/23.
                if any(kw in error_str for kw in ('eof occurred', 'violation of protocol')):
                    logger.warning(
                        f"⚠️ SSL transiente em {model}.{method}: {e} — retentando 1x"
                    )
                    self._models = None  # Forçar reconexão
                    try:
                        models_retry = self._get_models()
                        result = models_retry.execute_kw(
                            self.database, self._uid, self.api_key,
                            model, method, args, kwargs_resolved,
                        )
                        logger.info(f"✅ Retry SSL bem-sucedido: {model}.{method}")
                        return result
                    except Exception as e_retry:
                        logger.error(
                            f"❌ Retry SSL falhou em {model}.{method}: {e_retry}"
                        )
                        raise

                # Erro real - logar e propagar para Circuit Breaker detectar
                logger.error(f"❌ Erro na execução de {model}.{method}: {e}")
                raise

            finally:
                # 🔧 Restaurar timeout padrão após operação com timeout customizado
                if usar_timeout_customizado:
                    logger.debug(f"🔄 Restaurando timeout padrão: {self.timeout}s")
                    socket.setdefaulttimeout(self.timeout)
                    self._models = None  # Força reconexão na próxima chamada com timeout normal

        # 🔧 Usar Circuit Breaker para proteger execução
        return self.circuit_breaker.call(_do_execute)
    
    def search_read(self, model: str, domain: list, fields: Optional[list] = None, limit: Optional[int] = None, offset: Optional[int] = None, order: Optional[str] = None) -> list:
        """Busca registros no Odoo"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit is not None:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
        if order:
            kwargs['order'] = order

        return self.execute_kw(model, 'search_read', [domain], kwargs)

    def search(self, model: str, domain: list, limit: Optional[int] = None) -> list:
        """Busca IDs de registros no Odoo"""
        kwargs = {}
        if limit is not None:
            kwargs['limit'] = limit
        
        return self.execute_kw(model, 'search', [domain], kwargs)
    
    def read(self, model: str, ids: list, fields: Optional[list] = None) -> list:
        """Lê registros do Odoo por IDs"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields

        return self.execute_kw(model, 'read', [ids], kwargs)

    def write(self, model: str, ids: list, values: dict) -> bool:
        """
        Atualiza registros no Odoo

        Args:
            model: Nome do modelo Odoo (ex: 'purchase.order')
            ids: Lista de IDs a atualizar
            values: Dicionário com campos e valores a atualizar

        Returns:
            True se sucesso, False caso contrário
        """
        return self.execute_kw(model, 'write', [ids, values])

    def create(self, model: str, values: dict) -> int:
        """
        Cria novo registro no Odoo

        Args:
            model: Nome do modelo Odoo (ex: 'product.supplierinfo')
            values: Dicionário com campos e valores do novo registro

        Returns:
            ID do registro criado
        """
        return self.execute_kw(model, 'create', [values])

    def buscar_registro_por_id(self, model: str, record_id: int, fields: Optional[list] = None) -> Optional[Dict]:
        """
        Busca um único registro por ID
        Necessário para múltiplas queries no sistema de mapeamento
        """
        try:
            if not record_id:
                return None
            
            resultado = self.read(model, [record_id], fields)
            
            if resultado and isinstance(resultado, list) and len(resultado) > 0:
                return resultado[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar registro {record_id} no modelo {model}: {e}")
            return None
    
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

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Retorna status do Circuit Breaker"""
        return self.circuit_breaker.get_status()

    def reset_circuit_breaker(self):
        """Reseta manualmente o Circuit Breaker"""
        logger.warning("🔄 Reset manual do Circuit Breaker solicitado")
        self.circuit_breaker.reset()


def get_odoo_connection():
    """Retorna instância de conexão com Odoo"""
    from ..config.odoo_config import ODOO_CONFIG
    return OdooConnection(ODOO_CONFIG)


def test_connection():
    """Função de conveniência para testar conexão"""
    try:
        connection = get_odoo_connection()
        result = connection.test_connection()
        return result.get('success', False)
    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        return False


def get_odoo_version():
    """Função de conveniência para obter versão do Odoo"""
    try:
        connection = get_odoo_connection()
        result = connection.test_connection()
        if result.get('success'):
            version_info = result.get('data', {}).get('version', {})
            if isinstance(version_info, dict):
                return version_info.get('server_version', 'Desconhecida')
            return str(version_info)
        return 'Desconhecida'
    except Exception as e:
        logger.error(f"Erro ao obter versão: {e}")
        return 'Erro' 