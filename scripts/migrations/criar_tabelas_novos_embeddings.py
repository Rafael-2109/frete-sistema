"""
Migration: Criar tabelas de embeddings para novos dominios.

Cria:
- Tabela sql_template_embeddings (few-shot SQL templates)
- Tabela payment_category_embeddings (classificacao de pagamentos)
- Tabela devolucao_reason_embeddings (motivos de devolucao)
- Tabela carrier_embeddings (transportadoras)

Pre-requisito: pgvector ja instalado (por criar_tabelas_embeddings.py).

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_tabelas_novos_embeddings.py

Verificar:
    python scripts/migrations/criar_tabelas_novos_embeddings.py --verificar
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


NOVAS_TABELAS = [
    'sql_template_embeddings',
    'payment_category_embeddings',
    'devolucao_reason_embeddings',
    'carrier_embeddings',
]


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


def _pgvector_available(engine):
    """Verifica se pgvector esta instalado."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
        ))
        return result.fetchone() is not None


def criar_tabelas():
    """Cria as 4 novas tabelas de embeddings."""
    app = create_app()
    with app.app_context():
        engine = db.engine

        # ============================================
        # BEFORE: Verificar estado atual
        # ============================================
        print("=" * 60)
        print("CRIANDO TABELAS DE EMBEDDINGS — NOVOS DOMINIOS")
        print("=" * 60)

        pgvector = _pgvector_available(engine)
        embedding_type = "vector(1024)" if pgvector else "TEXT"
        print(f"\n[INFO] pgvector: {'SIM' if pgvector else 'NAO (fallback TEXT)'}")
        print(f"[INFO] Tipo embedding: {embedding_type}")

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = ANY(:tables)
                ORDER BY table_name;
            """), {"tables": NOVAS_TABELAS})
            existing = [row[0] for row in result.fetchall()]
            print(f"[INFO] Tabelas existentes: {existing or 'nenhuma'}")

        # ============================================
        # [1/4] sql_template_embeddings
        # ============================================
        print(f"\n[1/4] Criando tabela sql_template_embeddings...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS sql_template_embeddings (
                id SERIAL PRIMARY KEY,
                question_text TEXT NOT NULL,
                sql_text TEXT NOT NULL,
                tables_used TEXT,
                execution_count INTEGER NOT NULL DEFAULT 1,
                last_used_at TIMESTAMP,
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                content_hash VARCHAR(32),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """, "Tabela sql_template_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_sqlt_content_hash
                ON sql_template_embeddings(content_hash);
        """, "Indice content_hash")

        if pgvector:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_sqlt_emb_cosine
                    ON sql_template_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
            """, "Indice IVFFlat sql_templates (pode falhar se tabela vazia)")

        # ============================================
        # [2/4] payment_category_embeddings
        # ============================================
        print(f"\n[2/4] Criando tabela payment_category_embeddings...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS payment_category_embeddings (
                id SERIAL PRIMARY KEY,
                category_name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                examples TEXT,
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """, "Tabela payment_category_embeddings")

        if pgvector:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_paycat_emb_cosine
                    ON payment_category_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 5);
            """, "Indice IVFFlat payment_categories (pode falhar se tabela vazia)")

        # ============================================
        # [3/4] devolucao_reason_embeddings
        # ============================================
        print(f"\n[3/4] Criando tabela devolucao_reason_embeddings...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS devolucao_reason_embeddings (
                id SERIAL PRIMARY KEY,
                nf_devolucao_linha_id INTEGER,
                descricao_text TEXT NOT NULL,
                motivo_classificado VARCHAR(50),
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                content_hash VARCHAR(32),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """, "Tabela devolucao_reason_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_dre_motivo
                ON devolucao_reason_embeddings(motivo_classificado);
        """, "Indice motivo_classificado")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_dre_content_hash
                ON devolucao_reason_embeddings(content_hash);
        """, "Indice content_hash")

        if pgvector:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_dre_emb_cosine
                    ON devolucao_reason_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
            """, "Indice IVFFlat devolucao_reasons (pode falhar se tabela vazia)")

        # ============================================
        # [4/4] carrier_embeddings
        # ============================================
        print(f"\n[4/4] Criando tabela carrier_embeddings...")

        _execute_safe(engine, f"""
            CREATE TABLE IF NOT EXISTS carrier_embeddings (
                id SERIAL PRIMARY KEY,
                carrier_name TEXT NOT NULL,
                cnpj VARCHAR(20),
                aliases TEXT,
                texto_embedado TEXT NOT NULL,
                embedding {embedding_type},
                model_used VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT uq_carrier_name UNIQUE (carrier_name)
            );
        """, "Tabela carrier_embeddings")

        _execute_safe(engine, """
            CREATE INDEX IF NOT EXISTS idx_carrier_name
                ON carrier_embeddings(carrier_name);
        """, "Indice carrier_name")

        if pgvector:
            _execute_safe(engine, """
                CREATE INDEX IF NOT EXISTS idx_carrier_emb_cosine
                    ON carrier_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
            """, "Indice IVFFlat carriers (pode falhar se tabela vazia)")

        # ============================================
        # AFTER: Verificar resultado
        # ============================================
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = ANY(:tables)
                ORDER BY table_name;
            """), {"tables": NOVAS_TABELAS})
            tabelas = [row[0] for row in result.fetchall()]

        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"pgvector: {'SIM' if pgvector else 'NAO (fallback TEXT)'}")
        print(f"Tabelas criadas: {tabelas}")
        print(f"Esperado: {len(NOVAS_TABELAS)} | Criadas: {len(tabelas)}")
        print("=" * 60)


def verificar_tabelas():
    """Verifica se as tabelas existem e mostra estrutura."""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFICANDO TABELAS DE EMBEDDINGS — NOVOS DOMINIOS")
        print("=" * 60)

        with db.engine.connect() as conn:
            for tabela in NOVAS_TABELAS:
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
                    WHERE tablename = ANY(:tables)
                    ORDER BY tablename, indexname;
                """), {"tables": NOVAS_TABELAS})
                for row in result.fetchall():
                    print(f"   {row[0]}")
            except Exception as e:
                print(f"   ERRO: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas de embeddings — novos dominios')
    parser.add_argument('--verificar', action='store_true', help='Apenas verifica se as tabelas existem')

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    else:
        criar_tabelas()
        verificar_tabelas()
