"""
Migration: tabela agente_artifacts (Artifacts no Agente Web).

Persiste metadados de artifacts gerados pela skill `gerando-artifact`. Build
assincrono via worker RQ. Bundle.html final fica no S3 (prefix
agente/artifacts/). Tabela guarda apenas metadados + estado de build.

Schema: ver scripts/migrations/2026_05_12_agente_artifacts.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_12_agente_artifacts.py
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
        WHERE table_name = 'agente_artifacts'
    """)).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'agente_artifacts'
        ORDER BY indexname
    """)).fetchall()
    return [r[0] for r in rows]


def verificar_check_constraint() -> bool:
    result = db.session.execute(text("""
        SELECT 1 FROM pg_constraint
        WHERE conname = 'agente_artifacts_status_check'
    """)).scalar()
    return bool(result)


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] agente_artifacts exists: {existed_before}")

        print("[info] Criando agente_artifacts (Artifacts no Agente Web)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS agente_artifacts (
              id                  BIGSERIAL PRIMARY KEY,
              uuid                TEXT NOT NULL UNIQUE,
              user_id             INTEGER NOT NULL,
              session_id          TEXT NULL,
              titulo              TEXT NOT NULL,
              status              TEXT NOT NULL DEFAULT 'queued',
              s3_key              TEXT NULL,
              bundle_size_bytes   BIGINT NULL,
              error_message       TEXT NULL,
              spec_json           JSONB NULL,
              created_at          TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
              expires_at          TIMESTAMP NOT NULL,
              build_started_at    TIMESTAMP NULL,
              build_completed_at  TIMESTAMP NULL
            )
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agente_artifacts_user_created_idx
              ON agente_artifacts (user_id, created_at DESC)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agente_artifacts_status_pending_idx
              ON agente_artifacts (status)
              WHERE status IN ('queued', 'building')
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agente_artifacts_expires_idx
              ON agente_artifacts (expires_at)
              WHERE status != 'expired'
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS agente_artifacts_session_idx
              ON agente_artifacts (session_id)
              WHERE session_id IS NOT NULL
        """))

        # Check constraint (DO $$ block para idempotencia)
        db.session.execute(text("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'agente_artifacts_status_check'
              ) THEN
                ALTER TABLE agente_artifacts
                  ADD CONSTRAINT agente_artifacts_status_check
                  CHECK (status IN ('queued', 'building', 'ready', 'error', 'expired'));
              END IF;
            END $$
        """))

        db.session.execute(text("""
            COMMENT ON TABLE agente_artifacts IS
              'Artifacts (bundle.html auto-contido) gerados pelo agente via skill '
              'gerando-artifact. Build async via RQ (queue artifacts). Bundle no S3 '
              '(prefix agente/artifacts/). Sem FK — preserva historico apos cascade '
              'delete. uuid e referenciado externamente via token assinado.'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela nao aparece em information_schema apos commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'agente_artifacts_pkey',
            'agente_artifacts_uuid_key',  # implicito do UNIQUE
            'agente_artifacts_user_created_idx',
            'agente_artifacts_status_pending_idx',
            'agente_artifacts_expires_idx',
            'agente_artifacts_session_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[aviso] Indices faltando (pode ser nome diferente do esperado): {missing}")
            print(f"[info] Indices reais: {indices}")

        if not verificar_check_constraint():
            print("[erro] Constraint agente_artifacts_status_check nao foi criada.")
            return 1

        print(f"[after] agente_artifacts indexes: {indices}")
        print(f"[after] agente_artifacts_status_check: OK")

        count = db.session.execute(text(
            "SELECT COUNT(*) FROM agente_artifacts"
        )).scalar()
        print(f"[after] agente_artifacts rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela ja existia, schema valido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
