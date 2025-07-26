#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app import create_app, db

app = create_app()

with app.app_context():
    print("Criando tabelas no PostgreSQL...")
    db.create_all()
    print("Tabelas criadas com sucesso!")
    
    # Listar tabelas criadas
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"\nTabelas criadas: {len(tables)}")
    for table in sorted(tables):
        print(f"  - {table}")