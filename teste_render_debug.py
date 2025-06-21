#!/usr/bin/env python3
"""
Debug do problema de 404 no Render
"""

import urllib.request
import urllib.error

def debug_render():
    print("🔍 DEBUG RENDER - TESTANDO DIFERENTES URLs")
    print("=" * 60)
    
    # URLs para testar
    urls_teste = [
        "https://frete-sistema.onrender.com/",
        "https://frete-sistema.onrender.com/auth/login",
        "https://frete-sistema.onrender.com/api/v1/health",
        "https://frete-sistema.onrender.com/claude-ai/api/health",
        "https://frete-sistema.onrender.com/claude-ai/chat",
        "https://frete-sistema.onrender.com/claude-ai/dashboard"
    ]
    
    for url in urls_teste:
        nome = url.replace("https://frete-sistema.onrender.com", "").replace("/", "_") or "ROOT"
        print(f"\n🔗 TESTANDO {nome}:")
        print(f"   URL: {url}")
        
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            response = urllib.request.urlopen(req, timeout=15)
            status = response.getcode()
            content = response.read().decode('utf-8', errors='ignore')
            
            print(f"   ✅ Status: {status}")
            print(f"   📏 Tamanho: {len(content)} bytes")
            
            # Verificar se há conteúdo específico
            if 'claude' in content.lower():
                print("   🤖 Conteúdo Claude detectado")
            if 'login' in content.lower():
                print("   🔐 Página de login detectada")
            if 'error' in content.lower():
                print("   ⚠️ Erro no conteúdo")
            
        except urllib.error.HTTPError as e:
            print(f"   ❌ HTTP Error: {e.code}")
            if e.code == 404:
                print("   📍 Rota não encontrada")
            elif e.code == 403:
                print("   🔒 Acesso negado")
            elif e.code == 500:
                print("   💥 Erro interno do servidor")
            elif e.code == 302:
                print("   🔄 Redirecionamento")
                
        except urllib.error.URLError as e:
            print(f"   ❌ URL Error: {e}")
        except Exception as e:
            print(f"   ❌ Erro inesperado: {e}")
    
    print("\n" + "=" * 60)
    print("💡 ANÁLISE:")
    print("• Se '/' funciona mas '/claude-ai/*' não = problema de blueprint")
    print("• Se '/api/v1/health' funciona = servidor OK")
    print("• Se tudo dá 404 = deploy ainda não concluído")
    print("• Se '/auth/login' funciona = Flask funcionando")

if __name__ == "__main__":
    debug_render() 