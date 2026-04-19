#!/usr/bin/env python3
"""Migration E2 (2026-04-19): linha_original_id em carvia_extrato_linhas.

Idempotente. Uso:
    source .venv/bin/activate
    python scripts/migrations/carvia_e2_linha_original_id.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def coluna_existe():
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'carvia_extrato_linhas' "
        "AND column_name = 'linha_original_id'"
    )).fetchone()
    return r is not None


def constraint_existe():
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = 'fk_carvia_extrato_linha_original'"
    )).fetchone()
    return r is not None


def indice_existe():
    r = db.session.execute(text(
        "SELECT 1 FROM pg_indexes "
        "WHERE indexname = 'ix_carvia_extrato_linhas_linha_original'"
    )).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        if not coluna_existe():
            db.session.execute(text(
                'ALTER TABLE carvia_extrato_linhas '
                'ADD COLUMN linha_original_id INTEGER'
            ))
            db.session.commit()
            print('+ linha_original_id criado')
        else:
            print('= linha_original_id ja existe')

        if not constraint_existe():
            db.session.execute(text("""
                ALTER TABLE carvia_extrato_linhas
                ADD CONSTRAINT fk_carvia_extrato_linha_original
                FOREIGN KEY (linha_original_id)
                REFERENCES carvia_extrato_linhas(id)
                ON DELETE SET NULL
            """))
            db.session.commit()
            print('+ FK fk_carvia_extrato_linha_original criada')
        else:
            print('= FK fk_carvia_extrato_linha_original ja existe')

        if not indice_existe():
            db.session.execute(text(
                'CREATE INDEX ix_carvia_extrato_linhas_linha_original '
                'ON carvia_extrato_linhas (linha_original_id)'
            ))
            db.session.commit()
            print('+ index criado')
        else:
            print('= index ja existe')


if __name__ == '__main__':
    main()
