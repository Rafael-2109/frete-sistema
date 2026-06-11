"""Migration: blocos proativos pos-polling Teams (Fase E2 do plano teams-melhorias).

Mudanca:
  teams_tasks -> +proactive_partial_chars INTEGER NOT NULL DEFAULT 0
  (offset de chars da resposta ja entregues via blocos proativos pos-polling;
  a entrega FINAL envia apenas resposta[offset:]. Offset 0 = comportamento
  anterior: resposta completa.)

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/2026_06_11_teams_proactive_partial.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_STATEMENTS = [
    "ALTER TABLE teams_tasks ADD COLUMN IF NOT EXISTS "
    "proactive_partial_chars INTEGER NOT NULL DEFAULT 0;",
]


def _estado(inspector) -> dict:
    cols = {c['name'] for c in inspector.get_columns('teams_tasks')}
    return {
        'teams_tasks.proactive_partial_chars': 'proactive_partial_chars' in cols,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        antes = _estado(inspect(db.engine))
        print('Estado antes:')
        for k, v in antes.items():
            print(f'  {k}? {v}')

        with db.engine.begin() as conn:
            for sql in SQL_STATEMENTS:
                conn.execute(text(sql))

        depois = _estado(inspect(db.engine))
        print('\nEstado depois:')
        for k, v in depois.items():
            print(f'  {k}? {v}')

        if not all(depois.values()):
            print('\nERRO: alguma estrutura nao foi criada.')
            sys.exit(1)
        print('\nOK: migration aplicada.')


if __name__ == '__main__':
    main()
