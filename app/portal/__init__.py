"""
Módulo de Integração com Portais de Agendamento
Sistema para automatizar agendamentos em portais de clientes
"""

from flask import Blueprint

# Criar Blueprint para o módulo portal
portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

# Importar rotas para registrá-las no blueprint
from app.portal import routes