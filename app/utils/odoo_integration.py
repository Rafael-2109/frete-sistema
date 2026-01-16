#!/usr/bin/env python3
"""
Módulo de Integração com Odoo via XML-RPC
Sistema de Fretes - Integração com ERP Odoo
"""

import xmlrpc.client
import ssl
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from functools import wraps
import time

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class OdooConfig:
    """Configuração do Odoo"""
    url: str
    database: str
    username: str
    api_key: str
    timeout: int = 30
    retry_attempts: int = 3
    ssl_verify: bool = False

class OdooConnectionError(Exception):
    """Exceção para erros de conexão com Odoo"""
    pass

class OdooAuthenticationError(Exception):
    """Exceção para erros de autenticação"""
    pass

class OdooDataError(Exception):
    """Exceção para erros de dados"""
    pass

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator para retry automático em caso de falha"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}. Tentando novamente em {delay}s...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class OdooClient:
    """Cliente para integração com Odoo"""
    
    def __init__(self, config: OdooConfig):
        self.config = config
        self.uid = None
        self.common = None
        self.models = None
        self._setup_ssl_context()
        self._connect()
    
    def _setup_ssl_context(self):
        """Configurar contexto SSL"""
        self.ssl_context = ssl.create_default_context()
        if not self.config.ssl_verify:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    @retry_on_failure(max_retries=3)
    def _connect(self):
        """Conectar ao Odoo"""
        try:
            # Conectar ao endpoint comum
            self.common = xmlrpc.client.ServerProxy(
                f'{self.config.url}/xmlrpc/2/common',
                context=self.ssl_context
            )
            
            # Conectar ao endpoint de modelos
            self.models = xmlrpc.client.ServerProxy(
                f'{self.config.url}/xmlrpc/2/object',
                context=self.ssl_context
            )
            
            # Autenticar
            self._authenticate()
            
            logger.info(f"✅ Conectado ao Odoo - UID: {self.uid}")
            
        except Exception as e:
            logger.error(f"❌ Erro na conexão: {e}")
            raise OdooConnectionError(f"Falha na conexão com Odoo: {e}")
    
    def _authenticate(self):
        """Autenticar no Odoo"""
        try:
            self.uid = self.common.authenticate(
                self.config.database,
                self.config.username,
                self.config.api_key,
                {}
            )
            
            if not self.uid:
                raise OdooAuthenticationError("Falha na autenticação")
                
        except Exception as e:
            logger.error(f"❌ Erro na autenticação: {e}")
            raise OdooAuthenticationError(f"Falha na autenticação: {e}")
    
    @retry_on_failure(max_retries=3)
    def execute_kw(self, model: str, method: str, args: Optional[List] = None, kwargs: Optional[Dict] = None) -> Any:
        """Executar método no Odoo"""
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
            
        try:
            return self.models.execute_kw(
                self.config.database,
                self.uid,
                self.config.api_key,
                model,
                method,
                args,
                kwargs
            )
        except Exception as e:
            logger.error(f"❌ Erro ao executar {model}.{method}: {e}")
            raise OdooDataError(f"Erro ao executar {model}.{method}: {e}")
    
    def search(self, model: str, domain: Optional[List] = None, offset: int = 0, limit: Optional[int] = None, order: Optional[str] = None) -> List[int]:
        """Buscar registros"""
        if domain is None:
            domain = []
            
        kwargs = {'offset': offset}
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
            
        return self.execute_kw(model, 'search', [domain], kwargs)
    
    def read(self, model: str, ids: List[int], fields: Optional[List[str]] = None) -> List[Dict]:
        """Ler registros"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
            
        return self.execute_kw(model, 'read', [ids], kwargs)
    
    def search_read(self, model: str, domain: Optional[List] = None, fields: Optional[List[str]] = None, 
                   offset: int = 0, limit: Optional[int] = None, order: Optional[str] = None) -> List[Dict]:
        """Buscar e ler registros"""
        if domain is None:
            domain = []
            
        kwargs = {'offset': offset}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
            
        return self.execute_kw(model, 'search_read', [domain], kwargs)
    
    def create(self, model: str, values: Dict) -> int:
        """Criar registro"""
        return self.execute_kw(model, 'create', [values])
    
    def write(self, model: str, ids: List[int], values: Dict) -> bool:
        """Atualizar registros"""
        return self.execute_kw(model, 'write', [ids, values])
    
    def unlink(self, model: str, ids: List[int]) -> bool:
        """Deletar registros"""
        return self.execute_kw(model, 'unlink', [ids])

class OdooPartnerSync:
    """Sincronização de clientes/parceiros"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.model = 'res.partner'
    
    def get_customers(self, limit: Optional[int] = None, active_only: bool = True) -> List[Dict]:
        """Buscar clientes"""
        domain = [['is_company', '=', True]]
        if active_only:
            domain.append(['active', '=', True])
            
        fields = [
            'name', 'display_name', 'l10n_br_cnpj', 'phone', 'email', 'street',
            'street2', 'l10n_br_municipio_id', 'state_id', 'country_id', 'zip',
            'active', 'supplier_rank', 'customer_rank', 'create_date',
            'write_date'
        ]
        
        return self.client.search_read(
            self.model, domain, fields, limit=limit, order='name'
        )
    
    def get_customer_by_cnpj(self, cnpj: str) -> Optional[Dict]:
        """Buscar cliente por CNPJ/CPF"""
        domain = [['l10n_br_cnpj', '=', cnpj]]
        fields = ['name', 'display_name', 'l10n_br_cnpj', 'phone', 'email', 'l10n_br_municipio_id', 'state_id', 'country_id']
        
        results = self.client.search_read(self.model, domain, fields, limit=1)
        return results[0] if results else None    
    def create_customer(self, customer_data: Dict) -> int:
        """Criar cliente no Odoo"""
        return self.client.create(self.model, customer_data)
    
    def update_customer(self, customer_id: int, customer_data: Dict) -> bool:
        """Atualizar cliente no Odoo"""
        return self.client.write(self.model, [customer_id], customer_data)

