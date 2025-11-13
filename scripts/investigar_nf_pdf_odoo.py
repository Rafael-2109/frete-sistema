"""
Script de Investigação - PDFs de Notas Fiscais no Odoo
======================================================

OBJETIVO:
    Investigar como o Odoo armazena PDFs de notas fiscais de entrada:
    1. Modelo ir.attachment (anexos)
    2. Relação com stock.picking
    3. Campos disponíveis
    4. Como baixar o PDF

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os
import base64

# Adicionar path ANTES dos imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Imports do app após ajuste do path
from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

print("=" * 80)
print("🔍 INVESTIGAÇÃO - PDFs DE NOTAS FISCAIS NO ODOO")
print("=" * 80)

app = create_app()

with app.app_context():
    odoo = get_odoo_connection()

    # 1. Buscar um picking de exemplo recente
    print("\n1️⃣ Buscando picking de exemplo...")

    pickings = odoo.execute_kw(
        'stock.picking',
        'search_read',
        [[
            ['picking_type_code', '=', 'incoming'],
            ['state', '=', 'done']
        ]],
        {'fields': ['id', 'name', 'origin', 'date_done'], 'limit': 3}
    )

    if not pickings:
        print("❌ Nenhum picking encontrado!")
        sys.exit(1)

    print(f"✅ Encontrados {len(pickings)} pickings")

    for picking in pickings:
        print(f"\n   📦 Picking: {picking['name']} (ID: {picking['id']})")
        print(f"      Origin: {picking.get('origin')}")
        print(f"      Date: {picking.get('date_done')}")

    # 2. Investigar anexos (ir.attachment)
    print("\n" + "=" * 80)
    print("2️⃣ Investigando modelo ir.attachment...")
    print("=" * 80)

    picking_id = pickings[0]['id']
    picking_name = pickings[0]['name']

    print(f"\n🔍 Buscando anexos do picking {picking_name} (ID: {picking_id})...")

    # 2.1 Buscar anexos vinculados ao picking
    anexos = odoo.execute_kw(
        'ir.attachment',
        'search_read',
        [[
            ['res_model', '=', 'stock.picking'],
            ['res_id', '=', picking_id]
        ]],
        {'fields': [
            'id', 'name', 'mimetype', 'type',
            'res_model', 'res_id', 'file_size', 'checksum',
            'description'
        ]}
    )

    if anexos:
        print(f"✅ Encontrados {len(anexos)} anexo(s)")

        for anexo in anexos:
            print(f"\n   📎 Anexo: {anexo.get('name')}")
            print(f"      ID: {anexo.get('id')}")
            print(f"      Tipo MIME: {anexo.get('mimetype')}")
            print(f"      Tipo: {anexo.get('type')}")
            print(f"      Tamanho: {anexo.get('file_size')} bytes")
            print(f"      Checksum: {anexo.get('checksum')}")
            print(f"      Descrição: {anexo.get('description')}")
    else:
        print("⚠️  Nenhum anexo encontrado neste picking")

    # 2.2 Tentar buscar por nome de arquivo (padrão NF)
    print(f"\n🔍 Buscando anexos com padrão de NF...")

    anexos_nf = odoo.execute_kw(
        'ir.attachment',
        'search_read',
        [[
            ['res_model', '=', 'stock.picking'],
            '|',
            ['name', 'ilike', 'nota'],
            ['name', 'ilike', 'nfe'],
        ]],
        {'fields': ['id', 'name', 'res_id', 'mimetype', 'file_size'], 'limit': 5}
    )

    if anexos_nf:
        print(f"✅ Encontrados {len(anexos_nf)} anexo(s) com padrão NF")

        for anexo in anexos_nf:
            print(f"\n   📎 {anexo.get('name')}")
            print(f"      ID Anexo: {anexo.get('id')}")
            print(f"      ID Picking: {anexo.get('res_id')}")
            print(f"      Tipo: {anexo.get('mimetype')}")
            print(f"      Tamanho: {anexo.get('file_size')} bytes")
    else:
        print("⚠️  Nenhum anexo com padrão NF encontrado")

    # 3. Testar download de um anexo
    if anexos or anexos_nf:
        print("\n" + "=" * 80)
        print("3️⃣ Testando download de PDF...")
        print("=" * 80)

        anexo_teste = anexos[0] if anexos else anexos_nf[0]
        anexo_id = anexo_teste['id']
        anexo_nome = anexo_teste.get('name')

        print(f"\n🔍 Baixando anexo: {anexo_nome} (ID: {anexo_id})")

        # Buscar o campo 'datas' que contém o conteúdo base64
        anexo_completo = odoo.execute_kw(
            'ir.attachment',
            'read',
            [[anexo_id]],
            {'fields': ['datas', 'name', 'mimetype']}
        )

        if anexo_completo and anexo_completo[0].get('datas'):
            conteudo_base64 = anexo_completo[0]['datas']
            print(f"✅ Conteúdo base64 obtido: {len(conteudo_base64)} caracteres")

            # Tentar decodificar
            try:
                conteudo_bytes = base64.b64decode(conteudo_base64)
                print(f"✅ Decodificado: {len(conteudo_bytes)} bytes")

                # Verificar se é PDF
                if conteudo_bytes.startswith(b'%PDF'):
                    print("✅ Confirmado: É um arquivo PDF válido!")
                else:
                    print(f"⚠️  Não é PDF. Primeiros bytes: {conteudo_bytes[:20]}")

            except Exception as e:
                print(f"❌ Erro ao decodificar: {e}")
        else:
            print("⚠️  Campo 'datas' vazio ou não encontrado")

    # 4. Investigar account.move (nota fiscal eletrônica)
    print("\n" + "=" * 80)
    print("4️⃣ Investigando modelo account.move (NFe)...")
    print("=" * 80)

    print(f"\n🔍 Buscando notas fiscais relacionadas ao picking...")

    # Buscar por origin ou documento relacionado
    origin = pickings[0].get('origin')

    if origin:
        nfes = odoo.execute_kw(
            'account.move',
            'search_read',
            [[
                ['ref', '=', origin],
                ['move_type', 'in', ['in_invoice', 'in_refund']]  # Notas de entrada
            ]],
            {'fields': ['id', 'name', 'ref', 'move_type', 'state', 'invoice_date'], 'limit': 5}
        )

        if nfes:
            print(f"✅ Encontradas {len(nfes)} nota(s) fiscal(is)")

            for nfe in nfes:
                print(f"\n   📄 NFe: {nfe.get('name')}")
                print(f"      ID: {nfe.get('id')}")
                print(f"      Ref: {nfe.get('ref')}")
                print(f"      Tipo: {nfe.get('move_type')}")
                print(f"      Estado: {nfe.get('state')}")
                print(f"      Data: {nfe.get('invoice_date')}")

                # Buscar anexos da NFe
                anexos_nfe = odoo.execute_kw(
                    'ir.attachment',
                    'search_read',
                    [[
                        ['res_model', '=', 'account.move'],
                        ['res_id', '=', nfe['id']]
                    ]],
                    {'fields': ['id', 'name', 'mimetype', 'file_size']}
                )

                if anexos_nfe:
                    print(f"      📎 Anexos: {len(anexos_nfe)}")
                    for anexo in anexos_nfe:
                        print(f"         - {anexo.get('name')} ({anexo.get('mimetype')})")
        else:
            print("⚠️  Nenhuma nota fiscal encontrada")
    else:
        print("⚠️  Picking sem origin, não é possível buscar NFe")

    print("\n" + "=" * 80)
    print("✅ INVESTIGAÇÃO CONCLUÍDA")
    print("=" * 80)

    print("\n📋 RESUMO:")
    print("   1. Anexos são armazenados em 'ir.attachment'")
    print("   2. Vinculados via res_model='stock.picking' e res_id=picking_id")
    print("   3. Conteúdo em base64 no campo 'datas'")
    print("   4. NFes podem estar em 'account.move' com anexos próprios")
    print("\n" + "=" * 80)
