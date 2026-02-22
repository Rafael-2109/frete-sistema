"""
Migration: Criar tabela route_template_embeddings.

Indexação semântica de rotas e templates do sistema para busca
por linguagem natural ("onde fica contas a pagar?").

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_route_template_embeddings.py

Verificar:
    python scripts/migrations/criar_tabela_route_template_embeddings.py --verificar
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def _execute_safe(engine, sql_str, description):
    """Executa SQL em transação isolada. Retorna True se sucesso."""
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


def criar_tabela():
    """Cria tabela route_template_embeddings."""
    app = create_app()
    with app.app_context():
        engine = db.engine

        # ============================================
        # BEFORE: Verificar estado atual
        # ============================================
        print("=" * 60)
        print("CRIANDO TABELA route_template_embeddings")
        print("=" * 60)

        with engine.connect() as conn:
            # Verificar pgvector
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            pgvector_available = result.fetchone() is not None
            print(f"\n[INFO] pgvector disponivel: {pgvector_available}")

            exists = _table_exists(conn, 'route_template_embeddings')
            print(f"[INFO] route_template_embeddings ja existe: {exists}")
            if exists:
                count = _count_rows(conn, 'route_template_embeddings')
                print(f"[INFO] route_template_embeddings registros: {count}")

        embedding_type = "vector(1024)" if pgvector_available else "TEXT"

        # ============================================
        # EXECUTE: Criar tabela
        # ============================================
        print(f"\n[1/3] Criando tabela route_template_embeddings (embedding={embedding_type})...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS route_template_embeddings (
                id SERIAL PRIMARY KEY,

                -- Identificacao
                tipo VARCHAR(20) NOT NULL,
                blueprint_name VARCHAR(100) NOT NULL,
                function_name VARCHAR(200) NOT NULL,

                -- Rota
                url_path VARCHAR(500) NOT NULL,
                http_methods VARCHAR(50) NOT NULL,

                -- Template (nullable para rotas API)
                template_path VARCHAR(500),

                -- Navegacao
                menu_path TEXT,
                permission_decorator VARCHAR(200),

                -- Metadados
                source_file VARCHAR(500) NOT NULL,
                source_line INTEGER,
                docstring TEXT,
                ajax_endpoints TEXT,

                -- Embedding
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                content_hash VARCHAR(32),

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),

                -- Constraint unica
                CONSTRAINT uq_route_blueprint_function UNIQUE (blueprint_name, function_name)
            );
        """, "Tabela route_template_embeddings")

        # ============================================
        # EXECUTE: Criar indices
        # ============================================
        print("\n[2/3] Criando indices...")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_rte_tipo
                ON route_template_embeddings(tipo);
        """, "Indice idx_rte_tipo")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_rte_template_path
                ON route_template_embeddings(template_path);
        """, "Indice idx_rte_template_path")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_rte_content_hash
                ON route_template_embeddings(content_hash);
        """, "Indice idx_rte_content_hash")

        # ============================================
        # EXECUTE: Indice HNSW (apenas com pgvector)
        # ============================================
        print("\n[3/3] Criando indice HNSW...")

        if pgvector_available:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_rte_embedding_hnsw
                    ON route_template_embeddings USING hnsw (embedding vector_cosine_ops);
            """, "Indice HNSW idx_rte_embedding_hnsw")
        else:
            print("   Indice HNSW: SKIP (pgvector indisponivel)")

        # ============================================
        # AFTER: Verificar resultado
        # ============================================
        with engine.connect() as conn:
            ok = _table_exists(conn, 'route_template_embeddings')

        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"route_template_embeddings criada: {'SIM' if ok else 'NAO'}")
        print(f"Tipo embedding: {embedding_type}")
        print("=" * 60)


def verificar_tabela():
    """Verifica se a tabela existe e mostra estrutura."""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFICANDO TABELA route_template_embeddings")
        print("=" * 60)

        with db.engine.connect() as conn:
            table_name = 'route_template_embeddings'
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

            # Constraints
            print("Constraints:")
            result = conn.execute(text("""
                SELECT conname, contype
                FROM pg_constraint
                WHERE conrelid = :table_name::regclass
                ORDER BY conname;
            """), {"table_name": table_name})
            for row in result.fetchall():
                tipo = {'p': 'PRIMARY KEY', 'u': 'UNIQUE', 'f': 'FOREIGN KEY', 'c': 'CHECK'}.get(row[1], row[1])
                print(f"   {row[0]}: {tipo}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Criar tabela route_template_embeddings'
    )
    parser.add_argument(
        '--verificar', action='store_true',
        help='Apenas verifica se a tabela existe'
    )

    args = parser.parse_args()

    if args.verificar:
        verificar_tabela()
    else:
        criar_tabela()
        verificar_tabela()
