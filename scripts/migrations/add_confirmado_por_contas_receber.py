"""
Script para adicionar campo confirmado_por na tabela contas_a_receber
Campo específico do financeiro para registrar quem confirmou a entrega

Data: 28/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campo_confirmado_por():
    app = create_app()

    with app.app_context():
        try:
            # Verificar se o campo já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'contas_a_receber'
                AND column_name = 'confirmado_por'
            """))

            if resultado.fetchone():
                print("✅ Campo 'confirmado_por' já existe na tabela contas_a_receber")
                return True

            # Adicionar campo
            db.session.execute(text("""
                ALTER TABLE contas_a_receber
                ADD COLUMN confirmado_por VARCHAR(100) NULL
            """))

            db.session.commit()
            print("✅ Campo 'confirmado_por' adicionado com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar campo: {str(e)}")
            return False


# SQL para rodar no Shell do Render:
"""
ALTER TABLE contas_a_receber ADD COLUMN confirmado_por VARCHAR(100) NULL;
"""


if __name__ == '__main__':
    adicionar_campo_confirmado_por()
