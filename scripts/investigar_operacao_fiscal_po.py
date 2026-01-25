"""
Script para Investigar Operação Fiscal do Purchase Order
=========================================================

OBJETIVO:
    Identificar o campo l10n_br_operacao_id e suas opções

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
from pprint import pprint

# Configuração Odoo via variáveis de ambiente
import os
ODOO_CONFIG = {
    'url': os.environ.get('ODOO_URL', 'https://odoo.nacomgoya.com.br'),
    'database': os.environ.get('ODOO_DATABASE', 'odoo-17-ee-nacomgoya-prd'),
    'username': os.environ.get('ODOO_USERNAME', ''),
    'api_key': os.environ.get('ODOO_API_KEY', ''),
}

# Validação de credenciais
if not ODOO_CONFIG['api_key']:
    raise ValueError("ODOO_API_KEY não configurado. Configure via variável de ambiente.")


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

    def read(self, model, ids, fields=None):
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.execute_kw(model, 'read', [ids], kwargs)

    def search_read(self, model, domain, fields=None, limit=None):
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        return self.execute_kw(model, 'search_read', [domain], kwargs)


print("=" * 100)
print("🔍 INVESTIGANDO OPERAÇÃO FISCAL DO PURCHASE ORDER")
print("=" * 100)
print()

odoo = SimpleOdooClient(ODOO_CONFIG)
odoo.authenticate()

# 1. Buscar PO 31086
print("1️⃣ Buscando Purchase Order 31086...")
po_data = odoo.read(
    'purchase.order',
    [31086],
    ['id', 'name', 'company_id', 'l10n_br_operacao_id']
)

if po_data and len(po_data) > 0:
    po = po_data[0]
    print(f"✅ PO encontrado:")
    print(f"   ID: {po.get('id')}")
    print(f"   Nome: {po.get('name')}")
    print(f"   Company: {po.get('company_id')}")
    print(f"   Operação Fiscal (l10n_br_operacao_id): {po.get('l10n_br_operacao_id')}")
    print()

    operacao_id = po.get('l10n_br_operacao_id')
    if operacao_id and isinstance(operacao_id, list):
        operacao_id = operacao_id[0]

# 2. Buscar operações fiscais disponíveis para empresa CD (ID 4)
print("2️⃣ Buscando operações fiscais da empresa NACOM GOYA - CD (ID 4)...")
operacoes_cd = odoo.search_read(
    'l10n_br_operacao',
    [
        '|',
        ('company_id', '=', 4),
        ('company_id', '=', False),  # Operações globais
    ],
    fields=['id', 'name', 'company_id'],
    limit=20
)

if operacoes_cd:
    print(f"✅ Operações fiscais encontradas: {len(operacoes_cd)}")
    for op in operacoes_cd:
        company = op.get('company_id')
        company_str = f"{company[1]}" if company else "Global"
        print(f"   ID: {op.get('id'):5} | Empresa: {company_str:30} | Nome: {op.get('name')}")
else:
    print("❌ Nenhuma operação fiscal encontrada")

print()
print("=" * 100)
print()

# 3. Buscar especificamente operações relacionadas a "serviço" e "transporte"
print("3️⃣ Buscando operações relacionadas a 'serviço de transporte'...")
operacoes_transporte = odoo.search_read(
    'l10n_br_operacao',
    [
        '&',
        ('name', 'ilike', 'transporte'),
        '|',
        ('company_id', '=', 4),
        ('company_id', '=', False),
    ],
    fields=['id', 'name', 'company_id'],
    limit=10
)

if operacoes_transporte:
    print(f"✅ Operações de transporte encontradas: {len(operacoes_transporte)}")
    for op in operacoes_transporte:
        company = op.get('company_id')
        company_str = f"{company[1]}" if company else "Global"
        marcador = " ⭐ USAR ESTA" if company and company[0] == 4 else ""
        print(f"   ID: {op.get('id'):5} | Empresa: {company_str:30} | Nome: {op.get('name')}{marcador}")
else:
    print("❌ Nenhuma operação de transporte encontrada")

print()
print("=" * 100)
