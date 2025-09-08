#!/usr/bin/env python3
"""
Script para alterar o campo filial de VARCHAR(20) para VARCHAR(100) localmente
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def alterar_campo_filial():
    """Altera o tamanho do campo filial na tabela portal_sendas_filial_depara"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("ALTERANDO CAMPO FILIAL - SENDAS")
        print("=" * 60)
        
        try:
            # Verificar tamanho atual
            print("\n1. Verificando tamanho atual do campo...")
            result = db.session.execute(text("""
                SELECT character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'portal_sendas_filial_depara' 
                AND column_name = 'filial'
            """))
            tamanho_atual = result.scalar()
            print(f"   Tamanho atual: VARCHAR({tamanho_atual})")
            
            if tamanho_atual == 100:
                print("   ✅ Campo já está com VARCHAR(100). Nada a fazer!")
                return True
            
            # Alterar o campo
            print("\n2. Alterando campo para VARCHAR(100)...")
            db.session.execute(text("""
                ALTER TABLE portal_sendas_filial_depara 
                ALTER COLUMN filial TYPE VARCHAR(100)
            """))
            db.session.commit()
            print("   ✅ Campo alterado com sucesso!")
            
            # Verificar alteração
            print("\n3. Verificando alteração...")
            result = db.session.execute(text("""
                SELECT character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'portal_sendas_filial_depara' 
                AND column_name = 'filial'
            """))
            novo_tamanho = result.scalar()
            print(f"   Novo tamanho: VARCHAR({novo_tamanho})")
            
            if novo_tamanho == 100:
                print("\n" + "=" * 60)
                print("✅ ALTERAÇÃO CONCLUÍDA COM SUCESSO!")
                print("=" * 60)
                return True
            else:
                print("\n❌ Erro: Campo não foi alterado corretamente")
                return False
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("\n🚀 Iniciando alteração do campo filial...")
    
    try:
        if alterar_campo_filial():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro ao executar script: {e}")
        sys.exit(1)