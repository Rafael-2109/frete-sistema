#!/usr/bin/env python3
"""
Script de teste para verificar encoding UTF-8
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def test_database_connection():
    """Testa conexão com banco de dados"""
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    try:
        # Parse da URL
        parsed = urlparse(database_url)
        
        # Configurar conexão com UTF-8 explícito
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove '/' do início
            user=parsed.username,
            password=parsed.password,
            options='-c client_encoding=utf8'
        )
        
        # Testar encoding
        cursor = conn.cursor()
        cursor.execute("SHOW client_encoding;")
        encoding = cursor.fetchone()[0]
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"✅ Encoding: {encoding}")
        
        # Testar caracteres especiais
        cursor.execute("SELECT 'Olá, teste com acentuação!' as teste;")
        result = cursor.fetchone()[0]
        print(f"✅ Teste de caracteres: {result}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def test_python_encoding():
    """Testa encoding do Python"""
    
    print(f"✅ Python encoding: {sys.getdefaultencoding()}")
    print(f"✅ Filesystem encoding: {sys.getfilesystemencoding()}")
    print(f"✅ Locale encoding: {locale.getpreferredencoding()}")
    
    # Testar caracteres especiais
    test_string = "Olá, mundo com acentuação! 🚀"
    print(f"✅ Teste string: {test_string}")
    
    return True

if __name__ == "__main__":
    import locale
    
    print("🚀 Testando encoding UTF-8...")
    print("="*50)
    
    test_python_encoding()
    print("="*50)
    test_database_connection()
    print("="*50)
    print("✅ Teste concluído!")
