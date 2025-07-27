"""
Módulo de Permissões Avançadas
Sistema granular para controle de acesso baseado em módulos e funções
"""

from flask import Blueprint

# Criar blueprint para permissões
permissions_bp = Blueprint('permissions', __name__, url_prefix='/permissions')

# Apply permission bypass patch for admin
try:
    from . import decorators_patch
except Exception as e:
    import logging
    logging.warning(f"Could not apply permissions patch: {e}")

# Importar rotas ANTES de registrar o blueprint
from . import routes
from . import routes_hierarchical

# Função para inicializar o módulo
def init_app(app):
    """Inicializa o módulo de permissões"""
    # Registrar blueprint
    app.register_blueprint(permissions_bp)
    
    # Registrar blueprint da API
    try:
        from .api import permissions_api_bp
        app.register_blueprint(permissions_api_bp)
    except ImportError:
        # Try alternative name
        try:
            from .api import permissions_api
            app.register_blueprint(permissions_api)
        except ImportError:
            import logging
            logging.warning("Could not import permissions API blueprint")
    
    # Registrar blueprint da API hierárquica
    try:
        from .api_hierarchical import hierarchical_api
        app.register_blueprint(hierarchical_api)
    except ImportError:
        import logging
        logging.warning("Could not import hierarchical API blueprint")
    
    # Registrar funções auxiliares para templates
    from .utils import usuario_pode_ver, usuario_pode_editar, get_modulos_menu
    app.jinja_env.globals.update(
        usuario_pode_ver=usuario_pode_ver,
        usuario_pode_editar=usuario_pode_editar,
        get_modulos_menu=get_modulos_menu
    )