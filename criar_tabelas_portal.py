#!/usr/bin/env python3
"""
Script para criar as tabelas do portal no banco de dados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

app = create_app()

def verificar_e_criar_tabelas():
    """Verifica se as tabelas do portal existem e as cria se necessário"""
    with app.app_context():
        print("=" * 60)
        print("🔍 VERIFICANDO TABELAS DO PORTAL")
        print("=" * 60)
        
        # Verificar se a tabela portal_integracoes existe
        try:
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'portal_integracoes'
                );
            """))
            exists = result.scalar()
            
            if exists:
                print("✅ Tabela portal_integracoes já existe!")
                
                # Contar registros
                count_result = db.session.execute(text("SELECT COUNT(*) FROM portal_integracoes"))
                count = count_result.scalar()
                print(f"   Total de registros: {count}")
                
                # Listar todas as tabelas portal
                tables_result = db.session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name LIKE 'portal_%'
                    ORDER BY table_name
                """))
                tables = [row[0] for row in tables_result]
                print(f"\n📋 Tabelas do portal encontradas:")
                for table in tables:
                    print(f"   - {table}")
                    
            else:
                print("❌ Tabela portal_integracoes NÃO existe!")
                print("📝 Criando tabelas agora...")
                
                # Ler o script SQL
                sql_file = "app/portal/sql/001_criar_tabelas_portal.sql"
                
                if not os.path.exists(sql_file):
                    print(f"❌ Arquivo SQL não encontrado: {sql_file}")
                    return False
                
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                # Executar o script SQL
                print("🔧 Executando script SQL...")
                
                # Dividir o script em comandos individuais
                # Remove comentários e divide por ponto e vírgula
                commands = []
                current_command = []
                
                for line in sql_script.split('\n'):
                    # Ignorar comentários de linha
                    if line.strip().startswith('--'):
                        continue
                    
                    current_command.append(line)
                    
                    # Se a linha termina com ; é o fim do comando
                    if line.strip().endswith(';'):
                        command = '\n'.join(current_command)
                        if command.strip():
                            commands.append(command)
                        current_command = []
                
                # Executar cada comando
                success_count = 0
                error_count = 0
                
                for i, command in enumerate(commands, 1):
                    try:
                        # Pular comandos vazios
                        if not command.strip():
                            continue
                            
                        # Executar comando
                        db.session.execute(text(command))
                        db.session.commit()
                        success_count += 1
                        
                        # Mostrar progresso para comandos CREATE TABLE
                        if 'CREATE TABLE' in command.upper():
                            # Extrair nome da tabela
                            lines = command.split('\n')
                            for line in lines:
                                if 'CREATE TABLE' in line.upper():
                                    print(f"   ✅ Tabela criada: {line.strip()}")
                                    break
                                    
                    except Exception as e:
                        error_count += 1
                        # Ignorar erros de "already exists"
                        if 'already exists' not in str(e).lower():
                            print(f"   ⚠️ Erro no comando {i}: {str(e)[:100]}")
                        db.session.rollback()
                
                print(f"\n📊 Resultado:")
                print(f"   ✅ Comandos executados com sucesso: {success_count}")
                if error_count > 0:
                    print(f"   ⚠️ Comandos com erro (ignorados): {error_count}")
                
                # Verificar novamente se as tabelas foram criadas
                db.session.commit()
                
                verify_result = db.session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name LIKE 'portal_%'
                    ORDER BY table_name
                """))
                created_tables = [row[0] for row in verify_result]
                
                if created_tables:
                    print(f"\n✅ SUCESSO! {len(created_tables)} tabelas criadas:")
                    for table in created_tables:
                        print(f"   - {table}")
                else:
                    print("\n❌ Nenhuma tabela foi criada. Verifique os erros acima.")
                    
        except Exception as e:
            print(f"❌ Erro ao verificar/criar tabelas: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

def testar_import_modelos():
    """Testa se os modelos do portal podem ser importados e usados"""
    print("\n" + "=" * 60)
    print("🔍 TESTANDO MODELOS DO PORTAL")
    print("=" * 60)
    
    try:
        from app.portal.models import PortalIntegracao, PortalConfiguracao, PortalLog, PortalSessao
        
        print("✅ Todos os modelos importados com sucesso:")
        print(f"   - PortalIntegracao: {PortalIntegracao.__tablename__}")
        print(f"   - PortalConfiguracao: {PortalConfiguracao.__tablename__}")
        print(f"   - PortalLog: {PortalLog.__tablename__}")
        print(f"   - PortalSessao: {PortalSessao.__tablename__}")
        
        # Tentar criar as tabelas via SQLAlchemy
        with app.app_context():
            print("\n🔧 Criando tabelas via SQLAlchemy (create_all)...")
            
            # Importar todos os modelos para garantir que estão registrados
            from app.portal import models as portal_models
            
            # Criar apenas as tabelas do portal
            db.create_all()
            print("✅ db.create_all() executado com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro ao importar/criar modelos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 CONFIGURAÇÃO DO PORTAL - CRIAÇÃO DE TABELAS")
    print("=" * 60)
    
    # Primeiro tenta criar via SQLAlchemy
    testar_import_modelos()
    
    # Depois verifica e cria via SQL se necessário
    if verificar_e_criar_tabelas():
        print("\n✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📝 Próximos passos:")
        print("1. Reinicie o servidor Flask")
        print("2. Limpe o cache do navegador (Ctrl+F5)")
        print("3. Teste os botões na Carteira Agrupada")
    else:
        print("\n❌ Houve problemas na configuração.")
        print("Verifique os erros acima e tente novamente.")