"""
Módulo Odoo - Integração com ERP Odoo
=====================================

Estrutura organizada por domínio:
- routes/: Rotas organizadas por responsabilidade
- services/: Serviços de integração
- validators/: Validadores específicos
- utils/: Utilitários e mapeamentos
"""

from flask import Blueprint
import logging

logger = logging.getLogger(__name__)

# Importar sub-blueprints com tratamento de erro
def _import_routes():
    """Importar rotas com tratamento de erro"""
    routes = {}
    
    try:
        from .routes.auth import auth_bp
        routes['auth'] = auth_bp
    except ImportError as e:
        logger.warning(f"⚠️ Rotas de autenticação não disponíveis: {e}")
    
    try:
        from .routes.carteira import carteira_bp
        routes['carteira'] = carteira_bp
    except ImportError as e:
        logger.warning(f"⚠️ Rotas de carteira não disponíveis: {e}")
    
    try:
        from .routes.faturamento import faturamento_bp
        routes['faturamento'] = faturamento_bp
    except ImportError as e:
        logger.warning(f"⚠️ Rotas de faturamento não disponíveis: {e}")
    
    try:
        from .routes.dashboard import dashboard_bp
        routes['dashboard'] = dashboard_bp
    except ImportError as e:
        logger.warning(f"⚠️ Rotas de dashboard não disponíveis: {e}")
    
    return routes

# Criar blueprint principal
odoo_bp = Blueprint('odoo', __name__, url_prefix='/odoo')

# Registrar sub-blueprints disponíveis
available_routes = _import_routes()

for route_name, route_bp in available_routes.items():
    odoo_bp.register_blueprint(route_bp)
    logger.info(f"✅ Registrado: {route_name}")

# Rota principal de status
@odoo_bp.route('/')
def index():
    """Página inicial do módulo Odoo"""
    return {
        'module': 'Odoo Integration',
        'version': '1.0.0',
        'available_routes': list(available_routes.keys()),
        'endpoints': [
            '/odoo/test',
            '/odoo/carteira/importar',
            '/odoo/faturamento/importar',
            '/odoo/dashboard'
        ]
    }

logger.info(f"🔗 Módulo Odoo inicializado com {len(available_routes)} rotas")

__all__ = ['odoo_bp'] 