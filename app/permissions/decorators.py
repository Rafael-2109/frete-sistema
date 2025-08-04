"""
Decoradores de Permissão - Compatibilidade
==========================================

Este arquivo mantém compatibilidade com o código existente,
redirecionando para o sistema simples de permissões.
"""

from app.permissions.permissions import check_permission as simple_check_permission

# Manter o nome antigo para compatibilidade
def check_permission(route_pattern, *args):
    """
    Mantém compatibilidade com o formato antigo.
    Converte o padrão de rota para nome de módulo.
    """
    # Extrair nome do módulo do padrão de rota
    if '.' in route_pattern:
        module_name = route_pattern.split('.')[0]
    else:
        module_name = route_pattern
    
    # Se foram passados argumentos extras (formato antigo)
    if args:
        module_name = route_pattern  # Primeiro arg era o módulo
    
    # Usar o decorador simples
    return simple_check_permission(module_name)


# Alias para compatibilidade
require_permission = check_permission


def require_permission_admin():
    """
    Decorador que permite apenas administradores.
    Mantido para compatibilidade.
    """
    from functools import wraps
    from flask import abort, request, jsonify
    from flask_login import current_user
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Não autenticado'}), 401
                abort(401)
            
            if current_user.perfil not in ['administrador', 'gerente_comercial']:
                if request.is_json:
                    return jsonify({'error': 'Acesso restrito a administradores'}), 403
                abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def check_edit_permission(route_pattern):
    """
    Verifica permissão de edição.
    Mantido para compatibilidade.
    """
    # Extrair nome do módulo
    if '.' in route_pattern:
        module_name = route_pattern.split('.')[0]
    else:
        module_name = route_pattern
    
    # Usar o decorador simples com ação 'edit'
    return simple_check_permission(module_name, 'edit')