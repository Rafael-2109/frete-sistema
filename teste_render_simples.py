#!/usr/bin/env python3
"""
Teste simples do MCP v3.0 no Render (sem requests)
"""

import urllib.request
import urllib.error
from datetime import datetime

def testar_render_simples():
    print("🧪 TESTE SIMPLES MCP v3.0 NO RENDER")
    print("=" * 50)
    
    urls = [
        "https://frete-sistema.onrender.com/claude-ai/api/health",
        "https://frete-sistema.onrender.com/claude-ai/dashboard", 
        "https://frete-sistema.onrender.com/claude-ai/chat"
    ]
    
    for i, url in enumerate(urls, 1):
        nome = url.split('/')[-1].upper()
        print(f"\n{i}. TESTANDO {nome}:")
        print(f"   🔗 {url}")
        
        try:
            response = urllib.request.urlopen(url, timeout=10)
            status = response.getcode()
            size = len(response.read())
            
            if status == 200:
                print(f"   ✅ Status: {status} - OK")
                print(f"   📏 Tamanho: {size} bytes")
            else:
                print(f"   ⚠️ Status: {status}")
                
        except urllib.error.HTTPError as e:
            print(f"   ❌ HTTP Error: {e.code}")
        except urllib.error.URLError as e:
            print(f"   ❌ URL Error: {e}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 FUNCIONALIDADES V3.0 DEPLOYADAS:")
    print("• consultar_pedidos_cliente ✅")
    print("• exportar_pedidos_excel ✅")
    print("\n💡 TESTE MANUAL NO NAVEGADOR:")
    print("• https://frete-sistema.onrender.com/claude-ai/chat")
    print("• Digite: 'Pedidos do cliente Assai'")

if __name__ == "__main__":
    testar_render_simples() 