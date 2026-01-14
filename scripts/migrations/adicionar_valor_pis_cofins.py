"""
Migration: Adicionar campos valor_pis e valor_cofins
====================================================

Tabela: cadastro_primeira_compra

Campos adicionados:
- valor_pis (NUMERIC(15,2))
- valor_cofins (NUMERIC(15,2))

Execute:
    python scripts/migrations/adicionar_valor_pis_cofins.py

SQL para Render Shell:
    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_pis NUMERIC(15,2);
    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_cofins NUMERIC(15,2);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Adicionar valor_pis e valor_cofins")
            print("=" * 60)

            # Adicionar campo valor_pis
            print("\n[1/2] Adicionando campo valor_pis...")
            db.session.execute(text("""
                ALTER TABLE cadastro_primeira_compra
                ADD COLUMN IF NOT EXISTS valor_pis NUMERIC(15, 2);
            """))
            print("      ✓ Campo valor_pis adicionado")

            # Adicionar campo valor_cofins
            print("\n[2/2] Adicionando campo valor_cofins...")
            db.session.execute(text("""
                ALTER TABLE cadastro_primeira_compra
                ADD COLUMN IF NOT EXISTS valor_cofins NUMERIC(15, 2);
            """))
            print("      ✓ Campo valor_cofins adicionado")

            db.session.commit()

            print("\n" + "=" * 60)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 60)

            # Verificar campos
            print("\n📋 Verificando estrutura da tabela...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'cadastro_primeira_compra'
                AND column_name IN ('valor_pis', 'valor_cofins')
                ORDER BY column_name;
            """))

            colunas = result.fetchall()
            if colunas:
                print("\nColunas encontradas:")
                for col in colunas:
                    print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                print("   ⚠️ Colunas não encontradas - verifique manualmente")

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
