"""
Migration: Trocar indice idx_sqlt_content_hash por unique parcial idx_sqlt_content_hash_unique.

Habilita ON CONFLICT (content_hash) WHERE content_hash IS NOT NULL para upsert
em sql_template_embeddings — mesmo padrao de devolucao_reason_embeddings.

Executar:
    source .venv/bin/activate
    python scripts/migrations/fix_unique_idx_sqlt_content_hash.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import text


def main():
    from app import create_app, db

    app = create_app()

    with app.app_context():
        # BEFORE
        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'sql_template_embeddings'
                  AND indexname IN ('idx_sqlt_content_hash', 'idx_sqlt_content_hash_unique')
            """))
            before = {row[0]: row[1] for row in result.fetchall()}
            print("=== BEFORE ===")
            for name, defn in before.items():
                print(f"  {name}: {defn}")
            if not before:
                print("  (nenhum indice content_hash encontrado)")

        # EXECUTE
        with db.engine.begin() as conn:
            # Drop antigo (se existir)
            conn.execute(text("DROP INDEX IF EXISTS idx_sqlt_content_hash"))
            print("\n[OK] DROP INDEX idx_sqlt_content_hash (if existed)")

            # Criar novo unique parcial
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sqlt_content_hash_unique
                ON sql_template_embeddings (content_hash)
                WHERE content_hash IS NOT NULL
            """))
            print("[OK] CREATE UNIQUE INDEX idx_sqlt_content_hash_unique (partial)")

        # AFTER
        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'sql_template_embeddings'
                  AND indexname IN ('idx_sqlt_content_hash', 'idx_sqlt_content_hash_unique')
            """))
            after = {row[0]: row[1] for row in result.fetchall()}
            print("\n=== AFTER ===")
            for name, defn in after.items():
                print(f"  {name}: {defn}")

            if 'idx_sqlt_content_hash_unique' in after and 'idx_sqlt_content_hash' not in after:
                print("\n[SUCCESS] Migration concluida com sucesso")
            else:
                print("\n[WARNING] Verificar resultado manualmente")


if __name__ == '__main__':
    main()
