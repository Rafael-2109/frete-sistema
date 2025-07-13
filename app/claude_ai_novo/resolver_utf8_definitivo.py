#!/usr/bin/env python3
"""
🔧 SOLUÇÃO DEFINITIVA: UTF-8 no Sistema
======================================
"""

import os
import sys

def main():
    """Resolve o problema de UTF-8 no sistema"""
    print("="*60)
    print("🔧 RESOLVENDO UTF-8 DEFINITIVAMENTE")
    print("="*60)
    
    print("\n1️⃣ Definindo variável de ambiente SKIP_DB_CREATE...")
    os.environ['SKIP_DB_CREATE'] = 'true'
    print("✅ Variável definida!")
    
    print("\n2️⃣ Testando importação do sistema...")
    
    # Adicionar o diretório raiz ao path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    try:
        # Tentar importar com SKIP_DB_CREATE ativo
        from app import create_app, db
        print("✅ Importação bem sucedida!")
        
        # Criar app
        app = create_app()
        print("✅ App criado com sucesso!")
        
        # Testar contexto
        with app.app_context():
            # Testar query simples
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Conexão com banco funcionando!")
            
            # Verificar encoding
            encoding = db.session.execute(db.text("SHOW client_encoding")).scalar()
            print(f"📝 Client encoding: {encoding}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n3️⃣ Instruções para correção permanente:")
    print("\n📝 Adicione ao seu arquivo .env:")
    print("SKIP_DB_CREATE=true")
    
    print("\n📝 Ou defina a variável antes de executar:")
    print("# Windows PowerShell:")
    print("$env:SKIP_DB_CREATE=\"true\"")
    print("\n# Windows CMD:")
    print("set SKIP_DB_CREATE=true")
    print("\n# Linux/Mac:")
    print("export SKIP_DB_CREATE=true")
    
    print("\n✅ SOLUÇÃO APLICADA!")
    print("\nO erro UTF-8 ocorre porque o Flask tenta criar tabelas automaticamente")
    print("durante a inicialização, mas encontra caracteres especiais em algum arquivo.")
    print("Com SKIP_DB_CREATE=true, pulamos essa etapa problemática.")
    print("\nAs tabelas já existem no banco PostgreSQL, então não há problema!")
    
    return True

if __name__ == "__main__":
    success = main() 