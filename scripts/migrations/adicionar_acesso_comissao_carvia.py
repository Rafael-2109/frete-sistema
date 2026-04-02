"""
Migration: Adicionar campo acesso_comissao_carvia na tabela usuarios
=====================================================================

Executar: python scripts/migrations/adicionar_acesso_comissao_carvia.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def check_column_exists(table_name, column_name):
    """Verifica se coluna ja existe."""
    result = db.session.execute(
        db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = :t AND column_name = :c"
            ")"
        ),
        {'t': table_name, 'c': column_name},
    )
    return result.scalar()


def run_migration():
    app = create_app()
    with app.app_context():
        col_exists = check_column_exists('usuarios', 'acesso_comissao_carvia')
        print(f"[BEFORE] acesso_comissao_carvia existe: {col_exists}")

        if col_exists:
            print("[SKIP] Coluna ja existe. Nada a fazer.")
            return

        db.session.execute(db.text(
            "ALTER TABLE usuarios "
            "ADD COLUMN acesso_comissao_carvia BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        db.session.commit()

        col_now = check_column_exists('usuarios', 'acesso_comissao_carvia')
        print(f"[AFTER] acesso_comissao_carvia existe: {col_now}")
        print("[DONE] Migration concluida com sucesso.")


if __name__ == '__main__':
    run_migration()
