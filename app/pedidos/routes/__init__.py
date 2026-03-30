"""
Routes do Modulo Pedidos
Padrao CarVia: register_routes(bp) com sub-modulos.
"""
from flask import Blueprint

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')


def register_routes(bp):
    """Registra todas as rotas no blueprint principal."""
    from app.pedidos.routes.lista_routes import register_lista_routes
    from app.pedidos.routes.edit_routes import register_edit_routes
    from app.pedidos.routes.api_routes import register_api_routes
    from app.pedidos.routes.cotacao_routes import register_cotacao_routes
    from app.pedidos.routes.admin_routes import register_admin_routes

    register_lista_routes(bp)
    register_edit_routes(bp)
    register_api_routes(bp)
    register_cotacao_routes(bp)
    register_admin_routes(bp)


# Auto-registrar ao importar o modulo
register_routes(pedidos_bp)
