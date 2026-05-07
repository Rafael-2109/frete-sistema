"""Migration HORA 36: campo `consumidor_final` (Boolean) em hora_venda.

Mudancas:
  1. hora_venda -> +consumidor_final BOOLEAN (nullable, default NULL)

Semantica:
  - NULL  -> nao informado pelo operador; payload_builder infere via CPF/CNPJ.
  - TRUE  -> NFe sai com `consumidor_final: true` (default para PF / B2C).
  - FALSE -> NFe sai com `consumidor_final: false` (revenda PJ).

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_36_consumidor_final.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_ALTER_VENDA = [
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS consumidor_final BOOLEAN;",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        cols_antes = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('Estado antes:')
        print(f'  hora_venda.consumidor_final? {"consumidor_final" in cols_antes}')

        with db.engine.begin() as conn:
            for sql in SQL_ALTER_VENDA:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        cols_depois = {c['name'] for c in inspector.get_columns('hora_venda')}

        print('\nEstado depois:')
        print(f'  hora_venda.consumidor_final? {"consumidor_final" in cols_depois}')

        if 'consumidor_final' not in cols_depois:
            print('\nERRO: coluna consumidor_final nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 36 concluida com sucesso.')


if __name__ == '__main__':
    main()
