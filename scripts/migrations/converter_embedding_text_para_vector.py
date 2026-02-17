#!/usr/bin/env python3
"""
Migration: Converter colunas embedding de TEXT para vector(1024).

Problema: session_turn_embeddings e agent_memory_embeddings foram criadas
com embedding TEXT. Indices HNSW requerem tipo vector nativo.

Executar:
    source .venv/bin/activate
    python scripts/migrations/converter_embedding_text_para_vector.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


TABLES_TO_FIX = [
    "session_turn_embeddings",
    "agent_memory_embeddings",
]


def main():
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()

    with app.app_context():
        # ----------------------------------------------------------
        # BEFORE: verificar tipo atual
        # ----------------------------------------------------------
        print("=" * 60)
        print("BEFORE: Tipo da coluna embedding")
        print("=" * 60)

        with db.engine.connect() as conn:
            for table in TABLES_TO_FIX:
                result = conn.execute(text("""
                    SELECT udt_name
                    FROM information_schema.columns
                    WHERE table_name = :table AND column_name = 'embedding'
                """), {"table": table})
                row = result.fetchone()
                tipo = row[0] if row else "NAO ENCONTRADA"
                print(f"  {table}.embedding: {tipo}")

                if tipo == "vector":
                    print(f"    -> Ja e vector, nada a fazer")

        # ----------------------------------------------------------
        # EXECUTE: converter TEXT → vector(1024)
        # ----------------------------------------------------------
        print("\n" + "=" * 60)
        print("EXECUTE: Convertendo TEXT -> vector(1024)")
        print("=" * 60)

        with db.engine.begin() as conn:
            for table in TABLES_TO_FIX:
                # Verificar tipo atual
                result = conn.execute(text("""
                    SELECT udt_name
                    FROM information_schema.columns
                    WHERE table_name = :table AND column_name = 'embedding'
                """), {"table": table})
                row = result.fetchone()
                tipo = row[0] if row else "unknown"

                if tipo == "vector":
                    print(f"  {table}: ja e vector (skip)")
                    continue

                # Contar rows com embedding nao-NULL
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {table} WHERE embedding IS NOT NULL
                """))
                count = result.scalar()
                print(f"  {table}: {count} rows com embedding (tipo atual: {tipo})")

                # Converter
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                            ALTER COLUMN embedding TYPE vector(1024)
                            USING embedding::vector(1024)
                    """))
                    print(f"  {table}: CONVERTIDO para vector(1024)")
                except Exception as e:
                    print(f"  {table}: ERRO na conversao — {e}")
                    raise

                # Criar indice HNSW
                idx_name = f"idx_hnsw_{table.replace('_embeddings', '')}_embedding"
                try:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name}
                            ON {table}
                            USING hnsw (embedding vector_cosine_ops)
                            WITH (m = 16, ef_construction = 64)
                    """))
                    print(f"  {idx_name}: CRIADO")
                except Exception as e:
                    print(f"  {idx_name}: ERRO — {e}")

        # ----------------------------------------------------------
        # AFTER: verificar resultado
        # ----------------------------------------------------------
        print("\n" + "=" * 60)
        print("AFTER: Verificacao")
        print("=" * 60)

        with db.engine.connect() as conn:
            for table in TABLES_TO_FIX:
                result = conn.execute(text("""
                    SELECT udt_name
                    FROM information_schema.columns
                    WHERE table_name = :table AND column_name = 'embedding'
                """), {"table": table})
                row = result.fetchone()
                tipo = row[0] if row else "NAO ENCONTRADA"
                print(f"  {table}.embedding: {tipo}")

            # Verificar indices
            result = conn.execute(text("""
                SELECT indexname, tablename
                FROM pg_indexes
                WHERE indexname LIKE 'idx_hnsw_%'
                ORDER BY tablename
            """))
            print("\n  Indices HNSW:")
            for row in result.fetchall():
                print(f"    {row[0]} -> {row[1]}")

        print("\nMigration concluida!")


if __name__ == '__main__':
    main()
