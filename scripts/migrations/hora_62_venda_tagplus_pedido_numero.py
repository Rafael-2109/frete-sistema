"""Migration HORA 62: coluna tagplus_pedido_numero em hora_venda.

Adiciona `tagplus_pedido_numero` (INTEGER, NULL) — numero VISIVEL do pedido no
TagPlus, distinto do `tagplus_pedido_id` (ID interno). Idempotente
(ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS).

Uso:
    # Local:
    python scripts/migrations/hora_62_venda_tagplus_pedido_numero.py
    # PROD (Render):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/hora_62_venda_tagplus_pedido_numero.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS tagplus_pedido_numero INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_hora_venda_tagplus_pedido_numero "
    "ON hora_venda (tagplus_pedido_numero)",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_venda')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_venda.tagplus_pedido_numero existe? {"tagplus_pedido_numero" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = 'tagplus_pedido_numero' in _colunas()
        print('\nEstado depois:')
        print(f'  hora_venda.tagplus_pedido_numero existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 62 concluida com sucesso.')


if __name__ == '__main__':
    main()
