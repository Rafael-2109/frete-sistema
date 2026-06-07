"""Migration HORA 50: fila de aprovacao de desconto (roadmap #28, Fatia 2).

Cria hora_aprovacao_desconto. Idempotente (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_50_aprovacao_desconto.py
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
    CREATE TABLE IF NOT EXISTS hora_aprovacao_desconto (
        id              SERIAL PRIMARY KEY,
        venda_id        INTEGER NOT NULL REFERENCES hora_venda (id),
        status          VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
        detalhe         TEXT,
        solicitado_em   TIMESTAMP NOT NULL,
        solicitado_por  VARCHAR(100),
        decidido_em     TIMESTAMP,
        decidido_por    VARCHAR(100),
        motivo_decisao  VARCHAR(500)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_hora_aprov_desc_venda ON hora_aprovacao_desconto (venda_id);",
    "CREATE INDEX IF NOT EXISTS idx_hora_aprov_desc_status ON hora_aprovacao_desconto (status);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        print('Estado antes:')
        print(f'  hora_aprovacao_desconto? {"hora_aprovacao_desconto" in inspector.get_table_names()}')
        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))
        inspector = inspect(db.engine)
        existe = 'hora_aprovacao_desconto' in inspector.get_table_names()
        print('\nEstado depois:')
        print(f'  hora_aprovacao_desconto? {existe}')
        if not existe:
            print('\nERRO: tabela nao criada.')
            sys.exit(1)
        print('\nMigration HORA 50 concluida com sucesso.')


if __name__ == '__main__':
    main()
