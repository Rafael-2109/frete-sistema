"""
Migration: tabela agent_invocation_metrics (A1 — telemetria per-subagent).

Persiste uma linha por spawn->stop de subagent. Distinta de agent_session_costs
(per-message). Habilitada via flag AGENT_INVOCATION_METRICS_PERSIST.

Schema: ver scripts/migrations/2026_05_16_agent_invocation_metrics.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_16_agent_invocation_metrics.py
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def verificar_tabela() -> bool:
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'agent_invocation_metrics'
    """)).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'agent_invocation_metrics'
        ORDER BY indexname
    """)).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] agent_invocation_metrics exists: {existed_before}")

        print("[info] Criando agent_invocation_metrics (A1 telemetria per-subagent)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_invocation_metrics (
              id              BIGSERIAL PRIMARY KEY,
              agent_id        TEXT NOT NULL,
              agent_type      TEXT NOT NULL,
              session_id      TEXT NULL,
              user_id         INTEGER NULL,
              started_at      TIMESTAMP NULL,
              finished_at     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
              duration_ms     INTEGER NULL,
              num_turns       INTEGER NULL,
              stop_reason     TEXT NULL,
              cost_usd        NUMERIC(10, 6) NULL,
              input_tokens          INTEGER NOT NULL DEFAULT 0,
              output_tokens         INTEGER NOT NULL DEFAULT 0,
              cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
              cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
              escalated_to_human       BOOLEAN NOT NULL DEFAULT FALSE,
              user_correction_received BOOLEAN NULL,
              source          TEXT NOT NULL DEFAULT 'production',
              recorded_at     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
            )
        """))

        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS agent_invocation_metrics_agent_id_uniq
              ON agent_invocation_metrics (agent_id)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_invocation_metrics_type_recorded_idx
              ON agent_invocation_metrics (agent_type, recorded_at DESC)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_invocation_metrics_user_recorded_idx
              ON agent_invocation_metrics (user_id, recorded_at DESC)
              WHERE user_id IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_invocation_metrics_session_idx
              ON agent_invocation_metrics (session_id)
              WHERE session_id IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_invocation_metrics_recorded_idx
              ON agent_invocation_metrics (recorded_at DESC)
        """))

        db.session.execute(text("""
            COMMENT ON TABLE agent_invocation_metrics IS
              'A1 (2026-05-16): telemetria per-invocacao de subagent. '
              'Habilitado via flag AGENT_INVOCATION_METRICS_PERSIST. Sem FK '
              'para agent_sessions — preserva historico apos cascade delete. '
              'Granularidade distinta de agent_session_costs (per-message). '
              'source=production|dev distingue Claude Code CLI vs agente web.'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela nao aparece em information_schema apos commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'agent_invocation_metrics_pkey',
            'agent_invocation_metrics_agent_id_uniq',
            'agent_invocation_metrics_type_recorded_idx',
            'agent_invocation_metrics_user_recorded_idx',
            'agent_invocation_metrics_session_idx',
            'agent_invocation_metrics_recorded_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[erro] Indices faltando: {missing}")
            return 1

        print(f"[after] agent_invocation_metrics indexes: {indices}")

        count = db.session.execute(text(
            "SELECT COUNT(*) FROM agent_invocation_metrics"
        )).scalar()
        print(f"[after] agent_invocation_metrics rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela ja existia, schema valido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
