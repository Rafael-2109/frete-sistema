"""
Migration: Adicionar campo tags_pedido na tabela separacao
Data: 2026-02-04
Descrição: Adiciona coluna TEXT para armazenar tags do pedido (JSON) sincronizadas de CarteiraPrincipal

Executar localmente:
    source .venv/bin/activate
    python migrations/adicionar_tags_pedido_separacao.py

Executar no Render Shell:
    python migrations/adicionar_tags_pedido_separacao.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_tags_pedido():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'separacao'
                AND column_name = 'tags_pedido'
            """))

            if result.fetchone():
                print("✅ Coluna tags_pedido já existe na tabela separacao. Nada a fazer.")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE separacao
                ADD COLUMN tags_pedido TEXT NULL
            """))

            db.session.commit()
            print("✅ Coluna tags_pedido adicionada com sucesso na tabela separacao!")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    adicionar_tags_pedido()
