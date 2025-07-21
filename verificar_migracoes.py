#!/usr/bin/env python3
"""
Script para verificar o status das migrações do Flask-Migrate
"""

import os
import sys
from datetime import datetime

def verificar_migracoes():
    print("=" * 70)
    print("VERIFICAÇÃO DE MIGRAÇÕES DO BANCO DE DADOS")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    try:
        from app import create_app
        from flask_migrate import current, upgrade, show
        
        app = create_app()
        
        with app.app_context():
            print("🔍 Verificando status das migrações...")
            
            # 1. Verificar diretório de migrações
            migrations_dir = os.path.join(os.getcwd(), 'migrations', 'versions')
            if os.path.exists(migrations_dir):
                migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py')]
                print(f"✅ {len(migration_files)} arquivos de migração encontrados")
                
                # Mostrar as últimas 5 migrações
                migration_files.sort(reverse=True)
                print("   Últimas migrações:")
                for i, file in enumerate(migration_files[:5]):
                    print(f"   {i+1}. {file}")
            else:
                print("❌ Diretório de migrações não encontrado")
                return False
            
            # 2. Verificar migração atual
            try:
                current_revision = current()
                if current_revision:
                    print(f"✅ Migração atual: {current_revision}")
                else:
                    print("⚠️  Nenhuma migração aplicada no banco")
            except Exception as e:
                print(f"❌ Erro ao verificar migração atual: {e}")
            
            # 3. Verificar se há migrações pendentes
            print("\n🔄 Verificando migrações pendentes...")
            
            # Executar flask db show para ver o status
            try:
                from flask_migrate import show
                
                # Verificar heads
                print("📋 Status das migrações:")
                print("   → Execute 'flask db current' para ver a migração atual")
                print("   → Execute 'flask db heads' para ver as últimas migrações")
                print("   → Execute 'flask db history' para ver o histórico completo")
                
            except Exception as e:
                print(f"⚠️  Erro ao verificar status: {e}")
            
            # 4. Verificar se o modelo está atualizado
            print("\n🏗️  Verificando se o modelo precisa de migração...")
            try:
                from app.carteira.models import PreSeparacaoItem
                from sqlalchemy import inspect
                
                inspector = inspect(app.extensions['migrate'].db.engine)
                
                # Verificar se a tabela existe
                if inspector.has_table('pre_separacao_item'):
                    print("✅ Tabela pre_separacao_item existe no banco")
                    
                    # Verificar colunas
                    columns = inspector.get_columns('pre_separacao_item')
                    column_names = [col['name'] for col in columns]
                    
                    if 'data_expedicao_editada' in column_names:
                        print("✅ Coluna data_expedicao_editada existe")
                        
                        # Verificar se é NOT NULL
                        data_col = next((col for col in columns if col['name'] == 'data_expedicao_editada'), None)
                        if data_col and not data_col['nullable']:
                            print("✅ Coluna é NOT NULL - implementação correta")
                        else:
                            print("⚠️  Coluna permite NULL - pode precisar de migração")
                    else:
                        print("❌ Coluna data_expedicao_editada NÃO existe")
                        print("   → Execute: flask db migrate -m 'Add data_expedicao_editada column'")
                        print("   → Depois: flask db upgrade")
                else:
                    print("❌ Tabela pre_separacao_item NÃO existe")
                    print("   → Execute: flask db migrate -m 'Create pre_separacao_item table'")
                    print("   → Depois: flask db upgrade")
                    
            except Exception as e:
                print(f"❌ Erro ao verificar modelo: {e}")
            
            print("\n" + "=" * 70)
            print("INSTRUÇÕES PARA APLICAR MIGRAÇÕES:")
            print("=" * 70)
            print()
            print("1. Para criar uma nova migração:")
            print("   flask db migrate -m 'Implementar sistema pre-separacao avancado'")
            print()
            print("2. Para aplicar migrações pendentes:")
            print("   flask db upgrade")
            print()
            print("3. Para verificar status:")
            print("   flask db current    # Migração atual")
            print("   flask db heads      # Últimas migrações")
            print("   flask db history    # Histórico completo")
            print()
            print("4. Para reverter (se necessário):")
            print("   flask db downgrade  # Reverter última migração")
            print()
            print("=" * 70)
            
            return True
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("   → Verifique se o ambiente está correto")
        return False
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    success = verificar_migracoes()
    sys.exit(0 if success else 1)