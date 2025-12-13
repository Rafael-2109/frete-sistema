"""
Script para dropar a tabela agent_events (não mais usada).

Uso local:
    python scripts/migrations/drop_agent_events_table.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def drop_agent_events_table():
    """Dropa a tabela agent_events."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_events'
                );
            """))
            exists = result.scalar()

            if not exists:
                print("Tabela agent_events não existe. Nada a fazer.")
                return

            # Conta registros antes de dropar
            count_result = db.session.execute(text("SELECT COUNT(*) FROM agent_events"))
            count = count_result.scalar()
            print(f"Tabela agent_events tem {count} registros.")

            # Dropa a tabela
            db.session.execute(text("DROP TABLE IF EXISTS agent_events CASCADE"))
            db.session.commit()

            print("✅ Tabela agent_events removida com sucesso!")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            sys.exit(1)


if __name__ == '__main__':
    drop_agent_events_table()
