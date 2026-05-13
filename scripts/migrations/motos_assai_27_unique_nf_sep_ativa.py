"""Migration 27: UNIQUE parcial em assai_nf_qpa(separacao_id) WHERE status_match != 'CANCELADA'.

Spec: §2.2 (A3)
Plano: Task 8
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_27_unique_nf_sep_ativa.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        # Pre-check
        violacoes = db.session.execute(text(
            "SELECT COUNT(*) FROM (SELECT separacao_id FROM assai_nf_qpa "
            "WHERE separacao_id IS NOT NULL AND status_match != 'CANCELADA' "
            "GROUP BY separacao_id HAVING COUNT(*) > 1) sub"
        )).scalar() or 0
        if violacoes > 0:
            print(f'[ABORT] {violacoes} seps com >1 NF ativa. Resolver antes.')
            sys.exit(1)

        db.session.execute(text(sql))
        db.session.commit()
        print('[ok] Migration 27 aplicada com sucesso')


if __name__ == '__main__':
    main()
