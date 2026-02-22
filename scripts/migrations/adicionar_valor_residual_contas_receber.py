"""
Script para adicionar campo valor_residual na tabela contas_a_receber.

Alinha com o padrão já existente em contas_a_pagar.
- valor_residual: abs(amount_residual) do Odoo — saldo remanescente do título

Data: 21/02/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_valor_residual():
    app = create_app()

    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'contas_a_receber'
                AND column_name = 'valor_residual'
            """))

            if resultado.fetchone():
                print("valor_residual ja existe na tabela contas_a_receber")
            else:
                db.session.execute(text("""
                    ALTER TABLE contas_a_receber
                    ADD COLUMN valor_residual FLOAT NULL
                """))
                print("Campo 'valor_residual' adicionado com sucesso!")

            db.session.commit()
            print("\nMigration concluida com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro: {str(e)}")
            return False


# SQL para rodar no Shell do Render:
"""
ALTER TABLE contas_a_receber ADD COLUMN IF NOT EXISTS valor_residual FLOAT NULL;
"""


if __name__ == '__main__':
    adicionar_valor_residual()
