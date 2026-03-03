"""
Migration: Adicionar importance_score e last_accessed_at a agent_memories.

Suporta QW-1: Memory Importance Scoring + Decay
- importance_score (FLOAT, default 0.5): peso heuristico da memoria
- last_accessed_at (TIMESTAMP): quando a memoria foi ultima vez injetada/lida

Executar:
    source .venv/bin/activate
    python scripts/migrations/add_importance_score_memories.py

Verificar:
    python scripts/migrations/add_importance_score_memories.py --verificar
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def _execute_safe(engine, sql_str, description):
    """Executa SQL em transacao isolada. Retorna True se sucesso."""
    try:
        with engine.begin() as conn:
            conn.execute(text(sql_str))
        print(f"   {description}: OK")
        return True
    except Exception as e:
        print(f"   {description}: FALHOU — {e}")
        return False


def _column_exists(conn, table_name, column_name):
    """Verifica se coluna existe na tabela."""
    result = conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :table_name AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None


def _index_exists(conn, index_name):
    """Verifica se indice existe."""
    result = conn.execute(text("""
        SELECT 1 FROM pg_indexes
        WHERE indexname = :index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


def migrate(engine):
    """Executa a migration."""
    print("\n=== Migration: add_importance_score_memories ===\n")

    # 1. Verificar estado ANTES
    with engine.connect() as conn:
        has_importance = _column_exists(conn, 'agent_memories', 'importance_score')
        has_last_accessed = _column_exists(conn, 'agent_memories', 'last_accessed_at')

    if has_importance and has_last_accessed:
        print("   Colunas ja existem — nada a fazer")
    else:
        # 2. Adicionar colunas
        if not has_importance:
            _execute_safe(engine,
                "ALTER TABLE agent_memories ADD COLUMN importance_score FLOAT DEFAULT 0.5",
                "ADD importance_score"
            )

        if not has_last_accessed:
            _execute_safe(engine,
                "ALTER TABLE agent_memories ADD COLUMN last_accessed_at TIMESTAMP DEFAULT NOW()",
                "ADD last_accessed_at"
            )

    # 3. Indices
    with engine.connect() as conn:
        if not _index_exists(conn, 'idx_agent_memories_last_accessed'):
            _execute_safe(engine,
                "CREATE INDEX idx_agent_memories_last_accessed ON agent_memories (user_id, last_accessed_at DESC)",
                "CREATE INDEX idx_agent_memories_last_accessed"
            )

        if not _index_exists(conn, 'idx_agent_memories_importance'):
            _execute_safe(engine,
                "CREATE INDEX idx_agent_memories_importance ON agent_memories (user_id, importance_score DESC)",
                "CREATE INDEX idx_agent_memories_importance"
            )

    # 4. Backfill last_accessed_at para registros existentes
    _execute_safe(engine, """
        UPDATE agent_memories
        SET last_accessed_at = COALESCE(updated_at, created_at, NOW())
        WHERE last_accessed_at IS NULL
    """, "BACKFILL last_accessed_at")

    # 5. Verificar DEPOIS
    verify(engine)


def verify(engine):
    """Verifica estado apos migration."""
    print("\n--- Verificacao ---")

    with engine.connect() as conn:
        has_importance = _column_exists(conn, 'agent_memories', 'importance_score')
        has_last_accessed = _column_exists(conn, 'agent_memories', 'last_accessed_at')
        has_idx_accessed = _index_exists(conn, 'idx_agent_memories_last_accessed')
        has_idx_importance = _index_exists(conn, 'idx_agent_memories_importance')

        # Contar registros sem backfill
        result = conn.execute(text("""
            SELECT COUNT(*) FROM agent_memories WHERE last_accessed_at IS NULL
        """))
        null_count = result.scalar() if has_last_accessed else 'N/A'

    checks = [
        ("importance_score column", has_importance),
        ("last_accessed_at column", has_last_accessed),
        ("idx_agent_memories_last_accessed", has_idx_accessed),
        ("idx_agent_memories_importance", has_idx_importance),
        ("Sem registros NULL em last_accessed_at", null_count == 0),
    ]

    all_ok = True
    for desc, ok in checks:
        status = "OK" if ok else "FALHOU"
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
