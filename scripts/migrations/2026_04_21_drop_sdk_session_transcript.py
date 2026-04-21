"""
Migration: drop agent_sessions.sdk_session_transcript (SessionStore Fase C).

Pos SessionStore Fase B cutover (2026-04-21): coluna TEXT 1GB nao tem mais
callers operacionais. `save_transcript()` / `get_transcript()` em models.py
nunca sao chamados (zero callers verificados). `session_has_legacy_transcript()`
em session_store_adapter.py apenas checava existencia para dual-run (removido).

Ganho: ~66MB + remocao de coluna confusa.

Idempotente: verifica existencia antes do drop.

Usage:
    python scripts/migrations/2026_04_21_drop_sdk_session_transcript.py
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def verificar_coluna() -> bool:
    """Retorna True se a coluna ainda existe."""
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_sessions'
          AND column_name = 'sdk_session_transcript'
    """)).scalar()
    return bool(result)


def medir_volume() -> int:
    """Retorna numero de linhas com transcript nao-nulo (diagnostico pre-drop)."""
    result = db.session.execute(text("""
        SELECT COUNT(*) FROM agent_sessions
        WHERE sdk_session_transcript IS NOT NULL
          AND length(sdk_session_transcript) > 0
    """)).scalar()
    return int(result or 0)


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_coluna()
        print(f"[before] agent_sessions.sdk_session_transcript exists: {existed_before}")

        if existed_before:
            volume = medir_volume()
            print(f"[before] linhas com transcript populado: {volume}")

        print("[info] Removendo coluna sdk_session_transcript (idempotente)...")
        db.session.execute(text("""
            ALTER TABLE agent_sessions
              DROP COLUMN IF EXISTS sdk_session_transcript
        """))
        db.session.commit()

        if verificar_coluna():
            print("[erro] Coluna ainda existe apos DROP — migration falhou.")
            return 1

        print("[after] agent_sessions.sdk_session_transcript: REMOVIDA")

        if existed_before:
            print("[ok] Fase C executada — coluna removida com sucesso.")
        else:
            print("[ok] Migration idempotente — coluna ja havia sido removida.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
