#!/usr/bin/env python3
"""
Script para verificar se a VIEW pedidos já existe
Usado no deploy para evitar recriar a VIEW desnecessariamente
"""

import os
import sys
from sqlalchemy import create_engine, text

def verificar_view_existe():
    """Verifica se a VIEW pedidos já existe no banco"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não configurada")
        return False
    
    # Corrigir URL se necessário (postgres:// -> postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        engine = create_engine(database_url)
        
        # Verificar se VIEW existe
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.views 
                WHERE table_schema = 'public' 
                AND table_name = 'pedidos'
            """))
            
            count = result.scalar()
            
            if count > 0:
                print("✅ VIEW pedidos já existe")
                
                # Verificar se tem o filtro de PREVISAO
                result = conn.execute(text("""
                    SELECT view_definition 
                    FROM information_schema.views 
                    WHERE table_schema = 'public' 
                    AND table_name = 'pedidos'
                """))
                
                view_def = result.scalar()
                if view_def and "status != 'PREVISAO'" in view_def:
                    print("✅ VIEW tem filtro correto (exclui PREVISAO)")
                    return True
                else:
                    print("⚠️ VIEW existe mas pode não ter o filtro correto")
                    return False
            else:
                print("ℹ️ VIEW pedidos não existe")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao verificar VIEW: {e}")
        return False

def verificar_tabela_backup():
    """Verifica se a tabela pedidos_backup já existe"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return False
    
    # Corrigir URL se necessário
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'pedidos_backup'
            """))
            
            count = result.scalar()
            return count > 0
            
    except Exception as e:
        print(f"❌ Erro ao verificar tabela backup: {e}")
        return False

def main():
    """Verifica estado da migração"""
    
    print("=" * 50)
    print("VERIFICANDO ESTADO DA MIGRAÇÃO PEDIDOS → VIEW")
    print("=" * 50)
    
    view_existe = verificar_view_existe()
    backup_existe = verificar_tabela_backup()
    
    if view_existe and backup_existe:
        print("\n✅ Migração já foi aplicada anteriormente")
        print("   - VIEW pedidos existe e está correta")
        print("   - Tabela pedidos_backup existe")
        return 0  # Sucesso - já migrado
    
    elif not view_existe and not backup_existe:
        print("\n⚠️ Migração ainda não foi aplicada")
        print("   - VIEW pedidos não existe")
        print("   - Tabela pedidos_backup não existe")
        return 1  # Precisa migrar
    
    else:
        print("\n⚠️ Estado inconsistente:")
        print(f"   - VIEW existe: {view_existe}")
        print(f"   - Backup existe: {backup_existe}")
        return 2  # Estado inconsistente

if __name__ == "__main__":
    sys.exit(main())