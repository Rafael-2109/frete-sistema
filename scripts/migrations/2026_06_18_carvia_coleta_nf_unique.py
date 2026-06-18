"""Migration: UNIQUE(carvia_nf_id) em carvia_coleta_nfs (fix do redesign stream 3).

Logica SQL em 2026_06_18_carvia_coleta_nf_unique.sql (fonte de verdade). Idempotente.
PRE-CHECK: aborta se houver carvia_nf_id duplicado (so deveria ocorrer em base de teste suja).
Uso: python scripts/migrations/2026_06_18_carvia_coleta_nf_unique.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
CONSTRAINT = 'uq_carvia_coleta_nf'
SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_18_carvia_coleta_nf_unique.sql')


def _existe():
    return (db.session.execute(
        text("SELECT COUNT(*) FROM pg_constraint WHERE conname = :c"), {'c': CONSTRAINT}
    ).scalar() or 0) > 0


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Constraint ANTES:', 'EXISTE' if _existe() else 'ausente')

        dups = db.session.execute(text(
            "SELECT carvia_nf_id, COUNT(*) FROM carvia_coleta_nfs "
            "WHERE carvia_nf_id IS NOT NULL GROUP BY carvia_nf_id HAVING COUNT(*) > 1"
        )).fetchall()
        assert not dups, f'carvia_nf_id duplicado impede a UNIQUE — resolver antes: {dups}'

        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        print('Constraint DEPOIS:', 'EXISTE' if _existe() else 'ausente')
        assert _existe(), 'Migration nao criou a constraint uq_carvia_coleta_nf'
        print('OK — UNIQUE(carvia_nf_id) aplicada em carvia_coleta_nfs.')


if __name__ == '__main__':
    main()
