#!/usr/bin/env python3
"""
Gera URLs de autorização OAuth2 corrigidas para TagPlus
"""

from urllib.parse import urlencode
import webbrowser

print("=" * 70)
print("GERADOR DE URLs OAUTH2 - TAGPLUS")
print("=" * 70)

# URL base correta
BASE_AUTH_URL = "https://api.tagplus.com.br/oauth/authorize"

# Configurações das APIs
apis = {
    "clientes": {
        "client_id": "FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD",
        "redirect_uri": "https://sistema-fretes.onrender.com/webhook/tagplus/cliente",
        "scope": "read:clientes write:clientes",
        "state": "cliente_auth_123"
    },
    "notas": {
        "client_id": "8YZNqaklKj3CfIkOtkoV9ILpCllAtalT",
        "redirect_uri": "https://sistema-fretes.onrender.com/webhook/tagplus/nfe",
        "scope": "read:nfes read:financeiros",
        "state": "notas_auth_456"
    }
}

print("\n🔗 URLs de Autorização Corrigidas:\n")

urls_geradas = {}

for api_name, config in apis.items():
    params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": config["scope"],
        "state": config["state"]
    }
    
    url_completa = f"{BASE_AUTH_URL}?{urlencode(params)}"
    urls_geradas[api_name] = url_completa
    
    print(f"{'='*70}")
    print(f"API de {api_name.upper()}")
    print(f"{'='*70}")
    print(f"Client ID: {config['client_id'][:20]}...")
    print(f"Redirect: {config['redirect_uri']}")
    print(f"Scopes: {config['scope']}")
    print(f"\n📎 URL Completa:")
    print(url_completa)
    print()

print("=" * 70)
print("INSTRUÇÕES")
print("=" * 70)
print("""
1. Certifique-se que o sistema está rodando no Render
2. Copie uma das URLs acima
3. Cole no navegador
4. Faça login no TagPlus
5. Autorize o acesso
6. Você será redirecionado para o sistema
7. Repita para a outra API

⚠️ IMPORTANTE:
- O sistema PRECISA estar online no Render para receber o callback
- Após autorizar, os tokens serão salvos automaticamente
- Os tokens expiram em 24h (access) e 15 dias (refresh)
""")

# Opção de abrir no navegador
print("\n" + "=" * 70)
resposta = input("\nDeseja copiar as URLs para a área de transferência? (s/n): ").strip().lower()

if resposta == 's':
    try:
        import pyperclip
        texto = f"""
URLs de Autorização TagPlus:

1. API de Clientes:
{urls_geradas['clientes']}

2. API de Notas:
{urls_geradas['notas']}
"""
        pyperclip.copy(texto)
        print("✅ URLs copiadas para a área de transferência!")
    except ImportError:
        print("\n📋 Copie manualmente as URLs acima")
        print("(instale 'pip install pyperclip' para copiar automaticamente)")
else:
    print("\n📋 Copie manualmente as URLs acima quando precisar")