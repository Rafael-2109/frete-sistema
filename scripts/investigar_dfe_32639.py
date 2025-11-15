"""
Script de Investigação: DFe ID 32639 (CTe Cobaia)
==================================================

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

import sys
import os
from pprint import pprint
from datetime import datetime
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


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
        odoo = get_odoo_connection()

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
                'lines_ids',  # IDs das linhas (corrigido)
                'dups_ids',  # IDs dos pagamentos (corrigido)
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

        # 3. Buscar linhas existentes (lines_ids)
        print("3️⃣ Buscando LINHAS existentes (l10n_br_ciel_it_account.dfe.line)...")
        line_ids = dfe.get('lines_ids')

        if line_ids and isinstance(line_ids, list):
            print(f"   Total de linhas: {len(line_ids)}")
            print(f"   IDs das linhas: {line_ids}")
            print()

            # Buscar detalhes de cada linha
            for line_id in line_ids:
                print(f"   📋 Buscando detalhes da linha ID {line_id}...")

                linha_data = odoo.read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [line_id],
                    [
                        'id',
                        'product_id',
                        'analytic_distribution',
                        'l10n_br_quantidade',
                        'product_uom_id',
                        'name',
                        'price_unit',
                        'price_subtotal',
                    ]
                )

                if linha_data and len(linha_data) > 0:
                    linha = linha_data[0]
                    print(f"   ✅ Linha {line_id}:")
                    print(f"      product_id: {linha.get('product_id')}")
                    print(f"      analytic_distribution: {linha.get('analytic_distribution')}")
                    print(f"      l10n_br_quantidade: {linha.get('l10n_br_quantidade')}")
                    print(f"      product_uom_id: {linha.get('product_uom_id')}")
                    print(f"      name: {linha.get('name')}")
                    print(f"      price_unit: {linha.get('price_unit')}")
                    print(f"      price_subtotal: {linha.get('price_subtotal')}")
                    print()
        else:
            print("   ⚠️  Nenhuma linha encontrada!")
            print()

        # 4. Buscar pagamentos existentes (dups_ids)
        print("4️⃣ Buscando PAGAMENTOS existentes (l10n_br_ciel_it_account.dfe.pagamento)...")
        pagamento_ids = dfe.get('dups_ids')

        if pagamento_ids and isinstance(pagamento_ids, list):
            print(f"   Total de pagamentos: {len(pagamento_ids)}")
            print(f"   IDs dos pagamentos: {pagamento_ids}")
            print()

            # Buscar detalhes de cada pagamento
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

        # Tentar buscar por código [800000025]
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

            # Busca mais ampla
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

        # 7. Verificar métodos disponíveis no modelo DFe
        print("7️⃣ Verificando se método 'action_gerar_po_dfe' existe...")
        try:
            # Não dá para chamar diretamente, mas podemos listar métodos
            print("   ℹ️  Não é possível verificar métodos via XML-RPC diretamente")
            print("   ℹ️  Vamos assumir que 'action_gerar_po_dfe' existe baseado no HTML fornecido")
            print()
        except Exception as e:
            print(f"   ⚠️  Erro: {e}")
            print()

        # 8. Resumo para script de lançamento
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
        log_file = os.path.join(os.path.dirname(__file__), 'investigacao_dfe_32639.json')

        resultado = {
            'dfe_id': 32639,
            'dfe_data': dfe,
            'line_ids': line_ids,
            'pagamento_ids': pagamento_ids,
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
