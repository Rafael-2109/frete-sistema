"""CarVia — Comissoes: ajustes (debito/credito) + vinculo de vendedor.

Aplica carvia_comissao_ajustes.sql:
 (1) colunas vendedor_usuario_id + total_ajustes em carvia_comissao_fechamentos
 (2) tabela carvia_comissao_ajustes
 (3) backfill vendedor_usuario_id por e-mail

Idempotente; safe para re-execucao.
Executar: python scripts/migrations/carvia_comissao_ajustes.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def _cols_fechamento():
    rows = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'carvia_comissao_fechamentos' "
        "  AND column_name IN ('vendedor_usuario_id','total_ajustes') "
        "ORDER BY column_name"
    )).fetchall()
    return [r[0] for r in rows]


def _tabela_ajustes_existe():
    return db.session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'carvia_comissao_ajustes')"
    )).scalar()


def run():
    app = create_app()
    with app.app_context():
        print(f'BEFORE: colunas fechamento = {_cols_fechamento()}')
        print(f'BEFORE: tabela ajustes existe = {_tabela_ajustes_existe()}')

        sql_path = os.path.join(
            os.path.dirname(__file__), 'carvia_comissao_ajustes.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        cols = _cols_fechamento()
        tab = _tabela_ajustes_existe()
        backfilled = db.session.execute(text(
            "SELECT count(*) FROM carvia_comissao_fechamentos "
            "WHERE vendedor_usuario_id IS NOT NULL"
        )).scalar()

        print(f'AFTER: colunas fechamento = {cols}')
        print(f'AFTER: tabela ajustes existe = {tab}')
        print(f'AFTER: fechamentos com vendedor_usuario_id = {backfilled}')

        expected = ['total_ajustes', 'vendedor_usuario_id']
        if cols == expected and tab:
            print('OK: migration concluida.')
        else:
            print(f'ERRO: esperado colunas {expected} + tabela=True; '
                  f'obtido cols={cols} tab={tab}')
            sys.exit(1)


if __name__ == '__main__':
    run()
