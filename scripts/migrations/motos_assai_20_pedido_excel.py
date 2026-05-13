"""Migration 20: cria assai_pedido_excel + backfill de solicitacao_excel_s3_key.

Spec: §2.1, §12
Plano: Task 4
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_20_pedido_excel.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'assai_pedido_excel'"
        )).scalar()
        print(f'[before] assai_pedido_excel existe: {result_before}/1')

        db.session.execute(text(sql))
        db.session.commit()

        # M2 fix: validar que tabela foi criada
        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'assai_pedido_excel'"
        )).scalar()
        if result_after != 1:
            print('[ERROR] Migration 20 nao criou a tabela')
            sys.exit(1)

        backfill_count = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_excel WHERE motivo_regeneracao LIKE 'Backfill Migration 20%'"
        )).scalar()
        print(f'[after] tabela criada + {backfill_count} linhas de backfill')
        print('[ok] Migration 20 aplicada com sucesso')


if __name__ == '__main__':
    main()
