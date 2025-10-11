"""
Migration: Adiciona campo documento_devolucao ao modelo Moto
Data: 11/10/2025
Descrição: Adiciona controle de documento de devolução para agrupar motos devolvidas ao fornecedor
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_documento_devolucao():
    """Adiciona campo documento_devolucao à tabela moto"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar se coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='moto'
                AND column_name='documento_devolucao';
            """))

            if resultado.fetchone():
                print("❌ Campo 'documento_devolucao' já existe na tabela 'moto'")
                return

            # Adicionar coluna
            print("✅ Adicionando campo 'documento_devolucao' à tabela 'moto'...")
            db.session.execute(text("""
                ALTER TABLE moto
                ADD COLUMN documento_devolucao VARCHAR(20);
            """))

            # Criar índice
            print("✅ Criando índice para 'documento_devolucao'...")
            db.session.execute(text("""
                CREATE INDEX idx_moto_documento_devolucao
                ON moto(documento_devolucao);
            """))

            db.session.commit()
            print("✅ Migration concluída com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao executar migration: {str(e)}")
            raise

if __name__ == '__main__':
    adicionar_documento_devolucao()
