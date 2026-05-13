"""Migration HORA 41: campo `autopropelido` (Boolean) em hora_modelo.

Mudancas:
  1. hora_modelo -> +autopropelido BOOLEAN NOT NULL DEFAULT TRUE

Semantica:
  - TRUE  -> "Autopropelido" (bicicleta eletrica, Res. CONTRAN 996/2023):
            dispensa CNH e licenciamento; garantia 6m + 6m motor/bateria.
  - FALSE -> "Ciclomotor" — exige CNH e emplacamento; garantia 3m + 9m
            motor/bateria; ATPV emitido em ate 15 dias uteis da NF.

Default TRUE porque a HORA comercializa predominantemente bicicletas
eletricas; operador ajusta os ciclomotores caso a caso na tela de
edicao do modelo.

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_41_modelo_autopropelido.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_ALTER_MODELO = [
    "ALTER TABLE hora_modelo "
    "ADD COLUMN IF NOT EXISTS autopropelido BOOLEAN NOT NULL DEFAULT TRUE;",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        cols_antes = {c['name'] for c in inspector.get_columns('hora_modelo')}
        print('Estado antes:')
        print(f'  hora_modelo.autopropelido? {"autopropelido" in cols_antes}')

        with db.engine.begin() as conn:
            for sql in SQL_ALTER_MODELO:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        cols_depois = {c['name'] for c in inspector.get_columns('hora_modelo')}

        print('\nEstado depois:')
        print(f'  hora_modelo.autopropelido? {"autopropelido" in cols_depois}')

        if 'autopropelido' not in cols_depois:
            print('\nERRO: coluna autopropelido nao foi criada.')
            sys.exit(1)

        # Conta quantos modelos ficaram com TRUE (todos, por causa do DEFAULT).
        with db.engine.begin() as conn:
            total = conn.execute(
                text('SELECT COUNT(*) FROM hora_modelo')
            ).scalar() or 0
            autop_count = conn.execute(
                text('SELECT COUNT(*) FROM hora_modelo WHERE autopropelido IS TRUE')
            ).scalar() or 0

        print(
            f'\nModelos: {total} total | {autop_count} marcados autopropelido=TRUE '
            f'(default — revise os ciclomotores em /hora/modelos).'
        )
        print('\nMigration HORA 41 concluida com sucesso.')


if __name__ == '__main__':
    main()
