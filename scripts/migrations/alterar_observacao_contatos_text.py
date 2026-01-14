"""
Script para alterar o campo observacao de VARCHAR(255) para TEXT
na tabela contatos_agendamento.

Executar: source .venv/bin/activate && python scripts/migrations/alterar_observacao_contatos_text.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def alterar_campo_observacao():
    app = create_app()
    with app.app_context():
        try:
            print("Alterando campo observacao para TEXT...")
            db.session.execute(text("""
                ALTER TABLE contatos_agendamento
                ALTER COLUMN observacao TYPE TEXT;
            """))
            db.session.commit()
            print("✓ Campo observacao alterado com sucesso para TEXT!")
            print("  - Limite anterior: 255 caracteres")
            print("  - Limite atual: sem limite prático (até 1GB)")
        except Exception as e:
            print(f"✗ Erro: {e}")
            db.session.rollback()
            return False
    return True

if __name__ == "__main__":
    alterar_campo_observacao()
