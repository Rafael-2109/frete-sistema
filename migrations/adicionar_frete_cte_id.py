"""
Migration: Adicionar campo frete_cte_id em Frete

Data: 2025-01-18
Objetivo: Criar vínculo bidirecional entre Frete e ConhecimentoTransporte
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_frete_cte_id():
    """
    Adiciona campo frete_cte_id em Frete para vínculo bidirecional
    """
    app = create_app()

    with app.app_context():
        try:
            # Verificar se campo já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'fretes'
                AND column_name = 'frete_cte_id'
            """))

            if result.fetchone():
                print("✅ Campo frete_cte_id já existe em fretes")
                return

            print("📝 Adicionando campo frete_cte_id em fretes...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE fretes
                ADD COLUMN frete_cte_id INTEGER REFERENCES conhecimento_transporte(id)
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX idx_frete_cte_id ON fretes(frete_cte_id)
            """))

            db.session.commit()
            print("✅ Campo frete_cte_id adicionado com sucesso!")

            # Migrar dados existentes (vincular via chave_acesso ou numero_cte)
            print("\n🔄 Migrando vínculos existentes...")

            result = db.session.execute(text("""
                UPDATE fretes f
                SET frete_cte_id = ct.id
                FROM conhecimento_transporte ct
                WHERE ct.frete_id = f.id
                AND f.frete_cte_id IS NULL
            """))

            rows_updated = result.rowcount
            db.session.commit()

            print(f"✅ {rows_updated} vínculos migrados (via ConhecimentoTransporte.frete_id)")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")
            raise

if __name__ == '__main__':
    adicionar_frete_cte_id()
