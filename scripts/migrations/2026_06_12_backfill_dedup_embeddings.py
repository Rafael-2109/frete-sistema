"""Backfill de dedup_embedding em agent_memory_embeddings (registros pre-migration).

Incidente 2026-06-12: 145 registros sem dedup_embedding caiam no ramo FALLBACK
do dedup de memorias (embedding contextual, threshold antigo 0.70) e bloqueavam
saves de assuntos distintos do mesmo dominio. Este backfill popula o
dedup_embedding via _save_dedup_embedding_only (upsert idempotente) e elimina
o ramo fallback na pratica.

Uso:
    python scripts/migrations/2026_06_12_backfill_dedup_embeddings.py            # dry-run
    python scripts/migrations/2026_06_12_backfill_dedup_embeddings.py --executar
"""
import argparse
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app import create_app, db
from sqlalchemy import text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--executar", action="store_true",
                    help="executa de verdade (default: dry-run)")
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        rows = db.session.execute(text("""
            SELECT ame.id, ame.user_id, ame.path, am.content
            FROM agent_memory_embeddings ame
            JOIN agent_memories am ON am.id = ame.memory_id
            WHERE ame.dedup_embedding IS NULL
            ORDER BY ame.id
        """)).fetchall()
        print(f"[backfill] registros sem dedup_embedding: {len(rows)}")
        if not args.executar:
            for r in rows[:10]:
                print(f"  dry-run: id={r.id} user={r.user_id} path={r.path}")
            print("[backfill] dry-run — use --executar para aplicar")
            return

        from app.agente.tools.memory_mcp_tool import _save_dedup_embedding_only
        ok, skip = 0, 0
        for r in rows:
            try:
                _save_dedup_embedding_only(r.user_id, r.path, r.content or "")
                db.session.commit()
                ok += 1
            except Exception as e:
                db.session.rollback()
                skip += 1
                print(f"  ERRO id={r.id} path={r.path}: {e}")
        restante = db.session.execute(text(
            "SELECT COUNT(*) FROM agent_memory_embeddings WHERE dedup_embedding IS NULL"
        )).scalar()
        print(f"[backfill] ok={ok} erros={skip} restantes_sem_dedup={restante}")


if __name__ == "__main__":
    main()
