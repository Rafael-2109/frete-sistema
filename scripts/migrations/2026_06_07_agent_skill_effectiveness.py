"""Cria a tabela agent_skill_effectiveness (Fase 1 aprendizado por efetividade)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app import create_app, db
from sqlalchemy import text, inspect

SQL = open(os.path.join(os.path.dirname(__file__),
           "2026_06_07_agent_skill_effectiveness.sql")).read()


def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        before = 'agent_skill_effectiveness' in insp.get_table_names()
        print(f"[before] tabela existe? {before}")
        for stmt in [s.strip() for s in SQL.split(';') if s.strip()]:
            db.session.execute(text(stmt))
        db.session.commit()
        insp = inspect(db.engine)
        after = 'agent_skill_effectiveness' in insp.get_table_names()
        print(f"[after] tabela existe? {after}")
        assert after, "tabela nao foi criada"


if __name__ == "__main__":
    main()
