"""Decorators de autorizacao do Agente Lojas HORA."""
from functools import wraps

from flask import jsonify, redirect, url_for, flash, request
from flask_login import current_user


def require_acesso_agente_lojas(func):
    """Exige autenticacao + acesso ao modulo Lojas HORA (ou admin).

    Regra:
        - current_user.pode_acessar_lojas() -> True  (sistema_lojas OR admin)
    Resposta:
        - Rotas API (JSON): 401/403 JSON
        - Paginas: redirect para login/dashboard com flash
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        is_api = (
            request.path.startswith('/agente-lojas/api/')
            or request.headers.get('Accept', '').startswith('application/json')
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

        if not current_user.is_authenticated:
            if is_api:
                return jsonify({
                    'success': False,
                    'error': 'Nao autenticado',
                }), 401
            return redirect(url_for('auth.login'))

        if not current_user.pode_acessar_lojas():
            if is_api:
                return jsonify({
                    'success': False,
                    'error': 'Acesso negado ao Agente Lojas HORA',
                }), 403
            flash('Acesso negado ao Agente Lojas HORA.', 'danger')
            return redirect(url_for('main.dashboard'))

        return func(*args, **kwargs)

    return wrapper
