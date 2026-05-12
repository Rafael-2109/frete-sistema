"""Motos Assai - Migration 14: chassi_assai em `separacao` Nacom + ajuste UNIQUE.

Bug pre-existente: UNIQUE em (lote, cod_produto) bloqueava 2 chassis do mesmo
modelo no mesmo lote ASSAI-SEP-*. Decisao 2026-05-12: 1 linha por chassi.

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
        col_existe = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='separacao' AND column_name='chassi_assai'"
        )).scalar() or 0
        uq_antigo = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='separacao' AND indexname='uq_separacao_assai_lote_produto'"
        )).fetchall()
        uq_novo = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='separacao' AND indexname='uq_separacao_assai_lote_chassi'"
        )).fetchall()
        print(f'BEFORE: col chassi_assai={bool(col_existe)} | '
              f'uq_antigo={bool(uq_antigo)} uq_novo={bool(uq_novo)}')

        # Executar SQL
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_14_chassi_assai_em_separacao.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # AFTER
        col_existe = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='separacao' AND column_name='chassi_assai'"
        )).scalar() or 0
        uq_antigo = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='separacao' AND indexname='uq_separacao_assai_lote_produto'"
        )).fetchall()
        uq_novo = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename='separacao' AND indexname='uq_separacao_assai_lote_chassi'"
        )).fetchall()
        print(f'AFTER: col chassi_assai={bool(col_existe)} | '
              f'uq_antigo={bool(uq_antigo)} (deve ser False) | '
              f'uq_novo={bool(uq_novo)} (deve ser True)')

        if not col_existe:
            print('ERRO: coluna chassi_assai nao foi criada')
            sys.exit(1)
        if uq_antigo:
            print('ERRO: UNIQUE antigo nao foi removido')
            sys.exit(1)
        if not uq_novo:
            print('ERRO: UNIQUE novo nao foi criado')
            sys.exit(1)

        print('OK: migration 14 aplicada — granularidade do mirror agora e 1 linha por chassi')


if __name__ == '__main__':
    run()
