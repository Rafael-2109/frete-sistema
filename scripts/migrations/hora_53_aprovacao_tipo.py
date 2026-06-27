"""Migration HORA 53: coluna `tipo` em hora_aprovacao_desconto (#5b).

Generaliza a fila de aprovacao (antes so DESCONTO) para 3 gatilhos:
DESCONTO / FRETE / BRINDE. A coluna nasce NOT NULL DEFAULT 'DESCONTO', entao as
linhas legadas (aprovacoes de desconto ja existentes) ficam coerentes sem
backfill manual. Decisao 2026-06-26 (Haroldo/gestores): frete e brinde exigem
aprovacao gerencial antes de Confirmar a venda, alem do desconto acima do teto.

Idempotente — ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.

Uso:
    python scripts/migrations/hora_53_aprovacao_tipo.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_aprovacao_desconto "
    "ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'DESCONTO'",
    "CREATE INDEX IF NOT EXISTS ix_hora_aprovacao_desconto_tipo "
    "ON hora_aprovacao_desconto (tipo)",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_aprovacao_desconto')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_aprovacao_desconto.tipo existe? {"tipo" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = 'tipo' in _colunas()
        print('\nEstado depois:')
        print(f'  hora_aprovacao_desconto.tipo existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 53 concluida com sucesso.')


if __name__ == '__main__':
    main()
