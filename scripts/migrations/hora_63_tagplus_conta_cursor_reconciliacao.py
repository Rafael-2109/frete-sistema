"""Migration HORA 63: cursor do numero-walk em hora_tagplus_conta.

Adiciona `ultimo_pedido_numero_reconciliado` (INTEGER, NULL) — maior numero de
pedido ja varrido pela descoberta reversa (numero-walk +3, Fase 3 da sync
HORA<->TagPlus). Persistido para o scheduler retomar de onde parou. Idempotente
(ADD COLUMN IF NOT EXISTS). Sem indice (conta e singleton, 1 linha).

Uso:
    # Local:
    python scripts/migrations/hora_63_tagplus_conta_cursor_reconciliacao.py
    # PROD (Render):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/hora_63_tagplus_conta_cursor_reconciliacao.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

COLUNA = 'ultimo_pedido_numero_reconciliado'

SQL_DDL = [
    f"ALTER TABLE hora_tagplus_conta ADD COLUMN IF NOT EXISTS {COLUNA} INTEGER",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_tagplus_conta')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_tagplus_conta.{COLUNA} existe? {COLUNA in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = COLUNA in _colunas()
        print('\nEstado depois:')
        print(f'  hora_tagplus_conta.{COLUNA} existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 63 concluida com sucesso.')


if __name__ == '__main__':
    main()
