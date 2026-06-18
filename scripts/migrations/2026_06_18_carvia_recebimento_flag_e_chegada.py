"""Migration: flag acesso_recebimento_carvia (usuarios) + data_prevista_chegada (carvia_coletas).

Logica SQL em 2026_06_18_carvia_recebimento_flag_e_chegada.sql (fonte de verdade). Idempotente.
Uso: python scripts/migrations/2026_06_18_carvia_recebimento_flag_e_chegada.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
ESPERADO = {
    'usuarios': ['acesso_recebimento_carvia'],
    'carvia_coletas': ['data_prevista_chegada'],
}
SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_18_carvia_recebimento_flag_e_chegada.sql')


def _faltando(insp):
    faltam = {}
    for tabela, cols in ESPERADO.items():
        existentes = {c['name'] for c in insp.get_columns(tabela)}
        ausentes = [c for c in cols if c not in existentes]
        if ausentes:
            faltam[tabela] = ausentes
    return faltam


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Faltando ANTES:', _faltando(inspect(db.engine)))
        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()
        faltando = _faltando(inspect(db.engine))
        print('Faltando DEPOIS:', faltando)
        assert not faltando, f'Migration nao aplicou: {faltando}'
        print('OK — acesso_recebimento_carvia + data_prevista_chegada aplicadas.')


if __name__ == '__main__':
    main()
