"""
Migration: tabela agent_eval_scores (A3 Fase 1 — baseline de eval por-agente).

Persiste o score de eval (passed/total) por agent_name. Substitui o
`baseline_score=0.0` hardcoded no eval gate (módulo 28 do scheduler). O
baseline contra o qual o run atual compara é o `score` do run anterior mais
recente do mesmo agent_name.

Schema: ver scripts/migrations/2026_05_31_agent_eval_scores.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_31_agent_eval_scores.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script é executado direto
# (obrigatório — senão ModuleNotFoundError em Render Shell)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def verificar_tabela() -> bool:
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'agent_eval_scores'
    """)).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'agent_eval_scores'
        ORDER BY indexname
    """)).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] agent_eval_scores exists: {existed_before}")

        print("[info] Criando agent_eval_scores (A3 — baseline de eval por-agente)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_eval_scores (
              id           BIGSERIAL PRIMARY KEY,
              agent_name   TEXT NOT NULL,
              score        DOUBLE PRECISION NOT NULL,
              total        INTEGER NOT NULL DEFAULT 0,
              passed       INTEGER NOT NULL DEFAULT 0,
              git_sha      TEXT NULL,
              mode         TEXT NULL,
              recorded_at  TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
            )
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_eval_scores_agent_name_idx
              ON agent_eval_scores (agent_name)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_eval_scores_recorded_at_idx
              ON agent_eval_scores (recorded_at DESC)
        """))

        db.session.execute(text("""
            COMMENT ON TABLE agent_eval_scores IS
              'A3 Fase 1 (2026-05-31): baseline de eval por-agente para o eval gate. '
              '1 linha por run (score = passed/total). Baseline = score do run anterior '
              'mais recente do mesmo agent_name. Report-only inicialmente (mode), enforce '
              'futuro. Sem FK — preserva historico cross-deploy. Substitui '
              'baseline_score=0.0 hardcoded em eval_gate_service (modulo 28 do scheduler).'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela não aparece em information_schema após commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'agent_eval_scores_pkey',            # implícito via PRIMARY KEY
            'agent_eval_scores_agent_name_idx',
            'agent_eval_scores_recorded_at_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[erro] Índices faltando: {missing}")
            return 1

        print(f"[after] agent_eval_scores indexes: {indices}")

        count = db.session.execute(text(
            "SELECT COUNT(*) FROM agent_eval_scores"
        )).scalar()
        print(f"[after] agent_eval_scores rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela já existia, schema válido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
