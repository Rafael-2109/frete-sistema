#!/usr/bin/env python
"""
Script para adicionar campos CC e BCC na tabela de emails anexados
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

app = create_app()

with app.app_context():
    print("="*60)
    print("ADICIONANDO CAMPOS CC E BCC NA TABELA DE EMAILS")
    print("="*60)
    
    try:
        # Adiciona coluna cc (com cópia)
        from sqlalchemy import text
        db.session.execute(text("""
            ALTER TABLE emails_anexados 
            ADD COLUMN IF NOT EXISTS cc TEXT;
        """))
        print("✅ Campo 'cc' adicionado")
        
        # Adiciona coluna bcc (cópia oculta)
        db.session.execute(text("""
            ALTER TABLE emails_anexados 
            ADD COLUMN IF NOT EXISTS bcc TEXT;
        """))
        print("✅ Campo 'bcc' adicionado")
        
        db.session.commit()
        print("\n✅ Campos adicionados com sucesso!")
        
        # Verifica as colunas
        result = db.session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'emails_anexados'
            AND column_name IN ('cc', 'bcc')
            ORDER BY column_name;
        """))
        
        print("\nColunas verificadas:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        db.session.rollback()
    
    print("\n" + "="*60)
    print("PROCESSO CONCLUÍDO")
    print("="*60)