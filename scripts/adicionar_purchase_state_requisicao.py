"""
Script Python para adicionar campo purchase_state à tabela requisicao_compras

Data: 05/11/2025
Objetivo: Armazenar status da linha de requisição no Odoo

Uso:
    python scripts/adicionar_purchase_state_requisicao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_purchase_state():
    app = create_app()

    with app.app_context():
        try:
            print("🔧 Adicionando campo purchase_state...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE requisicao_compras
                ADD COLUMN IF NOT EXISTS purchase_state VARCHAR(20);
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_requisicao_purchase_state
                ON requisicao_compras(purchase_state);
            """))

            db.session.commit()

            # Verificar
            resultado = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = 'requisicao_compras'
                AND column_name = 'purchase_state';
            """))

            row = resultado.fetchone()
            if row:
                print(f"✅ Campo purchase_state adicionado com sucesso!")
                print(f"   Tipo: {row[1]}")
                print(f"   Nullable: {row[2]}")
            else:
                print("❌ Erro: Campo não foi criado")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")
            raise

if __name__ == '__main__':
    adicionar_purchase_state()
