"""
Modulo de Financas Pessoais

Controle de despesas pessoais/familiares via importacao de extratos Bradesco (CSV).
- Parsers para extrato CC e fatura cartao de credito
- Auto-categorizacao com aprendizado
- Identificacao de membro da familia
- Filtro de transacoes empresariais

Criado em: 22/02/2026

ACESSO RESTRITO: Apenas usuarios com IDs em USUARIOS_PESSOAL podem acessar.
"""
from flask import Blueprint

# =====================================================================
# LISTA UNICA de usuarios autorizados — TODA verificacao usa esta lista
# =====================================================================
USUARIOS_PESSOAL = [1, 62]


def pode_acessar_pessoal(user) -> bool:
    """Verifica se o usuario tem acesso ao modulo pessoal.

    Fonte unica de verdade para controle de acesso.
    Usado por: rotas, templates, agente.
    """
    if not user or not hasattr(user, 'id'):
        return False
    return user.id in USUARIOS_PESSOAL


pessoal_bp = Blueprint('pessoal', __name__, url_prefix='/pessoal')

# Registrar sub-blueprints de rotas
from app.pessoal.routes.importacao import importacao_bp  # noqa: E402
from app.pessoal.routes.transacoes import transacoes_bp  # noqa: E402
from app.pessoal.routes.configuracao import configuracao_bp  # noqa: E402

pessoal_bp.register_blueprint(importacao_bp)
pessoal_bp.register_blueprint(transacoes_bp)
pessoal_bp.register_blueprint(configuracao_bp)
