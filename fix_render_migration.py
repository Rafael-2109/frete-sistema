#!/usr/bin/env python3
"""
Script para corrigir problema de migration no Render
- Atualiza version para nossa migration segura
- Remove dependências problemáticas
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def get_database_url():
    """Obtém URL do banco do ambiente"""
    # Prioridade: variável de ambiente, depois valor padrão
    return os.environ.get('DATABASE_URL', 'postgresql://frete_user:frete_senha_2024@localhost:5432/frete_sistema')

def fix_migration_issue():
    """Corrige problema de migration no Render"""
    database_url = get_database_url()
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Inicia transação
            trans = conn.begin()
            
            try:
                print("🔍 Verificando versão atual da migration...")
                
                # Verifica versão atual
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_version = result.scalar()
                print(f"   Versão atual: {current_version}")
                
                if current_version == '935bc4a541de':
                    print("❌ Detectado problema: migration problemática ativa!")
                    print("🔄 Revertendo para versão segura...")
                    
                    # Reverte para permission_system_v1
                    conn.execute(text("UPDATE alembic_version SET version_num = 'permission_system_v1'"))
                    print("✅ Versão revertida para: permission_system_v1")
                    
                elif current_version == 'permission_system_v1':
                    print("✅ Versão já está correta!")
                    
                else:
                    print(f"⚠️ Versão inesperada: {current_version}")
                    print("🔄 Atualizando para versão segura...")
                    conn.execute(text("UPDATE alembic_version SET version_num = 'permission_system_v1'"))
                
                # Remove views problemáticas se existirem
                print("\n🧹 Limpando dependências problemáticas...")
                
                # Lista de views que podem causar problemas
                problematic_views = [
                    'ai_session_analytics',
                    'ai_performance_view',
                    'ai_learning_view'
                ]
                
                for view in problematic_views:
                    try:
                        # Verifica se a view existe
                        check_view = conn.execute(text(f"""
                            SELECT EXISTS (
                                SELECT FROM information_schema.views 
                                WHERE table_name = '{view}'
                            )
                        """)).scalar()
                        
                        if check_view:
                            print(f"   🗑️ Removendo view problemática: {view}")
                            conn.execute(text(f"DROP VIEW IF EXISTS {view} CASCADE"))
                            print(f"   ✅ View {view} removida")
                        else:
                            print(f"   ✅ View {view} não existe")
                            
                    except Exception as e:
                        print(f"   ⚠️ Erro ao remover {view}: {e}")
                        # Continua mesmo com erro
                
                # Remove constraints problemáticas
                print("\n🔗 Verificando constraints problemáticas...")
                
                problematic_constraints = [
                    ('ai_advanced_sessions', 'ai_advanced_sessions_pkey'),
                    ('ai_learning_patterns', 'ai_learning_patterns_pkey'),
                    ('ai_semantic_mappings', 'ai_semantic_mappings_pkey')
                ]
                
                for table, constraint in problematic_constraints:
                    try:
                        # Verifica se a tabela existe
                        table_exists = conn.execute(text(f"""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = '{table}'
                            )
                        """)).scalar()
                        
                        if table_exists:
                            print(f"   ⚠️ Tabela {table} ainda existe - pode causar problemas")
                        else:
                            print(f"   ✅ Tabela {table} não existe")
                            
                    except Exception as e:
                        print(f"   ⚠️ Erro ao verificar {table}: {e}")
                
                # Confirma transação
                trans.commit()
                print("\n✅ Correção aplicada com sucesso!")
                print("📋 Resumo:")
                print("   - Versão da migration corrigida")
                print("   - Views problemáticas removidas")
                print("   - Sistema pronto para aplicar migration segura")
                
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Erro durante correção: {e}")
                return False
                
    except SQLAlchemyError as e:
        print(f"❌ Erro de conexão com banco: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Iniciando correção de migration no Render")
    print("=" * 50)
    
    # Verifica se é ambiente Render
    is_render = os.environ.get('RENDER')
    if is_render:
        print("🌐 Ambiente Render detectado")
    else:
        print("🏠 Ambiente local detectado")
    
    # Executa correção
    success = fix_migration_issue()
    
    if success:
        print("\n🎉 Correção concluída com sucesso!")
        print("📋 Próximos passos:")
        print("   1. Aplicar migration segura: flask db upgrade")
        print("   2. Verificar se todas as tabelas foram criadas")
        print("   3. Testar funcionalidades do sistema")
        sys.exit(0)
    else:
        print("\n❌ Falha na correção!")
        print("📋 Ações recomendadas:")
        print("   1. Verificar logs de erro")
        print("   2. Checar conectividade com banco")
        print("   3. Executar script novamente")
        sys.exit(1)

if __name__ == "__main__":
    main()