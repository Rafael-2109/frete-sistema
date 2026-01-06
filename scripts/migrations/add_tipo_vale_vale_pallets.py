"""
Script de migracao: Adicionar campo tipo_vale na tabela vale_pallets

Campo: tipo_vale (VARCHAR(20), default='CANHOTO_ASSINADO')
Valores possiveis: VALE_PALLET, CANHOTO_ASSINADO

Execucao local:
    source .venv/bin/activate
    python scripts/migrations/add_tipo_vale_vale_pallets.py

SQL para Render (Shell):
    ALTER TABLE vale_pallets ADD COLUMN IF NOT EXISTS tipo_vale VARCHAR(20) DEFAULT 'CANHOTO_ASSINADO';
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campo_tipo_vale():
    """Adiciona campo tipo_vale na tabela vale_pallets"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se campo ja existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'vale_pallets'
                AND column_name = 'tipo_vale'
            """))

            if resultado.fetchone():
                print("Campo tipo_vale ja existe na tabela vale_pallets")
                return True

            # Adicionar campo
            db.session.execute(text("""
                ALTER TABLE vale_pallets
                ADD COLUMN tipo_vale VARCHAR(20) DEFAULT 'CANHOTO_ASSINADO'
            """))
            db.session.commit()

            print("Campo tipo_vale adicionado com sucesso!")
            print("Valores possiveis: VALE_PALLET, CANHOTO_ASSINADO")
            return True

        except Exception as e:
            print(f"Erro ao adicionar campo: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    adicionar_campo_tipo_vale()
