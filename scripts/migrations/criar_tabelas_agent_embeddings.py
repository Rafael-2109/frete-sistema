"""
Migration: Criar tabelas session_turn_embeddings e agent_memory_embeddings.

Fase 4 do Agent RAG — armazena embeddings de turns de sessao e memorias
do agente para busca semantica.

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_tabelas_agent_embeddings.py

Verificar:
    python scripts/migrations/criar_tabelas_agent_embeddings.py --verificar
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


def _table_exists(conn, table_name):
    """Verifica se tabela existe."""
    result = conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :table_name
    """), {"table_name": table_name})
    return result.fetchone() is not None


def _count_rows(conn, table_name):
    """Conta registros em tabela."""
    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    return result.scalar()


def criar_tabelas():
    """Cria tabelas session_turn_embeddings e agent_memory_embeddings."""
    app = create_app()
    with app.app_context():
        engine = db.engine

        # ============================================
        # BEFORE: Verificar estado atual
        # ============================================
        print("=" * 60)
        print("CRIANDO TABELAS DE EMBEDDINGS DO AGENTE (Fase 4)")
        print("=" * 60)

        with engine.connect() as conn:
            # Verificar pgvector
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            pgvector_available = result.fetchone() is not None
            print(f"\n[INFO] pgvector disponivel: {pgvector_available}")

            for table_name in ['session_turn_embeddings', 'agent_memory_embeddings']:
                exists = _table_exists(conn, table_name)
                print(f"[INFO] {table_name} ja existe: {exists}")
                if exists:
                    count = _count_rows(conn, table_name)
                    print(f"[INFO] {table_name} registros: {count}")

        embedding_type = "vector(1024)" if pgvector_available else "TEXT"

        # ============================================
        # EXECUTE: Criar session_turn_embeddings
        # ============================================
        print(f"\n[1/4] Criando tabela session_turn_embeddings (embedding={embedding_type})...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS session_turn_embeddings (
                id SERIAL PRIMARY KEY,

                -- Identificacao
                session_id VARCHAR(255) NOT NULL,
                user_id INTEGER NOT NULL,
                turn_index INTEGER NOT NULL,

                -- Conteudo
                user_content TEXT NOT NULL,
                assistant_summary TEXT,
                texto_embedado TEXT NOT NULL,

                -- Embedding
                embedding {embedding_type},
                model_used VARCHAR(50),
                content_hash VARCHAR(32),

                -- Metadata de sessao (denormalizado)
                session_title VARCHAR(200),
                session_created_at TIMESTAMP,

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),

                -- Constraint unica
                CONSTRAINT uq_session_turn UNIQUE (session_id, turn_index)
            );
        """, "Tabela session_turn_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_ste_user_id
                ON session_turn_embeddings(user_id);
        """, "Indice idx_ste_user_id")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_ste_session_id
                ON session_turn_embeddings(session_id);
        """, "Indice idx_ste_session_id")

        # ============================================
        # EXECUTE: Criar agent_memory_embeddings
        # ============================================
        print(f"\n[2/4] Criando tabela agent_memory_embeddings (embedding={embedding_type})...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS agent_memory_embeddings (
                id SERIAL PRIMARY KEY,

                -- Identificacao
                memory_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                path VARCHAR(500) NOT NULL,

                -- Embedding
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                content_hash VARCHAR(32),

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),

                -- Constraint unica
                CONSTRAINT uq_memory_embedding UNIQUE (memory_id)
            );
        """, "Tabela agent_memory_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_ame_user_id
                ON agent_memory_embeddings(user_id);
        """, "Indice idx_ame_user_id")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_ame_memory_id
                ON agent_memory_embeddings(memory_id);
        """, "Indice idx_ame_memory_id")

        # ============================================
        # EXECUTE: Cascade delete trigger
        # ============================================
        print("\n[3/4] Criando trigger de cascade delete para agent_memory_embeddings...")

        _execute_safe(engine, """
            CREATE OR REPLACE FUNCTION fn_delete_memory_embedding()
            RETURNS TRIGGER AS $$
            BEGIN
                DELETE FROM agent_memory_embeddings WHERE memory_id = OLD.id;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
        """, "Funcao fn_delete_memory_embedding")

        _execute_safe(engine, """
            DROP TRIGGER IF EXISTS trg_delete_memory_embedding ON agent_memories;
        """, "Drop trigger existente (idempotente)")

        _execute_safe(engine, """
            CREATE TRIGGER trg_delete_memory_embedding
            BEFORE DELETE ON agent_memories
            FOR EACH ROW
            EXECUTE FUNCTION fn_delete_memory_embedding();
        """, "Trigger trg_delete_memory_embedding")

        # Nota: IVFFlat indices serao criados pelos batch indexers apos populacao
        print("\n[4/4] IVFFlat indices serao criados pelos batch indexers apos populacao")

        # ============================================
        # AFTER: Verificar resultado
        # ============================================
        with engine.connect() as conn:
            ste_ok = _table_exists(conn, 'session_turn_embeddings')
            ame_ok = _table_exists(conn, 'agent_memory_embeddings')

        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"session_turn_embeddings criada: {'SIM' if ste_ok else 'NAO'}")
        print(f"agent_memory_embeddings criada: {'SIM' if ame_ok else 'NAO'}")
        print(f"Tipo embedding: {embedding_type}")
        print("=" * 60)


def verificar_tabelas():
    """Verifica se as tabelas existem e mostra estrutura."""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFICANDO TABELAS DE EMBEDDINGS DO AGENTE")
        print("=" * 60)

        with db.engine.connect() as conn:
            for table_name in ['session_turn_embeddings', 'agent_memory_embeddings']:
                print(f"\n--- {table_name} ---")

                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position;
                """), {"table_name": table_name})
                rows = result.fetchall()

                if rows:
                    print("Colunas:")
                    for row in rows:
                        print(f"   {row[0]}: {row[1]} (nullable={row[2]})")

                    count = _count_rows(conn, table_name)
                    print(f"Registros: {count}")

                    count_emb = conn.execute(text(
                        f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL"
                    )).scalar()
                    print(f"Com embedding: {count_emb}")
                else:
                    print("TABELA NAO ENCONTRADA")

                # Indices
                print("Indices:")
                result = conn.execute(text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = :table_name
                    ORDER BY indexname;
                """), {"table_name": table_name})
                for row in result.fetchall():
                    print(f"   {row[0]}")

            # Verificar trigger
            print("\n--- Triggers ---")
            result = conn.execute(text("""
                SELECT trigger_name, event_manipulation, action_statement
                FROM information_schema.triggers
                WHERE trigger_name = 'trg_delete_memory_embedding'
            """))
            triggers = result.fetchall()
            if triggers:
                for t in triggers:
                    print(f"   {t[0]}: {t[1]} → {t[2][:60]}...")
            else:
                print("   Nenhum trigger encontrado")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Criar tabelas de embeddings do agente (Fase 4)'
    )
    parser.add_argument(
        '--verificar', action='store_true',
        help='Apenas verifica se as tabelas existem'
    )

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    else:
        criar_tabelas()
        verificar_tabelas()
