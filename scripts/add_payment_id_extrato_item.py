"""
Migration: Adicionar campo payment_id ao extrato_item

O campo payment_id armazena o ID do account.payment criado no Odoo
durante a conciliação (tanto entrada quanto saída).

Nota: O código existente já fazia `item.payment_id = payment_id` mas
o campo não existia na tabela — era um atributo transiente Python.
Esta migration corrige o bug silencioso.

Uso:
    python scripts/add_payment_id_extrato_item.py

Ou no Render Shell:
    Execute o SQL diretamente.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_MIGRATION = """
-- Adicionar payment_id ao extrato_item
-- Data: 2026-02-08

ALTER TABLE extrato_item
    ADD COLUMN IF NOT EXISTS payment_id INTEGER;

COMMENT ON COLUMN extrato_item.payment_id IS 'account.payment ID criado no Odoo durante conciliação';
"""


def executar():
    app = create_app()
    with app.app_context():
        try:
            print("Executando migration: add_payment_id_extrato_item")
            print("=" * 60)

            db.session.execute(text(SQL_MIGRATION))
            db.session.commit()

            print("✓ Campo payment_id adicionado à tabela extrato_item")
            print("=" * 60)
            print("Migration concluída com sucesso!")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar()
