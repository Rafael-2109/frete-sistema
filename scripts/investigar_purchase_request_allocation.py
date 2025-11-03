"""
Script para investigar a tabela purchase_request_allocation_ids no Odoo
=======================================================================

Objetivo: Entender a estrutura e relacionamentos desta tabela
"""

import sys
import os
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection

def investigar_purchase_request_allocation():
    """
    Investiga a estrutura da tabela purchase_request_allocation no Odoo
    """
    print("=" * 80)
    print("🔍 INVESTIGANDO: purchase_request_allocation")
    print("=" * 80)

    conn = get_odoo_connection()

    # Autenticar
    uid = conn.authenticate()
    if not uid:
        print("❌ Falha na autenticação")
        return

    print(f"✅ Autenticado com sucesso (UID: {uid})")
    print()

    # ========================================
    # PASSO 1: Buscar o modelo no ir.model
    # ========================================
    print("📋 PASSO 1: Buscando modelo no ir.model...")
    print("-" * 80)

    try:
        modelos = conn.search_read(
            'ir.model',
            [['model', 'ilike', 'purchase.request.allocation']],
            ['id', 'name', 'model', 'info']
        )

        if not modelos:
            print("⚠️  Modelo não encontrado com 'purchase.request.allocation'")
            print("   Tentando buscar todos os modelos relacionados a purchase.request...")

            modelos = conn.search_read(
                'ir.model',
                [['model', 'ilike', 'purchase.request']],
                ['id', 'name', 'model', 'info']
            )

        if modelos:
            print(f"✅ Encontrados {len(modelos)} modelos:\n")
            for modelo in modelos:
                print(f"   - {modelo['model']} ({modelo['name']})")
        else:
            print("❌ Nenhum modelo encontrado")
            return
    except Exception as e:
        print(f"❌ Erro ao buscar modelo: {e}")
        return

    print()

    # ========================================
    # PASSO 2: Verificar campos do modelo
    # ========================================
    print("📊 PASSO 2: Investigando campos do modelo...")
    print("-" * 80)

    for modelo in modelos:
        if 'allocation' in modelo['model'].lower():
            print(f"\n🎯 MODELO ENCONTRADO: {modelo['model']}")
            print(f"   Nome: {modelo['name']}")
            print()

            try:
                # Buscar campos do modelo
                campos = conn.search_read(
                    'ir.model.fields',
                    [['model_id', '=', modelo['id']]],
                    ['name', 'field_description', 'ttype', 'relation', 'required']
                )

                print(f"   📋 CAMPOS ({len(campos)}):")
                print()

                campos_importantes = []
                for campo in sorted(campos, key=lambda x: x['name']):
                    info = f"      - {campo['name']:<35} ({campo['ttype']:<15})"

                    if campo.get('relation'):
                        info += f" → {campo['relation']}"
                        campos_importantes.append(campo)

                    if campo.get('required'):
                        info += " [OBRIGATÓRIO]"

                    print(info)

                # Destacar campos importantes
                if campos_importantes:
                    print()
                    print("   🔗 CAMPOS DE RELACIONAMENTO:")
                    print()
                    for campo in campos_importantes:
                        print(f"      ✅ {campo['name']}")
                        print(f"         Tipo: {campo['ttype']}")
                        print(f"         Relaciona com: {campo['relation']}")
                        print(f"         Descrição: {campo['field_description']}")
                        print()

            except Exception as e:
                print(f"   ❌ Erro ao buscar campos: {e}")

    print()

    # ========================================
    # PASSO 3: Buscar registros de exemplo
    # ========================================
    print("📦 PASSO 3: Buscando registros de exemplo...")
    print("-" * 80)

    for modelo in modelos:
        if 'allocation' in modelo['model'].lower():
            try:
                # Buscar primeiros 5 registros
                registros = conn.search_read(
                    modelo['model'],
                    [],
                    limit=5
                )

                if registros:
                    print(f"\n✅ Encontrados {len(registros)} registros de exemplo:")
                    print()

                    for idx, reg in enumerate(registros, 1):
                        print(f"   REGISTRO {idx}:")
                        pprint(reg, indent=6, width=100)
                        print()
                else:
                    print(f"⚠️  Nenhum registro encontrado no modelo {modelo['model']}")

            except Exception as e:
                print(f"❌ Erro ao buscar registros: {e}")

    print()
    print("=" * 80)
    print("✅ INVESTIGAÇÃO CONCLUÍDA")
    print("=" * 80)


if __name__ == '__main__':
    investigar_purchase_request_allocation()
