"""
Migration: adicionar coluna priority em agent_memories.

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md Task 2
Data: 2026-04-16
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def check_before(conn):
    print("=== BEFORE ===")
    inspector = inspect(conn)
    cols = {c['name'] for c in inspector.get_columns('agent_memories')}
    print(f"  Coluna priority: {'EXISTS' if 'priority' in cols else 'NAO EXISTE'}")

    indexes = {idx['name'] for idx in inspector.get_indexes('agent_memories')}
    print(f"  Index idx_agent_memories_mandatory: {'EXISTS' if 'idx_agent_memories_mandatory' in indexes else 'NAO EXISTE'}")


def run_migration(conn):
    print("\n=== MIGRATION ===")

    conn.execute(text("""
        ALTER TABLE agent_memories
        ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'contextual'
    """))
    print("  OK: coluna priority adicionada")

    result = conn.execute(text("""
        SELECT 1 FROM pg_constraint WHERE conname = 'agent_memories_priority_check'
    """)).fetchone()
    if not result:
        conn.execute(text("""
            ALTER TABLE agent_memories
            ADD CONSTRAINT agent_memories_priority_check
            CHECK (priority IN ('mandatory', 'advisory', 'contextual'))
        """))
        print("  OK: CHECK constraint adicionada")
    else:
        print("  SKIP: CHECK constraint ja existe")

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_agent_memories_mandatory
          ON agent_memories (user_id, path)
          WHERE priority = 'mandatory' AND is_cold = false
    """))
    print("  OK: index idx_agent_memories_mandatory criado")

    conn.commit()


def check_after(conn):
    print("\n=== AFTER ===")
    result = conn.execute(text("""
        SELECT priority, COUNT(*) as total FROM agent_memories GROUP BY priority ORDER BY priority
    """))
    for row in result:
        print(f"  priority={row[0]}: {row[1]} memorias")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            check_before(conn)
        with db.engine.begin() as conn:
            run_migration(conn)
        with db.engine.connect() as conn:
            check_after(conn)


if __name__ == '__main__':
    main()
