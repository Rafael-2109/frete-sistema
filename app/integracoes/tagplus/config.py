"""
Configuração da integração TagPlus
"""

import os

# Credenciais fornecidas
TAGPLUS_CONFIG = {
    # OAuth2 Credentials
    'client_id': os.environ.get('TAGPLUS_CLIENT_ID', 'FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD'),
    'client_secret': os.environ.get('TAGPLUS_CLIENT_SECRET', 'uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7'),
    'redirect_uri': os.environ.get('TAGPLUS_REDIRECT_URI', 'https://app.tagplus.com.br/xldby0d6/'),
    
    # Tokens (serão obtidos via OAuth2)
    'access_token': os.environ.get('TAGPLUS_ACCESS_TOKEN', ''),
    'refresh_token': os.environ.get('TAGPLUS_REFRESH_TOKEN', ''),
    
    # URLs OAuth2
    'oauth': {
        'authorize_url': 'https://developers.tagplus.com.br/oauth/authorize',
        'token_url': 'https://developers.tagplus.com.br/oauth/token',
        'api_base_url': 'https://api.tagplus.com.br/v1'
    },
    
    # URLs alternativas para teste
    'api_urls': {
        'base': 'https://api.tagplus.com.br',
        'v1': 'https://api.tagplus.com.br/v1',
        'oauth': 'https://developers.tagplus.com.br'
    },
    
    # Endpoints
    'endpoints': {
        'pedidos': '/pedidos',
        'notas_fiscais': '/notas-fiscais',
        'clientes': '/clientes',
        'produtos': '/produtos'
    },
    
    # Webhooks
    'webhooks': {
        'base_url': 'https://sistema-fretes.onrender.com/tagplus/webhook',
        'cliente': 'https://sistema-fretes.onrender.com/tagplus/webhook/cliente',
        'nfe': 'https://sistema-fretes.onrender.com/tagplus/webhook/nfe',
        'pedido': 'https://sistema-fretes.onrender.com/tagplus/webhook/pedido'
    },
    
    # Configurações de requisição
    'timeout': 30,
    'max_retries': 3,
    'verify_ssl': True
}

# Função helper para obter configuração
def get_config(key, default=None):
    """Obtém configuração aninhada usando notação de ponto"""
    keys = key.split('.')
    value = TAGPLUS_CONFIG
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value