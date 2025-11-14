"""
Migration: Adicionar campo numeros_nfs na tabela conhecimento_transporte
=========================================================================

OBJETIVO: Adicionar coluna para armazenar números de NFs contidas no CTe

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

def adicionar_numeros_nfs():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRATION: Adicionar campo numeros_nfs")
            print("=" * 80)

            # Verificar se coluna já existe
            print("\n1️⃣ Verificando se coluna já existe...")

            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'numeros_nfs'
            """))

            existe = resultado.fetchone()

            if existe:
                print("⚠️  Coluna 'numeros_nfs' já existe! Nada a fazer.")
                return

            print("✅ Coluna não existe. Adicionando...")

            # Adicionar coluna
            print("\n2️⃣ Adicionando coluna numeros_nfs...")

            db.session.execute(text("""
                ALTER TABLE conhecimento_transporte
                ADD COLUMN numeros_nfs TEXT
            """))

            db.session.commit()
            print("✅ Coluna adicionada com sucesso!")

            # Verificar
            print("\n3️⃣ Verificando coluna criada...")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'numeros_nfs'
            """))

            coluna = resultado.fetchone()
            if coluna:
                print(f"✅ Coluna verificada:")
                print(f"   Nome: {coluna[0]}")
                print(f"   Tipo: {coluna[1]}")
                print(f"   Nullable: {coluna[2]}")

            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    adicionar_numeros_nfs()
