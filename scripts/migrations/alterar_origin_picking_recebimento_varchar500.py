"""
Script para alterar o campo origin de VARCHAR(100) para VARCHAR(500)
na tabela picking_recebimento.

Motivo: Pickings de devolucao no Odoo concatenam multiplas referencias de pallet
no campo origin, excedendo 100 caracteres.

Executar: source .venv/bin/activate && python scripts/migrations/alterar_origin_picking_recebimento_varchar500.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def alterar_campo_origin():
    app = create_app()
    with app.app_context():
        try:
            print("Alterando campo origin de VARCHAR(100) para VARCHAR(500)...")
            db.session.execute(text("""
                ALTER TABLE picking_recebimento
                ALTER COLUMN origin TYPE VARCHAR(500);
            """))
            db.session.commit()
            print("  Campo origin alterado com sucesso!")
            print("  - Limite anterior: 100 caracteres")
            print("  - Limite atual: 500 caracteres")
        except Exception as e:
            print(f"  Erro: {e}")
            db.session.rollback()
            return False
    return True


if __name__ == "__main__":
    alterar_campo_origin()
