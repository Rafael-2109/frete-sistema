"""
Testar Acesso ao PDF via dfe_id
================================

OBJETIVO: Validar acesso ao PDF da NF através do caminho:
          purchase.order → dfe_id → l10n_br_ciel_it_account.dfe → l10n_br_pdf_dfe

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os
import base64

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

print("=" * 80)
print("🔍 TESTANDO ACESSO AO PDF VIA dfe_id")
print("=" * 80)

app = create_app()

with app.app_context():
    odoo = get_odoo_connection()

    # 1. Buscar pedido de compra com dfe_id
    print("\n1️⃣ Buscando pedidos de compra com dfe_id preenchido...")

    pedidos = odoo.execute_kw(
        'purchase.order',
        'search_read',
        [[
            ['state', 'in', ['purchase', 'done']],
            ['dfe_id', '!=', False]  # Apenas com dfe_id preenchido
        ]],
        {'fields': ['id', 'name', 'dfe_id', 'partner_id', 'date_order'], 'limit': 3}
    )

    if not pedidos:
        print("❌ Nenhum pedido com dfe_id encontrado!")
        sys.exit(1)

    print(f"✅ Encontrados {len(pedidos)} pedido(s) com dfe_id\n")

    for pedido in pedidos:
        print(f"   📋 Pedido: {pedido['name']} (ID: {pedido['id']})")
        print(f"      DFe ID: {pedido.get('dfe_id')}")
        print(f"      Fornecedor: {pedido.get('partner_id')}")
        print(f"      Data: {pedido.get('date_order')}")
        print()

    # 2. Investigar modelo l10n_br_ciel_it_account.dfe
    print("=" * 80)
    print("2️⃣ Investigando modelo l10n_br_ciel_it_account.dfe...")
    print("=" * 80)

    dfe_id = pedidos[0]['dfe_id']
    if isinstance(dfe_id, (list, tuple)):
        dfe_id = dfe_id[0]

    print(f"\n🔍 Buscando DFe ID: {dfe_id}...")

    try:
        # Primeiro, descobrir quais campos existem
        campos_dfe = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'fields_get',
            [],
            {'attributes': ['string', 'type']}
        )

        print(f"\n✅ Campos disponíveis no modelo DFe:\n")

        # Filtrar campos relevantes
        campos_relevantes = {}
        keywords = ['pdf', 'xml', 'danfe', 'nota', 'nfe', 'numero', 'chave', 'access']

        for nome, info in campos_dfe.items():
            nome_lower = nome.lower()
            string_lower = info.get('string', '').lower()

            for keyword in keywords:
                if keyword in nome_lower or keyword in string_lower:
                    campos_relevantes[nome] = info
                    break

        for nome, info in sorted(campos_relevantes.items()):
            print(f"   📋 {nome}")
            print(f"      Label: {info.get('string')}")
            print(f"      Tipo: {info.get('type')}")
            print()

    except Exception as e:
        print(f"❌ Erro ao buscar campos: {e}")

    # 3. Buscar dados completos do DFe
    print("=" * 80)
    print("3️⃣ Buscando dados completos do DFe...")
    print("=" * 80)

    try:
        dfe = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'read',
            [[dfe_id]],
            {'fields': list(campos_relevantes.keys())}
        )

        if dfe:
            dfe_data = dfe[0]
            print(f"\n✅ Dados do DFe:\n")

            for campo, valor in sorted(dfe_data.items()):
                if campo == 'id':
                    continue

                # Não exibir binários completos
                if isinstance(valor, str) and len(valor) > 100:
                    print(f"   {campo}: [Binary data - {len(valor)} bytes]")
                else:
                    print(f"   {campo}: {valor}")

    except Exception as e:
        print(f"❌ Erro ao buscar DFe: {e}")

    # 4. Tentar baixar o PDF
    print("\n" + "=" * 80)
    print("4️⃣ Tentando baixar PDF...")
    print("=" * 80)

    try:
        print(f"\n🔍 Buscando campo l10n_br_pdf_dfe do DFe ID {dfe_id}...")

        dfe_pdf = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'read',
            [[dfe_id]],
            {'fields': ['l10n_br_pdf_dfe', 'name']}
        )

        if dfe_pdf and dfe_pdf[0].get('l10n_br_pdf_dfe'):
            pdf_base64 = dfe_pdf[0]['l10n_br_pdf_dfe']
            nome_dfe = dfe_pdf[0].get('name', 'sem_nome')

            print(f"✅ PDF encontrado!")
            print(f"   Nome: {nome_dfe}")
            print(f"   Tamanho base64: {len(pdf_base64)} caracteres")

            # Decodificar
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                print(f"✅ Decodificado: {len(pdf_bytes)} bytes")

                # Verificar se é PDF
                if pdf_bytes.startswith(b'%PDF'):
                    print("✅ Confirmado: É um arquivo PDF válido!")

                    # Salvar para teste
                    test_path = f"/tmp/teste_nf_{dfe_id}.pdf"
                    with open(test_path, 'wb') as f:
                        f.write(pdf_bytes)
                    print(f"✅ PDF salvo em: {test_path}")

                else:
                    print(f"⚠️  Não é PDF. Primeiros bytes: {pdf_bytes[:20]}")

            except Exception as e:
                print(f"❌ Erro ao decodificar: {e}")

        else:
            print("⚠️  Campo l10n_br_pdf_dfe vazio ou não encontrado")

    except Exception as e:
        print(f"❌ Erro ao buscar PDF: {e}")

    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 80)

    print("\n📋 RESUMO:")
    print("   1. purchase.order tem campo dfe_id (many2one)")
    print("   2. dfe_id aponta para l10n_br_ciel_it_account.dfe")
    print("   3. DFe tem campo l10n_br_pdf_dfe (binary) com o PDF")
    print("   4. PDF pode ser baixado via base64")
    print("\n" + "=" * 80)
