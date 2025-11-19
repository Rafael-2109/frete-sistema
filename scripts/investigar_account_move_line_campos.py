"""
Script para INVESTIGAR todos os campos de account.move.line no Odoo
Descobre estrutura completa incluindo campos custom (x_studio_*)

Uso:
    python scripts/investigar_account_move_line_campos.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
import json
from datetime import datetime

def investigar_campos_account_move_line():
    """Investiga TODOS os campos disponíveis em account.move.line"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🔍 INVESTIGANDO CAMPOS DE account.move.line")
        print("=" * 80)

        connection = get_odoo_connection()
        uid = connection.authenticate()

        if not uid:
            print("❌ Falha na autenticação com Odoo")
            return

        print(f"✅ Autenticado com Odoo (UID: {uid})\n")

        # =====================================================
        # 1. BUSCAR METADADOS DOS CAMPOS
        # =====================================================
        print("\n📋 BUSCANDO METADADOS DOS CAMPOS...")
        print("-" * 80)

        try:
            # Usar fields_get para obter TODOS os campos
            fields_metadata = connection.execute_kw(
                'account.move.line',
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'relation', 'required', 'readonly', 'help']}
            )

            print(f"\n✅ {len(fields_metadata)} campos encontrados!\n")

            # =====================================================
            # 2. CATEGORIZAR CAMPOS
            # =====================================================
            campos_custom = {}
            campos_padrao = {}
            campos_relacionais = {}
            campos_data = {}
            campos_numericos = {}
            campos_texto = {}
            campos_booleanos = {}

            for nome_campo, metadata in fields_metadata.items():
                tipo = metadata.get('type', 'unknown')
                label = metadata.get('string', nome_campo)

                # Categorizar
                if nome_campo.startswith('x_studio_'):
                    campos_custom[nome_campo] = metadata
                elif tipo in ['many2one', 'one2many', 'many2many']:
                    campos_relacionais[nome_campo] = metadata
                elif tipo in ['date', 'datetime']:
                    campos_data[nome_campo] = metadata
                elif tipo in ['integer', 'float', 'monetary']:
                    campos_numericos[nome_campo] = metadata
                elif tipo == 'boolean':
                    campos_booleanos[nome_campo] = metadata
                elif tipo in ['char', 'text']:
                    campos_texto[nome_campo] = metadata
                else:
                    campos_padrao[nome_campo] = metadata

            # =====================================================
            # 3. EXIBIR CAMPOS CUSTOM (x_studio_*)
            # =====================================================
            print("\n🎨 CAMPOS CUSTOM (x_studio_*)")
            print("=" * 80)
            print(f"Total: {len(campos_custom)} campos\n")

            for nome_campo, metadata in sorted(campos_custom.items()):
                print(f"   🔹 {nome_campo}")
                print(f"      Label: {metadata.get('string', 'N/A')}")
                print(f"      Tipo: {metadata.get('type', 'unknown')}")
                if metadata.get('relation'):
                    print(f"      Relaciona com: {metadata['relation']}")
                if metadata.get('help'):
                    print(f"      Ajuda: {metadata['help']}")
                print()

            # =====================================================
            # 4. CAMPOS DE DATA
            # =====================================================
            print("\n📅 CAMPOS DE DATA")
            print("=" * 80)
            print(f"Total: {len(campos_data)} campos\n")

            for nome_campo, metadata in sorted(campos_data.items()):
                print(f"   📆 {nome_campo}")
                print(f"      Label: {metadata.get('string', 'N/A')}")
                print(f"      Tipo: {metadata.get('type', 'unknown')}")
                print()

            # =====================================================
            # 5. CAMPOS NUMÉRICOS
            # =====================================================
            print("\n💰 CAMPOS NUMÉRICOS")
            print("=" * 80)
            print(f"Total: {len(campos_numericos)} campos\n")

            for nome_campo, metadata in sorted(campos_numericos.items()):
                print(f"   💵 {nome_campo}")
                print(f"      Label: {metadata.get('string', 'N/A')}")
                print(f"      Tipo: {metadata.get('type', 'unknown')}")
                print()

            # =====================================================
            # 6. CAMPOS RELACIONAIS (partner_id, etc.)
            # =====================================================
            print("\n🔗 CAMPOS RELACIONAIS (Many2one, etc.)")
            print("=" * 80)
            print(f"Total: {len(campos_relacionais)} campos\n")

            for nome_campo, metadata in sorted(campos_relacionais.items()):
                print(f"   🔗 {nome_campo}")
                print(f"      Label: {metadata.get('string', 'N/A')}")
                print(f"      Tipo: {metadata.get('type', 'unknown')}")
                print(f"      Relaciona com: {metadata.get('relation', 'N/A')}")
                print()

            # =====================================================
            # 7. BUSCAR DADOS EXEMPLO
            # =====================================================
            print("\n📊 BUSCANDO DADOS EXEMPLO...")
            print("=" * 80)

            # Listar todos os campos para buscar
            todos_campos = list(fields_metadata.keys())

            # Limitar a campos importantes (evitar timeout)
            campos_exemplo = [
                'id', 'name', 'date', 'date_maturity', 'balance',
                'debit', 'credit', 'company_id', 'partner_id',
                'payment_provider_id'
            ]

            # Adicionar campos custom
            campos_exemplo.extend([c for c in campos_custom.keys()])

            print(f"\n🔍 Buscando 5 registros com {len(campos_exemplo)} campos...\n")

            try:
                registros = connection.search_read(
                    'account.move.line',
                    [['date', '>=', '2025-01-01']],  # Filtrar últimos registros
                    fields=campos_exemplo,
                    limit=5
                )

                print(f"✅ {len(registros)} registros encontrados!\n")

                for idx, registro in enumerate(registros, 1):
                    print(f"📌 Registro {idx}:")
                    print(f"   ID: {registro.get('id')}")
                    print(f"   Nome: {registro.get('name', 'N/A')}")
                    print(f"   Data: {registro.get('date', 'N/A')}")
                    print(f"   Vencimento: {registro.get('date_maturity', 'N/A')}")
                    print(f"   Saldo: {registro.get('balance', 0)}")

                    # Campos custom
                    print(f"\n   Campos Custom:")
                    for campo in campos_custom.keys():
                        valor = registro.get(campo, 'N/A')
                        label = campos_custom[campo].get('string', campo)
                        print(f"      {label} ({campo}): {valor}")

                    print("\n" + "-" * 80 + "\n")

            except Exception as e:
                print(f"⚠️  Erro ao buscar dados exemplo: {e}")

            # =====================================================
            # 8. SALVAR RESULTADO EM JSON
            # =====================================================
            print("\n💾 SALVANDO RESULTADO...")
            print("=" * 80)

            resultado = {
                "modelo": "account.move.line",
                "total_campos": len(fields_metadata),
                "data_analise": datetime.now().isoformat(),
                "categorias": {
                    "campos_custom": len(campos_custom),
                    "campos_data": len(campos_data),
                    "campos_numericos": len(campos_numericos),
                    "campos_relacionais": len(campos_relacionais),
                    "campos_texto": len(campos_texto),
                    "campos_booleanos": len(campos_booleanos),
                    "campos_outros": len(campos_padrao)
                },
                "campos_detalhados": {
                    "custom": {k: v for k, v in campos_custom.items()},
                    "data": {k: v for k, v in campos_data.items()},
                    "numericos": {k: v for k, v in campos_numericos.items()},
                    "relacionais": {k: v for k, v in campos_relacionais.items()},
                    "texto": {k: v for k, v in campos_texto.items()},
                    "booleanos": {k: v for k, v in campos_booleanos.items()},
                    "outros": {k: v for k, v in campos_padrao.items()}
                },
                "lista_completa_campos": sorted(fields_metadata.keys())
            }

            arquivo_saida = 'account_move_line_campos_completo.json'
            with open(arquivo_saida, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n✅ Análise completa salva em: {arquivo_saida}")

            # =====================================================
            # 9. RESUMO FINAL
            # =====================================================
            print("\n\n" + "=" * 80)
            print("📊 RESUMO FINAL")
            print("=" * 80)
            print(f"""
   Total de campos: {len(fields_metadata)}

   📂 Categorias:
      🎨 Custom (x_studio_*): {len(campos_custom)}
      📅 Datas: {len(campos_data)}
      💰 Numéricos: {len(campos_numericos)}
      🔗 Relacionais: {len(campos_relacionais)}
      📝 Texto: {len(campos_texto)}
      ☑️  Booleanos: {len(campos_booleanos)}
      📦 Outros: {len(campos_padrao)}

   🎯 Campos importantes identificados:
      ✅ x_studio_nf_e (NF-e)
      ✅ x_studio_tipo_de_documento_fiscal (Tipo Doc)
      ✅ x_studio_status_de_pagamento (Status Pgto)
      ✅ partner_id (Parceiro/Cliente)
      ✅ date (Data)
      ✅ date_maturity (Vencimento)
      ✅ balance (Saldo)
      ✅ company_id (Empresa)
      ✅ payment_provider_id (Forma Pgto)

   📋 Arquivo gerado: {arquivo_saida}
            """)

            print("=" * 80)

        except Exception as e:
            print(f"❌ Erro ao buscar campos: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    investigar_campos_account_move_line()
