"""Migration HORA 39: Devolucao de Venda (cliente -> HORA).

Cria duas tabelas novas, paralelas e independentes de hora_devolucao_fornecedor:
  - hora_devolucao_venda       (header)
  - hora_devolucao_venda_item  (1 linha por chassi devolvido)

Esta migration NAO altera hora_devolucao_fornecedor — ela continua existindo
para o fluxo interno de "Resolucao de divergencia de recebimento" usado em
resolucao_service. A UI publica de devolucao a partir de agora referencia
APENAS a nova devolucao de venda.

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_39_devolucao_venda.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_CREATE_HEADER = """
CREATE TABLE IF NOT EXISTS hora_devolucao_venda (
    id                  SERIAL PRIMARY KEY,
    venda_id            INTEGER NOT NULL REFERENCES hora_venda(id),
    loja_id             INTEGER NOT NULL REFERENCES hora_loja(id),
    motivo              TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    data_devolucao      DATE NOT NULL,
    data_resolucao      DATE,
    cancelamento_motivo VARCHAR(500),
    criado_por          VARCHAR(100),
    resolvida_por       VARCHAR(100),
    cancelada_por       VARCHAR(100),
    criado_em           TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    atualizado_em       TIMESTAMP
);
"""

SQL_INDICES_HEADER = [
    "CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_venda_id ON hora_devolucao_venda(venda_id);",
    "CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_loja_id  ON hora_devolucao_venda(loja_id);",
    "CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_status   ON hora_devolucao_venda(status);",
    "CREATE INDEX IF NOT EXISTS ix_hora_devolucao_venda_data     ON hora_devolucao_venda(data_devolucao);",
]

SQL_CREATE_ITEM = """
CREATE TABLE IF NOT EXISTS hora_devolucao_venda_item (
    id                    SERIAL PRIMARY KEY,
    devolucao_id          INTEGER NOT NULL REFERENCES hora_devolucao_venda(id) ON DELETE CASCADE,
    numero_chassi         VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    venda_item_id         INTEGER REFERENCES hora_venda_item(id),
    motivo_especifico     TEXT,
    status_item           VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    resolucao_acao        VARCHAR(30),
    resolucao_observacoes TEXT,
    resolvida_em          TIMESTAMP,
    resolvida_por         VARCHAR(100),
    avaria_id             INTEGER REFERENCES hora_avaria(id),
    peca_faltando_id      INTEGER REFERENCES hora_peca_faltando(id),
    criado_em             TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    CONSTRAINT uq_hora_dev_venda_item_chassi UNIQUE (devolucao_id, numero_chassi)
);
"""

SQL_INDICES_ITEM = [
    "CREATE INDEX IF NOT EXISTS ix_hora_dev_venda_item_devolucao ON hora_devolucao_venda_item(devolucao_id);",
    "CREATE INDEX IF NOT EXISTS ix_hora_dev_venda_item_chassi    ON hora_devolucao_venda_item(numero_chassi);",
    "CREATE INDEX IF NOT EXISTS ix_hora_dev_venda_item_status    ON hora_devolucao_venda_item(status_item);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tabelas_antes = set(inspector.get_table_names())

        print('Estado antes:')
        print(f'  hora_devolucao_venda?       {"hora_devolucao_venda" in tabelas_antes}')
        print(f'  hora_devolucao_venda_item?  {"hora_devolucao_venda_item" in tabelas_antes}')

        with db.engine.begin() as conn:
            conn.execute(text(SQL_CREATE_HEADER))
            for sql in SQL_INDICES_HEADER:
                conn.execute(text(sql))
            conn.execute(text(SQL_CREATE_ITEM))
            for sql in SQL_INDICES_ITEM:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        tabelas_depois = set(inspector.get_table_names())

        print('\nEstado depois:')
        print(f'  hora_devolucao_venda?       {"hora_devolucao_venda" in tabelas_depois}')
        print(f'  hora_devolucao_venda_item?  {"hora_devolucao_venda_item" in tabelas_depois}')

        faltantes = [
            t for t in ('hora_devolucao_venda', 'hora_devolucao_venda_item')
            if t not in tabelas_depois
        ]
        if faltantes:
            print(f'\nERRO: tabelas nao criadas: {faltantes}')
            sys.exit(1)

        # Confirma colunas-chave.
        cols_header = {c['name'] for c in inspector.get_columns('hora_devolucao_venda')}
        cols_item = {c['name'] for c in inspector.get_columns('hora_devolucao_venda_item')}
        esperadas_header = {
            'id', 'venda_id', 'loja_id', 'motivo', 'status', 'data_devolucao',
            'data_resolucao', 'criado_por', 'resolvida_por', 'cancelada_por',
            'criado_em', 'atualizado_em', 'cancelamento_motivo',
        }
        esperadas_item = {
            'id', 'devolucao_id', 'numero_chassi', 'venda_item_id',
            'motivo_especifico', 'status_item', 'resolucao_acao',
            'resolucao_observacoes', 'resolvida_em', 'resolvida_por',
            'avaria_id', 'peca_faltando_id', 'criado_em',
        }
        falt_h = esperadas_header - cols_header
        falt_i = esperadas_item - cols_item
        if falt_h or falt_i:
            print(f'\nERRO: colunas faltando — header: {falt_h}, item: {falt_i}')
            sys.exit(1)

        print('\nMigration HORA 39 concluida com sucesso.')


if __name__ == '__main__':
    main()
