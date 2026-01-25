"""
Módulo de Business Intelligence (BI) para análise de fretes
"""
from flask import Blueprint

bi_bp = Blueprint('bi', __name__, url_prefix='/bi')

# Importar rotas para registrá-las no blueprint
from app.bi import routes  # noqa: F401, E402
