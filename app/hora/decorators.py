"""Decorators de autorizacao do modulo HORA."""
from __future__ import annotations

from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user


def _is_ajax() -> bool:
    return request.is_json or request.headers.get('Accept') == 'application/json'


def require_lojas(func):
    """Exige autenticacao + flag sistema_lojas (ou admin).

    Redireciona para login se anonimo ou dashboard principal se sem permissao.
    Mantida para retrocompat enquanto migramos rotas para `require_hora_perm`.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.pode_acessar_lojas():
            flash('Acesso negado ao modulo Lojas HORA.', 'danger')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    return wrapper


def require_admin_lojas(func):
    """Exige admin (para telas de gestao de permissoes do proprio modulo)."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.perfil != 'administrador':
            flash('Acesso negado. Somente administradores.', 'danger')
            return redirect(url_for('hora.dashboard'))
        return func(*args, **kwargs)
    return wrapper


def require_hora_perm(modulo: str, acao: str = 'ver'):
    """Exige permissao granular (modulo, acao) no HORA.

    Admin sempre passa. Usuario sem sistema_lojas: bloqueado.
    Usuario com sistema_lojas mas sem permissao explicita: bloqueado.

    Em rotas AJAX (Accept: application/json) retorna 403 JSON.
    Em rotas HTML faz flash + redirect para o dashboard HORA (ou login).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                if _is_ajax():
                    return jsonify({'ok': False, 'erro': 'nao autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Acesso ao modulo (sistema_lojas ou admin) e pre-requisito.
            if not current_user.pode_acessar_lojas():
                if _is_ajax():
                    return jsonify({'ok': False, 'erro': 'sem acesso ao modulo'}), 403
                flash('Acesso negado ao modulo Lojas HORA.', 'danger')
                return redirect(url_for('main.dashboard'))

            # Import tardio evita ciclo (services -> models -> app -> ...)
            from app.hora.services.permissao_service import tem_perm
            if not tem_perm(current_user, modulo, acao):
                if _is_ajax():
                    return jsonify({
                        'ok': False,
                        'erro': f'sem permissao: {modulo}.{acao}',
                    }), 403
                flash(
                    f'Acesso negado: voce nao tem permissao "{acao}" em "{modulo}".',
                    'danger',
                )
                # Tenta voltar para o dashboard HORA; se nem isso o usuario tem,
                # cai no dashboard principal.
                if tem_perm(current_user, 'dashboard', 'ver') or current_user.perfil == 'administrador':
                    return redirect(url_for('hora.dashboard'))
                return redirect(url_for('main.dashboard'))
            return func(*args, **kwargs)
        return wrapper
    return decorator
