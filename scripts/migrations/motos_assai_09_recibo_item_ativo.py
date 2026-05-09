"""Adiciona coluna `ativo` em assai_recibo_item + UNIQUE PARCIAL.

Habilita soft-delete de chassis duplicados na importacao de recibo Motochefe
preservando o append-only do modulo. UNIQUE parcial permite re-importar
chassi inativado.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def run():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_09_recibo_item_ativo.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # Verificacao after
        coluna = db.session.execute(text(
            "SELECT column_name, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = 'assai_recibo_item' AND column_name = 'ativo'"
        )).first()
        idx_parcial = db.session.execute(text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'assai_recibo_item' "
            "  AND indexname = 'ux_assai_recibo_item_recibo_chassi'"
        )).first()

        print(f'OK: coluna ativo = {coluna}')
        print(f'OK: UNIQUE parcial = {idx_parcial}')


if __name__ == '__main__':
    run()
