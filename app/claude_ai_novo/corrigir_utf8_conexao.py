#!/usr/bin/env python3
"""
🔧 CORREÇÃO: UTF-8 na Conexão PostgreSQL
========================================
"""

import os
import sys
from urllib.parse import urlparse, parse_qs, urlencode

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def fix_database_url():
    """Corrige DATABASE_URL para incluir configurações UTF-8 adequadas"""
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        return None
        
    print("🔍 Analisando DATABASE_URL original...")
    
    # Parse URL
    parsed = urlparse(database_url)
    
    # Extrair query params existentes
    query_params = parse_qs(parsed.query)
    
    # Adicionar configurações UTF-8
    query_params['client_encoding'] = ['utf8']
    query_params['encoding'] = ['utf8']
    
    # Reconstruir query string
    new_query = urlencode(query_params, doseq=True)
    
    # Reconstruir URL
    new_url = parsed._replace(query=new_query).geturl()
    
    print(f"✅ DATABASE_URL corrigida com encoding UTF-8")
    print(f"   Original: ...{database_url[-30:]}")
    print(f"   Nova:     ...{new_url[-30:]}")
    
    return new_url

def test_direct_connection():
    """Testa conexão direta com psycopg2"""
    print("\n🧪 Testando conexão direta com psycopg2...")
    
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        # Obter URL corrigida
        database_url = fix_database_url()
        if not database_url:
            return
            
        # Conectar diretamente
        print("\n📡 Tentando conectar...")
        conn = psycopg2.connect(database_url)
        
        print("✅ Conexão estabelecida!")
        
        # Verificar encoding
        cursor = conn.cursor()
        cursor.execute("SHOW server_encoding")
        result = cursor.fetchone()
        server_encoding = result[0] if result else "Unknown"
        print(f"📝 Server encoding: {server_encoding}")
        
        cursor.execute("SHOW client_encoding")
        result = cursor.fetchone()
        client_encoding = result[0] if result else "Unknown"
        print(f"📝 Client encoding: {client_encoding}")
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão direta: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sqlalchemy_connection():
    """Testa conexão via SQLAlchemy com configurações UTF-8"""
    print("\n🧪 Testando conexão via SQLAlchemy...")
    
    try:
        from sqlalchemy import create_engine, text
        
        # Obter URL corrigida
        database_url = fix_database_url()
        if not database_url:
            return
            
        # Criar engine com configurações UTF-8
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "client_encoding": "utf8",
                "options": "-c client_encoding=UTF8"
            }
        )
        
        print("\n📡 Tentando conectar via SQLAlchemy...")
        
        # Testar conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexão SQLAlchemy estabelecida!")
            
            # Verificar encoding
            encoding = conn.execute(text("SHOW client_encoding")).scalar()
            print(f"📝 Client encoding: {encoding}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão SQLAlchemy: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_config_file():
    """Atualiza config.py com correções UTF-8"""
    print("\n📝 Sugestão de atualização para config.py:")
    print("""
# No início do arquivo, após load_dotenv():
DATABASE_URL = os.environ.get('DATABASE_URL')

# Corrigir encoding para PostgreSQL
if DATABASE_URL and DATABASE_URL.startswith(('postgresql://', 'postgres://')):
    from urllib.parse import urlparse, parse_qs, urlencode
    parsed = urlparse(DATABASE_URL)
    query_params = parse_qs(parsed.query)
    query_params['client_encoding'] = ['utf8']
    new_query = urlencode(query_params, doseq=True)
    DATABASE_URL = parsed._replace(query=new_query).geturl()
""")

def main():
    """Executa diagnóstico e correções"""
    print("="*60)
    print("🔧 CORREÇÃO UTF-8 - POSTGRESQL")
    print("="*60)
    
    # 1. Testar conexão direta
    direct_ok = test_direct_connection()
    
    # 2. Testar conexão SQLAlchemy
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    # 3. Sugerir correções
    if not (direct_ok and sqlalchemy_ok):
        update_config_file()
    
    print("\n" + "="*60)
    print("📊 RESULTADO:")
    print(f"   Conexão direta: {'✅ OK' if direct_ok else '❌ Falhou'}")
    print(f"   Conexão SQLAlchemy: {'✅ OK' if sqlalchemy_ok else '❌ Falhou'}")
    print("="*60)

if __name__ == "__main__":
    main() 