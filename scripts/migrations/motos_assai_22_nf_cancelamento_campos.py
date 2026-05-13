"""Migration 22: adiciona 3 colunas de cancelamento em assai_nf_qpa.

Spec: §9.4
Plano: Task 5
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_22_nf_cancelamento_campos.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'assai_nf_qpa' "
            "AND column_name IN ('cancelada_em', 'cancelada_por_id', 'motivo_cancelamento')"
        )).scalar()
        print(f'[before] colunas existentes: {result_before}/3')

        db.session.execute(text(sql))
        db.session.commit()

        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'assai_nf_qpa' "
            "AND column_name IN ('cancelada_em', 'cancelada_por_id', 'motivo_cancelamento')"
        )).scalar()
        print(f'[after] colunas existentes: {result_after}/3')

        if result_after != 3:
            sys.exit(1)
        print('[ok] Migration 22 aplicada com sucesso')


if __name__ == '__main__':
    main()
