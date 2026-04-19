#!/usr/bin/env python3
"""Migration A1 (2026-04-17): adiciona cte_complementar_id em
carvia_fatura_cliente_itens.

Motivacao: Bug #2 do plano CarVia — quando fatura PDF lista CTe Comp
antes do XML do Comp chegar, a `CarviaFaturaClienteItem` precisa guardar
a referencia ao CTe Comp. Este FK e populado por
`LinkingService.fechar_vinculo_cte_comp_fatura()`.

Idempotente: IF NOT EXISTS em tudo.

Uso local:
    source .venv/bin/activate
    python scripts/migrations/carvia_fatura_cliente_item_cte_complementar_id.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUMN_NAME = 'cte_complementar_id'
FK_NAME = 'fk_fatura_item_cte_complementar'
INDEX_NAME = 'ix_carvia_fatura_cliente_itens_cte_complementar_id'


def column_exists():
    result = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'carvia_fatura_cliente_itens' "
        f"AND column_name = '{COLUMN_NAME}'"
    )).fetchone()
    return result is not None


def constraint_exists():
    result = db.session.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        f"WHERE constraint_name = '{FK_NAME}' "
        "AND table_name = 'carvia_fatura_cliente_itens'"
    )).fetchone()
    return result is not None


def index_exists():
    result = db.session.execute(text(
        "SELECT 1 FROM pg_indexes "
        f"WHERE indexname = '{INDEX_NAME}'"
    )).fetchone()
    return result is not None


def main():
    app = create_app()
    with app.app_context():
        print('=== Before ===')
        print(f'  column {COLUMN_NAME}:', 'exists' if column_exists() else 'missing')
        print(f'  FK {FK_NAME}:', 'exists' if constraint_exists() else 'missing')
        print(f'  index {INDEX_NAME}:', 'exists' if index_exists() else 'missing')

        # 1. Coluna
        if not column_exists():
            db.session.execute(text(
                "ALTER TABLE carvia_fatura_cliente_itens "
                f"ADD COLUMN {COLUMN_NAME} INTEGER"
            ))
            db.session.commit()
            print(f'+ Coluna {COLUMN_NAME} criada')
        else:
            print(f'= Coluna {COLUMN_NAME} ja existe')

        # 2. FK
        if not constraint_exists():
            db.session.execute(text(
                "ALTER TABLE carvia_fatura_cliente_itens "
                f"ADD CONSTRAINT {FK_NAME} "
                f"FOREIGN KEY ({COLUMN_NAME}) "
                "REFERENCES carvia_cte_complementares(id) "
                "ON DELETE SET NULL"
            ))
            db.session.commit()
            print(f'+ FK {FK_NAME} criada')
        else:
            print(f'= FK {FK_NAME} ja existe')

        # 3. Index
        if not index_exists():
            db.session.execute(text(
                f"CREATE INDEX {INDEX_NAME} "
                f"ON carvia_fatura_cliente_itens ({COLUMN_NAME})"
            ))
            db.session.commit()
            print(f'+ Index {INDEX_NAME} criado')
        else:
            print(f'= Index {INDEX_NAME} ja existe')

        print('=== After ===')
        print(f'  column {COLUMN_NAME}:', 'exists' if column_exists() else 'missing')
        print(f'  FK {FK_NAME}:', 'exists' if constraint_exists() else 'missing')
        print(f'  index {INDEX_NAME}:', 'exists' if index_exists() else 'missing')


if __name__ == '__main__':
    main()
