#!/usr/bin/env python3
import os
import sys
import subprocess

def force_fix_migrations():
    """Força correção de migrações antes de inicializar o banco"""
    try:
        print("🔧 Verificando e corrigindo migrações...")
        
        # Definir FLASK_APP
        os.environ['FLASK_APP'] = 'run.py'
        
        # Primeiro, tentar limpar qualquer estado de migração corrompido
        try:
            print("   📌 Limpando estado de migrações...")
            # Tentar fazer downgrade para base (início)
            subprocess.run(['flask', 'db', 'downgrade', 'base'], 
                         capture_output=True, check=False)
        except:
            pass
        
        # Aplicar a migração inicial
        try:
            print("   📌 Aplicando migração inicial consolidada...")
            result = subprocess.run(['flask', 'db', 'stamp', 'initial_consolidated_2025'], 
                                  capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                print("   ✅ Migração inicial aplicada")
            else:
                # Se falhar, tentar stamp head como fallback
                print("   ⚠️ Tentando stamp head como fallback...")
                subprocess.run(['flask', 'db', 'stamp', 'head'], 
                             capture_output=True, check=False)
        except:
            pass
        
        # Finalmente, tentar aplicar todas as migrações
        try:
            print("   📌 Aplicando todas as migrações...")
            result = subprocess.run(['flask', 'db', 'upgrade'], 
                                  capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                print("   ✅ Migrações aplicadas com sucesso")
            else:
                print("   ⚠️ Algumas migrações podem não ter sido aplicadas")
        except:
            pass
            
    except Exception as e:
        print(f"   ⚠️ Aviso na verificação de migrações: {e}")
        # Continuar mesmo com erro

def init_database():
    try:
        print("=== INICIANDO BANCO DE DADOS ===")
        
        # NOVO: Corrigir migrações ANTES de tudo
        if os.environ.get('DATABASE_URL'):
            # Só executar em produção
            force_fix_migrations()
        
        # Verificar se estamos em produção
        if os.environ.get('DATABASE_URL'):
            print("✓ Ambiente de produção detectado (PostgreSQL)")
        else:
            print("✓ Ambiente de desenvolvimento detectado (SQLite)")
            
        # Importar app
        from app import create_app, db
        
        print("✓ Módulos importados com sucesso")
        
        # Criar aplicação
        app = create_app()
        print("✓ Aplicação Flask criada")
        
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("✓ Comando db.create_all() executado")
            
            # Verificar tabelas criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✓ {len(tables)} tabelas criadas:")
            for table in sorted(tables)[:10]:  # Mostrar apenas as primeiras 10
                print(f"  - {table}")
            if len(tables) > 10:
                print(f"  ... e mais {len(tables) - 10} tabelas")
            
            print("✓ Banco de dados inicializado com sucesso")
                
        print("=== BANCO INICIALIZADO COM SUCESSO ===")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na inicialização: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1) 