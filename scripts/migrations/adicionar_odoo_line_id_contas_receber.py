"""
Script para adicionar campo odoo_line_id na tabela contas_a_receber
Alinha com o padrão já existente em contas_a_pagar (account.move.line ID do Odoo)

Data: 21/02/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_odoo_line_id():
    app = create_app()

    with app.app_context():
        try:
            # Verificar se o campo já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'contas_a_receber'
                AND column_name = 'odoo_line_id'
            """))

            if resultado.fetchone():
                print("✅ Campo 'odoo_line_id' já existe na tabela contas_a_receber")
            else:
                # Adicionar campo
                db.session.execute(text("""
                    ALTER TABLE contas_a_receber
                    ADD COLUMN odoo_line_id INTEGER NULL
                """))
                print("✅ Campo 'odoo_line_id' adicionado com sucesso!")

            # Verificar se o índice UNIQUE já existe
            resultado_idx = db.session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'contas_a_receber'
                AND indexname = 'ix_contas_a_receber_odoo_line_id'
            """))

            if resultado_idx.fetchone():
                print("✅ Índice 'ix_contas_a_receber_odoo_line_id' já existe")
            else:
                db.session.execute(text("""
                    CREATE UNIQUE INDEX ix_contas_a_receber_odoo_line_id
                    ON contas_a_receber(odoo_line_id)
                """))
                print("✅ Índice UNIQUE 'ix_contas_a_receber_odoo_line_id' criado com sucesso!")

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {str(e)}")
            return False


# SQL para rodar no Shell do Render:
"""
ALTER TABLE contas_a_receber ADD COLUMN IF NOT EXISTS odoo_line_id INTEGER NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_contas_a_receber_odoo_line_id ON contas_a_receber(odoo_line_id);
"""


if __name__ == '__main__':
    adicionar_odoo_line_id()
