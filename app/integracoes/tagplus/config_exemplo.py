"""
Exemplo de configuração para integração TagPlus

Para configurar a integração, você pode usar uma das seguintes opções:

MÉTODO 1 - OAuth2 com Tokens (RECOMENDADO):
1. Acesse https://developers.tagplus.com.br/
2. Faça login com sua conta TagPlus
3. Crie um novo aplicativo
4. Use o fluxo OAuth2 para obter Access Token e Refresh Token
   - Acesse a página de importação TagPlus no sistema
   - Digite o Client ID e clique em "Autorizar Aplicação"
   - Após autorizar, cole o Client Secret para obter os tokens

Variáveis de ambiente:
   export TAGPLUS_ACCESS_TOKEN="seu-access-token-aqui"
   export TAGPLUS_REFRESH_TOKEN="seu-refresh-token-aqui"
   export TAGPLUS_CLIENT_ID="seu-client-id-aqui"
   export TAGPLUS_CLIENT_SECRET="seu-client-secret-aqui"
   
Ou no código:
   importador = ImportadorTagPlus(
       access_token='seu-access-token',
       refresh_token='seu-refresh-token',
       client_id='seu-client-id',
       client_secret='seu-client-secret'
   )

MÉTODO 2 - API Key:
Variáveis de ambiente:
   export TAGPLUS_API_KEY="sua-api-key-aqui"
   
Ou no código:
   importador = ImportadorTagPlus(api_key='sua-api-key-aqui')

MÉTODO 3 - Usuário/Senha:
   importador = ImportadorTagPlus(usuario='rayssa', senha='A12345')

NOTAS IMPORTANTES:
- Access Token é válido por 24 horas
- Refresh Token é válido por 15 dias
- Quando você obtém novos tokens, os anteriores são invalidados
- Use o Postman para testar as requisições iniciais

Para teste local sem TagPlus real:
   export TAGPLUS_TEST_MODE=local
   export TAGPLUS_TEST_URL=http://localhost:8080/api/v1
"""

# Configuração de exemplo
TAGPLUS_CONFIG = {
    # Método 1: OAuth2 com Tokens (recomendado)
    'access_token': 'cole-seu-access-token-aqui',
    'refresh_token': 'cole-seu-refresh-token-aqui',
    'client_id': 'cole-seu-client-id-aqui',
    'client_secret': 'cole-seu-client-secret-aqui',
    
    # Método 2: API Key
    'api_key': 'cole-sua-api-key-aqui',
    
    # Método 3: Usuário/Senha (menos seguro)
    'usuario': 'rayssa',
    'senha': 'A12345',
    
    # URLs de webhook para configurar no TagPlus
    'webhooks': {
        'cliente': 'https://sistema-fretes.onrender.com/webhook/tagplus/cliente',
        'nfe': 'https://sistema-fretes.onrender.com/webhook/tagplus/nfe',
        'teste': 'https://sistema-fretes.onrender.com/webhook/tagplus/teste'
    },
    
    # URLs OAuth2
    'oauth': {
        'authorize_url': 'https://developers.tagplus.com.br/oauth/authorize',
        'token_url': 'https://developers.tagplus.com.br/oauth/token',
        'api_base_url': 'https://api.tagplus.com.br/v1'
    }
}