#!/usr/bin/env python3
"""
Script para testar se o Playwright está instalado e funcionando
"""

import sys
import os

def test_playwright():
    print("\n" + "="*60)
    print("TESTE DE INSTALAÇÃO DO PLAYWRIGHT")
    print("="*60)
    
    # 1. Testar importação
    print("\n1️⃣ Testando importação do Playwright...")
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar Playwright: {e}")
        print("Execute: pip install playwright")
        return False
    
    # 2. Testar se navegador está instalado
    print("\n2️⃣ Verificando navegador Chromium...")
    try:
        with sync_playwright() as p:
            # Tentar lançar o navegador em modo headless
            browser = p.chromium.launch(headless=True)
            print("✅ Chromium instalado e funcionando")
            
            # Criar uma página e navegar
            page = browser.new_page()
            page.goto("https://example.com")
            title = page.title()
            print(f"✅ Navegação funcionando - Título: {title}")
            
            browser.close()
            print("✅ Browser fechado com sucesso")
            
    except Exception as e:
        print(f"❌ Erro com Chromium: {e}")
        print("\nExecute os seguintes comandos:")
        print("1. playwright install chromium")
        print("2. playwright install-deps")
        return False
    
    # 3. Verificar arquivo de sessão
    print("\n3️⃣ Verificando arquivo de sessão...")
    storage_file = "storage_state_atacadao.json"
    if os.path.exists(storage_file):
        print(f"⚠️ Arquivo de sessão já existe: {storage_file}")
        print("   A sessão anterior será reutilizada")
    else:
        print("📝 Arquivo de sessão não existe (será criado no primeiro login)")
    
    print("\n" + "="*60)
    print("✅ PLAYWRIGHT ESTÁ FUNCIONANDO!")
    print("="*60)
    print("\nPróximos passos:")
    print("1. Para configurar sessão manualmente:")
    print("   python configurar_sessao_atacadao.py")
    print("\n2. Para iniciar o sistema:")
    print("   python app.py")
    
    return True

if __name__ == "__main__":
    success = test_playwright()
    sys.exit(0 if success else 1)