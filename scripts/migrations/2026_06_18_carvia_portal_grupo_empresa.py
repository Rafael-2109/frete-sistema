"""Migration: carvia_portal_usuarios.grupo_empresa (Portal do Cliente — vinculo por grupo).

Logica SQL em 2026_06_18_carvia_portal_grupo_empresa.sql (fonte de verdade). Idempotente.
Uso: python scripts/migrations/2026_06_18_carvia_portal_grupo_empresa.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_18_carvia_portal_grupo_empresa.sql')


def _tem_coluna():
    cols = {c['name'] for c in inspect(db.engine).get_columns('carvia_portal_usuarios')}
    return 'grupo_empresa' in cols


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('grupo_empresa ANTES:', 'EXISTE' if _tem_coluna() else 'ausente')
        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()
        print('grupo_empresa DEPOIS:', 'EXISTE' if _tem_coluna() else 'ausente')
        assert _tem_coluna(), 'Migration nao criou grupo_empresa'
        print('OK — carvia_portal_usuarios.grupo_empresa aplicada.')


if __name__ == '__main__':
    main()
