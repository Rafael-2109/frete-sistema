"""Migration HORA 58: coluna telefone_lead em hora_venda.

Adiciona `telefone_lead` (VARCHAR(20), NULL) — telefone do LEAD (contato
original que originou a venda), distinto do telefone do destinatario fiscal
(`telefone_cliente`). Registro/exibicao apenas; NAO entra no payload da NFe
(mesmo criterio de `inscricao_estadual`). Idempotente — ADD COLUMN IF NOT EXISTS.

Uso:
    # Local (DATABASE_URL do .env -> localhost):
    python scripts/migrations/hora_58_venda_telefone_lead.py

    # PROD (Render):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/hora_58_venda_telefone_lead.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS telefone_lead VARCHAR(20)",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_venda')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_venda.telefone_lead existe? {"telefone_lead" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = 'telefone_lead' in _colunas()
        print('\nEstado depois:')
        print(f'  hora_venda.telefone_lead existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 58 concluida com sucesso.')


if __name__ == '__main__':
    main()
