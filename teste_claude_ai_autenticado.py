#!/usr/bin/env python3
"""
Teste das rotas Claude AI com autenticação simulada
"""

import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar

def teste_claude_ai_autenticado():
    print("🔐 TESTANDO CLAUDE AI COM AUTENTICAÇÃO SIMULADA")
    print("=" * 60)
    
    # Criar gerenciador de cookies para manter sessão
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # Headers padrão
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    base_url = "https://frete-sistema.onrender.com"
    
    # Teste 1: Verificar se a página de login está acessível
    print("1. 🔍 TESTANDO PÁGINA DE LOGIN:")
    try:
        req = urllib.request.Request(f"{base_url}/auth/login", headers=headers)
        response = opener.open(req, timeout=10)
        
        if response.getcode() == 200:
            print("   ✅ Página de login acessível")
            content = response.read().decode('utf-8', errors='ignore')
            
            if 'claude' in content.lower():
                print("   🤖 Referência ao Claude encontrada")
            if 'login' in content.lower():
                print("   📝 Formulário de login detectado")
        else:
            print(f"   ⚠️ Status inesperado: {response.getcode()}")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 2: Tentar acessar rotas Claude AI (esperado: redirecionamento)
    print("\n2. 🤖 TESTANDO ROTAS CLAUDE AI (sem autenticação):")
    
    rotas_claude = [
        "/claude-ai/chat",
        "/claude-ai/dashboard", 
        "/claude-ai/api/health"
    ]
    
    for rota in rotas_claude:
        print(f"   🔗 Testando: {rota}")
        try:
            req = urllib.request.Request(f"{base_url}{rota}", headers=headers)
            response = opener.open(req, timeout=10)
            
            if response.getcode() == 200:
                print(f"   ✅ Acessível: {response.getcode()}")
            elif response.getcode() == 302:
                print(f"   🔄 Redirecionamento para login: {response.getcode()}")
                # Isso é esperado para rotas protegidas
            else:
                print(f"   ⚠️ Status: {response.getcode()}")
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"   ❌ Rota não encontrada: {e.code}")
            elif e.code == 302:
                print(f"   🔄 Redirecionamento: {e.code}")
            elif e.code == 403:
                print(f"   🔒 Acesso negado: {e.code}")
            else:
                print(f"   ❌ Erro HTTP: {e.code}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    # Teste 3: Verificar se as rotas estão registradas
    print("\n3. 🔍 VERIFICANDO REGISTRO DAS ROTAS:")
    
    # Tentar acessar uma rota que deve existir mas retornar 302
    try:
        req = urllib.request.Request(f"{base_url}/claude-ai/chat", headers=headers)
        response = opener.open(req, timeout=10)
        print("   ✅ Rota /claude-ai/chat registrada (acessível)")
    except urllib.error.HTTPError as e:
        if e.code == 302:
            print("   ✅ Rota /claude-ai/chat registrada (redirecionamento)")
        elif e.code == 404:
            print("   ❌ Rota /claude-ai/chat NÃO registrada")
        else:
            print(f"   ⚠️ Rota /claude-ai/chat retornou: {e.code}")
    except Exception as e:
        print(f"   ❌ Erro ao testar rota: {e}")
    
    print("\n" + "=" * 60)
    print("📊 CONCLUSÃO:")
    print("• Se retornar 302 (redirecionamento) = ✅ Rotas funcionando")
    print("• Se retornar 404 = ❌ Blueprint não registrado")
    print("• Se retornar 200 = ✅ Rotas acessíveis")
    print("• Se retornar 403 = ⚠️ Problema de autenticação")
    
    print("\n💡 PRÓXIMO PASSO:")
    print("• Testar via navegador com login real")
    print("• URL: https://frete-sistema.onrender.com/claude-ai/chat")

if __name__ == "__main__":
    teste_claude_ai_autenticado() 