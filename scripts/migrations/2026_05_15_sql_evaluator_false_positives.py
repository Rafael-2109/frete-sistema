"""
Migration: tabela sql_evaluator_false_positives (T7 — Auto few-shot).

Armazena pares (SQL_rejeitada, motivo) confirmados como falsos positivos do
Haiku evaluator. Em queries futuras, busca semantica por cosine > 0.85 injeta
contra-exemplos no prompt do evaluator para evitar repeticao do mesmo erro.

DESIGN:
- status='pending_review' por padrao (NAO injeta automaticamente)
- Promocao para 'active' requer review humano (D8 dialogue ou admin manual)
- Soft delete: status='rejected', nao DELETE fisico
- Linkado ao agent_improvement_dialogue via improvement_key (sem FK fisica)

Pre-requisito: extensao 'vector' (pgvector) ja instalada (usada por
sql_template_embeddings, agent_memory_embeddings, etc.).

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_15_sql_evaluator_false_positives.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script e executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


TABELA = "sql_evaluator_false_positives"


def verificar_tabela() -> bool:
    """Retorna True se a tabela ja existe."""
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :t
    """), {"t": TABELA}).scalar()
    return bool(result)


def verificar_pgvector() -> bool:
    """Retorna True se extensao vector esta instalada."""
    result = db.session.execute(text("""
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    """)).scalar()
    return bool(result)


def listar_indices() -> list:
    """Lista indices criados na tabela."""
    result = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = :t
        ORDER BY indexname
    """), {"t": TABELA}).fetchall()
    return [r[0] for r in result]


def main() -> int:
    app = create_app()
    with app.app_context():
        # Pre-check: pgvector disponivel?
        if not verificar_pgvector():
            print("[erro] Extensao 'vector' (pgvector) nao instalada — abortando.")
            print("       Solucao: CREATE EXTENSION vector; (executar como superuser)")
            return 2

        existed_before = verificar_tabela()
        print(f"[before] {TABELA} exists: {existed_before}")
        if existed_before:
            print(f"[before] indices: {listar_indices()}")

        print(f"[info] Criando tabela {TABELA} (T7 — Auto few-shot)...")

        db.session.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TABELA} (
                id                   SERIAL PRIMARY KEY,
                sql_text             TEXT NOT NULL,
                rejection_reason     TEXT NOT NULL,
                rejection_category   VARCHAR(50),
                texto_embedado       TEXT NOT NULL,
                embedding            vector(1024),
                model_used           VARCHAR(50),
                content_hash         VARCHAR(64) NOT NULL,
                improvement_key      VARCHAR(100),
                status               VARCHAR(20) NOT NULL DEFAULT 'pending_review',
                confirmed_by_user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                confirmed_at         TIMESTAMP NOT NULL DEFAULT NOW(),
                reviewed_by_user_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                reviewed_at          TIMESTAMP,
                times_referenced     INTEGER NOT NULL DEFAULT 0,
                last_referenced_at   TIMESTAMP,
                created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),

                CONSTRAINT sql_eval_falses_status_chk
                    CHECK (status IN ('pending_review', 'active', 'rejected'))
            )
        """))

        # Index unico em content_hash evita duplicacao
        db.session.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sql_eval_falses_content_hash
                ON {TABELA} (content_hash)
        """))

        # Parcial 'active' (hot path no Evaluator)
        db.session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_active_status
                ON {TABELA} (status)
                WHERE status = 'active'
        """))

        # improvement_key (lookups por D8)
        db.session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_imp_key
                ON {TABELA} (improvement_key)
                WHERE improvement_key IS NOT NULL
        """))

        # Review queue (UI admin)
        db.session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_pending
                ON {TABELA} (created_at DESC)
                WHERE status = 'pending_review'
        """))

        # IVFFlat embedding (lists=10 — tabela <500 rows estimada)
        db.session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_embedding
                ON {TABELA}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 10)
        """))

        # Comments para documentacao schema
        db.session.execute(text(f"""
            COMMENT ON TABLE {TABELA} IS
                'T7 — Falsos positivos confirmados do Haiku evaluator. '
                'Status=active injetado como contra-exemplo. '
                'Status=pending_review aguarda revisao humana.'
        """))
        db.session.execute(text(f"""
            COMMENT ON COLUMN {TABELA}.content_hash IS
                'sha256(sql_text + rejection_reason) — evita duplicacao'
        """))
        db.session.execute(text(f"""
            COMMENT ON COLUMN {TABELA}.improvement_key IS
                'Correlaciona com agent_improvement_dialogue.suggestion_key (sem FK fisica)'
        """))
        db.session.execute(text(f"""
            COMMENT ON COLUMN {TABELA}.times_referenced IS
                'Quantas vezes foi injetado como contra-exemplo no Evaluator'
        """))

        db.session.commit()

        # Verificacao after
        if not verificar_tabela():
            print(f"[erro] Tabela {TABELA} nao aparece em information_schema apos commit.")
            return 1

        indices = listar_indices()
        expected_indices = {
            f"{TABELA}_pkey",
            "idx_sql_eval_falses_content_hash",
            "idx_sql_eval_falses_active_status",
            "idx_sql_eval_falses_imp_key",
            "idx_sql_eval_falses_pending",
            "idx_sql_eval_falses_embedding",
        }
        missing = expected_indices - set(indices)
        if missing:
            print(f"[erro] Indices faltando: {missing}")
            return 1

        print(f"[after] {TABELA} indices: {indices}")

        count = db.session.execute(text(f"SELECT COUNT(*) FROM {TABELA}")).scalar()
        print(f"[after] {TABELA} rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela ja existia, schema valido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
