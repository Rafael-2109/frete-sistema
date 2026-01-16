# Routes do modulo recebimento

from app.recebimento.routes.validacao_fiscal_routes import validacao_fiscal_bp
from app.recebimento.routes.validacao_nf_po_routes import validacao_nf_po_bp
from app.recebimento.routes.views import recebimento_views_bp

__all__ = [
    'validacao_fiscal_bp',
    'validacao_nf_po_bp',
    'recebimento_views_bp'
]
