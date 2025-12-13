#!/usr/bin/env python3
"""
Migração: Criar tabela agent_events para instrumentação de hooks.

Uso local:
    python scripts/migrations/create_agent_events_table.py

A tabela armazena eventos append-only para:
- Dataset de ML
- Analytics de uso
- Debugging e auditoria
- Rastreamento de comportamento
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def create_table():
    """Cria tabela agent_events."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela já existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_events'
                );
            """))
            exists = result.scalar()

            if exists:
                print("✓ Tabela agent_events já existe")
                return True

            # Cria tabela
            db.session.execute(text("""
                CREATE TABLE agent_events (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES usuarios(id),
                    session_id VARCHAR(100) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))

            # Cria índices
            db.session.execute(text("""
                CREATE INDEX ix_agent_events_user_id ON agent_events(user_id);
            """))
            db.session.execute(text("""
                CREATE INDEX ix_agent_events_session_id ON agent_events(session_id);
            """))
            db.session.execute(text("""
                CREATE INDEX ix_agent_events_event_type ON agent_events(event_type);
            """))
            db.session.execute(text("""
                CREATE INDEX ix_agent_events_user_session ON agent_events(user_id, session_id);
            """))
            db.session.execute(text("""
                CREATE INDEX ix_agent_events_type_created ON agent_events(event_type, created_at);
            """))

            # Índice GIN para busca em JSONB
            db.session.execute(text("""
                CREATE INDEX ix_agent_events_data_gin ON agent_events USING GIN (data);
            """))

            db.session.commit()
            print("✓ Tabela agent_events criada com sucesso")
            print("✓ Índices criados")
            return True

        except Exception as e:
            print(f"✗ Erro: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    success = create_table()
    sys.exit(0 if success else 1)
