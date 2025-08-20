#!/usr/bin/env python
"""
Script para criar a tabela de emails anexados
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.email_models import EmailAnexado

app = create_app()

with app.app_context():
    print("="*60)
    print("CRIANDO TABELA DE EMAILS ANEXADOS")
    print("="*60)
    
    try:
        # Cria a tabela se não existir
        db.create_all()
        
        # Verifica se a tabela foi criada
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if 'emails_anexados' in inspector.get_table_names():
            print("✅ Tabela 'emails_anexados' criada com sucesso!")
            
            # Lista as colunas
            columns = inspector.get_columns('emails_anexados')
            print("\nColunas criadas:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print("❌ Erro: Tabela não foi criada")
            
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("PROCESSO CONCLUÍDO")
    print("="*60)