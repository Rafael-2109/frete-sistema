#!/usr/bin/env python3
"""Migration D6 (2026-04-19): autoria de DIVERGENTE e EM_CONFERENCIA
em CarviaFaturaTransportadora (GAP-32).

Idempotente. Uso local:
    source .venv/bin/activate
    python scripts/migrations/carvia_d6_autoria_status.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS = [
    ('divergente_por', 'VARCHAR(100)'),
    ('divergente_em', 'TIMESTAMP'),
    ('em_conferencia_por', 'VARCHAR(100)'),
    ('em_conferencia_em', 'TIMESTAMP'),
]


def coluna_existe(coluna):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'carvia_faturas_transportadora' "
        f"AND column_name = '{coluna}'"
    )).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        print('=== Before ===')
        for nome, _ in COLUNAS:
            print(f'  {nome}:', 'exists' if coluna_existe(nome) else 'missing')

        for nome, tipo in COLUNAS:
            if coluna_existe(nome):
                continue
            db.session.execute(text(
                f'ALTER TABLE carvia_faturas_transportadora ADD COLUMN {nome} {tipo}'
            ))
            db.session.commit()
            print(f'+ {nome} criada')

        print('=== After ===')
        for nome, _ in COLUNAS:
            print(f'  {nome}:', 'exists' if coluna_existe(nome) else 'missing')


if __name__ == '__main__':
    main()
