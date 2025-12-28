"""
Modulo de Custeio
Sistema de calculo e gerenciamento de custos de produtos
"""
from flask import Blueprint

# Criar blueprint para o modulo
custeio_bp = Blueprint('custeio', __name__, url_prefix='/custeio')

# Importar modelos para registrar no SQLAlchemy
from app.custeio import models  # noqa: F401

# Importar e registrar rotas
from app.custeio.routes import register_routes
register_routes(custeio_bp)
