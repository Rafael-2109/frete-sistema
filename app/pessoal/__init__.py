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
USUARIOS_PESSOAL = [1, 55, 62]

# SQL Admin: acesso total ao SQL do agente (bypass keywords, tabelas, read-only)
# Conceito separado de PESSOAL (financas pessoais ≠ poder SQL total)
USUARIOS_SQL_ADMIN = {1, 55, 62}


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
from app.pessoal.routes.dashboard import dashboard_bp  # noqa: E402
from app.pessoal.routes.orcamento import orcamento_bp  # noqa: E402
from app.pessoal.routes.analise import analise_bp  # noqa: E402
from app.pessoal.routes.compensacao import compensacao_bp  # noqa: E402
from app.pessoal.routes.pluggy import pluggy_bp  # noqa: E402
from app.pessoal.routes.fluxo_caixa import fluxo_caixa_bp  # noqa: E402
from app.pessoal.routes.provisao import provisao_bp  # noqa: E402
from app.pessoal.routes.matches_empresa import matches_empresa_bp  # noqa: E402

pessoal_bp.register_blueprint(importacao_bp)
pessoal_bp.register_blueprint(transacoes_bp)
pessoal_bp.register_blueprint(configuracao_bp)
pessoal_bp.register_blueprint(dashboard_bp)
pessoal_bp.register_blueprint(orcamento_bp)
pessoal_bp.register_blueprint(analise_bp)
pessoal_bp.register_blueprint(compensacao_bp)
pessoal_bp.register_blueprint(pluggy_bp)
pessoal_bp.register_blueprint(fluxo_caixa_bp)
pessoal_bp.register_blueprint(provisao_bp)
pessoal_bp.register_blueprint(matches_empresa_bp)
