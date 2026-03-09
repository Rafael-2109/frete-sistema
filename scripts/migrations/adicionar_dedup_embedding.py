#!/usr/bin/env python3
"""
Migration: Adicionar coluna dedup_embedding em agent_memory_embeddings.

Contexto (2026-03-09):
  O dedup de memórias comparava embed(texto_limpo) contra
  embed(contexto_sonnet + [path]: XML). Essa lacuna de representação
  derruba similarity em 0.07-0.19 pontos, gerando falsos negativos
  com threshold 0.85 (diagnóstico: 4/4 duplicatas não detectadas).

  Fix: armazenar um segundo embedding gerado a partir do texto limpo
  (sem contexto Sonnet, sem path, sem XML) na coluna dedup_embedding.
  O dedup busca contra essa coluna — ambos os lados com input_type="document",
  mesma representação, comparação simétrica.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_dedup_embedding.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def run_migration():
    from app import create_app
    app = create_app()

    with app.app_context():
        from app import db
        from sqlalchemy import text

        # ── Before ──
        print("=== BEFORE ===")
        cols = db.session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'agent_memory_embeddings'
            ORDER BY ordinal_position
        """)).fetchall()
        for col_name, data_type in cols:
            marker = " ◄ NOVO" if col_name == 'dedup_embedding' else ""
            print(f"  {col_name}: {data_type}{marker}")

        has_column = any(c[0] == 'dedup_embedding' for c in cols)
        if has_column:
            print("\n✓ Coluna dedup_embedding já existe. Migration já aplicada.")
            return

        # ── Adicionar coluna ──
        print("\nAplicando migration...")

        # 1. Adicionar coluna (nullable, sem default)
        db.session.execute(text("""
            ALTER TABLE agent_memory_embeddings
            ADD COLUMN IF NOT EXISTS dedup_embedding vector(1024)
        """))
        db.session.commit()
        print("  ✓ Coluna dedup_embedding adicionada (vector(1024), nullable)")

        # 2. Criar índice HNSW para busca por dedup_embedding
        # Usa cosine distance (<=>), mesmo operador do embedding principal
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hnsw_dedup_embedding
            ON agent_memory_embeddings
            USING hnsw (dedup_embedding vector_cosine_ops)
        """))
        db.session.commit()
        print("  ✓ Índice HNSW criado para dedup_embedding")

        # ── After ──
        print("\n=== AFTER ===")
        cols_after = db.session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'agent_memory_embeddings'
            ORDER BY ordinal_position
        """)).fetchall()
        for col_name, data_type in cols_after:
            marker = " ◄ NOVO" if col_name == 'dedup_embedding' else ""
            print(f"  {col_name}: {data_type}{marker}")

        # Contar registros sem dedup_embedding (precisam backfill)
        count = db.session.execute(text("""
            SELECT COUNT(*) FROM agent_memory_embeddings
            WHERE dedup_embedding IS NULL
        """)).scalar()
        print(f"\n  {count} registros precisam de backfill (dedup_embedding IS NULL)")
        print("  Backfill: python scripts/migrations/backfill_dedup_embedding.py")

        print("\n✓ Migration concluída!")


if __name__ == '__main__':
    run_migration()
