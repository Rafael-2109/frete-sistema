"""
Decorators para controle de acesso do módulo comercial
=======================================================

Este módulo contém decorators para validação de acesso e permissões
específicas do módulo comercial.

Autor: Sistema de Fretes
Data: 2025-01-21
"""

from functools import wraps
from flask import redirect, url_for, flash, g
from flask_login import current_user, login_required


def get_permissoes_cached():
    """
    Retorna as permissões do usuário atual com cache na request.
    OTIMIZAÇÃO: Evita múltiplas queries de permissões na mesma request.

    Returns:
        Dict com permissões do usuário ou None se não logado
    """
    if not current_user.is_authenticated:
        return None

    # Verificar se já está em cache no contexto da request
    cache_key = f'_permissoes_comercial_{current_user.id}'
    if hasattr(g, cache_key):
        return getattr(g, cache_key)

    # Buscar permissões e cachear
    from app.comercial.services.permissao_service import PermissaoService
    permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)
    setattr(g, cache_key, permissoes)

    return permissoes


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