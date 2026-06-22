"""Migration: coluna `valor_base` em carvia_emissao_cte_complementar + backfill.

Logica SQL em 2026_06_22_carvia_emissao_cte_comp_valor_base.sql (fonte de verdade).
Idempotente. Uso: python scripts/migrations/2026_06_22_carvia_emissao_cte_comp_valor_base.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
SQL_FILE = os.path.join(
    os.path.dirname(__file__),
    '2026_06_22_carvia_emissao_cte_comp_valor_base.sql',
)


def _tem_coluna():
    return (db.session.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = 'carvia_emissao_cte_complementar' "
        "AND column_name = 'valor_base'"
    )).scalar() or 0) > 0


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Coluna valor_base ANTES:', 'EXISTE' if _tem_coluna() else 'ausente')

        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        print('Coluna valor_base DEPOIS:', 'EXISTE' if _tem_coluna() else 'ausente')
        assert _tem_coluna(), (
            'Migration nao criou a coluna valor_base em carvia_emissao_cte_complementar'
        )

        preenchidas = db.session.execute(text(
            "SELECT COUNT(*) FROM carvia_emissao_cte_complementar WHERE valor_base IS NOT NULL"
        )).scalar() or 0
        print(f'OK — coluna valor_base aplicada. Emissoes com valor_base (pos-backfill): {preenchidas}.')


if __name__ == '__main__':
    main()
