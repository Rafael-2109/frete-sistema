"""CarVia — Carta de Correcao (CCe) anexavel por NF/cotacao.

Aplica carvia_cce.sql:
 (1) tabela carvia_cartas_correcao (arquivo S3 + descricao)
 (2) tabela carvia_carta_correcao_vinculos (N:N polimorfico cotacao/nf)

Idempotente; safe para re-execucao.
Executar: python scripts/migrations/carvia_cce.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def _tabela_existe(nome):
    return db.session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :t)"
    ), {'t': nome}).scalar()


def run():
    app = create_app()
    with app.app_context():
        print(f'BEFORE: cartas={_tabela_existe("carvia_cartas_correcao")} '
              f'vinculos={_tabela_existe("carvia_carta_correcao_vinculos")}')

        sql_path = os.path.join(os.path.dirname(__file__), 'carvia_cce.sql')
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        cartas = _tabela_existe('carvia_cartas_correcao')
        vinc = _tabela_existe('carvia_carta_correcao_vinculos')
        print(f'AFTER: cartas={cartas} vinculos={vinc}')

        if cartas and vinc:
            print('OK: migration concluida.')
        else:
            print('ERRO: tabelas nao criadas.')
            sys.exit(1)


if __name__ == '__main__':
    run()
