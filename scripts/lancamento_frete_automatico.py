"""
Script de Lançamento Automático de Frete no Odoo
=================================================

OBJETIVO:
    Automatizar o lançamento de CTe no Odoo seguindo o processo manual:

    1. Buscar CTe pela chave no modelo l10n_br_ciel_it_account.dfe
    2. Atualizar l10n_br_data_entrada com data de hoje
    3. Atualizar l10n_br_tipo_pedido para 'servico'
    4. Atualizar linha existente com product_id do "SERVICO DE FRETE"
    5. Atualizar vencimento do pagamento
    6. Executar action_gerar_po_dfe

CHAVE CTe TESTE: 33251120341933000150570010000281801000319398
DFe ID TESTE: 32639

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
import json
from datetime import datetime, date
from pprint import pprint

# Configuração Odoo
ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'database': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69',
}

# IDs fixos descobertos na investigação
PRODUTO_SERVICO_FRETE_ID = 29993  # ID do produto "SERVIÇO DE FRETE" (código 800000025)
CONTA_ANALITICA_LOGISTICA_ID = 1186  # ID da conta analítica "LOGISTICA TRANSPORTE" (código 119009)


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

    def write(self, model, ids, values):
        """Atualiza registros"""
        return self.execute_kw(model, 'write', [ids, values])


def lancar_frete_odoo(chave_cte, data_vencimento=None, modo_teste=True):
    """
    Lança frete no Odoo automaticamente

    Args:
        chave_cte: Chave de acesso do CTe
        data_vencimento: Data de vencimento (opcional, padrão: 30/11/2025)
        modo_teste: Se True, apenas simula sem executar action_gerar_po_dfe

    Returns:
        dict: Resultado do lançamento
    """
    print("=" * 100)
    print("🚀 LANÇAMENTO AUTOMÁTICO DE FRETE NO ODOO")
    print("=" * 100)
    print()
    print(f"Chave CTe: {chave_cte}")
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

        # 2. Buscar DFe pela chave
        print(f"2️⃣ Buscando DFe pela chave: {chave_cte}...")
        dfe_data = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [('protnfe_infnfe_chnfe', '=', chave_cte)],
            fields=['id', 'name', 'l10n_br_status', 'l10n_br_tipo_pedido', 'l10n_br_data_entrada', 'lines_ids', 'dups_ids'],
            limit=1
        )

        if not dfe_data or len(dfe_data) == 0:
            return {
                'sucesso': False,
                'erro': f'DFe não encontrado com chave {chave_cte}'
            }

        dfe = dfe_data[0]
        dfe_id = dfe['id']

        print(f"✅ DFe encontrado!")
        print(f"   ID: {dfe_id}")
        print(f"   Nome: {dfe['name']}")
        print(f"   Status: {dfe['l10n_br_status']}")
        print(f"   Tipo Pedido Atual: {dfe['l10n_br_tipo_pedido']}")
        print(f"   Data Entrada Atual: {dfe['l10n_br_data_entrada']}")
        print()

        # Verificar se status está correto (deve ser '04' para gerar PO)
        if dfe['l10n_br_status'] != '04':
            print(f"⚠️  ATENÇÃO: Status do DFe é '{dfe['l10n_br_status']}', esperado '04'")
            print("   O lançamento pode falhar se status não for '04'")
            print()

        # 3. Atualizar campos do DFe
        print("3️⃣ Atualizando campos do DFe...")
        hoje = date.today().strftime('%Y-%m-%d')

        valores_dfe = {
            'l10n_br_data_entrada': hoje,
            'l10n_br_tipo_pedido': 'servico'
        }

        print(f"   l10n_br_data_entrada: {hoje}")
        print(f"   l10n_br_tipo_pedido: servico")

        if not modo_teste:
            sucesso_dfe = odoo.write('l10n_br_ciel_it_account.dfe', [dfe_id], valores_dfe)
            if sucesso_dfe:
                print("✅ DFe atualizado com sucesso!")
            else:
                print("❌ Erro ao atualizar DFe!")
                return {'sucesso': False, 'erro': 'Erro ao atualizar DFe'}
        else:
            print("⚠️  [MODO TESTE] Simulando atualização do DFe")

        print()

        # 4. Atualizar linha do DFe com produto
        print("4️⃣ Atualizando linha do DFe com produto SERVICO DE FRETE...")
        line_ids = dfe.get('lines_ids')

        if not line_ids or len(line_ids) == 0:
            return {
                'sucesso': False,
                'erro': 'Nenhuma linha encontrada no DFe'
            }

        line_id = line_ids[0]  # Pegar primeira linha
        print(f"   ID da linha: {line_id}")

        valores_linha = {
            'product_id': PRODUTO_SERVICO_FRETE_ID,
            'l10n_br_quantidade': 1.0,
            'product_uom_id': 1,  # UN (Units)
        }

        print(f"   product_id: {PRODUTO_SERVICO_FRETE_ID} (SERVIÇO DE FRETE)")
        print(f"   l10n_br_quantidade: 1.0")
        print(f"   product_uom_id: 1 (UN)")

        # Verificar se deve preencher analytic_distribution manualmente
        # Segundo você, ao preencher produto, trigger pode preencher automaticamente
        # Vou deixar comentado para teste inicial
        # valores_linha['analytic_distribution'] = {str(CONTA_ANALITICA_LOGISTICA_ID): 100}

        if not modo_teste:
            sucesso_linha = odoo.write('l10n_br_ciel_it_account.dfe.line', [line_id], valores_linha)
            if sucesso_linha:
                print("✅ Linha atualizada com sucesso!")
            else:
                print("❌ Erro ao atualizar linha!")
                return {'sucesso': False, 'erro': 'Erro ao atualizar linha'}
        else:
            print("⚠️  [MODO TESTE] Simulando atualização da linha")

        print()

        # 5. Atualizar vencimento do pagamento
        print("5️⃣ Atualizando vencimento do pagamento...")
        pagamento_ids = dfe.get('dups_ids')

        if not data_vencimento:
            data_vencimento = '2025-11-30'  # Padrão de teste

        if pagamento_ids and len(pagamento_ids) > 0:
            pagamento_id = pagamento_ids[0]
            print(f"   ID do pagamento: {pagamento_id}")
            print(f"   Novo vencimento: {data_vencimento}")

            valores_pagamento = {
                'cobr_dup_dvenc': data_vencimento
            }

            if not modo_teste:
                sucesso_pagamento = odoo.write('l10n_br_ciel_it_account.dfe.pagamento', [pagamento_id], valores_pagamento)
                if sucesso_pagamento:
                    print("✅ Vencimento atualizado com sucesso!")
                else:
                    print("❌ Erro ao atualizar vencimento!")
                    return {'sucesso': False, 'erro': 'Erro ao atualizar vencimento'}
            else:
                print("⚠️  [MODO TESTE] Simulando atualização do vencimento")
        else:
            print("   ⚠️  Nenhum pagamento encontrado")

        print()

        # 6. Executar action_gerar_po_dfe
        print("6️⃣ Executando action_gerar_po_dfe...")
        print("   Contexto: {'validate_analytic': True}")

        if not modo_teste:
            try:
                resultado_po = odoo.execute_kw(
                    'l10n_br_ciel_it_account.dfe',
                    'action_gerar_po_dfe',
                    [[dfe_id]],
                    {'context': {'validate_analytic': True}}
                )
                print("✅ PO gerado com sucesso!")
                print(f"   Resultado: {resultado_po}")
            except Exception as e:
                print(f"❌ Erro ao gerar PO: {e}")
                return {'sucesso': False, 'erro': f'Erro ao gerar PO: {e}'}
        else:
            print("⚠️  [MODO TESTE] Simulando execução de action_gerar_po_dfe")
            print("   IMPORTANTE: Verifique manualmente no Odoo se os campos foram atualizados corretamente")
            print("   Após confirmar, execute novamente com modo_teste=False")

        print()
        print("=" * 100)
        print("✅ LANÇAMENTO CONCLUÍDO COM SUCESSO!")
        print("=" * 100)
        print()

        return {
            'sucesso': True,
            'dfe_id': dfe_id,
            'line_id': line_id,
            'pagamento_id': pagamento_ids[0] if pagamento_ids else None,
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
    # Teste com CTe cobaia
    CHAVE_TESTE = '33251120341933000150570010000281801000319398'
    DATA_VENCIMENTO_TESTE = '2025-11-30'

    print("\n")
    print("🔴 EXECUTANDO EM MODO REAL - EFETUANDO LANÇAMENTO NO ODOO")
    print("=" * 100)
    print()

    resultado = lancar_frete_odoo(
        chave_cte=CHAVE_TESTE,
        data_vencimento=DATA_VENCIMENTO_TESTE,
        modo_teste=False  # ✅ MODO REAL: Efetuando lançamento
    )

    print()
    print("📊 RESULTADO FINAL:")
    pprint(resultado)
