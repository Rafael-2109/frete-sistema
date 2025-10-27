"""
Rotas do módulo de Manufatura
"""
from app.manufatura.routes.dashboard_routes import register_dashboard_routes
from app.manufatura.routes.previsao_demanda_routes import register_previsao_demanda_routes
from app.manufatura.routes.necessidade_producao_routes import register_necessidade_producao_routes


def register_routes(bp):
    """Registra todas as rotas do módulo"""
    register_dashboard_routes(bp)
    register_previsao_demanda_routes(bp)
    register_necessidade_producao_routes(bp)