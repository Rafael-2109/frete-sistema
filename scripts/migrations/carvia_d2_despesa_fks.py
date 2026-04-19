#!/usr/bin/env python3
"""Migration D2 (2026-04-19): FKs operacao_id/frete_id em carvia_despesas.

Idempotente. Uso local:
    source .venv/bin/activate
    python scripts/migrations/carvia_d2_despesa_fks.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS = [
    ('operacao_id', 'INTEGER', 'fk_carvia_despesas_operacao',
     'carvia_operacoes', 'ix_carvia_despesas_operacao_id'),
    ('frete_id', 'INTEGER', 'fk_carvia_despesas_frete',
     'carvia_fretes', 'ix_carvia_despesas_frete_id'),
]


def coluna_existe(tabela, coluna):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        f"WHERE table_name = '{tabela}' AND column_name = '{coluna}'"
    )).fetchone()
    return r is not None


def constraint_existe(nome):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        f"WHERE constraint_name = '{nome}'"
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
        for col, _, fk, _, idx in COLUNAS:
            print(f'  {col}:', 'exists' if coluna_existe('carvia_despesas', col) else 'missing')

        for col, tipo, fk, referencia, idx in COLUNAS:
            if not coluna_existe('carvia_despesas', col):
                db.session.execute(text(
                    f'ALTER TABLE carvia_despesas ADD COLUMN {col} {tipo}'
                ))
                db.session.commit()
                print(f'+ Coluna {col} criada')

            if not constraint_existe(fk):
                db.session.execute(text(f"""
                    ALTER TABLE carvia_despesas
                    ADD CONSTRAINT {fk}
                    FOREIGN KEY ({col}) REFERENCES {referencia}(id)
                    ON DELETE SET NULL
                """))
                db.session.commit()
                print(f'+ FK {fk} criada')

            if not indice_existe(idx):
                db.session.execute(text(
                    f'CREATE INDEX {idx} ON carvia_despesas ({col})'
                ))
                db.session.commit()
                print(f'+ Index {idx} criado')

        print('=== After ===')
        for col, _, fk, _, idx in COLUNAS:
            print(f'  {col}:', 'exists' if coluna_existe('carvia_despesas', col) else 'missing')


if __name__ == '__main__':
    main()
