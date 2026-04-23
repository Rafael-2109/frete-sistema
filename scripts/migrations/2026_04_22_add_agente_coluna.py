"""
Migration: Adicionar coluna `agente` em agent_sessions e agent_memories.

Data: 2026-04-22
Motivo: Particionar sessoes e memorias entre agente logistico (web) e
        agente Lojas HORA (lojas). Sem a coluna, nao ha como listar apenas
        sessoes/memorias de um agente especifico no endpoint dedicado.

Valores esperados:
    - 'web'   -> agente logistico Nacom Goya (default, compat com dados legados)
    - 'lojas' -> agente Lojas HORA (novo)

Index:
    - ix_agent_sessions_agente_user (agente, user_id)
    - ix_agent_memories_agente_user (agente, user_id)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def check_before(conn):
    """Verifica estado antes."""
    print("=== BEFORE ===")

    for tabela in ('agent_sessions', 'agent_memories'):
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = 'agente'"
        ), {"t": tabela})
        existe = result.scalar() is not None
        print(f"  {tabela}.agente existe? {existe}")

        result = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
        print(f"  {tabela} total: {result.scalar()}")

    print()


def run_migration(conn):
    """Executa migration idempotente."""

    # 1. agent_sessions.agente
    conn.execute(text(
        "ALTER TABLE agent_sessions "
        "ADD COLUMN IF NOT EXISTS agente VARCHAR(20) NOT NULL DEFAULT 'web'"
    ))
    print("[1/4] agent_sessions.agente: coluna garantida")

    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_agent_sessions_agente_user "
        "ON agent_sessions (agente, user_id)"
    ))
    print("[2/4] ix_agent_sessions_agente_user: index garantido")

    # 2. agent_memories.agente
    conn.execute(text(
        "ALTER TABLE agent_memories "
        "ADD COLUMN IF NOT EXISTS agente VARCHAR(20) NOT NULL DEFAULT 'web'"
    ))
    print("[3/4] agent_memories.agente: coluna garantida")

    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_agent_memories_agente_user "
        "ON agent_memories (agente, user_id)"
    ))
    print("[4/4] ix_agent_memories_agente_user: index garantido")


def check_after(conn):
    """Verifica estado depois."""
    print("\n=== AFTER ===")

    for tabela in ('agent_sessions', 'agent_memories'):
        result = conn.execute(text(
            f"SELECT agente, COUNT(*) FROM {tabela} GROUP BY agente ORDER BY agente"
        ))
        rows = result.fetchall()
        print(f"  {tabela}:")
        for agente, total in rows:
            print(f"    {agente}: {total}")


def main():
    app = create_app()

    with app.app_context():
        with db.engine.begin() as conn:
            check_before(conn)
            run_migration(conn)
            check_after(conn)

    print("\n=== MIGRATION CONCLUIDA ===")


if __name__ == '__main__':
    main()
