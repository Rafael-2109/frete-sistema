"""
Migration: tabela agent_eval_case (A3-R3 — calibração do judge de eval).

Persiste 1 linha POR CASO avaliado num run (o veredito granular do judge —
mediana de N runs), habilitando spot-check humano de 5-10% e a metrica de
concordancia judge-vs-humano (eixos/A-flywheel.md:165 — "Calibração obrigatória:
spot-check humano de 5-10% das notas do judge"). Sem calibração, trocamos um
proxy cego (eco) por outro (judge nao-auditado) — A-flywheel.md:318.

Schema: ver scripts/migrations/2026_06_01_agent_eval_case.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_06_01_agent_eval_case.py
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
        WHERE table_name = 'agent_eval_case'
    """)).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'agent_eval_case'
        ORDER BY indexname
    """)).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] agent_eval_case exists: {existed_before}")

        print("[info] Criando agent_eval_case (A3-R3 — calibracao do judge de eval)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_eval_case (
              id                  BIGSERIAL PRIMARY KEY,
              agent_name          TEXT NOT NULL,
              case_id             TEXT NOT NULL,
              git_sha             TEXT NULL,
              case_score          DOUBLE PRECISION NOT NULL,
              status              TEXT NOT NULL,
              n_runs              INTEGER NOT NULL DEFAULT 1,
              case_score_variance DOUBLE PRECISION NOT NULL DEFAULT 0.0,
              invoke_failures     INTEGER NOT NULL DEFAULT 0,
              evidence            TEXT NULL,
              human_verdict       TEXT NULL,
              human_note          TEXT NULL,
              reviewed_by         INTEGER NULL,
              reviewed_at         TIMESTAMP NULL,
              recorded_at         TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
            )
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_eval_case_agent_name_idx
              ON agent_eval_case (agent_name)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_eval_case_recorded_at_idx
              ON agent_eval_case (recorded_at DESC)
        """))

        # Indice PARCIAL para a amostragem de nao-revisados (sample_unreviewed).
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agent_eval_case_unreviewed_idx
              ON agent_eval_case (agent_name)
              WHERE human_verdict IS NULL
        """))

        db.session.execute(text("""
            COMMENT ON TABLE agent_eval_case IS
              'A3-R3 (2026-06-01): calibracao do judge de eval. 1 linha por caso '
              'avaliado num run (case_score = mediana do judge de N runs). Habilita '
              'spot-check humano de 5-10% (sample_unreviewed) + metrica de '
              'concordancia judge-vs-humano (concordance_rate). human_verdict '
              'NULL=nao revisado; agree|disagree quando revisado. Sem FK — preserva '
              'historico cross-deploy. Gated por AGENT_EVAL_CALIBRATION '
              '(persist_eval_cases em eval_runner). Spec eixos/A-flywheel.md:165.'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela não aparece em information_schema após commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'agent_eval_case_pkey',                # implícito via PRIMARY KEY
            'agent_eval_case_agent_name_idx',
            'agent_eval_case_recorded_at_idx',
            'agent_eval_case_unreviewed_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[erro] Índices faltando: {missing}")
            return 1

        print(f"[after] agent_eval_case indexes: {indices}")

        count = db.session.execute(text(
            "SELECT COUNT(*) FROM agent_eval_case"
        )).scalar()
        print(f"[after] agent_eval_case rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela já existia, schema válido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
