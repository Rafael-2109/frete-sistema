"""Motos Assai - Migration 13: drop UNIQUE em_separacao para permitir N veiculos simultaneos.

Reverte indice criado erroneamente na migration 12. Regra de negocio (2026-05-12):
separacoes = veiculos. 2+ veiculos podem carregar paralelamente do mesmo (pedido, loja).

Idempotente; safe para re-execucao.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        before = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'assai_separacao' "
            "  AND indexname = 'ux_assai_separacao_pedido_loja_em_separacao'"
        )).fetchall()
        print(f'BEFORE: indice ux_em_separacao existe={bool(before)}')

        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_13_drop_unique_em_separacao.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        after = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'assai_separacao' "
            "  AND indexname = 'ux_assai_separacao_pedido_loja_em_separacao'"
        )).fetchall()
        print(f'AFTER: indice ux_em_separacao existe={bool(after)}')

        if after:
            print('ERRO: indice nao foi dropado')
            sys.exit(1)

        print('OK: indice ux_assai_separacao_pedido_loja_em_separacao dropado. '
              'N separacoes EM_SEPARACAO simultaneas agora permitidas por (pedido, loja).')


if __name__ == '__main__':
    run()
