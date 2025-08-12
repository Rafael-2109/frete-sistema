"""
Rotas do módulo de Manufatura
"""
from app.manufatura.routes.dashboard_routes import register_dashboard_routes
from app.manufatura.routes.previsao_demanda_routes import register_previsao_demanda_routes
from app.manufatura.routes.ordem_producao_routes import register_ordem_producao_routes
from app.manufatura.routes.requisicao_compras_routes import register_requisicao_compras_routes
from app.manufatura.routes.plano_mestre_routes import register_plano_mestre_routes
from app.manufatura.routes.integracao_routes import register_integracao_routes


def register_routes(bp):
    """Registra todas as rotas do módulo"""
    register_dashboard_routes(bp)
    register_previsao_demanda_routes(bp)
    register_ordem_producao_routes(bp)
    register_requisicao_compras_routes(bp)
    register_plano_mestre_routes(bp)
    register_integracao_routes(bp)