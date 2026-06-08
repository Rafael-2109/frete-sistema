"""Migration S1: tabela table_catalog_embeddings + indices (HNSW cosine).

Subsistema S1 (progressive disclosure) do pacote text-to-sql. Cria a tabela que
guarda 1 embedding por tabela do catalog.json, consumida pela tool
buscar_tabelas (camada semantica, fundida com a busca textual deterministica).

Conforme regra ~/.claude/CLAUDE.md (DOIS artefatos: .py + .sql).
Python valida pgvector presente + cria estrutura via SQL idempotente.

Uso local:
    source .venv/bin/activate
    python scripts/migrations/2026_06_07_table_catalog_embeddings.py

Uso PROD (Render Shell):
    psql $DATABASE_URL -f scripts/migrations/2026_06_07_table_catalog_embeddings.sql
"""

import sys
from pathlib import Path

# Garante imports a partir da raiz do projeto
# (regra memory/feedback_migration_sys_path.md)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def verify_pgvector():
    """Verifica que extensao pgvector esta instalada."""
    result = db.session.execute(db.text(
        "SELECT extname FROM pg_extension WHERE extname='vector'"
    )).first()
    if not result:
        raise RuntimeError(
            "Extensao pgvector NAO instalada. Rode primeiro: "
            "CREATE EXTENSION vector;"
        )


def check_table_exists() -> bool:
    result = db.session.execute(db.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'table_catalog_embeddings'"
    )).first()
    return result is not None


def main():
    app = create_app()
    with app.app_context():
        verify_pgvector()
        before = check_table_exists()
        print(f"[BEFORE] tabela existe: {before}")

        # SQL é todo idempotente (IF NOT EXISTS) — executa SEMPRE p/ garantir
        # tabela + indices (inclusive o HNSW), mesmo que a tabela ja exista sem
        # os indices (ex: criada por db.create_all, que nao cria HNSW).
        # Remove linhas de comentario ANTES do split p/ nao perder o statement
        # que vier logo apos um comentario.
        sql_path = Path(__file__).parent / "2026_06_07_table_catalog_embeddings.sql"
        sql = sql_path.read_text()
        sql_sem_comentarios = "\n".join(
            line for line in sql.splitlines() if not line.strip().startswith("--")
        )
        for statement in sql_sem_comentarios.split(";"):
            stmt = statement.strip()
            if stmt:
                db.session.execute(db.text(stmt))
        db.session.commit()
        print("[CREATE] tabela + indices garantidos via SQL idempotente")

        after = check_table_exists()
        print(f"[AFTER] tabela existe: {after}")

        idx = db.session.execute(db.text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'table_catalog_embeddings' "
            "AND indexname = 'ix_table_catalog_embed_cosine'"
        )).first()
        print(f"[INDEX] HNSW cosine: {'OK' if idx else 'FALTA'}")

        assert after, "Migration FALHOU — tabela nao criada"
        assert idx, "Indice HNSW cosine nao criado"
        print("[OK] Migration S1 table_catalog_embeddings concluida.")


if __name__ == "__main__":
    main()
