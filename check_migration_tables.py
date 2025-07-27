#!/usr/bin/env python3
"""
Script para verificar se as tabelas da migration segura foram criadas
"""

import os
from sqlalchemy import create_engine, text

def check_tables():
    """Verifica se as tabelas foram criadas"""
    database_url = os.environ.get('DATABASE_URL', 'postgresql://frete_user:frete_senha_2024@localhost:5432/frete_sistema')
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Verifica versão da migration
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"📋 Versão atual da migration: {version}")
        
        # Lista de tabelas para verificar
        tables_to_check = [
            'permission_cache',
            'submodule', 
            'user_permission',
            'permissao_equipe',
            'permissao_vendedor',
            'permission_module',
            'permission_submodule'
        ]
        
        print("\n🔍 Verificando tabelas criadas pela migration segura:")
        
        for table in tables_to_check:
            try:
                # Verifica se a tabela existe
                exists_result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                
                if exists_result.scalar():
                    # Conta registros
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    print(f"   ✅ {table}: {count} registros")
                else:
                    print(f"   ❌ {table}: tabela não existe")
                    
            except Exception as e:
                print(f"   ⚠️ {table}: erro - {e}")
        
        # Verifica se PreSeparacaoItem tem o campo separacao_lote_id
        print("\n🔍 Verificando campo separacao_lote_id em PreSeparacaoItem:")
        try:
            field_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'pre_separacao_item' 
                    AND column_name = 'separacao_lote_id'
                )
            """))
            
            if field_check.scalar():
                print("   ✅ Campo separacao_lote_id existe")
            else:
                print("   ❌ Campo separacao_lote_id não existe")
                
        except Exception as e:
            print(f"   ⚠️ Erro ao verificar campo: {e}")

if __name__ == "__main__":
    check_tables()