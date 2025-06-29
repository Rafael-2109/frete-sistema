from flask import Blueprint, render_template
from flask_login import login_required

# 📦 Blueprint da carteira (seguindo padrão dos outros módulos)
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')

@carteira_bp.route('/')
@login_required
def index():
    """Dashboard do módulo carteira - TODO: Implementar quando necessário"""
    return render_template('carteira/dashboard.html')

# TODO: Implementar rotas da carteira quando necessário 