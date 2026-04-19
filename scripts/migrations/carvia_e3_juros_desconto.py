#!/usr/bin/env python3
"""Migration E3 (2026-04-19): valor_acrescimo/valor_desconto em
carvia_conciliacoes."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS = [
    ('valor_acrescimo', 'NUMERIC(15, 2)'),
    ('valor_desconto', 'NUMERIC(15, 2)'),
]


def coluna_existe(nome):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'carvia_conciliacoes' "
        f"AND column_name = '{nome}'"
    )).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        for nome, tipo in COLUNAS:
            if coluna_existe(nome):
                print(f'= {nome} ja existe')
                continue
            db.session.execute(text(
                f'ALTER TABLE carvia_conciliacoes ADD COLUMN {nome} {tipo}'
            ))
            db.session.commit()
            print(f'+ {nome} criado')


if __name__ == '__main__':
    main()
