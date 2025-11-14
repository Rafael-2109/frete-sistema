"""
Script: Verificar Campos do CTe no Odoo
========================================

Verifica:
1. informacoes_complementares (sempre False?)
2. Tomador (valores possíveis)
3. PDF/XML em base64

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


def verificar_campos():
    print("=" * 100)
    print("🔍 VERIFICANDO CAMPOS DO CTe NO ODOO")
    print("=" * 100)
    print()

    try:
        odoo = get_odoo_connection()

        if not odoo.authenticate():
            print("❌ Erro: Falha na autenticação")
            return

        print("✅ Conectado com sucesso!")
        print()

        # Buscar CTe de teste
        chave_cte = "35251121498155000170570010000025641000026852"

        filtro = [("protnfe_infnfe_chnfe", "=", chave_cte)]

        cte = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro,
            limit=1
        )

        if not cte:
            print("❌ CTe não encontrado!")
            return

        cte_data = cte[0]

        print(f"CTe ID: {cte_data.get('id')}")
        print(f"Nome: {cte_data.get('name')}")
        print()

        # 1. Informações Complementares
        print("=" * 100)
        print("1️⃣ INFORMAÇÕES COMPLEMENTARES")
        print("=" * 100)
        info_compl = cte_data.get('nfe_infnfe_infadic_infcpl')
        print(f"Tipo: {type(info_compl)}")
        print(f"Valor: {info_compl}")
        print(f"É False?: {info_compl is False}")
        print(f"É bool?: {isinstance(info_compl, bool)}")
        print()

        # 2. Tomador
        print("=" * 100)
        print("2️⃣ TOMADOR")
        print("=" * 100)
        tomador = cte_data.get('cte_infcte_ide_toma3_toma')
        print(f"Tipo: {type(tomador)}")
        print(f"Valor: {tomador}")
        print()

        # 3. PDF/XML
        print("=" * 100)
        print("3️⃣ PDF E XML")
        print("=" * 100)
        pdf_base64 = cte_data.get('l10n_br_pdf_dfe')
        xml_base64 = cte_data.get('l10n_br_xml_dfe')

        print(f"PDF existe?: {pdf_base64 is not None and pdf_base64 != False}")
        print(f"PDF tipo: {type(pdf_base64)}")
        if pdf_base64 and pdf_base64 != False:
            print(f"PDF tamanho: {len(pdf_base64)} chars")
            print(f"PDF preview: {pdf_base64[:50]}...")

        print()

        print(f"XML existe?: {xml_base64 is not None and xml_base64 != False}")
        print(f"XML tipo: {type(xml_base64)}")
        if xml_base64 and xml_base64 != False:
            print(f"XML tamanho: {len(xml_base64)} chars")
            print(f"XML preview: {xml_base64[:50]}...")

        print()

        # 4. Buscar vários CTes para ver padrões
        print("=" * 100)
        print("4️⃣ AMOSTRA DE 5 CTes")
        print("=" * 100)

        filtro_geral = [
            "&",
            "|",
            ("active", "=", True),
            ("active", "=", False),
            ("is_cte", "=", True)
        ]

        ctes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro_geral,
            [
                'id',
                'name',
                'cte_infcte_ide_toma3_toma',
                'nfe_infnfe_infadic_infcpl',
                'l10n_br_pdf_dfe',
                'l10n_br_xml_dfe'
            ],
            limit=5
        )

        for i, c in enumerate(ctes, 1):
            print(f"\n📋 CTe {i}:")
            print(f"   ID: {c.get('id')}")
            print(f"   Nome: {c.get('name')}")

            tomador_val = c.get('cte_infcte_ide_toma3_toma')
            print(f"   Tomador: {tomador_val} (tipo: {type(tomador_val).__name__})")

            info_val = c.get('nfe_infnfe_infadic_infcpl')
            print(f"   Info Compl: {info_val} (tipo: {type(info_val).__name__})")

            pdf_val = c.get('l10n_br_pdf_dfe')
            print(f"   PDF: {'✅ Sim' if pdf_val and pdf_val != False else '❌ Não'}")

            xml_val = c.get('l10n_br_xml_dfe')
            print(f"   XML: {'✅ Sim' if xml_val and xml_val != False else '❌ Não'}")

        print()
        print("=" * 100)
        print("✅ VERIFICAÇÃO CONCLUÍDA!")
        print("=" * 100)

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    verificar_campos()
