"""
Migration: Adicionar campo momento_devolucao em ocorrencia_devolucao
Data: 2026-01-01
Descricao: Campo para indicar se a devolucao ocorreu no ato da entrega ou posterior
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
            # Verificar se coluna ja existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ocorrencia_devolucao'
                AND column_name = 'momento_devolucao'
            """))

            if resultado.fetchone():
                print("Coluna 'momento_devolucao' ja existe. Migration ignorada.")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE ocorrencia_devolucao
                ADD COLUMN momento_devolucao VARCHAR(20) DEFAULT 'INDEFINIDO'
            """))

            db.session.commit()
            print("Coluna 'momento_devolucao' adicionada com sucesso!")
            print("Valores possiveis: ATO_ENTREGA, POSTERIOR_ENTREGA, INDEFINIDO")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    executar_migration()
