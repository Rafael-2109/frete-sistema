"""Migration 18: cria assai_carregamento + assai_carregamento_item.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §2.1
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md Task 2

Idempotente. Padrao Migration 17.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_18_carregamento.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        # Verifica before
        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name IN ('assai_carregamento', 'assai_carregamento_item')"
        )).scalar()
        print(f'[before] tabelas existentes: {result_before}/2')

        # Executa o SQL
        db.session.execute(text(sql))
        db.session.commit()

        # Verifica after
        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name IN ('assai_carregamento', 'assai_carregamento_item')"
        )).scalar()
        print(f'[after] tabelas existentes: {result_after}/2')

        if result_after != 2:
            print('[ERROR] migration falhou — verificar logs')
            sys.exit(1)
        print('[ok] Migration 18 aplicada com sucesso')


if __name__ == '__main__':
    main()
