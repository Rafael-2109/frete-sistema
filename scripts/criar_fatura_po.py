"""
Script de Criação de Fatura do Purchase Order
==============================================

OBJETIVO:
    Criar fatura do Purchase Order e atualizar impostos

    5. Executar action_create_invoice no PO
    6. Executar onchange_l10n_br_calcular_imposto na fatura

PO ID TESTE: 31085

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


def criar_fatura(po_id):
    """
    Cria fatura do Purchase Order e atualiza impostos

    Args:
        po_id: ID do Purchase Order

    Returns:
        dict: Resultado da criação
    """
    print("=" * 100)
    print("🚀 CRIAÇÃO DE FATURA DO PURCHASE ORDER")
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
        print(f"2️⃣ Buscando Purchase Order {po_id}...")

        po_data = odoo.read(
            'purchase.order',
            [po_id],
            ['id', 'name', 'state', 'invoice_status', 'invoice_ids']
        )

        if not po_data or len(po_data) == 0:
            return {'sucesso': False, 'erro': f'PO {po_id} não encontrado'}

        po = po_data[0]

        print(f"✅ PO encontrado!")
        print(f"   Nome: {po.get('name')}")
        print(f"   State: {po.get('state')}")
        print(f"   Invoice Status: {po.get('invoice_status')}")
        print(f"   Invoice IDs: {po.get('invoice_ids')}")
        print()

        # 3. Verificar se pode criar fatura
        state = po.get('state')
        invoice_status = po.get('invoice_status')

        if state not in ('purchase', 'done'):
            print(f"⚠️  PO não está em state válido para criar fatura (state: {state})")
            return {
                'sucesso': False,
                'erro': f"State '{state}' não permite criar fatura"
            }

        if invoice_status in ('no', 'invoiced'):
            print(f"⚠️  Invoice status '{invoice_status}' não permite criar fatura")
            return {
                'sucesso': False,
                'erro': f"Invoice status '{invoice_status}' não permite criar fatura"
            }

        # 4. Criar fatura
        print("3️⃣ Criando fatura...")
        print("   Executando action_create_invoice...")

        try:
            resultado_invoice = odoo.execute_kw(
                'purchase.order',
                'action_create_invoice',
                [[po_id]],
                {}
            )
            print("✅ Fatura criada!")
            print(f"   Resultado: {resultado_invoice}")
            print()

            # Resultado esperado: {'type': 'ir.actions.act_window', 'res_id': invoice_id, ...}
            invoice_id = None
            if isinstance(resultado_invoice, dict):
                invoice_id = resultado_invoice.get('res_id')
                print(f"   Invoice ID extraído: {invoice_id}")

        except Exception as e:
            print(f"❌ Erro ao criar fatura: {e}")
            return {'sucesso': False, 'erro': str(e)}

        print()

        # 5. Buscar fatura criada (se não conseguiu extrair ID do resultado)
        if not invoice_id:
            print("4️⃣ Buscando fatura criada...")
            po_atualizado = odoo.read('purchase.order', [po_id], ['invoice_ids'])

            if po_atualizado and len(po_atualizado) > 0:
                invoice_ids = po_atualizado[0].get('invoice_ids')
                if invoice_ids and len(invoice_ids) > 0:
                    invoice_id = invoice_ids[-1]  # Pegar a última (mais recente)
                    print(f"   ✅ Invoice ID encontrado: {invoice_id}")
                    print()

        if not invoice_id:
            print("⚠️  Não foi possível identificar ID da fatura criada")
            return {
                'sucesso': False,
                'erro': 'Fatura criada mas ID não identificado'
            }

        # 6. Atualizar impostos
        print("5️⃣ Atualizando impostos da fatura...")
        print(f"   Invoice ID: {invoice_id}")
        print("   Executando onchange_l10n_br_calcular_imposto...")

        try:
            resultado_impostos = odoo.execute_kw(
                'account.move',
                'onchange_l10n_br_calcular_imposto',
                [[invoice_id]],
                {}
            )
            print("✅ Impostos atualizados!")
            print(f"   Resultado: {resultado_impostos}")
        except Exception as e:
            print(f"⚠️  Erro ao atualizar impostos: {e}")
            print("   Fatura foi criada, mas impostos podem precisar ser atualizados manualmente")

        print()
        print("=" * 100)
        print("✅ CRIAÇÃO DE FATURA CONCLUÍDA!")
        print("=" * 100)
        print()

        return {
            'sucesso': True,
            'po_id': po_id,
            'po_name': po.get('name'),
            'invoice_id': invoice_id
        }

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


if __name__ == '__main__':
    PO_ID = 31085

    print("\n")
    resultado = criar_fatura(PO_ID)

    print()
    print("📊 RESULTADO:")
    pprint(resultado)
