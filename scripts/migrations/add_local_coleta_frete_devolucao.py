"""
Adiciona campo local_coleta na tabela frete_devolucao

Campo para armazenar o nome do local de coleta (digitável pelo usuário)
Ex: "CD Atacadao", "Loja Assai Centro"

Executar: python scripts/migrations/add_local_coleta_frete_devolucao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def add_local_coleta():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'frete_devolucao'
                AND column_name = 'local_coleta'
            """)
            result = db.session.execute(check_sql).fetchone()

            if result:
                print("Coluna 'local_coleta' já existe na tabela frete_devolucao")
                return

            # Adicionar coluna
            alter_sql = text("""
                ALTER TABLE frete_devolucao
                ADD COLUMN local_coleta VARCHAR(255)
            """)
            db.session.execute(alter_sql)
            db.session.commit()

            print("Coluna 'local_coleta' adicionada com sucesso à tabela frete_devolucao")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    add_local_coleta()
