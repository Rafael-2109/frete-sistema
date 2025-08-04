"""
Simplified permission decorators for immediate fix
==================================================

This module provides simple, working decorators that fix the immediate
TypeError while the full system is being refactored.
"""

from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def require_permission(*args, **kwargs):
    """
    Simplified decorator that handles both old and new formats
    
    Old format: @require_permission('module', 'function', 'level')
    New format: @require_permission('module.function')
    """
    # Determine format based on number of arguments
    if len(args) == 3:
        # Old format: module, function, level
        module, function, level = args
        permission_key = f"{module}.{function}"
        action = 'edit' if level == 'editar' else 'view'
    elif len(args) == 1:
        # New format: permission string
        permission_key = args[0]
        module = permission_key.split('.')[0] if '.' in permission_key else permission_key
        function = None
        action = 'view'
    else:
        raise TypeError(f"require_permission() takes 1 or 3 arguments, got {len(args)}")
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*fargs, **fkwargs):
            # Check authentication
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Admin bypass
            if hasattr(current_user, 'perfil_nome') and current_user.perfil_nome in ['admin', 'administrador', 'administrator']:
                logger.info(f"✅ Admin access granted for {permission_key}")
                return f(*fargs, **fkwargs)
            
            # Legacy permission check
            if action == 'edit' and hasattr(current_user, 'pode_editar'):
                has_permission = current_user.pode_editar(module)
            elif hasattr(current_user, 'tem_permissao'):
                has_permission = current_user.tem_permissao(module)
            else:
                # Fallback: check if user has any admin role
                has_permission = (hasattr(current_user, 'perfil') and 
                                current_user.perfil in ['administrador', 'admin', 'gerente'])
            
            if not has_permission:
                logger.warning(f"❌ Access denied for {current_user.email} - {permission_key}")
                flash(f'Você não tem permissão para acessar {module}', 'danger')
                return redirect(url_for('main.dashboard'))
            
            logger.info(f"✅ Access granted for {current_user.email} - {permission_key}")
            return f(*fargs, **fkwargs)
        
        return decorated_function
    return decorator


def require_admin_new(*args, **kwargs):
    """Admin-only decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*fargs, **fkwargs):
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Check admin status
            is_admin = (
                (hasattr(current_user, 'perfil_nome') and current_user.perfil_nome == 'admin') or
                (hasattr(current_user, 'perfil') and current_user.perfil in ['administrador', 'admin'])
            )
            
            if not is_admin:
                flash('Acesso restrito a administradores.', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*fargs, **fkwargs)
        
        return decorated_function
    return decorator


# Export the main decorator
__all__ = ['require_permission', 'require_admin_new']