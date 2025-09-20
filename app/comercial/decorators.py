"""
Decorators para controle de acesso do módulo comercial
=======================================================

Este módulo contém decorators para validação de acesso e permissões
específicas do módulo comercial.

Autor: Sistema de Fretes
Data: 2025-01-21
"""

from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user, login_required


def comercial_required(f):
    """
    Decorator que garante que apenas usuários com acesso ao módulo comercial possam acessar.
    Vendedores são redirecionados para o dashboard comercial se tentarem acessar outras áreas.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Se for vendedor e não estiver no módulo comercial, redirecionar
        if current_user.perfil == 'vendedor':
            # Vendedor sempre tem acesso ao comercial
            return f(*args, **kwargs)

        # Outros perfis têm acesso total
        return f(*args, **kwargs)
    return decorated_function


def admin_comercial_required(f):
    """
    Decorator que garante que apenas administradores e gerentes comerciais
    possam acessar funções administrativas do módulo comercial.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Verificar se é admin ou gerente comercial
        if current_user.perfil not in ['administrador', 'gerente_comercial']:
            flash('Acesso negado. Apenas administradores e gerentes comerciais podem acessar esta área.', 'danger')
            return redirect(url_for('comercial.dashboard_diretoria'))

        return f(*args, **kwargs)
    return decorated_function


def vendedor_redirect(f):
    """
    Decorator que redireciona vendedores para o dashboard comercial
    se tentarem acessar outras áreas do sistema.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Se for vendedor, redirecionar para comercial
        if current_user.perfil == 'vendedor':
            return redirect(url_for('comercial.dashboard_diretoria'))

        return f(*args, **kwargs)
    return decorated_function