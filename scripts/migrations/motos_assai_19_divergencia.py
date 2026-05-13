"""Migration 19: cria assai_divergencia.

Spec: §2.1, §7.1
Plano: Task 3
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_19_divergencia.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_divergencia'"
        )).scalar()
        print(f'[before] assai_divergencia existe: {result_before}/1')

        db.session.execute(text(sql))
        db.session.commit()

        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_divergencia'"
        )).scalar()
        print(f'[after] assai_divergencia existe: {result_after}/1')

        if result_after != 1:
            print('[ERROR] migration falhou')
            sys.exit(1)
        print('[ok] Migration 19 aplicada com sucesso')


if __name__ == '__main__':
    main()
