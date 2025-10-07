"""
Blueprint principal do sistema MotoChefe
"""
from flask import Blueprint

# Criar blueprint
# Templates em: app/templates/motochefe/
motochefe_bp = Blueprint('motochefe', __name__, url_prefix='/motochefe')

# Importar rotas depois de criar blueprint para evitar imports circulares
from . import cadastros, produtos, operacional, logistica, vendas, financeiro, extrato, titulos_a_pagar

__all__ = ['motochefe_bp']
