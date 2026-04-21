"""
Migration: tabela claude_session_store para SessionStore adapter (SDK 0.1.64).

Schema copiado de examples/session_stores/postgres_session_store.py do repo
anthropics/claude-agent-sdk-python (branch main, commit 2026-04-19 — PR 842).

Fase A dual-run: tabela nova, nao toca nada existente. session_persistence.py
continua funcionando em paralelo. Flag AGENT_SDK_SESSION_STORE_ENABLED=false
por default — rollback imediato via env var.

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_04_21_claude_session_store.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script e executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def verificar_tabela() -> bool:
    """Retorna True se a tabela ja existe."""
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'claude_session_store'
    """)).scalar()
    return bool(result)


def verificar_indice() -> bool:
    """Retorna True se o indice parcial ja existe."""
    result = db.session.execute(text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'claude_session_store'
          AND indexname = 'claude_session_store_list_idx'
    """)).scalar()
    return bool(result)


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] claude_session_store exists: {existed_before}")

        print("[info] Criando claude_session_store (schema oficial do SDK 0.1.64)...")
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS claude_session_store (
              project_key text   NOT NULL,
              session_id  text   NOT NULL,
              subpath     text   NOT NULL DEFAULT '',
              seq         bigserial,
              entry       jsonb  NOT NULL,
              mtime       bigint NOT NULL,
              PRIMARY KEY (project_key, session_id, subpath, seq)
            )
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS claude_session_store_list_idx
              ON claude_session_store (project_key, session_id)
              WHERE subpath = ''
        """))
        db.session.execute(text("""
            COMMENT ON TABLE claude_session_store IS
              'SessionStore v0.1.64 backend (Fase A dual-run). '
              'Uma linha por entry. Mantido pelo SDK via TranscriptMirrorBatcher. '
              'Schema oficial do examples/session_stores/postgres_session_store.py.'
        """))
        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela nao aparece em information_schema apos commit.")
            return 1
        if not verificar_indice():
            print("[erro] Indice parcial nao criado.")
            return 1

        indexes = db.session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'claude_session_store'
            ORDER BY indexname
        """)).fetchall()
        print(f"[after] claude_session_store indexes: {[r[0] for r in indexes]}")

        # Volumetria (deve ser 0 logo apos criacao)
        count = db.session.execute(text(
            "SELECT COUNT(*) FROM claude_session_store"
        )).scalar()
        print(f"[after] claude_session_store rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela ja existia, schema valido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
