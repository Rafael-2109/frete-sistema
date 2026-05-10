"""
Migration: tabela agent_session_costs (F8 — cost tracker persistente).

Persiste entradas de CostTracker em DB para historico cross-deploy. Habilitado
via flag AGENT_COST_TRACKER_PERSIST=true. Comportamento atual (in-memory)
permanece quando flag off.

Schema: ver scripts/migrations/2026_05_09_agent_session_costs.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_09_agent_session_costs.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script eh executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def verificar_tabela() -> bool:
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'agent_session_costs'
    """)).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'agent_session_costs'
        ORDER BY indexname
    """)).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] agent_session_costs exists: {existed_before}")

        print("[info] Criando agent_session_costs (F8 cost tracker persistente)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_session_costs (
              id              BIGSERIAL PRIMARY KEY,
              message_id      TEXT NOT NULL,
              session_id      TEXT NULL,
              user_id         INTEGER NULL,
              tool_name       TEXT NULL,
              model           TEXT NULL,
              input_tokens    INTEGER NOT NULL DEFAULT 0,
              output_tokens   INTEGER NOT NULL DEFAULT 0,
              cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
              cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
              cost_usd        NUMERIC(10, 6) NOT NULL DEFAULT 0,
              recorded_at     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
            )
        """))

        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS agent_session_costs_message_id_uniq
              ON agent_session_costs (message_id)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_session_costs_user_recorded_idx
              ON agent_session_costs (user_id, recorded_at DESC)
              WHERE user_id IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_session_costs_session_idx
              ON agent_session_costs (session_id)
              WHERE session_id IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_session_costs_recorded_idx
              ON agent_session_costs (recorded_at DESC)
        """))

        db.session.execute(text("""
            COMMENT ON TABLE agent_session_costs IS
              'F8 (2026-05-09): persistencia de cost_tracker entries. '
              'Habilitado via flag AGENT_COST_TRACKER_PERSIST. Sem FK para '
              'agent_sessions — preserva historico mesmo apos cascade delete. '
              'Caller filtra orfaos quando necessario.'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela nao aparece em information_schema apos commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'agent_session_costs_pkey',  # implicito via PRIMARY KEY
            'agent_session_costs_message_id_uniq',
            'agent_session_costs_user_recorded_idx',
            'agent_session_costs_session_idx',
            'agent_session_costs_recorded_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[erro] Indices faltando: {missing}")
            return 1

        print(f"[after] agent_session_costs indexes: {indices}")

        count = db.session.execute(text(
            "SELECT COUNT(*) FROM agent_session_costs"
        )).scalar()
        print(f"[after] agent_session_costs rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela ja existia, schema valido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
