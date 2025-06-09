#!/usr/bin/env python3
"""
Script para inicializar o banco de dados em produção
Cria todas as tabelas baseadas nos models SQLAlchemy
"""

from app import create_app, db

def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    print("🔄 Inicializando banco de dados...")
    
    app = create_app()
    
    with app.app_context():
        # Criar todas as tabelas baseadas nos models
        db.create_all()
        print("✅ Todas as tabelas criadas com sucesso!")
        
        # Verificar tabelas criadas
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"📊 Tabelas criadas ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")

if __name__ == "__main__":
    init_database() 