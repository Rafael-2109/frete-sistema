"""Migration: identidade unificada Teams <-> Web (Fase A do plano teams-melhorias).

Mudancas:
  1. usuarios -> +teams_user_id VARCHAR(64) (AAD object ID; UNIQUE parcial)
  2. usuarios -> +teams_vinculo_origem VARCHAR(20) ('codigo'|'email'|'admin')
  3. teams_vinculo_codigos -> tabela nova (codigos de pareamento sha256, TTL, uso unico)

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/2026_06_10_teams_identidade.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_STATEMENTS = [
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS teams_user_id VARCHAR(64);",
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS teams_vinculo_origem VARCHAR(20);",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_teams_user_id "
    "ON usuarios (teams_user_id) WHERE teams_user_id IS NOT NULL;",
    """
    CREATE TABLE IF NOT EXISTS teams_vinculo_codigos (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES usuarios(id),
        codigo_hash VARCHAR(64) NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_teams_vinculo_codigos_hash "
    "ON teams_vinculo_codigos (codigo_hash);",
]


def _estado(inspector) -> dict:
    cols_usuarios = {c['name'] for c in inspector.get_columns('usuarios')}
    return {
        'usuarios.teams_user_id': 'teams_user_id' in cols_usuarios,
        'usuarios.teams_vinculo_origem': 'teams_vinculo_origem' in cols_usuarios,
        'tabela teams_vinculo_codigos': inspector.has_table('teams_vinculo_codigos'),
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
