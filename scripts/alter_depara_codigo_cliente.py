"""
Script para aumentar o campo codigo_cliente de VARCHAR(50) para VARCHAR(255)
na tabela depara_produto_cliente.

Execute localmente: python scripts/alter_depara_codigo_cliente.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def alterar_campo():
    app = create_app()
    with app.app_context():
        try:
            print("Alterando campo codigo_cliente de VARCHAR(50) para VARCHAR(255)...")
            db.session.execute(text("""
                ALTER TABLE depara_produto_cliente
                ALTER COLUMN codigo_cliente TYPE VARCHAR(255);
            """))
            db.session.commit()
            print("✓ Campo alterado com sucesso!")
        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            return False
    return True


if __name__ == "__main__":
    alterar_campo()
