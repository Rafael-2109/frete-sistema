"""CarVia — cria carvia_cotacoes_rapidas_publicas (Cotacao Rapida da tela publica).

Aplica 2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql.
Idempotente; safe para re-execucao.
Executar: python scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text

TABELA = 'carvia_cotacoes_rapidas_publicas'


def _tabela_existe(nome):
    return db.session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :t)"
    ), {'t': nome}).scalar()


def run():
    app = create_app()
    with app.app_context():
        print(f'BEFORE: {TABELA}={_tabela_existe(TABELA)}')
        sql_path = os.path.join(
            os.path.dirname(__file__),
            '2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()
        existe = _tabela_existe(TABELA)
        print(f'AFTER: {TABELA}={existe}')
        if not existe:
            print('ERRO: tabela nao criada.')
            sys.exit(1)
        print('OK: migration concluida.')


if __name__ == '__main__':
    run()
