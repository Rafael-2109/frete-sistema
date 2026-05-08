"""
Migration: Adicionar sistema_motos_assai em usuarios
=====================================================
Executar: python scripts/migrations/motos_assai_02_toggle_usuario.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def adicionar_campo():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        colunas = [c['name'] for c in inspector.get_columns('usuarios')]
        if 'sistema_motos_assai' in colunas:
            print("Campo 'sistema_motos_assai' já existe.")
            return

        print("Adicionando campo sistema_motos_assai...")
        db.session.execute(text("""
            ALTER TABLE usuarios
            ADD COLUMN sistema_motos_assai BOOLEAN DEFAULT FALSE NOT NULL;
        """))
        db.session.commit()

        inspector = inspect(db.engine)
        colunas_depois = [c['name'] for c in inspector.get_columns('usuarios')]
        if 'sistema_motos_assai' in colunas_depois:
            print("OK: campo sistema_motos_assai adicionado.")
        else:
            print("ERRO: campo não foi adicionado.")
            sys.exit(1)


if __name__ == '__main__':
    adicionar_campo()
