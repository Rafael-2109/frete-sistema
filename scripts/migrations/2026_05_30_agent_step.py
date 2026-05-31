"""
Migration: tabela agent_step (Onda 0 — fundação física de passo/turno).

1 registro por TURNO (par user→assistant). step_uid = "{session_id}:{turn_seq}".
Fundação que destrava 3 eixos do blueprint: flywheel, qualidade, planejador.

Schema: ver scripts/migrations/2026_05_30_agent_step.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_30_agent_step.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script é executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def verificar_tabela() -> bool:
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'agent_step'
    """)).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'agent_step'
        ORDER BY indexname
    """)).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] agent_step exists: {existed_before}")

        print("[info] Criando agent_step (Onda 0 — passo/turno do agente)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_step (
              id                      BIGSERIAL PRIMARY KEY,
              step_uid                TEXT NOT NULL,
              session_id              TEXT NULL,
              user_id                 INTEGER NULL,
              channel                 TEXT NULL,
              model                   TEXT NULL,
              input_tokens            INTEGER NOT NULL DEFAULT 0,
              output_tokens           INTEGER NOT NULL DEFAULT 0,
              tools_used              JSONB NULL,
              outcome_signal          JSONB NULL,
              outcome_effective_count INTEGER NULL,
              created_at              TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
            )
        """))

        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS agent_step_step_uid_uniq
              ON agent_step (step_uid)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_step_session_id_idx
              ON agent_step (session_id)
              WHERE session_id IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_step_user_id_idx
              ON agent_step (user_id)
              WHERE user_id IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_step_created_at_idx
              ON agent_step (created_at DESC)
        """))

        db.session.execute(text("""
            COMMENT ON TABLE agent_step IS
              'Onda 0 (2026-05-30): entidade de passo/turno do agente. '
              '1 registro por par user→assistant. step_uid = session_id:turn_seq. '
              'Sem FK para agent_sessions — preserva histórico após cascade delete. '
              'outcome_signal e outcome_effective_count preenchidos na Onda 1.'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela não aparece em information_schema após commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'agent_step_pkey',            # implícito via PRIMARY KEY
            'agent_step_step_uid_uniq',
            'agent_step_session_id_idx',
            'agent_step_user_id_idx',
            'agent_step_created_at_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[erro] Índices faltando: {missing}")
            return 1

        print(f"[after] agent_step indexes: {indices}")

        count = db.session.execute(text(
            "SELECT COUNT(*) FROM agent_step"
        )).scalar()
        print(f"[after] agent_step rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela já existia, schema válido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
