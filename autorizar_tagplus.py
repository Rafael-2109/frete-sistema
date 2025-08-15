#!/usr/bin/env python3
"""
Script para iniciar o processo de autorização OAuth2 do TagPlus
"""

import webbrowser
from app import create_app
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2

def main():
    print("=" * 70)
    print("AUTORIZAÇÃO OAUTH2 - TAGPLUS")
    print("=" * 70)
    
    print("\nEste script irá gerar URLs de autorização para as APIs do TagPlus.")
    print("Você precisará acessar essas URLs no navegador e autorizar o acesso.\n")
    
    app = create_app()
    
    with app.app_context():
        # API de Clientes
        print("1️⃣ API DE CLIENTES")
        print("-" * 40)
        oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
        url_clientes = oauth_clientes.get_authorization_url(state='cliente_auth_123')
        
        print("URL de autorização:")
        print(url_clientes)
        print("\n📝 Callback esperado em:")
        print("https://sistema-fretes.onrender.com/webhook/tagplus/cliente")
        
        resposta = input("\nDeseja abrir no navegador? (s/n): ").strip().lower()
        if resposta == 's':
            webbrowser.open(url_clientes)
        
        print("\n" + "=" * 70)
        
        # API de Notas
        print("2️⃣ API DE NOTAS FISCAIS")
        print("-" * 40)
        oauth_notas = TagPlusOAuth2V2(api_type='notas')
        url_notas = oauth_notas.get_authorization_url(state='notas_auth_456')
        
        print("URL de autorização:")
        print(url_notas)
        print("\n📝 Callback esperado em:")
        print("https://sistema-fretes.onrender.com/webhook/tagplus/nfe")
        
        resposta = input("\nDeseja abrir no navegador? (s/n): ").strip().lower()
        if resposta == 's':
            webbrowser.open(url_notas)
        
        print("\n" + "=" * 70)
        print("INSTRUÇÕES:")
        print("-" * 40)
        print("1. Acesse as URLs acima no navegador")
        print("2. Faça login no TagPlus com suas credenciais")
        print("3. Autorize o acesso aos dados solicitados")
        print("4. Você será redirecionado para o sistema após autorizar")
        print("5. Os tokens serão salvos automaticamente")
        print("\n⚠️  IMPORTANTE:")
        print("- As URLs de callback devem estar acessíveis publicamente")
        print("- Se estiver testando localmente, use ngrok ou similar")
        print("- Os tokens expiram em 24h (access) e 15 dias (refresh)")
        print("=" * 70)
        
        print("\n🌐 INTERFACE WEB:")
        print("Você também pode acessar a interface web em:")
        print("https://sistema-fretes.onrender.com/tagplus/oauth/")
        print("(requer login no sistema)")

if __name__ == "__main__":
    main()