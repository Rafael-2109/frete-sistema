"""A4: adiciona agent_memories.directive_status (candidata|shadow|ativa|despromovida)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text, inspect


def _tem_coluna():
    insp = inspect(db.engine)
    return any(c['name'] == 'directive_status' for c in insp.get_columns('agent_memories'))


def main():
    app = create_app()
    with app.app_context():
        antes = _tem_coluna()
        print(f"[A4 migration] directive_status existe ANTES? {antes}")
        if not antes:
            db.session.execute(text(
                "ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS directive_status VARCHAR(20)"
            ))
            db.session.commit()
        depois = _tem_coluna()
        print(f"[A4 migration] directive_status existe DEPOIS? {depois}")
        assert depois, "Falha: coluna não criada"
        print("[A4 migration] OK")


if __name__ == '__main__':
    main()
