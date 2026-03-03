"""
Migration (data fix): Remove embeddings orfãos de agent_memory_embeddings.

Orfãos são registros cujo memory_id não existe mais em agent_memories.
Isso pode acontecer se o trigger trg_delete_memory_embedding falhou
ou se a deleção ocorreu antes do trigger ser criado.

Executar:
    source .venv/bin/activate
    python scripts/migrations/gc_orphan_embeddings.py

Dry-run:
    python scripts/migrations/gc_orphan_embeddings.py --dry-run
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def gc_orphan_embeddings(dry_run: bool = False):
    """Remove embeddings orfãos."""
    print("\n=== GC: Orphan Embeddings ===\n")

    # 1. Contar orfãos
    result = db.session.execute(text("""
        SELECT COUNT(*)
        FROM agent_memory_embeddings ame
        LEFT JOIN agent_memories am ON ame.memory_id = am.id
        WHERE am.id IS NULL
    """))
    orphan_count = result.scalar()

    print(f"   Embeddings orfãos encontrados: {orphan_count}")

    if orphan_count == 0:
        print("   Nada a fazer — sem orfãos.\n")
        return

    # 2. Listar orfãos para auditoria
    orphans = db.session.execute(text("""
        SELECT ame.id, ame.memory_id, ame.user_id, ame.path
        FROM agent_memory_embeddings ame
        LEFT JOIN agent_memories am ON ame.memory_id = am.id
        WHERE am.id IS NULL
        ORDER BY ame.id
        LIMIT 50
    """)).fetchall()

    for o in orphans:
        print(f"   Orfão: id={o.id} memory_id={o.memory_id} user_id={o.user_id} path={o.path}")

    if orphan_count and len(orphans) < orphan_count:
        print(f"   ... e mais {orphan_count - len(orphans)} orfãos")

    # 3. Deletar
    if dry_run:
        print(f"\n   [DRY-RUN] {orphan_count} embeddings seriam removidos.\n")
        return

    try:
        deleted = db.session.execute(text("""
            DELETE FROM agent_memory_embeddings
            WHERE id IN (
                SELECT ame.id
                FROM agent_memory_embeddings ame
                LEFT JOIN agent_memories am ON ame.memory_id = am.id
                WHERE am.id IS NULL
            )
        """))
        db.session.commit()
        print(f"\n   Removidos: {deleted.rowcount} embeddings orfãos.")

        # Verificação pós-delete
        remaining = db.session.execute(text("""
            SELECT COUNT(*)
            FROM agent_memory_embeddings ame
            LEFT JOIN agent_memories am ON ame.memory_id = am.id
            WHERE am.id IS NULL
        """)).scalar()
        print(f"   Orfãos remanescentes: {remaining}\n")

    except Exception as e:
        db.session.rollback()
        print(f"\n   ERRO ao deletar orfãos: {e}")
        print("   Rollback executado. Nenhum dado foi alterado.\n")
        raise


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        dry_run = '--dry-run' in sys.argv
        gc_orphan_embeddings(dry_run=dry_run)
