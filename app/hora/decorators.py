"""Decorators de autorização do módulo HORA."""
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def require_lojas(func):
    """Exige autenticação + flag sistema_lojas (ou admin).

    Redireciona para login se anônimo ou dashboard principal se sem permissão.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.pode_acessar_lojas():
            flash('Acesso negado ao módulo Lojas HORA.', 'danger')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    return wrapper


def require_admin_lojas(func):
    """Exige admin (para telas de gestão de permissões do próprio módulo)."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.perfil != 'administrador':
            flash('Acesso negado. Somente administradores.', 'danger')
            return redirect(url_for('hora.dashboard'))
        return func(*args, **kwargs)
    return wrapper
