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


# Context processor: badge de aprovacoes PENDENTE no menu CarVia.
# Registrado ANTES do init_app para evitar AssertionError de blueprint
# ja registrado (Flask 3).
@carvia_bp.context_processor
def inject_carvia_aprovacoes_pendentes():
    from flask_login import current_user
    if not (current_user.is_authenticated and getattr(current_user, 'sistema_carvia', False)):
        return {'carvia_aprovacoes_pendentes': 0}
    try:
        from app.carvia.services.documentos.aprovacao_frete_service import (
            AprovacaoFreteService,
        )
        return {
            'carvia_aprovacoes_pendentes': AprovacaoFreteService().contar_pendentes()
        }
    except Exception:
        return {'carvia_aprovacoes_pendentes': 0}


_routes_registered = False


def init_app(app):
    """Registra o blueprint CarVia e sub-blueprints"""
    global _routes_registered
    if not _routes_registered:
        register_routes(carvia_bp)
        _routes_registered = True
    app.register_blueprint(carvia_bp)
