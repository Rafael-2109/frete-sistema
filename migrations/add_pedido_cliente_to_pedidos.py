#!/usr/bin/env python3
"""
Migração para adicionar campo pedido_cliente na tabela pedidos
Executar com: python migrations/add_pedido_cliente_to_pedidos.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
app = create_app()
from sqlalchemy import text, exc

def add_pedido_cliente_to_pedidos():
    """Adiciona campo pedido_cliente na tabela pedidos"""
    
    with app.app_context():
        try:
            # Verificar se a coluna já existe
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'pedidos' 
                AND column_name = 'pedido_cliente'
            """))
            
            if result.scalar() > 0:
                print("✅ Campo pedido_cliente já existe na tabela pedidos")
                return
            
            # Adicionar a coluna
            print("📝 Adicionando campo pedido_cliente na tabela pedidos...")
            db.session.execute(text("""
                ALTER TABLE pedidos 
                ADD COLUMN pedido_cliente VARCHAR(100) DEFAULT NULL
            """))
            
            # Commit das mudanças
            db.session.commit()
            print("✅ Campo pedido_cliente adicionado com sucesso!")
            
        except exc.SQLAlchemyError as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar campo: {e}")
            raise

if __name__ == "__main__":
    add_pedido_cliente_to_pedidos()