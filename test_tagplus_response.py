#!/usr/bin/env python3
"""
Script para analisar resposta do TagPlus
"""

import requests
from urllib.parse import urlencode

# Credenciais
CLIENT_ID = "FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD"
CLIENT_SECRET = "uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7"

print("=" * 60)
print("ANÁLISE DETALHADA DA RESPOSTA TAGPLUS")
print("=" * 60)

# URL que retornou 200
url = "https://tagplus.com.br/api/oauth/token"

# Testar requisição
print(f"\nTestando: {url}")
print("-" * 40)

try:
    response = requests.post(
        url,
        data=urlencode({
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        },
        timeout=10,
        allow_redirects=True
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"Encoding: {response.encoding}")
    print(f"URL Final: {response.url}")
    print(f"Redirecionamentos: {len(response.history)}")
    
    if response.history:
        print("\nHistórico de redirecionamentos:")
        for i, resp in enumerate(response.history):
            print(f"  {i+1}. {resp.status_code} -> {resp.url}")
    
    print(f"\nPrimeiros 500 caracteres da resposta:")
    print("-" * 40)
    print(response.text[:500])
    print("-" * 40)
    
    # Tentar diferentes parsers
    print("\nTentando interpretar resposta...")
    
    # Como JSON
    try:
        data = response.json()
        print("✅ É JSON válido!")
        print(data)
    except:
        print("❌ Não é JSON")
    
    # Verificar se é HTML
    if 'html' in response.text.lower()[:100]:
        print("📄 Parece ser HTML")
        
        # Extrair título se houver
        import re
        title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
        if title_match:
            print(f"   Título: {title_match.group(1)}")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")

# Testar outras URLs e endpoints
print("\n" + "=" * 60)
print("TESTANDO OUTROS ENDPOINTS")
print("=" * 60)

endpoints_to_test = [
    ("https://api.tagplus.com.br/v1/auth/login", "POST", {
        "username": "rayssa",
        "password": "A12345"
    }),
    ("https://api.tagplus.com.br/auth/login", "POST", {
        "username": "rayssa",
        "password": "A12345"
    }),
    ("https://tagplus.com.br/api/v1/login", "POST", {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }),
    ("https://api.tagplus.com.br/v1/token", "POST", {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
]

for url, method, data in endpoints_to_test:
    print(f"\n{method} {url}")
    try:
        if method == "POST":
            resp = requests.post(url, json=data, timeout=5)
        else:
            resp = requests.get(url, timeout=5)
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Resposta: {resp.text[:200]}...")
    except Exception as e:
        print(f"Erro: {str(e)[:100]}...")

print("\n" + "=" * 60)
print("CONCLUSÃO:")
print("=" * 60)
print("\nParece que as credenciais fornecidas são para um aplicativo OAuth2,")
print("mas precisamos do fluxo completo:")
print("\n1. Usuário acessa URL de autorização no navegador")
print("2. Faz login e autoriza o aplicativo")
print("3. É redirecionado para a URL de retorno com um código")
print("4. Usamos o código para obter o access_token")
print("\nOu talvez seja necessário usar um método diferente de autenticação.")
print("Verifique com o TagPlus qual é o método correto para API.")
print("=" * 60)