"""
Rotas do Dashboard/Hub inicial do módulo de Manufatura
"""
from flask import render_template
from flask_login import login_required


def register_dashboard_routes(bp):

    @bp.route('/')
    @login_required
    def index():
        """Tela inicial do módulo de manufatura - Hub de acesso"""
        return render_template('manufatura/index.html')
