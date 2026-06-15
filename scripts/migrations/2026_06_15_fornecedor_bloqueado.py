"""Migration: tabela `fornecedor_bloqueado`.

Cria a tabela de fornecedores cujas ENTRADAS DE COMPRA nao devem ser
registradas no sistema. Quando o CNPJ esta cadastrado e ATIVO, o sync do
Odoo NAO grava:
  - PedidoCompras            (pedido_compras_service)
  - MovimentacaoEstoque      ENTRADA/COMPRA (entrada_material_service +
                             recebimento_fisico_odoo_service)

CNPJ armazenado NORMALIZADO (apenas digitos). Match exato de 14 digitos.

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS / CREATE TABLE IF NOT EXISTS).

Uso:
    python scripts/migrations/2026_06_15_fornecedor_bloqueado.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS fornecedor_bloqueado (
        id              SERIAL PRIMARY KEY,
        cnpj            VARCHAR(14)  NOT NULL,
        razao_social    VARCHAR(255),
        motivo          VARCHAR(500),
        ativo           BOOLEAN      NOT NULL DEFAULT TRUE,
        criado_em       TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
        criado_por      VARCHAR(100),
        atualizado_em   TIMESTAMP,
        atualizado_por  VARCHAR(100),
        CONSTRAINT uq_fornecedor_bloqueado_cnpj UNIQUE (cnpj)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_fornecedor_bloqueado_cnpj "
    "ON fornecedor_bloqueado (cnpj);",
    "CREATE INDEX IF NOT EXISTS ix_fornecedor_bloqueado_ativo "
    "ON fornecedor_bloqueado (ativo);",
]


def _estado(inspector) -> dict:
    tabelas = set(inspector.get_table_names())
    existe = 'fornecedor_bloqueado' in tabelas
    cols = (
        {c['name'] for c in inspector.get_columns('fornecedor_bloqueado')}
        if existe else set()
    )
    return {
        'tabela fornecedor_bloqueado': existe,
        'coluna cnpj': 'cnpj' in cols,
        'coluna ativo': 'ativo' in cols,
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
