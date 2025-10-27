"""
Script de migração para remover UniqueConstraint de RecursosProducao
Permite múltiplas linhas de produção por produto

Data: 2025-01-26
Autor: Sistema PCP
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def remove_unique_constraint():
    app = create_app()

    with app.app_context():
        try:
            print("🔍 Verificando constraint existente...")

            # Verifica se a constraint existe
            result = db.session.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'recursos_producao'
                AND constraint_type = 'UNIQUE'
            """))

            constraints = result.fetchall()

            if not constraints:
                print("✅ Nenhuma constraint UNIQUE encontrada. Nada a fazer.")
                return

            print(f"📋 Constraints encontradas: {[c[0] for c in constraints]}")

            # Remove cada constraint encontrada
            for constraint in constraints:
                constraint_name = constraint[0]
                print(f"🗑️  Removendo constraint: {constraint_name}")

                db.session.execute(text(f"""
                    ALTER TABLE recursos_producao
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                """))

            # Cria índice composto (não único) para performance
            print("📊 Criando índice composto para performance...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_recursos_produto_linha
                ON recursos_producao(cod_produto, linha_producao)
            """))

            db.session.commit()
            print("✅ Migração concluída com sucesso!")
            print("✅ RecursosProducao agora permite múltiplas linhas por produto")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro durante migração: {str(e)}")
            raise

if __name__ == '__main__':
    remove_unique_constraint()
