"""
Amplia o campo session_id de VARCHAR(100) para VARCHAR(255)
na tabela agent_sessions.

Necessario porque conversation_id do Teams pode exceder 100 chars
quando prefixado com "teams_".

Executar:
  python scripts/migrate_session_id_255.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def migrate():
    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text(
                "ALTER TABLE agent_sessions ALTER COLUMN session_id TYPE VARCHAR(255)"
            ))
            db.session.commit()
            print("OK: session_id ampliado para VARCHAR(255)")
        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()


if __name__ == '__main__':
    migrate()
