"""Motos Assai - Migration 11: 4 campos de agendamento (override) em assai_separacao.

Adiciona expedicao/agendamento/protocolo/agendamento_confirmado. NULL = herda do
AssaiPedidoVendaLoja correspondente.

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
        # BEFORE
        before = db.session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'assai_separacao' "
            "  AND column_name IN ('expedicao','agendamento','protocolo','agendamento_confirmado') "
            "ORDER BY column_name"
        )).fetchall()
        print(f'BEFORE: campos override existentes = {[r[0] for r in before]}')

        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_11_separacao_4campos.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # AFTER
        after = db.session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'assai_separacao' "
            "  AND column_name IN ('expedicao','agendamento','protocolo','agendamento_confirmado') "
            "ORDER BY column_name"
        )).fetchall()

        cols = [r[0] for r in after]
        expected = ['agendamento', 'agendamento_confirmado', 'expedicao', 'protocolo']

        if cols == expected:
            print(f'OK: 4 campos override adicionados em assai_separacao: {cols}')
        else:
            print(f'ERRO: campos esperados {expected}, encontrados {cols}')
            sys.exit(1)


if __name__ == '__main__':
    run()
