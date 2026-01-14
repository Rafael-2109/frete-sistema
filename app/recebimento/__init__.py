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
    # APIs de validacao fiscal
    from .routes.validacao_fiscal_routes import validacao_fiscal_bp
    app.register_blueprint(validacao_fiscal_bp)

    # Views (telas HTML) de validacao fiscal
    from .routes.views import recebimento_views_bp
    app.register_blueprint(recebimento_views_bp)
