"""Migration HORA 52: coluna inscricao_estadual em hora_venda.

Adiciona `inscricao_estadual VARCHAR(20)` (nullable) ao pedido de venda para
registro/exibicao do destinatario PJ. Decisao 2026-06-25 (dono do modulo): campo
SO de registro — NAO entra no payload da NFe (TagPlus). Preenchimento manual: a
ReceitaWS (base federal) nao retorna IE, que e estadual (SEFAZ).

Idempotente — ADD COLUMN IF NOT EXISTS.

Uso:
    python scripts/migrations/hora_52_inscricao_estadual.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS inscricao_estadual VARCHAR(20)",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_venda')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_venda.inscricao_estadual existe? {"inscricao_estadual" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = 'inscricao_estadual' in _colunas()
        print('\nEstado depois:')
        print(f'  hora_venda.inscricao_estadual existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 52 concluida com sucesso.')


if __name__ == '__main__':
    main()
