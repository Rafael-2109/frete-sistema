"""
Script de Migração: Adicionar campo tags_pedido em CarteiraPrincipal
======================================================================

Adiciona coluna tags_pedido (TEXT) para armazenar tags do Odoo em formato JSON

Autor: Sistema de Fretes
Data: 2025-10-30
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campo_tags_pedido():
    """Adiciona campo tags_pedido na tabela carteira_principal"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar se coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'carteira_principal'
                AND column_name = 'tags_pedido';
            """))

            coluna_existe = resultado.fetchone()

            if coluna_existe:
                print(f"✅ Coluna 'tags_pedido' já existe em carteira_principal")
                print(f"   Tipo: {coluna_existe[1]}, Nullable: {coluna_existe[2]}")
                return

            # Adicionar coluna tags_pedido
            print("🔄 Adicionando coluna 'tags_pedido' em carteira_principal...")
            db.session.execute(text("""
                ALTER TABLE carteira_principal
                ADD COLUMN tags_pedido TEXT NULL;
            """))

            db.session.commit()
            print("✅ Coluna 'tags_pedido' adicionada com sucesso!")

            # Verificar criação
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'carteira_principal'
                AND column_name = 'tags_pedido';
            """))

            coluna = resultado.fetchone()
            if coluna:
                print(f"✅ Verificação: Coluna criada com tipo {coluna[1]}, nullable={coluna[2]}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar coluna: {e}")
            raise

if __name__ == '__main__':
    print("🚀 Iniciando migração: Adicionar tags_pedido em CarteiraPrincipal")
    print("="*70)
    adicionar_campo_tags_pedido()
    print("="*70)
    print("✅ Migração concluída!")
