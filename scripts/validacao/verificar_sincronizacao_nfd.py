#!/usr/bin/env python3
"""
Verifica se a sincronização das NFDs foi bem-sucedida

Autor: Sistema de Fretes
Data: 11/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar():
    """Verifica o estado da sincronização das NFDs"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("🔍 VERIFICAÇÃO DE SINCRONIZAÇÃO NFD")
        print("=" * 60)

        # 1. Contagem por tipo_documento
        result = db.session.execute(text("""
            SELECT
                COALESCE(tipo_documento, 'NULL') as tipo,
                COUNT(*) as total
            FROM nf_devolucao
            WHERE ativo = true
            GROUP BY tipo_documento
            ORDER BY tipo_documento NULLS LAST
        """)).fetchall()

        print("\n📊 CONTAGEM POR tipo_documento:")
        for row in result:
            print(f"   {row[0]}: {row[1]}")

        # 2. Contagem por status_odoo
        result = db.session.execute(text("""
            SELECT
                COALESCE(status_odoo, 'NULL') as status,
                COUNT(*) as total
            FROM nf_devolucao
            WHERE ativo = true
            GROUP BY status_odoo
            ORDER BY status_odoo NULLS LAST
        """)).fetchall()

        print("\n📊 CONTAGEM POR status_odoo:")
        for row in result:
            print(f"   {row[0]}: {row[1]}")

        # 3. NFDs tipo 'NFD' sem data_entrada (Pendentes)
        result = db.session.execute(text("""
            SELECT COUNT(*)
            FROM nf_devolucao
            WHERE tipo_documento = 'NFD'
            AND data_entrada IS NULL
            AND ativo = true
        """)).scalar()

        print(f"\n⚠️  NFDs tipo 'NFD' sem data_entrada (Pendente): {result}")

        # 4. NFDs tipo 'NFD' COM data_entrada (Entrada OK)
        result_ok = db.session.execute(text("""
            SELECT COUNT(*)
            FROM nf_devolucao
            WHERE tipo_documento = 'NFD'
            AND data_entrada IS NOT NULL
            AND ativo = true
        """)).scalar()

        print(f"✅ NFDs tipo 'NFD' com data_entrada (Entrada OK): {result_ok}")

        # 5. Contagem status_monitoramento
        result = db.session.execute(text("""
            SELECT
                COALESCE(status_monitoramento, 'NULL') as status,
                COUNT(*) as total
            FROM nf_devolucao
            WHERE ativo = true
            GROUP BY status_monitoramento
            ORDER BY status_monitoramento NULLS LAST
        """)).fetchall()

        print("\n📊 CONTAGEM POR status_monitoramento:")
        for row in result:
            print(f"   {row[0]}: {row[1]}")

        # 6. Contagem por origem_registro
        result = db.session.execute(text("""
            SELECT
                COALESCE(origem_registro, 'NULL') as origem,
                COUNT(*) as total
            FROM nf_devolucao
            WHERE ativo = true
            GROUP BY origem_registro
            ORDER BY origem_registro
        """)).fetchall()

        print("\n📊 CONTAGEM POR origem_registro:")
        for row in result:
            print(f"   {row[0]}: {row[1]}")

        # 7. Verificar consistência: NFDs do Odoo com tipo NULL
        result = db.session.execute(text("""
            SELECT COUNT(*)
            FROM nf_devolucao
            WHERE origem_registro = 'ODOO'
            AND tipo_documento IS NULL
            AND ativo = true
        """)).scalar()

        if result > 0:
            print(f"\n🔴 ALERTA: {result} NFDs do Odoo sem tipo_documento!")
        else:
            print(f"\n✅ Todas as NFDs do Odoo têm tipo_documento preenchido")

        # 8. Verificar consistência: NFDs do Monitoramento com tipo NULL
        result = db.session.execute(text("""
            SELECT COUNT(*)
            FROM nf_devolucao
            WHERE origem_registro = 'MONITORAMENTO'
            AND tipo_documento IS NULL
            AND ativo = true
        """)).scalar()

        if result > 0:
            print(f"🔴 ALERTA: {result} NFDs do Monitoramento sem tipo_documento!")
        else:
            print(f"✅ Todas as NFDs do Monitoramento têm tipo_documento preenchido")

        print("\n" + "=" * 60)


if __name__ == '__main__':
    verificar()
