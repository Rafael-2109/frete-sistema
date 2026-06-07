"""Migration HORA 48: Brindes de venda (roadmap #36).

Cria a tabela hora_venda_brinde (peca dada de brinde numa venda: custo =
preco_venda_padrao snapshot; NAO cobrado; NAO abate estoque).

Idempotente — pode rodar 2x (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_48_venda_brinde.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS hora_venda_brinde (
        id              SERIAL PRIMARY KEY,
        venda_id        INTEGER NOT NULL REFERENCES hora_venda (id),
        peca_id         INTEGER NOT NULL REFERENCES hora_peca (id),
        qtd             NUMERIC(15, 3) NOT NULL DEFAULT 1,
        custo_unitario  NUMERIC(15, 2) NOT NULL DEFAULT 0,
        custo_total     NUMERIC(15, 2) NOT NULL DEFAULT 0,
        criado_em       TIMESTAMP NOT NULL,
        criado_por      VARCHAR(100)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_hora_venda_brinde_venda_id ON hora_venda_brinde (venda_id);",
    "CREATE INDEX IF NOT EXISTS idx_hora_venda_brinde_peca_id ON hora_venda_brinde (peca_id);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        print('Estado antes:')
        print(f'  hora_venda_brinde existe? {"hora_venda_brinde" in inspector.get_table_names()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        existe = 'hora_venda_brinde' in inspector.get_table_names()
        print('\nEstado depois:')
        print(f'  hora_venda_brinde existe? {existe}')
        if not existe:
            print('\nERRO: tabela hora_venda_brinde nao criada.')
            sys.exit(1)
        print('\nMigration HORA 48 concluida com sucesso.')


if __name__ == '__main__':
    main()
