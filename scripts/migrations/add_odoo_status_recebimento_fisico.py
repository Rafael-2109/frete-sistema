"""
Migration: Adiciona coluna odoo_status na tabela recebimento_fisico

Descricao:
    Campo para armazenar o status do picking no Odoo (state do stock.picking).
    Valores possiveis: 'draft', 'waiting', 'confirmed', 'assigned', 'done', 'cancel'

Executar:
    source .venv/bin/activate && python scripts/migrations/add_odoo_status_recebimento_fisico.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna ja existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'recebimento_fisico'
                AND column_name = 'odoo_status'
            """))

            if result.fetchone():
                print("Coluna 'odoo_status' ja existe na tabela 'recebimento_fisico'. Nada a fazer.")
                return True

            # Adicionar coluna
            print("Adicionando coluna 'odoo_status' na tabela 'recebimento_fisico'...")
            db.session.execute(text("""
                ALTER TABLE recebimento_fisico
                ADD COLUMN odoo_status VARCHAR(20) DEFAULT NULL
            """))
            db.session.commit()
            print("Coluna 'odoo_status' adicionada com sucesso!")
            return True

        except Exception as e:
            print(f"Erro ao executar migracao: {e}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
