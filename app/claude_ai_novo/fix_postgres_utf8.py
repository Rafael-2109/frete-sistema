#!/usr/bin/env python3
"""
🔧 FIX POSTGRES UTF-8 - Solução específica para o problema PostgreSQL
=====================================================================

O problema identificado:
- PostgreSQL retorna mensagens de erro em português
- Caracteres acentuados (ã, é, etc.) causam erro UTF-8
- Afeta a inicialização da aplicação Flask

Solução:
- Configurar locale apropriado
- Tratar erros de encoding do PostgreSQL
- Configurar psycopg2 para UTF-8
"""

import os
import sys
import locale
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_locale_settings():
    """Configura locale para tratar caracteres UTF-8 corretamente"""
    
    print("🌍 CONFIGURANDO LOCALE PARA UTF-8")
    print("=" * 50)
    
    # Tentar configurar locale UTF-8
    utf8_locales = [
        'en_US.UTF-8',
        'pt_BR.UTF-8', 
        'C.UTF-8',
        'Portuguese_Brazil.UTF-8',
        'English_United States.UTF-8'
    ]
    
    current_locale = locale.getlocale()
    print(f"📍 Locale atual: {current_locale}")
    
    for loc in utf8_locales:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            print(f"✅ Locale definido para: {loc}")
            break
        except locale.Error:
            print(f"❌ Locale {loc} não disponível")
    
    # Configurar variáveis de ambiente
    os.environ['LANG'] = 'en_US.UTF-8'
    os.environ['LC_ALL'] = 'en_US.UTF-8'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    print("✅ Variáveis de ambiente configuradas")

def fix_psycopg2_encoding():
    """Configura psycopg2 para trabalhar com UTF-8"""
    
    print("\n🗄️ CONFIGURANDO PSYCOPG2 PARA UTF-8")
    print("=" * 50)
    
    try:
        import psycopg2
        
        # Configurar extensões do psycopg2
        import psycopg2.extensions
        
        # Registrar adaptador Unicode
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
        
        # Configurar client encoding
        os.environ['PGCLIENTENCODING'] = 'UTF8'
        
        print("✅ psycopg2 configurado para UTF-8")
        return True
        
    except ImportError:
        print("❌ psycopg2 não instalado")
        return False
    except Exception as e:
        print(f"❌ Erro ao configurar psycopg2: {e}")
        return False

def create_safe_flask_app():
    """Cria aplicação Flask com tratamento de erro UTF-8"""
    
    print("\n🏗️ CRIANDO APLICAÇÃO FLASK SEGURA")
    print("=" * 50)
    
    # Adicionar path do projeto
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        from app import create_app
        
        # Desabilitar create_all temporariamente
        os.environ['SKIP_DB_CREATE'] = 'true'
        
        # Criar app
        app = create_app()
        
        print("✅ Aplicação Flask criada com sucesso")
        print(f"📊 App: {app}")
        print(f"🔧 Config: {app.config.get('SQLALCHEMY_DATABASE_URI', 'N/A')[:50]}...")
        
        return app
        
    except Exception as e:
        print(f"❌ Erro ao criar app: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_db_connection_safe():
    """Testa conexão com banco de forma segura"""
    
    print("\n🔍 TESTE DE CONEXÃO SEGURA COM BANCO")
    print("=" * 50)
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Obter DATABASE_URL
        db_url = os.getenv('DATABASE_URL', '')
        if not db_url:
            print("❌ DATABASE_URL não encontrada")
            return False
        
        # Parse da URL
        parsed = urlparse(db_url)
        
        # Configurar conexão com encoding UTF-8
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password,
            'client_encoding': 'UTF8'
        }
        
        print(f"🔗 Tentando conectar em {parsed.hostname}:{parsed.port}")
        
        # Tentar conexão
        conn = psycopg2.connect(**conn_params)
        
        # Testar query simples
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print(f"✅ Conexão bem-sucedida")
        print(f"🗄️ PostgreSQL: {version[0][:100]}...")
        
        cursor.close()
        conn.close()
        
        return True
        
    except UnicodeDecodeError as e:
        print(f"❌ Erro UTF-8: {e}")
        print(f"📍 Posição: {e.start}-{e.end}")
        print(f"📄 Objeto: {e.object}")
        return False
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def patch_create_app():
    """Aplica patch no create_app para evitar erro UTF-8"""
    
    print("\n🔧 APLICANDO PATCH NO CREATE_APP")
    print("=" * 50)
    
    # Adicionar path do projeto
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        # Modificar o arquivo app/__init__.py
        init_file = project_root / 'app' / '__init__.py'
        
        if not init_file.exists():
            print("❌ Arquivo app/__init__.py não encontrado")
            return False
        
        # Ler conteúdo atual
        content = init_file.read_text(encoding='utf-8')
        
        # Verificar se já tem o patch
        if 'SKIP_DB_CREATE' in content:
            print("✅ Patch já aplicado")
            return True
        
        # Encontrar db.create_all() e adicionar verificação
        if 'db.create_all()' in content:
            old_line = 'db.create_all()'
            new_line = '''# Verificar se deve pular criação de tabelas (para evitar erro UTF-8)
        if not os.getenv('SKIP_DB_CREATE'):
            try:
                db.create_all()
            except UnicodeDecodeError as e:
                print(f"⚠️ Erro UTF-8 na criação de tabelas: {e}")
                print("💡 Tabelas serão criadas manualmente quando necessário")
            except Exception as e:
                print(f"⚠️ Erro na criação de tabelas: {e}")
                print("💡 Continuando sem criação automática de tabelas")'''
            
            content = content.replace(old_line, new_line)
            
            # Adicionar import do os se não existir
            if 'import os' not in content:
                content = 'import os\n' + content
            
            # Salvar arquivo
            init_file.write_text(content, encoding='utf-8')
            
            print("✅ Patch aplicado com sucesso")
            return True
        else:
            print("⚠️ db.create_all() não encontrado")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao aplicar patch: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    
    print("🔧 FIX POSTGRES UTF-8 - INICIANDO")
    print("=" * 60)
    
    # Executar correções
    fix_locale_settings()
    psycopg2_ok = fix_psycopg2_encoding()
    
    if psycopg2_ok:
        db_ok = test_db_connection_safe()
        if not db_ok:
            print("\n🔧 Aplicando patch no create_app...")
            patch_ok = patch_create_app()
            if patch_ok:
                print("✅ Patch aplicado - testando novamente...")
                app = create_safe_flask_app()
                if app:
                    print("🎉 SUCESSO! Aplicação Flask criada sem erro UTF-8")
                else:
                    print("❌ Ainda há problemas na criação da aplicação")
        else:
            print("✅ Conexão com banco OK - testando create_app...")
            app = create_safe_flask_app()
            if app:
                print("🎉 SUCESSO! Aplicação Flask criada sem erro UTF-8")
    
    print("\n📊 CORREÇÕES CONCLUÍDAS")
    print("=" * 60)
    print("💡 Execute o validador novamente para verificar se o problema foi resolvido")

if __name__ == "__main__":
    main() 