"""Migration HORA 24: tabela hora_tagplus_backfill_job (background backfill).

Cria tabela para rastrear jobs de backfill TagPlus enfileirados em RQ
(queue `hora_backfill`). O worker grava progresso incremental nessa tabela,
permitindo:

  - Tela de detalhe com auto-refresh (operador acompanha sem ficar com aba
    travada por horas).
  - Resiliencia a SSL connection drop / DB timeout — cada NF processada
    persiste estado, retomada eh natural.
  - Historico de execucoes anteriores.

Idempotente — pode rodar 2x sem efeito (CREATE TABLE IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_24_tagplus_backfill_job.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_CREATE = """
CREATE TABLE IF NOT EXISTS hora_tagplus_backfill_job (
    id                  SERIAL PRIMARY KEY,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    since               DATE,
    "until"             DATE,
    limite              INTEGER,
    operador            VARCHAR(100),
    rq_job_id           VARCHAR(80),
    iniciado_em         TIMESTAMP,
    finalizado_em       TIMESTAMP,
    total_listadas      INTEGER NOT NULL DEFAULT 0,
    processadas         INTEGER NOT NULL DEFAULT 0,
    n_criado            INTEGER NOT NULL DEFAULT 0,
    n_atualizado        INTEGER NOT NULL DEFAULT 0,
    n_inalterado        INTEGER NOT NULL DEFAULT 0,
    n_cancelado         INTEGER NOT NULL DEFAULT 0,
    n_pulada_cancelada  INTEGER NOT NULL DEFAULT 0,
    n_pulada_invalida   INTEGER NOT NULL DEFAULT 0,
    n_dup               INTEGER NOT NULL DEFAULT 0,
    n_erro              INTEGER NOT NULL DEFAULT 0,
    n_divergencias      INTEGER NOT NULL DEFAULT 0,
    ultimo_erro         TEXT,
    relatorio           JSON,
    criado_em           TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP
);
"""

SQL_INDICES = [
    "CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_status "
    "ON hora_tagplus_backfill_job (status);",
    "CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_criado_em "
    "ON hora_tagplus_backfill_job (criado_em DESC);",
    "CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_rq_job_id "
    "ON hora_tagplus_backfill_job (rq_job_id);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        antes = inspector.has_table('hora_tagplus_backfill_job')
        print(f'Tabela hora_tagplus_backfill_job existe antes? {antes}')

        with db.engine.begin() as conn:
            conn.execute(text(SQL_CREATE))
            for sql in SQL_INDICES:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        depois = inspector.has_table('hora_tagplus_backfill_job')
        print(f'Tabela hora_tagplus_backfill_job existe depois? {depois}')

        if depois:
            cols = {c['name'] for c in inspector.get_columns('hora_tagplus_backfill_job')}
            print(f'Colunas ({len(cols)}): {sorted(cols)}')
            indices = inspector.get_indexes('hora_tagplus_backfill_job')
            print(f'Indices ({len(indices)}): {[i["name"] for i in indices]}')
        else:
            print('ERRO: tabela nao foi criada.')
            sys.exit(1)

        print('Migration HORA 24 concluida com sucesso.')


if __name__ == '__main__':
    main()
