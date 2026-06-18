"""Migration: coluna `uf` em carvia_coleta_nfs + backfill das linhas ja vinculadas.

Logica SQL em 2026_06_18_carvia_coleta_nf_uf.sql (fonte de verdade). Idempotente.
Uso: python scripts/migrations/2026_06_18_carvia_coleta_nf_uf.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_18_carvia_coleta_nf_uf.sql')


def _tem_coluna():
    return (db.session.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = 'carvia_coleta_nfs' AND column_name = 'uf'"
    )).scalar() or 0) > 0


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Coluna uf ANTES:', 'EXISTE' if _tem_coluna() else 'ausente')

        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        print('Coluna uf DEPOIS:', 'EXISTE' if _tem_coluna() else 'ausente')
        assert _tem_coluna(), 'Migration nao criou a coluna uf em carvia_coleta_nfs'

        preenchidas = db.session.execute(text(
            "SELECT COUNT(*) FROM carvia_coleta_nfs WHERE uf IS NOT NULL"
        )).scalar() or 0
        print(f'OK — coluna uf aplicada. Linhas com uf preenchida (pos-backfill): {preenchidas}.')


if __name__ == '__main__':
    main()