class OdooProductSync:
    """Sincronização de produtos"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.model = 'product.product'
    
    def get_products(self, limit: Optional[int] = None, active_only: bool = True) -> List[Dict]:
        """Buscar produtos"""
        domain = [['sale_ok', '=', True]]
        if active_only:
            domain.append(['active', '=', True])
            
        fields = [
            'name', 'display_name', 'default_code', 'barcode', 'categ_id',
            'list_price', 'standard_price', 'uom_id', 'weight', 'volume',
            'active', 'create_date', 'write_date'
        ]
        
        return self.client.search_read(
            self.model, domain, fields, limit=limit, order='name'
        )
    
    def get_product_by_code(self, code: str) -> Optional[Dict]:
        """Buscar produto por código"""
        domain = [['default_code', '=', code]]
        fields = ['name', 'display_name', 'default_code', 'list_price', 'weight']
        
        results = self.client.search_read(self.model, domain, fields, limit=1)
        return results[0] if results else None

class OdooSaleOrderSync:
    """Sincronização de pedidos de venda"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.model = 'sale.order'
    
    def get_orders(self, limit: Optional[int] = None, state: Optional[str] = None, 
                   date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Dict]:
        """Buscar pedidos de venda"""
        domain = []
        
        if state:
            domain.append(['state', '=', state])
        if date_from:
            domain.append(['create_date', '>=', date_from.strftime('%Y-%m-%d')])
        if date_to:
            domain.append(['create_date', '<=', date_to.strftime('%Y-%m-%d')])
            
        fields = [
            'name', 'partner_id', 'date_order', 'state', 'amount_total',
            'amount_untaxed', 'currency_id', 'user_id', 'team_id',
            'order_line', 'create_date', 'write_date'
        ]
        
        return self.client.search_read(
            self.model, domain, fields, limit=limit, order='date_order desc'
        )
    
    def get_order_by_name(self, name: str) -> Optional[Dict]:
        """Buscar pedido por nome/número"""
        domain = [['name', '=', name]]
        fields = ['name', 'partner_id', 'date_order', 'state', 'amount_total', 'order_line']
        
        results = self.client.search_read(self.model, domain, fields, limit=1)
        return results[0] if results else None
    
    def get_order_lines(self, order_id: int) -> List[Dict]:
        """Buscar linhas do pedido"""
        domain = [['order_id', '=', order_id]]
        fields = [
            'product_id', 'product_uom_qty', 'price_unit', 'price_subtotal',
            'name', 'product_uom', 'discount'
        ]
        
        return self.client.search_read('sale.order.line', domain, fields)

