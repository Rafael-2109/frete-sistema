#!/usr/bin/env python3
"""
Script de teste para integração com TagPlus
Testa autenticação e extração de informações
"""

import requests
import json
from datetime import datetime

# Credenciais fornecidas
CLIENT_ID = "FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD"
CLIENT_SECRET = "uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7"
REDIRECT_URI = "https://app.tagplus.com.br/xldby0d6/"

# URLs do TagPlus (baseado na documentação)
BASE_URL = "https://api.tagplus.com.br"
AUTH_URL = "https://api.tagplus.com.br/oauth/token"

print("=" * 60)
print("TESTE DE INTEGRAÇÃO TAGPLUS")
print("=" * 60)

# 1. Obter Access Token
print("\n1. OBTENDO ACCESS TOKEN...")
print(f"   Client ID: {CLIENT_ID[:10]}...")
print(f"   Client Secret: {CLIENT_SECRET[:10]}...")

try:
    # Preparar dados para autenticação
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    # Headers para autenticação
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print("\n   Enviando requisição de autenticação...")
    response = requests.post(AUTH_URL, json=auth_data, headers=headers)
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        token_type = token_data.get("token_type", "Bearer")
        expires_in = token_data.get("expires_in")
        
        print(f"   ✅ Token obtido com sucesso!")
        print(f"   Tipo: {token_type}")
        print(f"   Expira em: {expires_in} segundos")
        print(f"   Token: {access_token[:20]}...")
        
        # 2. Testar endpoints da API
        print("\n2. TESTANDO ENDPOINTS DA API...")
        
        # Headers com autenticação
        api_headers = {
            "Authorization": f"{token_type} {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Listar endpoints disponíveis
        endpoints_to_test = [
            "/api/v1/pedidos",
            "/api/v1/notas-fiscais", 
            "/api/v1/produtos",
            "/api/v1/clientes",
            "/api/v1/transportadoras",
            "/api/pedidos",  # Versão alternativa
            "/api/nfe",      # Versão alternativa
            "/pedidos",      # Sem prefixo api
            "/nfe"           # Sem prefixo api
        ]
        
        for endpoint in endpoints_to_test:
            try:
                url = BASE_URL + endpoint
                print(f"\n   Testando: {endpoint}")
                
                # Adicionar parâmetros de data para limitar resultados
                params = {
                    "data_inicial": "2025-08-01",
                    "data_final": "2025-08-05",
                    "limite": 5
                }
                
                resp = requests.get(url, headers=api_headers, params=params, timeout=10)
                print(f"   Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        print(f"   ✅ Sucesso! {len(data)} registros retornados")
                        if data:
                            print(f"   Exemplo: {json.dumps(data[0], indent=2)[:200]}...")
                    elif isinstance(data, dict):
                        print(f"   ✅ Sucesso! Resposta recebida")
                        print(f"   Campos: {list(data.keys())}")
                    else:
                        print(f"   ✅ Sucesso! Tipo: {type(data)}")
                elif resp.status_code == 404:
                    print("   ❌ Endpoint não encontrado")
                elif resp.status_code == 401:
                    print("   ❌ Não autorizado")
                else:
                    print(f"   ❌ Erro: {resp.text[:100]}...")
                    
            except requests.exceptions.Timeout:
                print("   ⏱️ Timeout na requisição")
            except Exception as e:
                print(f"   ❌ Erro: {str(e)}")
        
        # 3. Testar webhook (simulação)
        print("\n3. INFORMAÇÕES PARA WEBHOOK...")
        print(f"   URL do Webhook: https://sistema-fretes.onrender.com/tagplus/webhook")
        print(f"   Headers necessários:")
        print(f"   - X-TagPlus-Token: {access_token[:20]}...")
        print(f"   - Content-Type: application/json")
        
    else:
        print(f"   ❌ Erro na autenticação: {response.status_code}")
        print(f"   Resposta: {response.text}")
        
        # Tentar outro método de autenticação
        print("\n   Tentando autenticação básica...")
        import base64
        
        credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        alt_headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        alt_data = "grant_type=client_credentials"
        
        alt_response = requests.post(AUTH_URL, data=alt_data, headers=alt_headers)
        print(f"   Status (Basic Auth): {alt_response.status_code}")
        if alt_response.status_code == 200:
            print("   ✅ Autenticação básica funcionou!")
            print(f"   Resposta: {alt_response.json()}")
        else:
            print(f"   ❌ Falhou também: {alt_response.text}")

except Exception as e:
    print(f"❌ Erro geral: {str(e)}")
    import traceback
    traceback.print_exc()

# 4. Instruções para configuração
print("\n" + "=" * 60)
print("INSTRUÇÕES PARA CONFIGURAÇÃO:")
print("=" * 60)
print("\n1. Se a autenticação funcionou:")
print("   - Atualize app/integracoes/tagplus/config.py com as credenciais")
print("   - Configure o webhook no painel do TagPlus")
print("   - URL: https://sistema-fretes.onrender.com/tagplus/webhook")
print("\n2. Se não funcionou:")
print("   - Verifique se as credenciais estão corretas")
print("   - Confirme o método de autenticação com o TagPlus")
print("   - Verifique se a API está ativa para sua conta")
print("\n3. Próximos passos:")
print("   - Configurar mapeamento de campos")
print("   - Implementar processamento de pedidos")
print("   - Configurar sincronização automática")
print("=" * 60)