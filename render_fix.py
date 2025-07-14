#!/usr/bin/env python3
"""
Script para configurar o ambiente do Render com correções UTF-8
"""

import os

def fix_render_environment():
    """
    Aplica correções necessárias para o ambiente do Render
    """
    print("🔧 Configurando ambiente do Render...")
    
    # 1. Configurar encoding UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LANG'] = 'C.UTF-8'
    os.environ['LC_ALL'] = 'C.UTF-8'
    
    # 2. Configurar PostgreSQL com UTF-8
    database_url = os.environ.get('DATABASE_URL', '')
    if database_url and 'postgres' in database_url:
        # Corrigir URL do PostgreSQL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Adicionar parâmetros de encoding
        if 'client_encoding' not in database_url:
            if '?' in database_url:
                database_url += '&client_encoding=utf8'
            else:
                database_url += '?client_encoding=utf8'
        
        # Atualizar variável de ambiente
        os.environ['DATABASE_URL'] = database_url
        print(f"✅ DATABASE_URL configurada com UTF-8")
    
    # 3. Configurar Flask para pular criação automática de tabelas
    os.environ['SKIP_DB_CREATE'] = 'true'
    
    # 4. Configurar logs sem emojis para evitar problemas de encoding
    os.environ['NO_EMOJI_LOGS'] = 'true'
    
    print("✅ Ambiente do Render configurado com sucesso!")
    return True

if __name__ == "__main__":
    fix_render_environment()
    
    # Importar e executar o app após configurar o ambiente
    try:
        from app import create_app
        app = create_app()
        print("🚀 App iniciado com sucesso!")
        
        # Executar o app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Erro ao iniciar app: {e}")
        import traceback
        traceback.print_exc() 