"""
Sistema de autenticação para API Odoo
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from flask import request, g
from functools import wraps

logger = logging.getLogger(__name__)

# Configurações de autenticação
_jwt_secret = os.getenv('JWT_SECRET_KEY')
if not _jwt_secret:
    logger.warning(
        "⚠️ JWT_SECRET_KEY não configurada! "
        "Configure via variável de ambiente para segurança em produção."
    )
    _jwt_secret = 'dev-jwt-key-insecure-local-only'
JWT_SECRET_KEY = _jwt_secret
API_KEY_HEADER = 'X-API-Key'
JWT_HEADER = 'Authorization'

# API Keys válidas - devem ser configuradas via variáveis de ambiente em produção
# Formato: API_KEY_<NOME>=<permissões separadas por vírgula>
# Exemplo: API_KEY_ODOO_INTEGRATION=carteira,faturamento
def _load_api_keys_from_env():
    """Carrega API keys das variáveis de ambiente."""
    keys = {}
    for key, value in os.environ.items():
        if key.startswith('API_KEY_') and not key.endswith('_NAME'):
            key_id = key[8:].lower().replace('_', '-')
            key_name = os.getenv(f'{key}_NAME', key_id.replace('-', ' ').title())
            permissions = [p.strip() for p in value.split(',')]
            keys[os.getenv(f'API_KEY_{key[8:]}_VALUE', value)] = {
                'name': key_name,
                'permissions': permissions,
                'active': True
            }
    return keys

# Carrega API keys do ambiente ou usa fallback para desenvolvimento
_env_keys = _load_api_keys_from_env()
VALID_API_KEYS = _env_keys if _env_keys else {
    # Fallback apenas para desenvolvimento local (NUNCA usar em produção)
    'dev-api-key-local-only': {
        'name': 'Development Key',
        'permissions': ['carteira', 'faturamento'],
        'active': os.getenv('ENVIRONMENT') != 'production'
    },
}

def require_api_key():
    """
    Verifica se requisição tem API Key válida
    
    Returns:
        bool: True se válida, False caso contrário
    """
    try:
        # Buscar API Key nos headers
        api_key = request.headers.get(API_KEY_HEADER)
        
        if not api_key:
            logger.warning("API Key não fornecida")
            return False
        
        # Verificar se API Key é válida
        if api_key not in VALID_API_KEYS:
            logger.warning(f"API Key inválida: {api_key[:10]}...")
            return False
        
        # Verificar se está ativa
        key_info = VALID_API_KEYS[api_key]
        if not key_info.get('active', False):
            logger.warning(f"API Key desativada: {api_key[:10]}...")
            return False
        
        # Armazenar informações da API key no contexto
        g.api_key_info = key_info
        return True
        
    except Exception as e:
        logger.error(f"Erro na verificação de API Key: {str(e)}")
        return False

def require_jwt_token():
    """
    Verifica se requisição tem JWT Token válido
    
    Returns:
        bool: True se válido, False caso contrário
    """
    try:
        # Buscar JWT Token nos headers
        auth_header = request.headers.get(JWT_HEADER)
        
        if not auth_header:
            logger.warning("JWT Token não fornecido")
            return False
        
        # Extrair token do header "Bearer token"
        if not auth_header.startswith('Bearer '):
            logger.warning("JWT Token deve ter formato 'Bearer token'")
            return False
        
        token = auth_header.split(' ')[1]
        
        # Verificar e decodificar token
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            
            # Verificar se token não expirou
            if 'exp' in payload:
                if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                    logger.warning("JWT Token expirado")
                    return False
            
            # Armazenar informações do token no contexto
            g.jwt_payload = payload
            return True
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT Token expirado")
            return False
        except jwt.InvalidTokenError:
            logger.warning("JWT Token inválido")
            return False
            
    except Exception as e:
        logger.error(f"Erro na verificação de JWT Token: {str(e)}")
        return False

def generate_jwt_token(user_id, username, permissions=None, expires_in_hours=24):
    """
    Gera um JWT Token para autenticação
    
    Args:
        user_id (int): ID do usuário
        username (str): Nome do usuário
        permissions (list): Lista de permissões
        expires_in_hours (int): Expiração em horas
        
    Returns:
        str: JWT Token
    """
    try:
        payload = {
            'user_id': user_id,
            'username': username,
            'permissions': permissions or [],
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours)
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
        return token
        
    except Exception as e:
        logger.error(f"Erro ao gerar JWT Token: {str(e)}")
        return None

def validate_permissions(required_permissions):
    """
    Valida se usuário tem permissões necessárias
    
    Args:
        required_permissions (list): Lista de permissões necessárias
        
    Returns:
        bool: True se tem permissões, False caso contrário
    """
    try:
        # Verificar permissões da API Key
        if hasattr(g, 'api_key_info'):
            api_permissions = g.api_key_info.get('permissions', [])
            if not all(perm in api_permissions for perm in required_permissions):
                logger.warning(f"API Key não tem permissões necessárias: {required_permissions}")
                return False
        
        # Verificar permissões do JWT Token
        if hasattr(g, 'jwt_payload'):
            jwt_permissions = g.jwt_payload.get('permissions', [])
            if not all(perm in jwt_permissions for perm in required_permissions):
                logger.warning(f"JWT Token não tem permissões necessárias: {required_permissions}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Erro na validação de permissões: {str(e)}")
        return False

def require_permission(permission):
    """
    Decorator para exigir permissão específica
    
    Args:
        permission (str): Permissão necessária
        
    Returns:
        function: Decorator
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not validate_permissions([permission]):
                return {
                    'success': False,
                    'message': f'Permissão "{permission}" necessária',
                    'error_code': 'INSUFFICIENT_PERMISSIONS'
                }, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Configuração de rate limiting básico (em produção, usar Redis)
