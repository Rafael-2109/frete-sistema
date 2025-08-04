"""
Rotas das views (telas) para Carteira Não-Odoo
"""
from flask import Blueprint, render_template
from flask_login import login_required

views_nao_odoo_bp = Blueprint('views_nao_odoo', __name__)

@views_nao_odoo_bp.route('/cadastro-cliente')
@login_required
def cadastro_cliente():
    """Tela de cadastro de cliente não-Odoo"""
    return render_template('carteira/cadastro_cliente.html')

@views_nao_odoo_bp.route('/importacao-carteira')
@login_required
def importacao_carteira():
    """Tela de importação de carteira não-Odoo"""
    return render_template('carteira/importacao_carteira.html')

@views_nao_odoo_bp.route('/carteira-nao-odoo')
@login_required
def carteira_nao_odoo():
    """Tela principal da carteira não-Odoo"""
    return render_template('carteira/carteira_nao_odoo.html')