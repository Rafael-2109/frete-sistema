"""
Rotas do módulo de Manufatura
"""
from app.manufatura.routes.dashboard_routes import register_dashboard_routes
from app.manufatura.routes.previsao_demanda_routes import register_previsao_demanda_routes
from app.manufatura.routes.necessidade_producao_routes import register_necessidade_producao_routes
from app.manufatura.routes.historico_routes import register_historico_routes
from app.manufatura.routes.lista_materiais_routes import register_lista_materiais_routes
from app.manufatura.routes.requisicao_compras_routes import register_requisicao_compras_routes
from app.manufatura.routes.analise_producao_routes import register_analise_producao_routes
from app.manufatura.routes.pedidos_compras_routes import pedidos_compras_bp
from app.manufatura.routes.projecao_estoque_routes import projecao_estoque_bp
from app.manufatura.routes.macro_projecao_routes import macro_projecao_bp


def register_routes(bp):
    """Registra todas as rotas do módulo"""
    register_dashboard_routes(bp)
    register_previsao_demanda_routes(bp)
    register_necessidade_producao_routes(bp)
    register_historico_routes(bp)
    register_lista_materiais_routes(bp)
    register_requisicao_compras_routes(bp)
    register_analise_producao_routes(bp)


def register_blueprints(app):
    """Registra blueprints independentes"""
    app.register_blueprint(pedidos_compras_bp)
    app.register_blueprint(projecao_estoque_bp)
    app.register_blueprint(macro_projecao_bp)