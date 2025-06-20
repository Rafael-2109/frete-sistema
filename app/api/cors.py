from flask import jsonify
from functools import wraps

def cors_headers(origin="*"):
    """Adiciona headers CORS para permitir acesso de outros domínios"""
    headers = {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '86400'
    }
    return headers

def add_cors_headers(response):
    """Adiciona headers CORS a uma resposta"""
    for key, value in cors_headers().items():
        response.headers[key] = value
    return response

def cors_enabled(f):
    """Decorator para habilitar CORS em rotas específicas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Handle preflight requests
        from flask import request
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'OK'})
            return add_cors_headers(response)
        
        # Process normal request
        response = f(*args, **kwargs)
        
        # Add CORS headers to response
        if hasattr(response, 'headers'):
            return add_cors_headers(response)
        else:
            # If response is not a Flask Response object, create one
            from flask import make_response
            resp = make_response(response)
            return add_cors_headers(resp)
    
    return decorated_function 