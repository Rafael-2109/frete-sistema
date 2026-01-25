"""
Script de Confirmação Automática de Purchase Order
===================================================

OBJETIVO:
    Confirmar Purchase Order gerado pelo lançamento de CTe

    1. Buscar PO pelo ID
    2. Verificar se team_id e payment_provider_id estão preenchidos
    3. Executar button_confirm para confirmar pedido

PO ID TESTE: 31085
Nome: C2512194

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
import json
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

# IDs descobertos na investigação
TEAM_LANCAMENTO_FRETE_ID = 119  # "Lançamento Frete"
PAYMENT_PROVIDER_TRANSFERENCIA_ID = 30  # "Transferência Bancária"


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

    def write(self, model, ids, values):
        """Atualiza registros"""
        return self.execute_kw(model, 'write', [ids, values])


def confirmar_purchase_order(po_id, modo_teste=True):
    """
    Confirma Purchase Order no Odoo

    Args:
        po_id: ID do Purchase Order
        modo_teste: Se True, apenas simula sem executar button_confirm

    Returns:
        dict: Resultado da confirmação
    """
    print("=" * 100)
    print("🚀 CONFIRMAÇÃO AUTOMÁTICA DE PURCHASE ORDER")
    print("=" * 100)
    print()
    print(f"Purchase Order ID: {po_id}")
    print(f"Modo teste: {'SIM' if modo_teste else 'NÃO'}")
    print()

    try:
        # 1. Conectar no Odoo
        print("1️⃣ Conectando no Odoo...")
        odoo = SimpleOdooClient(ODOO_CONFIG)

        if not odoo.authenticate():
            return {
                'sucesso': False,
                'erro': 'Falha na autenticação no Odoo'
            }

        print("✅ Conectado com sucesso!")
        print()

        # 2. Buscar dados do PO
        print(f"2️⃣ Buscando Purchase Order ID {po_id}...")

        po_data = odoo.read(
            'purchase.order',
            [po_id],
            [
                'id',
                'name',
                'state',
                'team_id',
                'payment_provider_id',
                'partner_id',
                'amount_total',
            ]
        )

        if not po_data or len(po_data) == 0:
            return {
                'sucesso': False,
                'erro': f'Purchase Order {po_id} não encontrado'
            }

        po = po_data[0]

        print(f"✅ Purchase Order encontrado!")
        print(f"   ID: {po.get('id')}")
        print(f"   Nome: {po.get('name')}")
        print(f"   State: {po.get('state')}")
        print(f"   Team: {po.get('team_id')}")
        print(f"   Payment Provider: {po.get('payment_provider_id')}")
        print(f"   Partner: {po.get('partner_id')}")
        print(f"   Valor Total: {po.get('amount_total')}")
        print()

        # Verificar se state é 'draft'
        if po.get('state') != 'draft':
            print(f"⚠️  ATENÇÃO: State do PO é '{po.get('state')}', esperado 'draft'")
            print(f"   Não é possível confirmar pedido que não está em 'draft'")
            return {
                'sucesso': False,
                'erro': f"State do PO é '{po.get('state')}', esperado 'draft'"
            }

        # 3. Verificar e atualizar campos se necessário
        print("3️⃣ Verificando campos obrigatórios...")

        valores_atualizar = {}

        # Verificar team_id
        team_atual = po.get('team_id')
        if not team_atual or (isinstance(team_atual, list) and team_atual[0] != TEAM_LANCAMENTO_FRETE_ID):
            print(f"   ⚠️  team_id precisa ser atualizado para {TEAM_LANCAMENTO_FRETE_ID}")
            valores_atualizar['team_id'] = TEAM_LANCAMENTO_FRETE_ID
        else:
            print(f"   ✅ team_id já está correto: {team_atual}")

        # Verificar payment_provider_id
        provider_atual = po.get('payment_provider_id')
        if not provider_atual or (isinstance(provider_atual, list) and provider_atual[0] != PAYMENT_PROVIDER_TRANSFERENCIA_ID):
            print(f"   ⚠️  payment_provider_id precisa ser atualizado para {PAYMENT_PROVIDER_TRANSFERENCIA_ID}")
            valores_atualizar['payment_provider_id'] = PAYMENT_PROVIDER_TRANSFERENCIA_ID
        else:
            print(f"   ✅ payment_provider_id já está correto: {provider_atual}")

        print()

        # Atualizar campos se necessário
        if valores_atualizar:
            print("4️⃣ Atualizando campos do Purchase Order...")
            for campo, valor in valores_atualizar.items():
                print(f"   {campo}: {valor}")

            if not modo_teste:
                sucesso_update = odoo.write('purchase.order', [po_id], valores_atualizar)
                if sucesso_update:
                    print("✅ Campos atualizados com sucesso!")
                else:
                    print("❌ Erro ao atualizar campos!")
                    return {'sucesso': False, 'erro': 'Erro ao atualizar campos'}
            else:
                print("⚠️  [MODO TESTE] Simulando atualização dos campos")
            print()

        # 5. Confirmar Purchase Order
        print("5️⃣ Confirmando Purchase Order (button_confirm)...")
        print("   Contexto: {'validate_analytic': True}")

        if not modo_teste:
            try:
                resultado_confirm = odoo.execute_kw(
                    'purchase.order',
                    'button_confirm',
                    [[po_id]],
                    {'context': {'validate_analytic': True}}
                )
                print("✅ Purchase Order confirmado com sucesso!")
                print(f"   Resultado: {resultado_confirm}")
            except Exception as e:
                print(f"❌ Erro ao confirmar PO: {e}")
                return {'sucesso': False, 'erro': f'Erro ao confirmar PO: {e}'}
        else:
            print("⚠️  [MODO TESTE] Simulando execução de button_confirm")
            print("   IMPORTANTE: Verifique manualmente no Odoo se os campos estão corretos")
            print("   Após confirmar, execute novamente com modo_teste=False")

        print()
        print("=" * 100)
        print("✅ CONFIRMAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 100)
        print()

        return {
            'sucesso': True,
            'po_id': po_id,
            'po_name': po.get('name'),
            'modo_teste': modo_teste
        }

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        return {
            'sucesso': False,
            'erro': str(e)
        }


if __name__ == '__main__':
    # Teste com PO gerado
    PO_ID_TESTE = 31085

    print("\n")
    print("🔴 EXECUTANDO EM MODO REAL - CONFIRMANDO PURCHASE ORDER")
    print("=" * 100)
    print()

    resultado = confirmar_purchase_order(
        po_id=PO_ID_TESTE,
        modo_teste=False  # ✅ MODO REAL: Confirmando pedido
    )

    print()
    print("📊 RESULTADO FINAL:")
    pprint(resultado)
