"""Migration HORA 47: Recibo Simples (documento NAO-fiscal) de pecas/oficina.

Roadmap #1b. Cria:
  1. SEQUENCE hora_recibo_numero_seq (numeracao sequencial GLOBAL).
  2. TABLE hora_recibo (header do recibo; PDF no S3; coexiste com NFe).

Idempotente — pode rodar 2x (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_47_recibo.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "CREATE SEQUENCE IF NOT EXISTS hora_recibo_numero_seq START 1;",
    """
    CREATE TABLE IF NOT EXISTS hora_recibo (
        id              SERIAL PRIMARY KEY,
        numero          INTEGER NOT NULL UNIQUE,
        venda_id        INTEGER NOT NULL REFERENCES hora_venda (id),
        valor_total     NUMERIC(15, 2) NOT NULL DEFAULT 0,
        pdf_s3_key      VARCHAR(500),
        status          VARCHAR(20) NOT NULL DEFAULT 'EMITIDO',
        emitido_em      TIMESTAMP NOT NULL,
        emitido_por     VARCHAR(100),
        cancelado_em    TIMESTAMP,
        cancelado_por   VARCHAR(100),
        cancelamento_motivo VARCHAR(500)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_hora_recibo_venda_id ON hora_recibo (venda_id);",
    "CREATE INDEX IF NOT EXISTS idx_hora_recibo_status ON hora_recibo (status);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tabelas = set(inspector.get_table_names())
        print('Estado antes:')
        print(f'  hora_recibo existe? {"hora_recibo" in tabelas}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        tabelas = set(inspector.get_table_names())
        print('\nEstado depois:')
        print(f'  hora_recibo existe? {"hora_recibo" in tabelas}')

        if 'hora_recibo' not in tabelas:
            print('\nERRO: tabela hora_recibo nao criada.')
            sys.exit(1)

        with db.engine.begin() as conn:
            seq_ok = conn.execute(text(
                "SELECT 1 FROM pg_class WHERE relkind='S' AND relname='hora_recibo_numero_seq'"
            )).scalar()
        print(f'  sequence hora_recibo_numero_seq existe? {bool(seq_ok)}')

        print('\nMigration HORA 47 concluida com sucesso.')


if __name__ == '__main__':
    main()
