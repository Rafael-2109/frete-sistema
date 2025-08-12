"""
Módulo de Manufatura/PCP
"""
from flask import Blueprint

# Criar blueprint para o módulo
# Templates ficam em app/templates/manufatura conforme padrão do projeto
manufatura_bp = Blueprint('manufatura', __name__, url_prefix='/manufatura')

# Importar modelos para registrar no SQLAlchemy
from app.manufatura import models  # noqa: F401

# Importar e registrar rotas
from app.manufatura.routes import register_routes
register_routes(manufatura_bp)