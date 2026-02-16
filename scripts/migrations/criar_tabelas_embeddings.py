"""
Migration: Criar extensao pgvector e tabelas de embeddings.

Cria:
- Extensao pgvector (se disponivel)
- Tabela ssw_document_embeddings (busca semantica em docs SSW)
- Tabela product_embeddings (matching semantico de produtos)

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_tabelas_embeddings.py

Verificar:
    python scripts/migrations/criar_tabelas_embeddings.py --verificar
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


def _get_column_type(engine, table_name, column_name):
    """Retorna o data_type de uma coluna, ou None se nao existe."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :col
        """), {"table": table_name, "col": column_name})
        row = result.fetchone()
        return row[0] if row else None


def criar_tabelas_embeddings():
    """Cria extensao pgvector e tabelas de embeddings."""
    app = create_app()
    with app.app_context():
        engine = db.engine

        # ============================================
        # BEFORE: Verificar estado atual
        # ============================================
        print("=" * 60)
        print("CRIANDO INFRAESTRUTURA DE EMBEDDINGS")
        print("=" * 60)

        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            pgvector_already = result.fetchone() is not None
            print(f"\n[INFO] pgvector ja instalado: {pgvector_already}")

            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('ssw_document_embeddings', 'product_embeddings')
                ORDER BY table_name;
            """))
            existing = [row[0] for row in result.fetchall()]
            print(f"[INFO] Tabelas existentes: {existing or 'nenhuma'}")

        # ============================================
        # [1/3] Habilitar pgvector (transacao isolada)
        # ============================================
        print("\n[1/3] Habilitando extensao pgvector...")
        pgvector_available = _execute_safe(
            engine,
            "CREATE EXTENSION IF NOT EXISTS vector;",
            "pgvector"
        )
        if not pgvector_available:
            print("   Usando TEXT para armazenar embeddings (fallback)")

        embedding_type = "vector(1024)" if pgvector_available else "TEXT"

        # ============================================
        # Detectar tabelas criadas com tipo errado
        # ============================================
        for table_name in ['ssw_document_embeddings', 'product_embeddings']:
            if table_name in existing:
                current_type = _get_column_type(engine, table_name, 'embedding')
                needs_recreate = (
                    (pgvector_available and current_type == 'text') or
                    (not pgvector_available and current_type == 'USER-DEFINED')
                )
                if needs_recreate:
                    count_result = None
                    with engine.connect() as conn:
                        count_result = conn.execute(text(
                            f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL"
                        )).scalar()

                    if count_result and count_result > 0:
                        print(f"\n   [AVISO] {table_name} tem {count_result} embeddings com tipo {current_type}.")
                        print(f"   Nao sera recriada automaticamente. Use ALTER TABLE manualmente.")
                    else:
                        print(f"\n   [INFO] {table_name} tem tipo {current_type}, precisa de {embedding_type}. Recriando (0 embeddings)...")
                        _execute_safe(engine, f"DROP TABLE IF EXISTS {table_name} CASCADE;", f"Drop {table_name}")
                        existing = [t for t in existing if t != table_name]

        # ============================================
        # [2/3] Criar ssw_document_embeddings
        # ============================================
        print(f"\n[2/3] Criando tabela ssw_document_embeddings (embedding={embedding_type})...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS ssw_document_embeddings (
                id SERIAL PRIMARY KEY,
                doc_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                heading TEXT,
                doc_title TEXT,
                embedding {embedding_type},
                char_count INTEGER,
                token_count INTEGER,
                model_used VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT uq_ssw_doc_chunk UNIQUE (doc_path, chunk_index)
            );
        """, "Tabela ssw_document_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_ssw_emb_doc_path
                ON ssw_document_embeddings(doc_path);
        """, "Indice doc_path")

        if pgvector_available:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_ssw_emb_cosine
                    ON ssw_document_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 50);
            """, "Indice IVFFlat SSW (pode falhar se tabela vazia)")

        # ============================================
        # [3/3] Criar product_embeddings
        # ============================================
        print(f"\n[3/3] Criando tabela product_embeddings (embedding={embedding_type})...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS product_embeddings (
                id SERIAL PRIMARY KEY,
                cod_produto VARCHAR(50) NOT NULL UNIQUE,
                nome_produto TEXT NOT NULL,
                tipo_materia_prima VARCHAR(100),
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """, "Tabela product_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_prod_emb_cod
                ON product_embeddings(cod_produto);
        """, "Indice cod_produto")

        if pgvector_available:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_prod_emb_cosine
                    ON product_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 20);
            """, "Indice IVFFlat produtos (pode falhar se tabela vazia)")

        # ============================================
        # AFTER: Verificar resultado
        # ============================================
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('ssw_document_embeddings', 'product_embeddings')
                ORDER BY table_name;
            """))
            tabelas = [row[0] for row in result.fetchall()]

        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"pgvector: {'SIM' if pgvector_available else 'NAO (fallback TEXT)'}")
        print(f"Tabelas criadas: {tabelas}")
        print("=" * 60)


def verificar_tabelas():
    """Verifica se as tabelas existem e mostra estrutura."""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFICANDO INFRAESTRUTURA DE EMBEDDINGS")
        print("=" * 60)

        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            pgvector = result.fetchone() is not None
            print(f"\npgvector: {'INSTALADO' if pgvector else 'NAO INSTALADO'}")

            for tabela in ['ssw_document_embeddings', 'product_embeddings']:
                print(f"\n[{tabela}]")
                try:
                    result = conn.execute(text("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        ORDER BY ordinal_position;
                    """), {"table_name": tabela})
                    rows = result.fetchall()
                    if rows:
                        for row in rows:
                            print(f"   {row[0]}: {row[1]} (nullable={row[2]})")

                        count = conn.execute(text(
                            f"SELECT COUNT(*) FROM {tabela}"
                        )).scalar()
                        print(f"   REGISTROS: {count}")

                        count_emb = conn.execute(text(
                            f"SELECT COUNT(*) FROM {tabela} WHERE embedding IS NOT NULL"
                        )).scalar()
                        print(f"   COM EMBEDDING: {count_emb}")
                    else:
                        print("   TABELA NAO ENCONTRADA")
                except Exception as e:
                    print(f"   ERRO: {e}")

            print("\n[INDICES]")
            try:
                result = conn.execute(text("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename IN ('ssw_document_embeddings', 'product_embeddings')
                    ORDER BY tablename, indexname;
                """))
                for row in result.fetchall():
                    print(f"   {row[0]}")
            except Exception as e:
                print(f"   ERRO: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas de embeddings')
    parser.add_argument('--verificar', action='store_true', help='Apenas verifica se as tabelas existem')

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    else:
        criar_tabelas_embeddings()
        verificar_tabelas()
