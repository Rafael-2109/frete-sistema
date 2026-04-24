"""
Migration: Adicionar coluna `preferences` JSONB em usuarios.

Data: 2026-04-23
Motivo: Persistir preferencias per-user do Agente Logistico Web.
        Primeira preferencia: `agent_thinking_display` (summarized|omitted).

Sem index: consultas sao per-user-id (PK ja indexado). Coluna acessada como
payload via SELECT preferences FROM usuarios WHERE id = :id.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def check_before(conn):
    print("=== BEFORE ===")
    result = conn.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'usuarios' AND column_name = 'preferences'"
    ))
    row = result.fetchone()
    if row:
        print(f"  usuarios.preferences existe? SIM ({row[1]})")
    else:
        print(f"  usuarios.preferences existe? NAO")

    result = conn.execute(text("SELECT COUNT(*) FROM usuarios"))
    print(f"  usuarios total: {result.scalar()}")
    print()


def run_migration(conn):
    conn.execute(text(
        "ALTER TABLE usuarios "
        "ADD COLUMN IF NOT EXISTS preferences JSONB NOT NULL DEFAULT '{}'::jsonb"
    ))
    print("[1/1] usuarios.preferences: coluna JSONB garantida (default '{}')")


def check_after(conn):
    print("\n=== AFTER ===")
    result = conn.execute(text(
        "SELECT column_name, data_type, column_default, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = 'usuarios' AND column_name = 'preferences'"
    ))
    row = result.fetchone()
    if row:
        print(f"  {row[0]}: {row[1]} default={row[2]} nullable={row[3]}")
    else:
        print("  FALHA: coluna nao criada")

    # Sanidade: NULL count deve ser 0 (default '{}' aplicado)
    result = conn.execute(text(
        "SELECT COUNT(*) FROM usuarios WHERE preferences IS NULL"
    ))
    print(f"  preferences NULL count: {result.scalar()}")


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
