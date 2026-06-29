"""
Migration: trocar UNIQUE(user_id, path) -> UNIQUE(user_id, path, agente) em agent_memories.

Data: 2026-06-30
Motivo: M3/F2 Fase 1 — permitir que o agente 'web' (Nacom) e o agente 'lojas'
        (Lojas HORA) tenham memória no MESMO path por usuário (ex.: ambos
        /memories/user.xml). Pré-requisito da convergência F3 (motor único):
        quando o lojas gravar memória, não pode colidir com a do web.

Segurança (verificado em PROD 2026-06-29 via Render MCP):
    - 0 duplicatas (user_id, path) hoje -> nenhuma linha viola a constraint nova.
    - 1019 memórias, todas agente='web' -> a constraint nova (mais ampla) as
      mantém válidas. A troca é ADITIVA (afrouxa a unicidade).

Idempotente: dropa a constraint antiga IF EXISTS e cria a nova só se ausente.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def _constraints(conn):
    rows = conn.execute(text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = 'agent_memories'::regclass AND contype = 'u'"
    )).fetchall()
    return {r[0] for r in rows}


def check_before(conn):
    print("=== BEFORE ===")
    print(f"  unique constraints em agent_memories: {sorted(_constraints(conn))}")
    dup = conn.execute(text(
        "SELECT COUNT(*) FROM (SELECT user_id, path FROM agent_memories "
        "GROUP BY user_id, path HAVING COUNT(*) > 1) d"
    )).scalar()
    print(f"  duplicatas (user_id, path): {dup}  (deve ser 0 p/ migration segura)")
    print()


def run_migration(conn):
    # 1. Drop da constraint antiga
    conn.execute(text(
        "ALTER TABLE agent_memories DROP CONSTRAINT IF EXISTS uq_user_memory_path"
    ))
    # 2. Cria a nova só se ausente
    if 'uq_user_memory_path_agente' not in _constraints(conn):
        conn.execute(text(
            "ALTER TABLE agent_memories "
            "ADD CONSTRAINT uq_user_memory_path_agente UNIQUE (user_id, path, agente)"
        ))


def check_after(conn):
    print("=== AFTER ===")
    cons = _constraints(conn)
    print(f"  unique constraints em agent_memories: {sorted(cons)}")
    ok = 'uq_user_memory_path_agente' in cons and 'uq_user_memory_path' not in cons
    print(f"  migration OK? {ok}")
    return ok


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            check_before(conn)
            run_migration(conn)
            ok = check_after(conn)
    print("\n✅ Migration concluída." if ok else "\n⚠ Verificar estado das constraints.")


if __name__ == '__main__':
    main()
