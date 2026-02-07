"""
Migration: Cria tabela teams_tasks para processamento assíncrono do bot do Teams.

Suporta:
- Polling de status (Azure Function → Flask)
- AskUserQuestion via Adaptive Cards
- Cleanup de tasks stale

Uso local:
    source .venv/bin/activate
    python scripts/criar_tabela_teams_tasks.py

Uso no Render Shell:
    python scripts/criar_tabela_teams_tasks.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_CREATE = """
CREATE TABLE IF NOT EXISTS teams_tasks (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(200) NOT NULL,
    user_id INTEGER REFERENCES usuarios(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    mensagem TEXT NOT NULL,
    resposta TEXT,
    pending_questions JSON,
    pending_question_session_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
"""

SQL_INDICES = [
    "CREATE INDEX IF NOT EXISTS ix_teams_tasks_conversation_id ON teams_tasks (conversation_id);",
    "CREATE INDEX IF NOT EXISTS ix_teams_tasks_status ON teams_tasks (status);",
    "CREATE INDEX IF NOT EXISTS ix_teams_tasks_created_at ON teams_tasks (created_at);",
    # Índice composto para busca de tasks ativas por conversa
    "CREATE INDEX IF NOT EXISTS ix_teams_tasks_conv_status ON teams_tasks (conversation_id, status);",
]


def criar_tabela():
    app = create_app()
    with app.app_context():
        try:
            # Criar tabela
            db.session.execute(text(SQL_CREATE))
            print("[OK] Tabela teams_tasks criada")

            # Criar índices
            for sql in SQL_INDICES:
                db.session.execute(text(sql))
                idx_name = sql.split("INDEX IF NOT EXISTS ")[1].split(" ON")[0]
                print(f"[OK] Índice {idx_name} criado")

            db.session.commit()
            print("\n[SUCESSO] Migration completa!")

        except Exception as e:
            print(f"\n[ERRO] {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_tabela()
