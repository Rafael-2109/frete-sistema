"""
Módulo de Permissões Avançadas
Sistema granular para controle de acesso baseado em módulos e funções
"""

from flask import Blueprint

# Criar blueprint para permissões
permissions_bp = Blueprint('permissions', __name__, url_prefix='/admin/permissions')

# Importar rotas
from . import routes 