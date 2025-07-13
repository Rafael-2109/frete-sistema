#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO: DATABASE_URL Encoding
====================================
"""

import os
import sys
from urllib.parse import urlparse, quote_plus
import unicodedata

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def main():
    """Diagnostica problemas no DATABASE_URL"""
    print("="*60)
    print("🔍 DIAGNÓSTICO DATABASE_URL")
    print("="*60)
    
    # 1. Carregar .env
    from dotenv import load_dotenv
    load_dotenv()
    
    # 2. Obter DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        print("   Configure no arquivo .env ou variáveis de ambiente")
        return
        
    print(f"\n1️⃣ DATABASE_URL tem {len(database_url)} caracteres")
    
    # 3. Verificar caracteres problemáticos
    print("\n2️⃣ Analisando caracteres...")
    problemas = []
    
    for i, char in enumerate(database_url):
        try:
            # Tentar codificar/decodificar
            char.encode('utf-8').decode('utf-8')
            
            # Verificar se é caractere de controle ou especial
            if ord(char) < 32 or ord(char) > 126:
                problemas.append({
                    'posicao': i,
                    'char': repr(char),
                    'ord': ord(char),
                    'nome': unicodedata.name(char, 'DESCONHECIDO')
                })
        except Exception as e:
            problemas.append({
                'posicao': i,
                'char': repr(char),
                'erro': str(e)
            })
    
    if problemas:
        print("⚠️ CARACTERES PROBLEMÁTICOS ENCONTRADOS:")
        for p in problemas:
            print(f"   Posição {p['posicao']}: {p}")
    else:
        print("✅ Nenhum caractere problemático óbvio encontrado")
    
    # 4. Tentar parsear URL
    print("\n3️⃣ Parseando URL...")
    try:
        parsed = urlparse(database_url)
        print(f"   Protocolo: {parsed.scheme}")
        print(f"   Host: {parsed.hostname}")
        print(f"   Porta: {parsed.port}")
        print(f"   Database: {parsed.path}")
        print(f"   Username: {'***' if parsed.username else 'None'}")
        print(f"   Password: {'***' if parsed.password else 'None'}")
        
        # Verificar se há caracteres especiais na senha
        if parsed.password:
            print("\n   ⚠️ Senha contém caracteres especiais?")
            for char in parsed.password:
                if not char.isalnum():
                    print(f"      - '{char}' (ord: {ord(char)})")
                    
    except Exception as e:
        print(f"❌ Erro ao parsear URL: {e}")
    
    # 5. Mostrar área problemática
    print("\n4️⃣ Área do erro (posição 82):")
    if len(database_url) > 82:
        start = max(0, 82 - 20)
        end = min(len(database_url), 82 + 20)
        print(f"   ...{repr(database_url[start:end])}...")
        print(f"   {'   ' + ' ' * (82 - start) + '^'}")
        
        # Mostrar bytes
        print("\n   Bytes na posição 82:")
        try:
            bytes_data = database_url.encode('latin-1')  # Tentar latin-1
            if len(bytes_data) > 82:
                print(f"   Byte: 0x{bytes_data[82]:02x} ({bytes_data[82]})")
                print(f"   Char: {repr(database_url[82])}")
        except:
            pass
    
    # 6. Sugerir correção
    print("\n5️⃣ SUGESTÕES DE CORREÇÃO:")
    print("1. Se a senha contém caracteres especiais, escape-os:")
    print("   from urllib.parse import quote_plus")
    print("   password = quote_plus('sua@senha#especial')")
    print("\n2. Use formato correto:")
    print("   postgresql://user:password@host:port/database")
    print("\n3. Para caracteres não-ASCII, use percent-encoding:")
    print("   'ã' → '%C3%A3'")
    print("\n4. Verifique arquivo .env com editor que mostra encoding")
    print("   (Notepad++, VSCode com extensão encoding)")

if __name__ == "__main__":
    main() 