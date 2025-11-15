"""
Script para Descobrir ID da Empresa NACOM GOYA - CD
====================================================

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl

# Configuração Odoo
ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'database': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69',
}


class SimpleOdooClient:
    def __init__(self, config):
        self.config = config
        self.uid = None
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.common = xmlrpc.client.ServerProxy(
            f"{config['url']}/xmlrpc/2/common",
            context=self.ssl_context
        )
        self.models = xmlrpc.client.ServerProxy(
            f"{config['url']}/xmlrpc/2/object",
            context=self.ssl_context
        )

    def authenticate(self):
        self.uid = self.common.authenticate(
            self.config['database'],
            self.config['username'],
            self.config['api_key'],
            {}
        )
        return self.uid is not None

    def execute_kw(self, model, method, args, kwargs=None):
        if kwargs is None:
            kwargs = {}
        return self.models.execute_kw(
            self.config['database'],
            self.uid,
            self.config['api_key'],
            model,
            method,
            args,
            kwargs
        )

    def search_read(self, model, domain, fields=None, limit=None):
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        return self.execute_kw(model, 'search_read', [domain], kwargs)


print("🔍 Buscando empresa 'NACOM GOYA - CD'...")
print()

odoo = SimpleOdooClient(ODOO_CONFIG)
odoo.authenticate()

# Buscar empresa
empresas = odoo.search_read(
    'res.company',
    [('name', 'ilike', 'NACOM GOYA')],
    fields=['id', 'name'],
    limit=10
)

if empresas:
    print(f"✅ Empresa(s) encontrada(s): {len(empresas)}")
    for emp in empresas:
        print(f"   ID: {emp.get('id')} | Nome: {emp.get('name')}")
        if 'CD' in emp.get('name', ''):
            print(f"   ⭐ Esta parece ser a correta!")
else:
    print("❌ Nenhuma empresa encontrada")
