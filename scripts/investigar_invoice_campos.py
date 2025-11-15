"""
Investigar Campos da Invoice (Fatura)
======================================

OBJETIVO: Descobrir campo de "situação da NF-e" e outros campos necessários

Invoice ID: 405939

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl

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
        self.common = xmlrpc.client.ServerProxy(f"{config['url']}/xmlrpc/2/common", context=self.ssl_context)
        self.models = xmlrpc.client.ServerProxy(f"{config['url']}/xmlrpc/2/object", context=self.ssl_context)

    def authenticate(self):
        self.uid = self.common.authenticate(self.config['database'], self.config['username'], self.config['api_key'], {})
        return self.uid is not None

    def read(self, model, ids, fields=None):
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.models.execute_kw(self.config['database'], self.uid, self.config['api_key'], model, 'read', [ids], kwargs)

print("🔍 Investigando Invoice 405939...")
print()

odoo = SimpleOdooClient(ODOO_CONFIG)
odoo.authenticate()

# Buscar campos relacionados a situação, status, autorização
invoice_data = odoo.read('account.move', [405939], [
    'id',
    'name',
    'state',
    'l10n_br_compra_indcom',
    'invoice_date_due',
    'l10n_br_situacao_nfe',  # Tentativa 1
    'l10n_br_status_nfe',     # Tentativa 2
    'l10n_br_status',         # Tentativa 3
    'nfe_status',             # Tentativa 4
])

if invoice_data:
    inv = invoice_data[0]
    print("✅ Invoice encontrada:")
    for campo, valor in sorted(inv.items()):
        print(f"   {campo}: {valor}")
