#!/usr/bin/env python3
"""
Migration: Criar indices HNSW para 9 tabelas de embeddings.

HNSW (Hierarchical Navigable Small World):
- Funciona em tabelas vazias (IVFFlat requer dados)
- Melhor recall (>99%) que IVFFlat (~95%)
- Parametros: m=16, ef_construction=64 (defaults pgvector)
- Operador: vector_cosine_ops (cosine distance, usado por <=>)

Inclui: indice unico parcial em content_hash para devolucao_reason_embeddings

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_indices_hnsw_embeddings.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


HNSW_INDICES = [
    {
        "name": "idx_hnsw_ssw_embedding",
        "table": "ssw_document_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_product_embedding",
        "table": "product_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_financial_entity_embedding",
        "table": "financial_entity_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_session_turn_embedding",
        "table": "session_turn_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_agent_memory_embedding",
        "table": "agent_memory_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_sql_template_embedding",
        "table": "sql_template_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_payment_category_embedding",
        "table": "payment_category_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_devolucao_reason_embedding",
        "table": "devolucao_reason_embeddings",
        "column": "embedding",
    },
    {
        "name": "idx_hnsw_carrier_embedding",
        "table": "carrier_embeddings",
        "column": "embedding",
    },
]


def main():
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()

    with app.app_context():
        # ----------------------------------------------------------
        # BEFORE: verificar estado atual dos indices
        # ----------------------------------------------------------
        print("=" * 60)
        print("BEFORE: Indices de embedding existentes")
        print("=" * 60)

        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, tablename
                FROM pg_indexes
                WHERE indexname LIKE '%embedding%'
                  AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname
            """))
            existing = result.fetchall()
            if existing:
                for row in existing:
                    print(f"  {row[0]} -> {row[1]}")
            else:
                print("  (nenhum indice encontrado)")

        # ----------------------------------------------------------
        # EXECUTE: verificar pgvector e criar indices HNSW
        # ----------------------------------------------------------
        print("\n" + "=" * 60)
        print("EXECUTE: Criando indices HNSW")
        print("=" * 60)

        with db.engine.begin() as conn:
            # Verificar extensao pgvector
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            if not result.fetchone():
                print("ERRO: Extensao pgvector nao instalada!")
                print("Execute: CREATE EXTENSION IF NOT EXISTS vector;")
                return

            print("  pgvector: OK")

            # Criar indices HNSW
            created = 0
            skipped = 0
            for idx in HNSW_INDICES:
                # Verificar se ja existe
                result = conn.execute(text(
                    "SELECT 1 FROM pg_indexes WHERE indexname = :name"
                ), {"name": idx["name"]})

                if result.fetchone():
                    print(f"  {idx['name']}: ja existe (skip)")
                    skipped += 1
                    continue

                # Verificar se tabela existe
                result = conn.execute(text("""
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = :table
                """), {"table": idx["table"]})

                if not result.fetchone():
                    print(f"  {idx['name']}: tabela {idx['table']} nao existe (skip)")
                    skipped += 1
                    continue

                # Verificar se coluna embedding e tipo vector
                result = conn.execute(text("""
                    SELECT data_type, udt_name FROM information_schema.columns
                    WHERE table_name = :table AND column_name = :col
                """), {"table": idx["table"], "col": idx["column"]})
                col_info = result.fetchone()

                if not col_info:
                    print(f"  {idx['name']}: coluna {idx['column']} nao existe (skip)")
                    skipped += 1
                    continue

                col_type = col_info[1] if col_info else 'unknown'
                if col_type != 'vector':
                    print(f"  {idx['name']}: coluna {idx['column']} e tipo '{col_type}' (nao vector) — criando mesmo assim")

                # Criar indice HNSW
                sql = f"""
                    CREATE INDEX IF NOT EXISTS {idx['name']}
                        ON {idx['table']}
                        USING hnsw ({idx['column']} vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64)
                """
                try:
                    conn.execute(text(sql))
                    print(f"  {idx['name']}: CRIADO")
                    created += 1
                except Exception as e:
                    print(f"  {idx['name']}: ERRO — {e}")

            # Indice unico parcial em content_hash (devolucao_reason_embeddings)
            print("\n  Criando indice unico parcial content_hash...")
            try:
                # Drop antigo nao-unico
                conn.execute(text("DROP INDEX IF EXISTS idx_dre_content_hash"))
                # Criar unico parcial
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_dre_content_hash_unique
                        ON devolucao_reason_embeddings (content_hash)
                        WHERE content_hash IS NOT NULL
                """))
                print("  idx_dre_content_hash_unique: CRIADO")
                created += 1
            except Exception as e:
                print(f"  idx_dre_content_hash_unique: ERRO — {e}")

            print(f"\n  Resumo: {created} criados, {skipped} skipped")

        # ----------------------------------------------------------
        # AFTER: verificar indices criados
        # ----------------------------------------------------------
        print("\n" + "=" * 60)
        print("AFTER: Indices de embedding")
        print("=" * 60)

        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, tablename,
                       pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
                FROM pg_indexes
                WHERE indexname LIKE 'idx_hnsw_%'
                   OR indexname LIKE 'idx_dre_content_hash%'
                ORDER BY tablename, indexname
            """))
            for row in result.fetchall():
                print(f"  {row[0]} -> {row[1]} ({row[2]})")

        print("\nMigration concluida!")


if __name__ == '__main__':
    main()
