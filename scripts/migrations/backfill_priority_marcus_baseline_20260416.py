"""
Migration: backfill priority em memorias criticas do Marcus + baseline.

Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md Task 10
Data: 2026-04-16

Depende de: add_priority_agent_memories.py (coluna priority deve existir).

Regras de backfill:
1. preferences.xml (user_id=18) -> mandatory
2. user.xml (user_id=18) -> advisory
3. Baseline heuristica -> mandatory
4. Heuristicas/protocolos empresa com importance>=0.7 -> advisory

Idempotente: WHERE priority <> target_value garante que re-execucoes nao alteram nada.
Seguro em local dev: se as memorias nao existem, UPDATE afeta 0 linhas.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def check_before(conn):
    print("=== BEFORE ===")
    result = conn.execute(text("""
        SELECT priority, COUNT(*) AS total FROM agent_memories GROUP BY priority ORDER BY priority
    """))
    for row in result:
        print(f"  priority={row[0]}: {row[1]} memorias")

    result = conn.execute(text("""
        SELECT id, user_id, path, priority FROM agent_memories
        WHERE (user_id = 18 AND path IN ('/memories/user.xml', '/memories/preferences.xml'))
           OR path LIKE '/memories/empresa/heuristicas/financeiro/baseline-de-extratos%'
        ORDER BY user_id, path
    """))
    print("\n  Alvos especificos:")
    rows_found = 0
    for row in result:
        rows_found += 1
        print(f"    id={row[0]} user={row[1]} path={row[2]} priority={row[3]}")
    if rows_found == 0:
        print("    (nenhuma memoria-alvo encontrada neste banco)")


def run_migration(conn):
    print("\n=== MIGRATION ===")

    result = conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'mandatory'
        WHERE user_id = 18
          AND path = '/memories/preferences.xml'
          AND priority <> 'mandatory'
    """))
    print(f"  [1/4] preferences.xml user_id=18 -> mandatory: {result.rowcount} rows")

    result = conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'advisory'
        WHERE user_id = 18
          AND path = '/memories/user.xml'
          AND priority <> 'advisory'
    """))
    print(f"  [2/4] user.xml user_id=18 -> advisory: {result.rowcount} rows")

    result = conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'mandatory'
        WHERE path LIKE '/memories/empresa/heuristicas/financeiro/baseline-de-extratos%'
          AND priority <> 'mandatory'
    """))
    print(f"  [3/4] baseline heuristica -> mandatory: {result.rowcount} rows")

    result = conn.execute(text("""
        UPDATE agent_memories
        SET priority = 'advisory'
        WHERE user_id = 0
          AND (path LIKE '/memories/empresa/heuristicas/%'
               OR path LIKE '/memories/empresa/protocolos/%')
          AND importance_score >= 0.7
          AND priority = 'contextual'
    """))
    print(f"  [4/4] heuristicas/protocolos importance>=0.7 -> advisory: {result.rowcount} rows")


def check_after(conn):
    print("\n=== AFTER ===")
    result = conn.execute(text("""
        SELECT priority, COUNT(*) AS total FROM agent_memories GROUP BY priority ORDER BY priority
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
        print("\n[OK] Migration concluida.")


if __name__ == '__main__':
    main()
