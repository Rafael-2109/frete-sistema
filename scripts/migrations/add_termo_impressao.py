"""
Migration: Adicionar campos de rastreio de impressao/download do termo em descarte_devolucao
Data: 2026-01-01
Descricao: Campos para registrar quem baixou/imprimiu o termo e quando
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
            # Verificar se colunas ja existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'descarte_devolucao'
                AND column_name = 'termo_impresso_por'
            """))

            if resultado.fetchone():
                print("Colunas de impressao ja existem. Migration ignorada.")
                return

            # Adicionar colunas de impressao
            db.session.execute(text("""
                ALTER TABLE descarte_devolucao
                ADD COLUMN termo_impresso_por VARCHAR(100),
                ADD COLUMN termo_impresso_em TIMESTAMP,
                ADD COLUMN termo_salvo_por VARCHAR(100),
                ADD COLUMN termo_salvo_em TIMESTAMP
            """))

            db.session.commit()
            print("Colunas de rastreio de impressao adicionadas com sucesso!")
            print("- termo_impresso_por, termo_impresso_em")
            print("- termo_salvo_por, termo_salvo_em")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    executar_migration()
