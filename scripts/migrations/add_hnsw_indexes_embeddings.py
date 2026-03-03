"""
Migration: Criar indices HNSW para busca vetorial em embeddings.

Suporta T2-3: Performance de busca semantica via pgvector.
HNSW (Hierarchical Navigable Small World) oferece busca ANN com
O(log N) vs O(N) do sequential scan.

PREREQUISITO: pgvector instalado. HNSW funciona em tabelas vazias (diferente de IVFFlat).

Executar:
    source .venv/bin/activate
    python scripts/migrations/add_hnsw_indexes_embeddings.py

Verificar:
    python scripts/migrations/add_hnsw_indexes_embeddings.py --verificar
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def _index_exists(conn, index_name):
    """Verifica se indice existe."""
    result = conn.execute(text("""
        SELECT 1 FROM pg_indexes
        WHERE indexname = :index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


def _pgvector_available(conn):
    """Verifica se pgvector esta instalado."""
    try:
        result = conn.execute(text("""
            SELECT 1 FROM pg_extension WHERE extname = 'vector'
        """))
        return result.fetchone() is not None
    except Exception:
        return False


def _count_embeddings(conn, table_name):
    """Conta registros com embedding nao-null."""
    try:
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL
        """))
        return result.scalar()
    except Exception:
        return 0


def _execute_safe(engine, sql_str, description):
    """Executa SQL em transacao isolada."""
    try:
        with engine.begin() as conn:
            conn.execute(text(sql_str))
        print(f"   {description}: OK")
        return True
    except Exception as e:
        print(f"   {description}: FALHOU — {e}")
        return False


def migrate(engine):
    """Executa a migration."""
    print("\n=== Migration: add_hnsw_indexes_embeddings ===\n")

    with engine.connect() as conn:
        # Verificar prerequisito: pgvector
        if not _pgvector_available(conn):
            print("   BLOQUEADO: pgvector nao esta instalado.")
            print("   Execute: CREATE EXTENSION IF NOT EXISTS vector;")
            return False

        # Verificar se ha dados
        mem_count = _count_embeddings(conn, 'agent_memory_embeddings')
        session_count = _count_embeddings(conn, 'session_turn_embeddings')
        print(f"   Embeddings: memorias={mem_count}, sessoes={session_count}")

        if mem_count == 0 and session_count == 0:
            print("   INFO: Tabelas vazias. HNSW funciona em tabelas vazias (indices crescem incrementalmente).")

    # Criar indices HNSW (funciona em tabelas vazias — diferente de IVFFlat)
    # NOTA: Usando CREATE INDEX sem CONCURRENTLY porque precisamos de transacao
    # Em producao com carga, preferir o .sql com CONCURRENTLY

    with engine.connect() as conn:
        if not _index_exists(conn, 'idx_memory_emb_hnsw'):
            print("   Criando HNSW index para agent_memory_embeddings...")
            _execute_safe(engine, """
                CREATE INDEX idx_memory_emb_hnsw
                ON agent_memory_embeddings
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """, "CREATE INDEX idx_memory_emb_hnsw")
        else:
            print("   idx_memory_emb_hnsw: ja existe")

    with engine.connect() as conn:
        if not _index_exists(conn, 'idx_session_emb_hnsw'):
            print("   Criando HNSW index para session_turn_embeddings...")
            _execute_safe(engine, """
                CREATE INDEX idx_session_emb_hnsw
                ON session_turn_embeddings
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """, "CREATE INDEX idx_session_emb_hnsw")
        else:
            print("   idx_session_emb_hnsw: ja existe")

    verify(engine)
    return True


def verify(engine):
    """Verifica estado apos migration."""
    print("\n--- Verificacao ---")

    with engine.connect() as conn:
        has_pgvector = _pgvector_available(conn)
        has_mem_idx = _index_exists(conn, 'idx_memory_emb_hnsw')
        has_sess_idx = _index_exists(conn, 'idx_session_emb_hnsw')
        mem_count = _count_embeddings(conn, 'agent_memory_embeddings')
        session_count = _count_embeddings(conn, 'session_turn_embeddings')

    checks = [
        ("pgvector extension", has_pgvector),
        (f"idx_memory_emb_hnsw ({mem_count} embeddings)", has_mem_idx),
        (f"idx_session_emb_hnsw ({session_count} embeddings)", has_sess_idx),
    ]

    all_ok = True
    for desc, ok in checks:
        status = "OK" if ok else "PENDENTE"
        print(f"   {desc}: {status}")
        if not ok:
            all_ok = False

    print(f"\n{'   MIGRATION COMPLETA' if all_ok else '   MIGRATION INCOMPLETA'}\n")
    return all_ok


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        engine = db.engine

        if '--verificar' in sys.argv:
            verify(engine)
        else:
            migrate(engine)
