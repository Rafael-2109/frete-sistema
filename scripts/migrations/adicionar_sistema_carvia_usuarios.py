"""
Migration: Adicionar campo sistema_carvia na tabela usuarios
=============================================================

Executar: python scripts/migrations/adicionar_sistema_carvia_usuarios.py
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

        # Verificar se coluna ja existe
        colunas = [c['name'] for c in inspector.get_columns('usuarios')]
        if 'sistema_carvia' in colunas:
            print("Campo 'sistema_carvia' ja existe na tabela 'usuarios'.")
            print("Migration ja foi executada anteriormente.")
            return

        print("Adicionando campo sistema_carvia...")
        db.session.execute(text("""
            ALTER TABLE usuarios
            ADD COLUMN sistema_carvia BOOLEAN DEFAULT FALSE NOT NULL;
        """))
        db.session.commit()

        # Verificacao
        inspector = inspect(db.engine)
        colunas_depois = [c['name'] for c in inspector.get_columns('usuarios')]
        if 'sistema_carvia' in colunas_depois:
            print("Campo 'sistema_carvia' adicionado com sucesso!")
        else:
            print("ERRO: Campo nao foi adicionado!")


if __name__ == '__main__':
    adicionar_campo()
