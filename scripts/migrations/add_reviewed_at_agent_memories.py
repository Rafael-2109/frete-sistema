"""
Migration: Adicionar coluna reviewed_at em agent_memories.

Objetivo: Ciclo de revisao de memorias empresa — rastrear quando conteudo
foi validado pela ultima vez. Memorias sem revisao ha 60+ dias aparecem
no briefing intersessao.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/add_reviewed_at_agent_memories.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def run():
    from app import create_app, db
    from sqlalchemy import text, inspect

    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # ── Before: verificar estado atual ──
        columns = [c['name'] for c in inspector.get_columns('agent_memories')]
        if 'reviewed_at' in columns:
            print("[OK] Coluna 'reviewed_at' ja existe em agent_memories. Nada a fazer.")
            return

        print("[BEFORE] Coluna 'reviewed_at' NAO existe. Executando migration...")

        # ── DDL ──
        db.session.execute(text("""
            ALTER TABLE agent_memories
            ADD COLUMN reviewed_at TIMESTAMP NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_memories_reviewed_at
            ON agent_memories (reviewed_at) WHERE reviewed_at IS NULL
        """))

        db.session.commit()

        # ── After: verificar ──
        inspector = inspect(db.engine)
        columns_after = [c['name'] for c in inspector.get_columns('agent_memories')]
        if 'reviewed_at' in columns_after:
            print("[AFTER] Coluna 'reviewed_at' criada com sucesso.")
        else:
            print("[ERRO] Coluna 'reviewed_at' NAO encontrada apos migration!")
            sys.exit(1)

        # Verificar indice
        indexes = inspector.get_indexes('agent_memories')
        idx_names = [idx['name'] for idx in indexes]
        if 'idx_agent_memories_reviewed_at' in idx_names:
            print("[AFTER] Indice 'idx_agent_memories_reviewed_at' criado com sucesso.")
        else:
            print("[WARN] Indice parcial pode nao aparecer no inspect (comportamento normal do PostgreSQL).")

        print("[DONE] Migration concluida.")


if __name__ == '__main__':
    run()
