"""Migration 26: cria assai_nf_qpa_item_vinculo_historico.

Spec: §2.1
Plano: Task 7
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_26_vinculo_historico.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_nf_qpa_item_vinculo_historico'"
        )).scalar()
        print(f'[before] tabela existe: {result_before}/1')

        db.session.execute(text(sql))
        db.session.commit()

        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_nf_qpa_item_vinculo_historico'"
        )).scalar()
        print(f'[after] tabela existe: {result_after}/1')

        if result_after != 1:
            sys.exit(1)
        print('[ok] Migration 26 aplicada com sucesso')


if __name__ == '__main__':
    main()
