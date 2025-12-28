"""
Dashboard Financeiro - Central de acesso
"""

from flask import render_template
from flask_login import login_required, current_user
from functools import wraps

from app.financeiro.routes import financeiro_bp


def requires_financeiro(f):
    """Decorator para verificar permissao de acesso ao financeiro"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return render_template('errors/403.html'), 403

        # Verificar permissoes
        tem_permissao = (
            current_user.tem_permissao('financeiro') or
            current_user.tem_permissao('fretes') or
            current_user.tem_permissao('faturamento') or
            current_user.pode_acessar_financeiro() or
            current_user.perfil == 'administrador'
        )

        if not tem_permissao:
            return render_template('errors/403.html'), 403

        return f(*args, **kwargs)
    return decorated_function


@financeiro_bp.route('/dashboard')
@login_required
@requires_financeiro
def dashboard():
    """Dashboard central do modulo financeiro"""
    return render_template('financeiro/dashboard.html')
