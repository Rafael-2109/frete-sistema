"""
Script de Aprovação de Purchase Order
======================================

OBJETIVO:
    Aprovar Purchase Order que está em state 'to approve'

PO ID TESTE: 31085

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
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


def aprovar_po(po_id):
    """
    Aprova Purchase Order no Odoo

    Args:
        po_id: ID do Purchase Order

    Returns:
        dict: Resultado da aprovação
    """
    print("=" * 100)
    print("🚀 APROVAÇÃO DE PURCHASE ORDER")
    print("=" * 100)
    print()
    print(f"Purchase Order ID: {po_id}")
    print()

    try:
        # 1. Conectar no Odoo
        print("1️⃣ Conectando no Odoo...")
        odoo = SimpleOdooClient(ODOO_CONFIG)

        if not odoo.authenticate():
            return {'sucesso': False, 'erro': 'Falha na autenticação'}

        print("✅ Conectado!")
        print()

        # 2. Buscar estado do PO
        print(f"2️⃣ Buscando estado do Purchase Order {po_id}...")

        po_data = odoo.read(
            'purchase.order',
            [po_id],
            ['id', 'name', 'state', 'is_current_approver']
        )

        if not po_data or len(po_data) == 0:
            return {'sucesso': False, 'erro': f'PO {po_id} não encontrado'}

        po = po_data[0]

        print(f"✅ PO encontrado!")
        print(f"   Nome: {po.get('name')}")
        print(f"   State: {po.get('state')}")
        print(f"   Is Current Approver: {po.get('is_current_approver')}")
        print()

        # 3. Verificar se precisa aprovação
        if po.get('state') != 'to approve':
            print(f"⚠️  PO está em state '{po.get('state')}', não precisa de aprovação")
            return {
                'sucesso': True,
                'po_id': po_id,
                'mensagem': f"PO já está em state '{po.get('state')}'"
            }

        # 4. Aprovar
        print("3️⃣ Aprovando Purchase Order...")
        print("   Executando button_approve...")

        try:
            resultado = odoo.execute_kw(
                'purchase.order',
                'button_approve',
                [[po_id]],
                {}
            )
            print("✅ Purchase Order aprovado com sucesso!")
            print(f"   Resultado: {resultado}")
        except Exception as e:
            print(f"❌ Erro ao aprovar: {e}")
            return {'sucesso': False, 'erro': str(e)}

        print()

        # 5. Verificar estado final
        print("4️⃣ Verificando estado final...")
        po_final = odoo.read('purchase.order', [po_id], ['state'])

        if po_final and len(po_final) > 0:
            state_final = po_final[0].get('state')
            print(f"   State final: {state_final}")

        print()
        print("=" * 100)
        print("✅ APROVAÇÃO CONCLUÍDA!")
        print("=" * 100)
        print()

        return {
            'sucesso': True,
            'po_id': po_id,
            'po_name': po.get('name'),
            'state_final': state_final if po_final else None
        }

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


if __name__ == '__main__':
    PO_ID = 31085

    print("\n")
    resultado = aprovar_po(PO_ID)

    print()
    print("📊 RESULTADO:")
    pprint(resultado)
