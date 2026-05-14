"""Migration 29: cria tabelas de devolucao por NF de venda Q.P.A.

Tabelas criadas:
- assai_devolucao_nfd (cabecalho)
- assai_devolucao_item (1 por chassi devolvido)
- assai_devolucao_anexo (S3 keys)

Idempotente: usa CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
"""
import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'motos_assai_29_devolucao.sql',
)

TABELAS = (
    'assai_devolucao_nfd',
    'assai_devolucao_item',
    'assai_devolucao_anexo',
)


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        for tabela in TABELAS:
            existe = db.session.execute(text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
            ), {'t': tabela}).first()
            if existe:
                print(f'[skip] Tabela {tabela} ja existe — migration idempotente.')

        db.session.execute(text(sql))
        db.session.commit()

        for tabela in TABELAS:
            count = db.session.execute(text(
                f'SELECT COUNT(*) FROM {tabela}'
            )).scalar()
            print(f'[ok] {tabela}: {count} registros.')

        idx = db.session.execute(text(
            "SELECT tablename, indexname FROM pg_indexes "
            "WHERE tablename IN ('assai_devolucao_nfd', 'assai_devolucao_item', "
            "'assai_devolucao_anexo') ORDER BY tablename, indexname"
        )).fetchall()
        for tabela, indexname in idx:
            print(f'  - {tabela}.{indexname}')


if __name__ == '__main__':
    main()
