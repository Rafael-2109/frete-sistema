"""
Migration: Adicionar campo empresa_pagadora_id em despesa_mensal
Data: 2025-10-09
Descrição: Adiciona FK para rastrear qual empresa pagou a despesa

IMPORTANTE: Este script pode ser executado via CLI ou direto no Python.

USO:
    python3 migration_empresa_pagadora_despesa.py
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """
    Executa a migration para adicionar empresa_pagadora_id
    """
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🔧 MIGRATION: Adicionar empresa_pagadora_id em despesa_mensal")
        print("=" * 80)

        try:
            # 1. Verificar se coluna já existe
            check_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'despesa_mensal'
              AND column_name = 'empresa_pagadora_id';
            """

            result = db.session.execute(text(check_query))
            exists = result.fetchone()

            if exists:
                print("⚠️  Campo empresa_pagadora_id JÁ EXISTE em despesa_mensal")
                print("   Migration não é necessária.")
                return

            print("\n📝 Executando migration...")

            # 2. Adicionar coluna
            print("   1. Adicionando coluna empresa_pagadora_id...")
            db.session.execute(text("""
                ALTER TABLE despesa_mensal
                ADD COLUMN empresa_pagadora_id INTEGER;
            """))

            # 3. Adicionar comentário
            print("   2. Adicionando comentário...")
            db.session.execute(text("""
                COMMENT ON COLUMN despesa_mensal.empresa_pagadora_id
                IS 'Empresa que pagou a despesa (FK para empresa_venda_moto)';
            """))

            # 4. Criar índice
            print("   3. Criando índice...")
            db.session.execute(text("""
                CREATE INDEX idx_despesa_mensal_empresa_pagadora
                ON despesa_mensal(empresa_pagadora_id);
            """))

            # 5. Adicionar Foreign Key
            print("   4. Adicionando Foreign Key constraint...")
            db.session.execute(text("""
                ALTER TABLE despesa_mensal
                ADD CONSTRAINT fk_despesa_mensal_empresa_pagadora
                FOREIGN KEY (empresa_pagadora_id) REFERENCES empresa_venda_moto(id)
                ON DELETE SET NULL;
            """))

            # 6. Commit
            db.session.commit()

            print("\n✅ Migration executada com sucesso!")
            print("\n📊 Resultado:")

            # 7. Verificar
            verify_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'despesa_mensal'
              AND column_name = 'empresa_pagadora_id';
            """

            result = db.session.execute(text(verify_query))
            row = result.fetchone()

            if row:
                print(f"   Column Name: {row[0]}")
                print(f"   Data Type: {row[1]}")
                print(f"   Nullable: {row[2]}")
                print(f"   Default: {row[3] or 'NULL'}")

            print("\n🎯 PRÓXIMO PASSO:")
            print("   Descomentar campo no modelo Python:")
            print("   app/motochefe/models/operacional.py (linhas 76-85)")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao executar migration: {str(e)}")
            raise


if __name__ == '__main__':
    executar_migration()
