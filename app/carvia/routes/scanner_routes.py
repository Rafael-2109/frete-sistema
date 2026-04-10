"""
Scanner de Etiqueta Moto — Rota CarVia
=======================================

Tela dedicada para leitura de etiquetas de motos via camera.
Exibe resultados das leituras em lista para conferencia.
"""

import logging
from flask import render_template
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)


def register_scanner_routes(bp):

    @bp.route('/scanner-moto')  # type: ignore
    @login_required
    def scanner_moto():  # type: ignore
        """Tela de scanner de etiqueta de moto."""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import flash, redirect, url_for
            flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
            return redirect(url_for('main.dashboard'))

        return render_template('carvia/scanner_moto.html')