RATE_LIMIT_STORE = {}

def check_rate_limit(identifier, limit=100, window=3600):
    """
    Verifica rate limiting
    
    Args:
        identifier (str): Identificador único (IP, API Key, etc.)
        limit (int): Limite de requisições
        window (int): Janela de tempo em segundos
        
    Returns:
        bool: True se dentro do limite, False caso contrário
    """
    try:
        now = datetime.utcnow()
        
        # Limpar registros antigos
        cutoff = now - timedelta(seconds=window)
        if identifier in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[identifier] = [
                req_time for req_time in RATE_LIMIT_STORE[identifier] 
                if req_time > cutoff
            ]
        
        # Verificar limite
        if identifier not in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[identifier] = []
        
        if len(RATE_LIMIT_STORE[identifier]) >= limit:
            logger.warning(f"Rate limit excedido para {identifier}")
            return False
        
        # Registrar requisição atual
        RATE_LIMIT_STORE[identifier].append(now)
        return True
        
    except Exception as e:
        logger.error(f"Erro no rate limiting: {str(e)}")
        return True  # Em caso de erro, permitir requisição

def get_current_user_info():
    """
    Obtém informações do usuário atual do contexto
    
    Returns:
        dict: Informações do usuário
    """
    user_info = {
        'authenticated': False,
        'user_id': None,
        'username': None,
        'permissions': [],
        'api_key_name': None
    }
    
    # Informações do JWT Token
    if hasattr(g, 'jwt_payload'):
        user_info.update({
            'authenticated': True,
            'user_id': g.jwt_payload.get('user_id'),
            'username': g.jwt_payload.get('username'),
            'permissions': g.jwt_payload.get('permissions', [])
        })
    
    # Informações da API Key
    if hasattr(g, 'api_key_info'):
        user_info.update({
            'api_key_name': g.api_key_info.get('name'),
            'permissions': list(set(user_info['permissions'] + g.api_key_info.get('permissions', [])))
        })
    
    return user_info

def create_test_token():
    """
    Cria token de teste para desenvolvimento
    
    Returns:
        str: JWT Token de teste
    """
    return generate_jwt_token(
        user_id=1,
        username='test_user',
        permissions=['carteira', 'faturamento'],
        expires_in_hours=24
    ) 