class OdooIntegration:
    """Classe principal de integração com Odoo"""
    
    def __init__(self, config: OdooConfig):
        self.config = config
        self.client = OdooClient(config)
        self.partners = OdooPartnerSync(self.client)
        self.products = OdooProductSync(self.client)
        self.sales = OdooSaleOrderSync(self.client)
    
    def test_connection(self) -> Dict[str, Any]:
        """Testar conexão e retornar informações"""
        try:
            # Obter dados do usuário
            user_data = self.client.read('res.users', [self.client.uid], 
                                       ['name', 'login', 'company_id'])
            
            # Contar registros
            partner_count = len(self.client.search('res.partner', [['is_company', '=', True]]))
            product_count = len(self.client.search('product.product', [['active', '=', True]]))
            order_count = len(self.client.search('sale.order', [['state', '=', 'sale']]))
            
            return {
                'status': 'success',
                'user': user_data[0] if user_data else {},
                'counts': {
                    'customers': partner_count,
                    'products': product_count,
                    'orders': order_count
                },
                'server_info': self.client.common.version()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no teste de conexão: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def sync_customers_to_system(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Sincronizar clientes do Odoo para o sistema"""
        try:
            customers = self.partners.get_customers(limit=limit)
            
            # Aqui você implementaria a lógica de sincronização
            # com os modelos do seu sistema de fretes
            
            return {
                'status': 'success',
                'message': f'Sincronizados {len(customers)} clientes',
                'data': customers
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização de clientes: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def sync_products_to_system(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Sincronizar produtos do Odoo para o sistema"""
        try:
            products = self.products.get_products(limit=limit)
            
            # Aqui você implementaria a lógica de sincronização
            # com os modelos do seu sistema de fretes
            
            return {
                'status': 'success',
                'message': f'Sincronizados {len(products)} produtos',
                'data': products
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização de produtos: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def sync_orders_to_system(self, limit: Optional[int] = None, days_back: int = 30) -> Dict[str, Any]:
        """Sincronizar pedidos do Odoo para o sistema"""
        try:
            date_from = datetime.now() - timedelta(days=days_back)
            orders = self.sales.get_orders(limit=limit, date_from=date_from)
            
            # Aqui você implementaria a lógica de sincronização
            # com os modelos do seu sistema de fretes
            
            return {
                'status': 'success',
                'message': f'Sincronizados {len(orders)} pedidos',
                'data': orders
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização de pedidos: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

# Configuração padrão
DEFAULT_CONFIG = OdooConfig(
    url='https://odoo.nacomgoya.com.br',
    database='odoo-17-ee-nacomgoya-prd',
    username='rafael@conservascampobelo.com.br',
    api_key='67705b0986ff5c052e657f1c0ffd96ceb191af69',
    timeout=30,
    retry_attempts=3,
    ssl_verify=False
)

def get_odoo_integration() -> OdooIntegration:
    """Obter instância de integração com Odoo"""
    return OdooIntegration(DEFAULT_CONFIG)

# Exemplo de uso
if __name__ == "__main__":
    # Testar integração
    integration = get_odoo_integration()
    
    # Testar conexão
    test_result = integration.test_connection()
    print(f"🧪 Teste de conexão: {test_result}")
    
    # Sincronizar alguns clientes
    customers_result = integration.sync_customers_to_system(limit=5)
    print(f"👥 Sincronização de clientes: {customers_result['message']}")
    
    # Sincronizar alguns produtos
    products_result = integration.sync_products_to_system(limit=5)
    print(f"📦 Sincronização de produtos: {products_result['message']}")
    
    # Sincronizar pedidos recentes
    orders_result = integration.sync_orders_to_system(limit=5, days_back=7)
    print(f"📋 Sincronização de pedidos: {orders_result['message']}") 