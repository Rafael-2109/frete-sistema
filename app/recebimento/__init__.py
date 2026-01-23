"""
Modulo de Recebimento de Materiais
==================================

Implementacao faseada:
- Fase 1: Validacao Fiscal (ATUAL)
- Fase 2: Vinculacao NF - PO
- Fase 3: Tratamento de Parciais
- Fase 4: Recebimento Fisico (Lotes + Qualidade)
- Fase 5: Criacao Fatura Automatica

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

from flask import Blueprint

recebimento_bp = Blueprint('recebimento', __name__, url_prefix='/recebimento')


def init_app(app):
    """Registra blueprints do modulo recebimento"""
    # APIs de validacao fiscal (Fase 1)
    from .routes.validacao_fiscal_routes import validacao_fiscal_bp
    app.register_blueprint(validacao_fiscal_bp)

    # APIs de validacao NF x PO (Fase 2)
    from .routes.validacao_nf_po_routes import validacao_nf_po_bp
    app.register_blueprint(validacao_nf_po_bp)

    # Views (telas HTML) de recebimento
    from .routes.views import recebimento_views_bp
    app.register_blueprint(recebimento_views_bp)

    # APIs e Views de Recebimento Fisico (Fase 4)
    from .routes.recebimento_fisico_routes import recebimento_fisico_bp
    app.register_blueprint(recebimento_fisico_bp)
