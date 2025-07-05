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
        
        # Verificar se há múltiplas heads
        result = subprocess.run(['flask', 'db', 'heads'], 
                              capture_output=True, text=True)
        
        if 'merge_heads_20250705_093743' in result.stdout:
            # Se a migração de merge existe, aplicar stamp nela
            print("   📌 Aplicando stamp na migração de merge...")
            subprocess.run(['flask', 'db', 'stamp', 'merge_heads_20250705_093743'], 
                         check=False)
            print("   ✅ Migração de merge aplicada")
        elif 'Multiple head revisions' in result.stderr or result.returncode != 0:
            # Se há múltiplas heads, forçar stamp head
            print("   ⚠️ Múltiplas heads detectadas - aplicando correção...")
            subprocess.run(['flask', 'db', 'stamp', 'head'], check=False)
            print("   ✅ Stamp head aplicado")
        else:
            print("   ✅ Migrações OK")
            
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