"""
Migration: Criar tabela financial_entity_embeddings.

Armazena embeddings de entidades financeiras (fornecedores e clientes)
agrupados por CNPJ raiz para matching semantico.

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_financial_entity_embeddings.py

Verificar:
    python scripts/migrations/criar_tabela_financial_entity_embeddings.py --verificar
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


def criar_tabela():
    """Cria tabela financial_entity_embeddings."""
    app = create_app()
    with app.app_context():
        engine = db.engine

        # ============================================
        # BEFORE: Verificar estado atual
        # ============================================
        print("=" * 60)
        print("CRIANDO TABELA financial_entity_embeddings")
        print("=" * 60)

        with engine.connect() as conn:
            # Verificar pgvector
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            pgvector_available = result.fetchone() is not None
            print(f"\n[INFO] pgvector disponivel: {pgvector_available}")

            # Verificar se tabela ja existe
            result = conn.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'financial_entity_embeddings'
            """))
            exists = result.fetchone() is not None
            print(f"[INFO] Tabela ja existe: {exists}")

            if exists:
                count = conn.execute(text(
                    "SELECT COUNT(*) FROM financial_entity_embeddings"
                )).scalar()
                print(f"[INFO] Registros existentes: {count}")

        embedding_type = "vector(1024)" if pgvector_available else "TEXT"

        # ============================================
        # EXECUTE: Criar tabela
        # ============================================
        print(f"\n[1/3] Criando tabela (embedding={embedding_type})...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS financial_entity_embeddings (
                id SERIAL PRIMARY KEY,

                -- Identificacao
                entity_type VARCHAR(20) NOT NULL,
                cnpj_raiz VARCHAR(8) NOT NULL,
                cnpj_completo VARCHAR(20),
                nome TEXT NOT NULL,
                nomes_alternativos TEXT,
                texto_embedado TEXT NOT NULL,

                -- Embedding
                embedding {embedding_type},
                model_used VARCHAR(50),

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),

                -- Constraint unica
                CONSTRAINT uq_fin_entity_type_cnpj UNIQUE (entity_type, cnpj_raiz)
            );
        """, "Tabela financial_entity_embeddings")

        print("\n[2/3] Criando indices...")
        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_fin_entity_type
                ON financial_entity_embeddings(entity_type);
        """, "Indice entity_type")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_fin_entity_cnpj_raiz
                ON financial_entity_embeddings(cnpj_raiz);
        """, "Indice cnpj_raiz")

        if pgvector_available:
            print("\n[3/3] Criando indice IVFFlat...")
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_fin_entity_emb_cosine
                    ON financial_entity_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 30);
            """, "Indice IVFFlat (pode falhar se tabela vazia)")
        else:
            print("\n[3/3] pgvector indisponivel, sem indice IVFFlat")

        # ============================================
        # AFTER: Verificar resultado
        # ============================================
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'financial_entity_embeddings'
            """))
            criada = result.fetchone() is not None

        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"Tabela criada: {'SIM' if criada else 'NAO'}")
        print(f"Tipo embedding: {embedding_type}")
        print("=" * 60)


def verificar_tabela():
    """Verifica se a tabela existe e mostra estrutura."""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFICANDO financial_entity_embeddings")
        print("=" * 60)

        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'financial_entity_embeddings'
                ORDER BY ordinal_position;
            """))
            rows = result.fetchall()

            if rows:
                print("\nColunas:")
                for row in rows:
                    print(f"   {row[0]}: {row[1]} (nullable={row[2]})")

                count = conn.execute(text(
                    "SELECT COUNT(*) FROM financial_entity_embeddings"
                )).scalar()
                print(f"\nRegistros: {count}")

                count_emb = conn.execute(text(
                    "SELECT COUNT(*) FROM financial_entity_embeddings WHERE embedding IS NOT NULL"
                )).scalar()
                print(f"Com embedding: {count_emb}")

                # Por tipo
                result = conn.execute(text("""
                    SELECT entity_type, COUNT(*)
                    FROM financial_entity_embeddings
                    GROUP BY entity_type
                    ORDER BY entity_type
                """))
                tipos = result.fetchall()
                if tipos:
                    print("\nPor tipo:")
                    for row in tipos:
                        print(f"   {row[0]}: {row[1]}")
            else:
                print("\nTABELA NAO ENCONTRADA")

            # Indices
            print("\nIndices:")
            result = conn.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'financial_entity_embeddings'
                ORDER BY indexname;
            """))
            for row in result.fetchall():
                print(f"   {row[0]}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Criar tabela financial_entity_embeddings'
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
