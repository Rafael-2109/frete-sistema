"""Migration HORA 59: Custo de peca + snapshot do custo no item de venda.

Adiciona:
  1. hora_peca.custo                 (custo de aquisicao padrao da peca).
  2. hora_venda_item_peca.custo_unitario (snapshot do custo na venda).

Motivacao: o preview da NF (venda_preview_service) passa a calcular a margem
usando o CUSTO real da peca — em brindes (antes usavam preco_venda_padrao como
proxy) e em pecas vendidas (antes nao tinham o custo descontado da margem).

Idempotente — pode rodar 2x (ADD COLUMN IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_59_peca_custo.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_peca "
    "ADD COLUMN IF NOT EXISTS custo NUMERIC(15, 2) NOT NULL DEFAULT 0;",
    "ALTER TABLE hora_venda_item_peca "
    "ADD COLUMN IF NOT EXISTS custo_unitario NUMERIC(15, 2) NOT NULL DEFAULT 0;",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        cols_peca = {c['name'] for c in inspector.get_columns('hora_peca')}
        cols_item = {c['name'] for c in inspector.get_columns('hora_venda_item_peca')}
        print('Estado antes:')
        print(f'  hora_peca.custo? {"custo" in cols_peca}')
        print(f'  hora_venda_item_peca.custo_unitario? {"custo_unitario" in cols_item}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        cols_peca = {c['name'] for c in inspector.get_columns('hora_peca')}
        cols_item = {c['name'] for c in inspector.get_columns('hora_venda_item_peca')}
        print('\nEstado depois:')
        print(f'  hora_peca.custo? {"custo" in cols_peca}')
        print(f'  hora_venda_item_peca.custo_unitario? {"custo_unitario" in cols_item}')

        ok = 'custo' in cols_peca and 'custo_unitario' in cols_item
        if not ok:
            print('\nERRO: migration incompleta.')
            sys.exit(1)
        print('\nMigration HORA 59 concluida com sucesso.')


if __name__ == '__main__':
    main()
