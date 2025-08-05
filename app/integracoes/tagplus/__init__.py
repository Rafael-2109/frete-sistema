"""
Módulo de integração com TagPlus
"""

from flask import Blueprint

# Blueprint principal do TagPlus
tagplus_bp = Blueprint('tagplus', __name__)

# Importar e registrar sub-blueprints
from .oauth_flow import tagplus_oauth_bp
from .routes import tagplus_bp as tagplus_routes_bp

# Registrar OAuth como sub-blueprint
tagplus_bp.register_blueprint(tagplus_oauth_bp)