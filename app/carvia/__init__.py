"""
Modulo CarVia — Gestao de Frete Subcontratado
==============================================

Fluxo: Importar NFs (PDF/XML) -> Criar Operacao (CTe CarVia) ->
       Subcontratar Transportadoras -> Cotar Frete -> Faturar
"""

from flask import Blueprint

carvia_bp = Blueprint(
    'carvia',
    __name__,
    url_prefix='/carvia',
    template_folder='../templates/carvia'
)

from app.carvia.routes import register_routes  # noqa: E402


def init_app(app):
    """Registra o blueprint CarVia e sub-blueprints"""
    register_routes(carvia_bp)
    app.register_blueprint(carvia_bp)
