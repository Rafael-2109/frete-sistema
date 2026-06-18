"""Migration: Portal do Cliente CarVia (usuario externo) — stream 5.

Cria carvia_portal_usuarios + carvia_portal_usuario_cnpjs. Idempotente.
Uso: python scripts/migrations/2026_06_17_carvia_portal_cliente.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
TABELAS = ['carvia_portal_usuarios', 'carvia_portal_usuario_cnpjs']
SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_17_carvia_portal_cliente.sql')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        print('Ja existentes ANTES:', [t for t in TABELAS if insp.has_table(t)])
        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()
        insp = inspect(db.engine)
        faltando = [t for t in TABELAS if not insp.has_table(t)]
        print('Faltando DEPOIS:', faltando)
        assert not faltando, f'Migration nao criou: {faltando}'
        cols = {c['name'] for c in insp.get_columns('carvia_portal_usuarios')}
        assert {'email', 'senha_hash', 'status', 'tipo_escopo', 'cliente_comercial_id'} <= cols
        print('OK — tabelas do portal do cliente criadas.')


if __name__ == '__main__':
    main()
