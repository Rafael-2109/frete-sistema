"""
Investigar Campos Disponíveis no stock.picking
===============================================

OBJETIVO: Descobrir TODOS os campos disponíveis no modelo stock.picking
          para verificar se há campos relacionados a NF/XML/PDF

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

print("=" * 80)
print("🔍 INVESTIGANDO CAMPOS DO MODELO stock.picking")
print("=" * 80)

app = create_app()

with app.app_context():
    odoo = get_odoo_connection()

    # Buscar TODOS os campos do modelo
    print("\n1️⃣ Listando TODOS os campos do modelo stock.picking...")

    try:
        # Usar fields_get para obter metadados
        campos = odoo.execute_kw(
            'stock.picking',
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help']}
        )

        # Filtrar campos relacionados a NF/XML/Fiscal
        campos_fiscais = {}
        keywords = ['nf', 'nota', 'fiscal', 'xml', 'pdf', 'danfe', 'invoice', 'document', 'eletr']

        for nome_campo, info in campos.items():
            campo_lower = nome_campo.lower()
            string_lower = info.get('string', '').lower()
            help_lower = info.get('help', '').lower()

            for keyword in keywords:
                if keyword in campo_lower or keyword in string_lower or keyword in help_lower:
                    campos_fiscais[nome_campo] = info
                    break

        if campos_fiscais:
            print(f"\n✅ Encontrados {len(campos_fiscais)} campos relacionados a NF/Fiscal:\n")

            for nome, info in sorted(campos_fiscais.items()):
                print(f"   📋 {nome}")
                print(f"      Label: {info.get('string')}")
                print(f"      Tipo: {info.get('type')}")
                if info.get('help'):
                    print(f"      Ajuda: {info.get('help')}")
                print()
        else:
            print("\n⚠️  Nenhum campo fiscal encontrado no stock.picking")

        # 2. Buscar um picking real e ver seus campos
        print("\n" + "=" * 80)
        print("2️⃣ Buscando valores reais de um picking...")
        print("=" * 80)

        pickings = odoo.execute_kw(
            'stock.picking',
            'search_read',
            [[
                ['picking_type_code', '=', 'incoming'],
                ['state', '=', 'done']
            ]],
            {'limit': 1}
        )

        if pickings:
            picking = pickings[0]
            picking_id = picking['id']
            picking_name = picking.get('name')

            print(f"\n📦 Picking: {picking_name} (ID: {picking_id})")
            print(f"\nCAMPOS COM VALORES:\n")

            # Ordenar e exibir campos com valores
            for campo, valor in sorted(picking.items()):
                if valor and campo not in ['id', '__last_update']:
                    # Truncar valores muito longos
                    if isinstance(valor, str) and len(valor) > 100:
                        valor_print = valor[:100] + '...'
                    else:
                        valor_print = valor

                    print(f"   {campo}: {valor_print}")

    except Exception as e:
        print(f"❌ Erro: {e}")

    # 3. Verificar se há módulo fiscal instalado
    print("\n" + "=" * 80)
    print("3️⃣ Verificando módulos fiscais instalados...")
    print("=" * 80)

    try:
        modulos_fiscais = odoo.execute_kw(
            'ir.module.module',
            'search_read',
            [[
                ['state', '=', 'installed'],
                '|', '|', '|',
                ['name', 'ilike', 'fiscal'],
                ['name', 'ilike', 'nfe'],
                ['name', 'ilike', 'brazil'],
                ['name', 'ilike', 'l10n_br']
            ]],
            {'fields': ['name', 'shortdesc', 'summary']}
        )

        if modulos_fiscais:
            print(f"\n✅ Encontrados {len(modulos_fiscais)} módulo(s) fiscal(is):\n")
            for modulo in modulos_fiscais:
                print(f"   📦 {modulo['name']}")
                print(f"      {modulo.get('shortdesc') or modulo.get('summary')}\n")
        else:
            print("\n⚠️  Nenhum módulo fiscal instalado")

    except Exception as e:
        print(f"❌ Erro ao buscar módulos: {e}")

    print("\n" + "=" * 80)
    print("✅ INVESTIGAÇÃO CONCLUÍDA")
    print("=" * 80)
