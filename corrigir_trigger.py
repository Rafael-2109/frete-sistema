#!/usr/bin/env python
"""
Script para corrigir o trigger que está causando erro
"""

from app import create_app, db
from sqlalchemy import text

def corrigir_trigger():
    """Corrige o trigger problemático"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 Corrigindo trigger problemático...")
            
            # Primeiro, remover o trigger da tabela alertas_separacao_cotada
            sql_remove_trigger = """
            DROP TRIGGER IF EXISTS update_alertas_separacao_cotada_updated_at ON alertas_separacao_cotada;
            """
            
            # Adicionar coluna atualizado_em se não existir
            sql_add_column = """
            ALTER TABLE alertas_separacao_cotada 
            ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """
            
            try:
                db.session.execute(text(sql_remove_trigger))
                print("✅ Trigger removido")
            except:
                print("⚠️ Trigger não existia ou já foi removido")
            
            try:
                db.session.execute(text(sql_add_column))
                print("✅ Coluna atualizado_em adicionada")
            except:
                print("⚠️ Coluna já existe")
            
            db.session.commit()
            print("✅ Correção aplicada com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()

if __name__ == '__main__':
    corrigir_trigger()