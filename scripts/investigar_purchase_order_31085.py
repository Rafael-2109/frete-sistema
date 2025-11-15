"""
Script de Investigação: Purchase Order ID 31085
================================================

OBJETIVO:
    Buscar dados do PO gerado e descobrir IDs necessários:
    - team_id: "Lançamento Frete"
    - payment_provider_id: "Transferência Bancária CD"

PO ID: 31085
Nome: C2512194

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
import json
from pprint import pprint

# Configuração Odoo
ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'database': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69',
}


class SimpleOdooClient:
    """Cliente simples para Odoo sem dependências"""

    def __init__(self, config):
        self.config = config
        self.uid = None

        # Setup SSL
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        # Conexões
        self.common = xmlrpc.client.ServerProxy(
            f"{config['url']}/xmlrpc/2/common",
            context=self.ssl_context
        )
        self.models = xmlrpc.client.ServerProxy(
            f"{config['url']}/xmlrpc/2/object",
            context=self.ssl_context
        )

    def authenticate(self):
        """Autentica no Odoo"""
        self.uid = self.common.authenticate(
            self.config['database'],
            self.config['username'],
            self.config['api_key'],
            {}
        )
        return self.uid is not None

    def execute_kw(self, model, method, args, kwargs=None):
        """Executa método no Odoo"""
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
        """Lê registros"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.execute_kw(model, 'read', [ids], kwargs)

    def search_read(self, model, domain, fields=None, limit=None):
        """Busca e lê registros"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        return self.execute_kw(model, 'search_read', [domain], kwargs)


def investigar_po():
    """
    Investiga Purchase Order 31085 e descobre IDs necessários
    """
    print("=" * 100)
    print("🔍 INVESTIGANDO Purchase Order ID 31085")
    print("=" * 100)
    print()

    try:
        # 1. Conectar no Odoo
        print("1️⃣ Conectando no Odoo...")
        odoo = SimpleOdooClient(ODOO_CONFIG)

        if not odoo.authenticate():
            print("❌ Erro: Falha na autenticação")
            return

        print("✅ Conectado com sucesso!")
        print()

        # 2. Buscar dados do PO 31085
        print("2️⃣ Buscando dados do Purchase Order ID 31085...")

        po_data = odoo.read(
            'purchase.order',
            [31085],
            [
                'id',
                'name',
                'state',
                'team_id',
                'payment_provider_id',
                'partner_id',
                'date_order',
                'amount_total',
            ]
        )

        if not po_data or len(po_data) == 0:
            print("❌ PO não encontrado!")
            return

        po = po_data[0]

        print(f"✅ Purchase Order encontrado!")
        print(f"   ID: {po.get('id')}")
        print(f"   Nome: {po.get('name')}")
        print(f"   State: {po.get('state')}")
        print(f"   Team ID Atual: {po.get('team_id')}")
        print(f"   Payment Provider ID Atual: {po.get('payment_provider_id')}")
        print(f"   Partner: {po.get('partner_id')}")
        print(f"   Data: {po.get('date_order')}")
        print(f"   Valor Total: {po.get('amount_total')}")
        print()

        # 3. Buscar team_id "Lançamento Frete"
        print("3️⃣ Buscando team_id 'Lançamento Frete' (crm.team)...")

        teams = odoo.search_read(
            'crm.team',
            [('name', 'ilike', 'Lançamento Frete')],
            fields=['id', 'name'],
            limit=5
        )

        if teams:
            print(f"   ✅ Team(s) encontrado(s): {len(teams)}")
            for team in teams:
                print(f"      ID: {team.get('id')} | Nome: {team.get('name')}")
            print()
        else:
            print("   ⚠️  Team 'Lançamento Frete' não encontrado!")
            print("   Buscando todos os teams disponíveis...")

            teams_all = odoo.search_read(
                'crm.team',
                [('name', 'ilike', 'frete')],
                fields=['id', 'name'],
                limit=10
            )

            if teams_all:
                print(f"   📋 Teams relacionados a 'frete': {len(teams_all)}")
                for team in teams_all:
                    print(f"      ID: {team.get('id')} | Nome: {team.get('name')}")
                teams = teams_all
            print()

        # 4. Buscar payment_provider_id "Transferência Bancária CD"
        print("4️⃣ Buscando payment_provider_id 'Transferência Bancária CD' (payment.provider)...")

        providers = odoo.search_read(
            'payment.provider',
            [('name', 'ilike', 'Transferência Bancária CD')],
            fields=['id', 'name', 'code'],
            limit=5
        )

        if providers:
            print(f"   ✅ Provider(s) encontrado(s): {len(providers)}")
            for prov in providers:
                print(f"      ID: {prov.get('id')} | Nome: {prov.get('name')} | Code: {prov.get('code')}")
            print()
        else:
            print("   ⚠️  Provider 'Transferência Bancária CD' não encontrado!")
            print("   Buscando providers com 'Transferência' ou 'Bancária'...")

            providers_all = odoo.search_read(
                'payment.provider',
                [
                    '|',
                    ('name', 'ilike', 'Transferência'),
                    ('name', 'ilike', 'Bancária')
                ],
                fields=['id', 'name', 'code'],
                limit=10
            )

            if providers_all:
                print(f"   📋 Providers relacionados: {len(providers_all)}")
                for prov in providers_all:
                    print(f"      ID: {prov.get('id')} | Nome: {prov.get('name')} | Code: {prov.get('code')}")
                providers = providers_all
            print()

        # 5. Resumo
        print("=" * 100)
        print("📋 RESUMO PARA SCRIPT DE CONFIRMAÇÃO")
        print("=" * 100)
        print()
        print(f"Purchase Order ID: 31085")
        print(f"Nome: {po.get('name')}")
        print(f"State atual: {po.get('state')}")
        print()

        if teams and len(teams) > 0:
            team = teams[0]
            print(f"✅ Team 'Lançamento Frete':")
            print(f"   ID: {team.get('id')}")
            print(f"   Nome: {team.get('name')}")
            print()

        if providers and len(providers) > 0:
            provider = providers[0]
            print(f"✅ Payment Provider 'Transferência Bancária CD':")
            print(f"   ID: {provider.get('id')}")
            print(f"   Nome: {provider.get('name')}")
            print(f"   Code: {provider.get('code')}")
            print()

        print("=" * 100)
        print()
        print("✅ INVESTIGAÇÃO CONCLUÍDA!")
        print()

        # Salvar resultado
        import os
        log_file = os.path.join(os.path.dirname(__file__), 'investigacao_po_31085.json')

        resultado = {
            'po_id': 31085,
            'po_data': po,
            'team': teams[0] if teams else None,
            'payment_provider': providers[0] if providers else None,
        }

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

        print(f"💾 Resultado salvo em: {log_file}")
        print()

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    investigar_po()
