"""
Migration: Adicionar campo 'importante' na tabela carteira_principal

Descrição:
- Adiciona campo boolean 'importante' (default False) na CarteiraPrincipal
- Campo usado para marcar pedidos importantes visualmente
- Inclui índice para performance

Data: 2025-01-17
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campo_importante():
    """Adiciona campo importante na tabela carteira_principal"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar se coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='carteira_principal'
                AND column_name='importante'
            """))

            if resultado.fetchone():
                print("✅ Coluna 'importante' já existe na tabela carteira_principal")
                return

            print("📝 Adicionando coluna 'importante' na tabela carteira_principal...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE carteira_principal
                ADD COLUMN importante BOOLEAN NOT NULL DEFAULT FALSE
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX idx_carteira_importante
                ON carteira_principal(importante)
            """))

            db.session.commit()
            print("✅ Coluna 'importante' adicionada com sucesso!")
            print("✅ Índice 'idx_carteira_importante' criado com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar coluna: {e}")
            raise

if __name__ == '__main__':
    print("=" * 70)
    print("MIGRATION: Adicionar campo 'importante' na CarteiraPrincipal")
    print("=" * 70)
    adicionar_campo_importante()
    print("=" * 70)
    print("✅ Migration concluída!")
    print("=" * 70)
