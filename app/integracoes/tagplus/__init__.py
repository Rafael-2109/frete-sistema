"""
Módulo de integração com TagPlus
"""

# Importar o blueprint principal diretamente de routes
from .routes import tagplus_bp

# O oauth_flow_bp será registrado dentro do app/__init__.py se necessário