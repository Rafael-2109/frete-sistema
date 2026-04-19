#!/usr/bin/env python3
"""Migration D10 (2026-04-19): icms_valor e icms_base_calculo em
carvia_operacoes.

Idempotente. Uso local:
    source .venv/bin/activate
    python scripts/migrations/carvia_d10_icms_valor_base.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS = [
    ('icms_valor', 'NUMERIC(15, 2)'),
    ('icms_base_calculo', 'NUMERIC(15, 2)'),
]
INDEX_NAME = 'ix_carvia_operacoes_icms_valor'


def coluna_existe(tabela, coluna):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        f"WHERE table_name = '{tabela}' AND column_name = '{coluna}'"
    )).fetchone()
    return r is not None


def indice_existe(nome):
    r = db.session.execute(text(
        f"SELECT 1 FROM pg_indexes WHERE indexname = '{nome}'"
    )).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        print('=== Before ===')
        for nome, _ in COLUNAS:
            print(f'  {nome}:', 'exists' if coluna_existe('carvia_operacoes', nome) else 'missing')
        print(f'  index {INDEX_NAME}:', 'exists' if indice_existe(INDEX_NAME) else 'missing')

        for nome, tipo in COLUNAS:
            if coluna_existe('carvia_operacoes', nome):
                print(f'= {nome} ja existe')
                continue
            db.session.execute(text(
                f'ALTER TABLE carvia_operacoes ADD COLUMN {nome} {tipo}'
            ))
            db.session.commit()
            print(f'+ {nome} criada')

        if not indice_existe(INDEX_NAME):
            db.session.execute(text(
                f'CREATE INDEX {INDEX_NAME} ON carvia_operacoes (icms_valor) '
                'WHERE icms_valor IS NOT NULL'
            ))
            db.session.commit()
            print(f'+ {INDEX_NAME} criado')
        else:
            print(f'= {INDEX_NAME} ja existe')

        print('=== After ===')
        for nome, _ in COLUNAS:
            print(f'  {nome}:', 'exists' if coluna_existe('carvia_operacoes', nome) else 'missing')


if __name__ == '__main__':
    main()
