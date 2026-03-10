"""
Migration: Adicionar numero_nota_credito a nf_devolucao
======================================================
Permite exibir o numero da Nota de Credito nas reversoes.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_numero_nota_credito.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text

def run_migration():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Verificar se coluna ja existe
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'nf_devolucao' AND column_name = 'numero_nota_credito'
            """))
            if result.fetchone():
                print("Coluna numero_nota_credito ja existe. Nada a fazer.")
                return

            # Adicionar coluna
            conn.execute(text("""
                ALTER TABLE nf_devolucao ADD COLUMN numero_nota_credito VARCHAR(20)
            """))
            print("Coluna numero_nota_credito adicionada.")

            # Criar indice
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_nf_devolucao_numero_nota_credito
                ON nf_devolucao(numero_nota_credito)
            """))
            print("Indice idx_nf_devolucao_numero_nota_credito criado.")

            conn.commit()
            print("Migration concluida com sucesso!")

if __name__ == '__main__':
    run_migration()
