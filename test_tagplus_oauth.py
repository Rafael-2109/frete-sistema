#!/usr/bin/env python3
"""
Script para testar OAuth2 do TagPlus
"""

import requests
import json
import base64
from urllib.parse import urlencode

# Credenciais
CLIENT_ID = "FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD"
CLIENT_SECRET = "uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7"
REDIRECT_URI = "https://app.tagplus.com.br/xldby0d6/"

print("=" * 60)
print("TESTE OAUTH2 TAGPLUS")
print("=" * 60)

# URLs possíveis
urls_to_test = [
    "https://api.tagplus.com.br/oauth/token",
    "https://developers.tagplus.com.br/oauth/token",
    "https://app.tagplus.com.br/oauth/token",
    "https://tagplus.com.br/api/oauth/token"
]

# Métodos de autenticação a testar
auth_methods = [
    {
        "name": "Client Credentials Flow",
        "data": {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        },
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        "use_json": False
    },
    {
        "name": "Client Credentials (JSON)",
        "data": {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        },
        "headers": {
            "Content-Type": "application/json"
        },
        "use_json": True
    },
    {
        "name": "Basic Auth + Client Credentials",
        "data": {
            "grant_type": "client_credentials"
        },
        "headers": {
            "Authorization": f"Basic {base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        "use_json": False
    },
    {
        "name": "Password Grant (se houver usuário/senha)",
        "data": {
            "grant_type": "password",
            "username": "rayssa",  # Exemplo da documentação
            "password": "A12345",  # Exemplo da documentação
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        },
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        "use_json": False
    }
]

# Testar cada combinação
for url in urls_to_test:
    print(f"\nTestando URL: {url}")
    print("-" * 40)
    
    for method in auth_methods:
        print(f"\nMétodo: {method['name']}")
        
        try:
            if method['use_json']:
                response = requests.post(
                    url,
                    json=method['data'],
                    headers=method['headers'],
                    timeout=10
                )
            else:
                response = requests.post(
                    url,
                    data=urlencode(method['data']) if not method['use_json'] else method['data'],
                    headers=method['headers'],
                    timeout=10
                )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCESSO!")
                data = response.json()
                print(f"Resposta: {json.dumps(data, indent=2)}")
                
                # Se obteve token, testar API
                if 'access_token' in data:
                    access_token = data['access_token']
                    print(f"\nTestando API com token...")
                    
                    # Testar endpoint
                    api_response = requests.get(
                        "https://api.tagplus.com.br/v1/clientes",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/json"
                        },
                        params={"limite": 1}
                    )
                    
                    print(f"API Status: {api_response.status_code}")
                    if api_response.status_code == 200:
                        print("✅ API funcionando!")
                    else:
                        print(f"API Response: {api_response.text[:200]}...")
                
                break  # Se funcionou, não precisa testar outros métodos
                
            else:
                print(f"Erro: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("⏱️ Timeout")
        except requests.exceptions.ConnectionError:
            print("❌ Erro de conexão")
        except Exception as e:
            print(f"❌ Erro: {str(e)}")

# Informações sobre fluxo OAuth2 completo
print("\n" + "=" * 60)
print("FLUXO OAUTH2 COMPLETO:")
print("=" * 60)
print("\n1. URL de Autorização (para o navegador):")

# Construir URL de autorização
auth_params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "read:clientes write:clientes read:nfes"
}

for base in ["https://api.tagplus.com.br", "https://developers.tagplus.com.br", "https://app.tagplus.com.br"]:
    auth_url = f"{base}/oauth/authorize?{urlencode(auth_params)}"
    print(f"\n   {auth_url}")

print("\n2. Após autorização, você receberá um código na URL de retorno")
print("3. Use o código para obter o access_token")

print("\n" + "=" * 60)
print("CONFIGURAÇÃO RECOMENDADA:")
print("=" * 60)
print("\n1. Se nenhum método funcionou:")
print("   - Verifique com o TagPlus o método correto de autenticação")
print("   - Confirme se as credenciais estão ativas")
print("   - Verifique se precisa de IP na whitelist")
print("\n2. Se algum método funcionou:")
print("   - Use o access_token obtido")
print("   - Configure renovação automática com refresh_token")
print("   - Implemente tratamento de expiração")
print("=" * 60)