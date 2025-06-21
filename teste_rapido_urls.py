#!/usr/bin/env python3
"""
TESTE RÁPIDO - URLs MCP Corrigidas
Verifica se as correções de URL funcionaram
"""

import urllib.request
import urllib.error
from datetime import datetime

def teste_rapido():
    """Teste rápido das URLs MCP"""
    
    print("="*60)
    print("⚡ TESTE RÁPIDO - URLs MCP CORRIGIDAS")
    print("="*60)
    print(f"Testado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    base_url = "https://frete-sistema.onrender.com"
    
    # URLs para testar
    urls_teste = [
        ("Claude AI Dashboard", f"{base_url}/claude-ai/dashboard"),
        ("Claude AI Chat", f"{base_url}/claude-ai/chat"), 
        ("Claude AI Health API", f"{base_url}/claude-ai/api/health")
    ]
    
    for nome, url in urls_teste:
        print(f"🔍 {nome}")
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Teste-Rapido'})
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.getcode()
                
                if status in [200, 302, 401]:
                    print(f"   ✅ {status} - OK")
                else:
                    print(f"   ⚠️ {status} - Inesperado")
                    
        except urllib.error.HTTPError as e:
            if e.code in [200, 302, 401]:
                print(f"   ✅ {e.code} - OK (Auth)")
            else:
                print(f"   ❌ {e.code} - Erro")
                
        except Exception as e:
            print(f"   💥 Erro: {str(e)[:40]}...")
    
    print("\n" + "="*60)
    print("🎯 RESULTADO:")
    print("✅ Se todos mostraram status 200/302/401 = URLs funcionando")
    print("❌ Se algum mostrou 404 = Ainda com problema")
    print("⏳ Se erro de timeout = Deploy ainda em andamento")
    print("="*60)

if __name__ == "__main__":
    teste_rapido() 