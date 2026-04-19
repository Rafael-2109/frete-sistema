#!/usr/bin/env python3
"""Migration F1 (2026-04-19): eh_compensacao + compensacao_motivo em
carvia_conciliacoes (encontro de contas cross-tipo)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def coluna_existe(nome):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'carvia_conciliacoes' "
        f"AND column_name = '{nome}'"
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
        if not coluna_existe('eh_compensacao'):
            db.session.execute(text(
                'ALTER TABLE carvia_conciliacoes '
                'ADD COLUMN eh_compensacao BOOLEAN NOT NULL DEFAULT FALSE'
            ))
            db.session.commit()
            print('+ eh_compensacao criado')
        else:
            print('= eh_compensacao ja existe')

        if not coluna_existe('compensacao_motivo'):
            db.session.execute(text(
                'ALTER TABLE carvia_conciliacoes '
                'ADD COLUMN compensacao_motivo VARCHAR(255)'
            ))
            db.session.commit()
            print('+ compensacao_motivo criado')
        else:
            print('= compensacao_motivo ja existe')

        idx = 'ix_carvia_conciliacoes_eh_compensacao'
        if not indice_existe(idx):
            db.session.execute(text(
                f'CREATE INDEX {idx} ON carvia_conciliacoes (eh_compensacao) '
                'WHERE eh_compensacao = TRUE'
            ))
            db.session.commit()
            print(f'+ {idx} criado')
        else:
            print(f'= {idx} ja existe')


if __name__ == '__main__':
    main()
