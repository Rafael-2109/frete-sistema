"""
Migracao: Criar tabela agent_improvement_dialogue

Tabela para dialogo versionado de melhoria continua entre Agent SDK e Claude Code.
Agent SDK escreve sugestoes (v1), Claude Code avalia/implementa (v2), Agent SDK verifica (v3).

Executar:
    source .venv/bin/activate
    python scripts/migrations/agent_improvement_dialogue.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria tabela agent_improvement_dialogue no PostgreSQL."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela ja existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_improvement_dialogue'
                )
            """))

            if result.scalar():
                print("Tabela agent_improvement_dialogue ja existe")
                return True

            # Cria tabela
            print("Criando tabela agent_improvement_dialogue...")

            db.session.execute(text("""
                CREATE TABLE agent_improvement_dialogue (
                    id SERIAL PRIMARY KEY,
                    suggestion_key VARCHAR(100) NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    author VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'proposed',
                    category VARCHAR(30) NOT NULL,
                    severity VARCHAR(10) NOT NULL DEFAULT 'info',
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    evidence_json JSONB DEFAULT '{}'::jsonb,
                    affected_files TEXT[],
                    implementation_notes TEXT,
                    auto_implemented BOOLEAN DEFAULT FALSE,
                    source_session_ids TEXT[],
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(suggestion_key, version)
                )
            """))

            # Cria indices
            print("Criando indices...")

            db.session.execute(text("""
                CREATE INDEX idx_aid_status
                ON agent_improvement_dialogue(status)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_aid_key
                ON agent_improvement_dialogue(suggestion_key)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_aid_category_status
                ON agent_improvement_dialogue(category, status)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_aid_author_status
                ON agent_improvement_dialogue(author, status)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_aid_pending
                ON agent_improvement_dialogue(created_at ASC)
                WHERE status = 'proposed' AND author = 'agent_sdk'
            """))

            db.session.commit()
            print("Tabela agent_improvement_dialogue criada com sucesso")

            # Verificacao pos-criacao
            result = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'agent_improvement_dialogue'
                ORDER BY ordinal_position
            """))

            print("\nColunas criadas:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"ERRO ao criar tabela: {e}")
            return False


if __name__ == '__main__':
    success = criar_tabela()
    sys.exit(0 if success else 1)
