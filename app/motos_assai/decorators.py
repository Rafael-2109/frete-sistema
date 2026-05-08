"""Decorator de proteção de rotas do módulo Motos Assaí.

Padrão idêntico ao Hora `require_lojas`: gate de status + admin bypass.
"""

from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user


def require_motos_assai(func):
    """Bloqueia rotas para usuários sem `sistema_motos_assai`.

    Comportamento:
    - Não autenticado: redirect para login
    - Sem flag (e não admin): JSON 403 ou flash + redirect para dashboard principal
    - Status != 'ativo': mesma resposta de "sem flag"
    - Admin (perfil='administrador'): sempre passa
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if not current_user.pode_acessar_motos_assai():
            wants_json = (
                request.is_json
                or 'application/json' in request.headers.get('Accept', '')
            )
            if wants_json:
                return jsonify({'error': 'Acesso negado ao módulo Motos Assaí'}), 403
            flash('Acesso negado ao módulo Motos Assaí.', 'danger')
            return redirect(url_for('main.dashboard'))

        return func(*args, **kwargs)
    return wrapper
