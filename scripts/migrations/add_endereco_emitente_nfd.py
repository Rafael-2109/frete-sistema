"""
Migration: Adicionar campos de endereco do emitente na nf_devolucao
Data: 2026-01-02
Descricao: Campos para armazenar UF e municipio do cliente que emitiu a NFD
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
                WHERE table_name = 'nf_devolucao'
                AND column_name = 'uf_emitente'
            """))

            if resultado.fetchone():
                print("Colunas de endereco do emitente ja existem. Migration ignorada.")
                return

            # Adicionar colunas de endereco do emitente
            db.session.execute(text("""
                ALTER TABLE nf_devolucao
                ADD COLUMN uf_emitente VARCHAR(2),
                ADD COLUMN municipio_emitente VARCHAR(100),
                ADD COLUMN cep_emitente VARCHAR(10),
                ADD COLUMN endereco_emitente VARCHAR(255)
            """))

            db.session.commit()
            print("Colunas de endereco do emitente adicionadas com sucesso!")
            print("- uf_emitente")
            print("- municipio_emitente")
            print("- cep_emitente")
            print("- endereco_emitente")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    executar_migration()
