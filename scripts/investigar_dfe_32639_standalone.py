"""
Script de Investigação: DFe ID 32639 (CTe Cobaia) - Versão Standalone
======================================================================

OBJETIVO:
    Buscar TODOS os dados do DFe ID 32639 incluindo:
    - Linhas existentes (l10n_br_ciel_it_account.dfe.line)
    - Pagamentos existentes (l10n_br_ciel_it_account.dfe.pagamento)
    - Produto "SERVICO DE FRETE" (ID exato)
    - Estrutura de campos necessários para lançamento

CHAVE CTe: 33251120341933000150570010000281801000319398
DFe ID: 32639

AUTOR: Sistema de Fretes
DATA: 14/11/2025
"""

import xmlrpc.client
import ssl
import json
from datetime import datetime
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

    def search_read(self, model, domain, fields=None, limit=None):
        """Busca e lê registros"""
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        return self.execute_kw(model, 'search_read', [domain], kwargs)


def investigar_dfe_32639():
    """
    Investiga DFe ID 32639 para preparar lançamento automático
    """
    print("=" * 100)
    print("🔍 INVESTIGANDO DFe ID 32639 - CTe Cobaia")
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

        # 2. Buscar dados completos do DFe 32639
        print("2️⃣ Buscando dados completos do DFe ID 32639...")

        dfe_data = odoo.read(
            'l10n_br_ciel_it_account.dfe',
            [32639],
            [
                'id',
                'name',
                'active',
                'is_cte',
                'l10n_br_status',
                'l10n_br_data_entrada',
                'l10n_br_tipo_pedido',
                'protnfe_infnfe_chnfe',
                'nfe_infnfe_ide_nnf',
                'nfe_infnfe_total_icmstot_vnf',
                'lines_ids',
                'dups_ids',
            ]
        )

        if not dfe_data or len(dfe_data) == 0:
            print("❌ DFe não encontrado!")
            return

        dfe = dfe_data[0]

        print(f"✅ DFe encontrado!")
        print(f"   ID: {dfe.get('id')}")
        print(f"   Nome: {dfe.get('name')}")
        print(f"   Status: {dfe.get('l10n_br_status')}")
        print(f"   Tipo Pedido: {dfe.get('l10n_br_tipo_pedido')}")
        print(f"   Data Entrada: {dfe.get('l10n_br_data_entrada')}")
        print(f"   Chave: {dfe.get('protnfe_infnfe_chnfe')}")
        print()

        # 3. Buscar linhas existentes
        print("3️⃣ Buscando LINHAS existentes (l10n_br_ciel_it_account.dfe.line)...")
        line_ids = dfe.get('lines_ids')
        linhas_detalhes = []

        if line_ids and isinstance(line_ids, list) and len(line_ids) > 0:
            print(f"   Total de linhas: {len(line_ids)}")
            print(f"   IDs das linhas: {line_ids}")
            print()

            for line_id in line_ids:
                print(f"   📋 Buscando detalhes da linha ID {line_id}...")

                # Buscar TODOS os campos sem especificar (para descobrir estrutura real)
                linha_data = odoo.read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [line_id],
                    None  # Buscar todos os campos
                )

                if linha_data and len(linha_data) > 0:
                    linha = linha_data[0]
                    linhas_detalhes.append(linha)
                    print(f"   ✅ Linha {line_id} - TODOS OS CAMPOS:")
                    for campo, valor in sorted(linha.items()):
                        print(f"      {campo}: {valor}")
                    print()
        else:
            print("   ⚠️  Nenhuma linha encontrada!")
            print()

        # 4. Buscar pagamentos existentes
        print("4️⃣ Buscando PAGAMENTOS existentes (l10n_br_ciel_it_account.dfe.pagamento)...")
        pagamento_ids = dfe.get('dups_ids')
        pagamentos_detalhes = []

        if pagamento_ids and isinstance(pagamento_ids, list) and len(pagamento_ids) > 0:
            print(f"   Total de pagamentos: {len(pagamento_ids)}")
            print(f"   IDs dos pagamentos: {pagamento_ids}")
            print()

            for pag_id in pagamento_ids:
                print(f"   💰 Buscando detalhes do pagamento ID {pag_id}...")

                pagamento_data = odoo.read(
                    'l10n_br_ciel_it_account.dfe.pagamento',
                    [pag_id],
                    [
                        'id',
                        'cobr_dup_dvenc',
                        'cobr_dup_ndup',
                        'cobr_dup_vdup',
                    ]
                )

                if pagamento_data and len(pagamento_data) > 0:
                    pagamento = pagamento_data[0]
                    pagamentos_detalhes.append(pagamento)
                    print(f"   ✅ Pagamento {pag_id}:")
                    print(f"      cobr_dup_dvenc: {pagamento.get('cobr_dup_dvenc')}")
                    print(f"      cobr_dup_ndup: {pagamento.get('cobr_dup_ndup')}")
                    print(f"      cobr_dup_vdup: {pagamento.get('cobr_dup_vdup')}")
                    print()
        else:
            print("   ⚠️  Nenhum pagamento encontrado!")
            print()

        # 5. Buscar produto "SERVICO DE FRETE"
        print("5️⃣ Buscando produto 'SERVICO DE FRETE' (product.product)...")

        produtos = odoo.search_read(
            'product.product',
            [
                '|',
                ('default_code', '=', '800000025'),
                ('name', 'ilike', 'SERVICO DE FRETE')
            ],
            fields=['id', 'name', 'default_code', 'uom_id'],
            limit=5
        )

        if produtos:
            print(f"   ✅ Produto(s) encontrado(s): {len(produtos)}")
            for prod in produtos:
                print(f"      ID: {prod.get('id')} | Código: {prod.get('default_code')} | Nome: {prod.get('name')}")
                print(f"      UOM: {prod.get('uom_id')}")
            print()
        else:
            print("   ⚠️  Produto não encontrado! Tentando busca mais ampla...")

            produtos_ampla = odoo.search_read(
                'product.product',
                [('name', 'ilike', 'FRETE')],
                fields=['id', 'name', 'default_code', 'uom_id'],
                limit=10
            )

            if produtos_ampla:
                print(f"   📦 Produtos relacionados a 'FRETE': {len(produtos_ampla)}")
                for prod in produtos_ampla:
                    print(f"      ID: {prod.get('id')} | Código: {prod.get('default_code')} | Nome: {prod.get('name')}")
                produtos = produtos_ampla
            print()

        # 6. Buscar conta analítica "LOGISTICA TRANSPORTE"
        print("6️⃣ Buscando conta analítica 'LOGISTICA TRANSPORTE'...")

        contas_analiticas = odoo.search_read(
            'account.analytic.account',
            [
                '|',
                ('code', '=', '119009'),
                ('name', 'ilike', 'LOGISTICA TRANSPORTE')
            ],
            fields=['id', 'name', 'code'],
            limit=5
        )

        if contas_analiticas:
            print(f"   ✅ Conta(s) analítica(s) encontrada(s): {len(contas_analiticas)}")
            for conta in contas_analiticas:
                print(f"      ID: {conta.get('id')} | Código: {conta.get('code')} | Nome: {conta.get('name')}")
            print()
        else:
            print("   ⚠️  Conta analítica não encontrada!")
            print()

        # 7. Resumo para script de lançamento
        print("=" * 100)
        print("📋 RESUMO PARA SCRIPT DE LANÇAMENTO")
        print("=" * 100)
        print()
        print("DFe ID: 32639")
        print(f"Status atual: {dfe.get('l10n_br_status')}")
        print(f"Tipo pedido atual: {dfe.get('l10n_br_tipo_pedido')}")
        print(f"Data entrada atual: {dfe.get('l10n_br_data_entrada')}")
        print(f"Linhas existentes: {line_ids if line_ids else 'Nenhuma'}")
        print(f"Pagamentos existentes: {pagamento_ids if pagamento_ids else 'Nenhum'}")
        print()

        if produtos and len(produtos) > 0:
            produto_frete = produtos[0]
            print(f"✅ Produto SERVICO DE FRETE:")
            print(f"   ID: {produto_frete.get('id')}")
            print(f"   Nome: {produto_frete.get('name')}")
            print(f"   Código: {produto_frete.get('default_code')}")
            print()

        if contas_analiticas and len(contas_analiticas) > 0:
            conta_logistica = contas_analiticas[0]
            print(f"✅ Conta Analítica LOGISTICA TRANSPORTE:")
            print(f"   ID: {conta_logistica.get('id')}")
            print(f"   Nome: {conta_logistica.get('name')}")
            print(f"   Código: {conta_logistica.get('code')}")
            print()

        print("=" * 100)
        print()
        print("✅ INVESTIGAÇÃO CONCLUÍDA!")
        print()

        # Salvar resultado em arquivo
        import os
        log_file = os.path.join(os.path.dirname(__file__), 'investigacao_dfe_32639.json')

        resultado = {
            'dfe_id': 32639,
            'dfe_data': dfe,
            'linhas': linhas_detalhes,
            'pagamentos': pagamentos_detalhes,
            'produto_frete': produtos[0] if produtos else None,
            'conta_analitica': contas_analiticas[0] if contas_analiticas else None,
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
    investigar_dfe_32639()
