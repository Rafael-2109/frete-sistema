"""Migration: tabela sped_ecd_rule_embeddings + indices.

Conforme regra ~/.claude/CLAUDE.md (DOIS artefatos: .py + .sql).
Python valida pgvector presente + cria estrutura via SQL idempotente.

Uso local:
    source .venv/bin/activate
    python scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.py

Uso PROD (Render Shell):
    psql $DATABASE_URL -f scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.sql
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
        "WHERE table_name = 'sped_ecd_rule_embeddings'"
    )).first()
    return result is not None


def main():
    app = create_app()
    with app.app_context():
        verify_pgvector()
        before = check_table_exists()
        print(f"[BEFORE] tabela existe: {before}")

        if not before:
            sql_path = Path(__file__).parent / "2026_05_16_sped_ecd_rule_embeddings.sql"
            sql = sql_path.read_text()
            # Executar comando por comando (alguns drivers preferem)
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt and not stmt.startswith("--"):
                    db.session.execute(db.text(stmt))
            db.session.commit()
            print("[CREATE] tabela + indices criados via SQL")

        after = check_table_exists()
        print(f"[AFTER] tabela existe: {after}")

        idx = db.session.execute(db.text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'sped_ecd_rule_embeddings' "
            "AND indexname = 'ix_sped_rule_embed_cosine'"
        )).first()
        print(f"[INDEX] HNSW cosine: {'OK' if idx else 'FALTA'}")

        assert after, "Migration FALHOU — tabela nao criada"
        assert idx, "Indice HNSW cosine nao criado"


if __name__ == "__main__":
    main()
