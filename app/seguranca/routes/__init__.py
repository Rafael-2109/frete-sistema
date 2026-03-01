"""
Routes do Modulo Seguranca
"""


def register_routes(bp):
    """Registra todas as rotas no blueprint principal"""
    from app.seguranca.routes.dashboard_routes import register_dashboard_routes
    from app.seguranca.routes.vulnerabilidade_routes import register_vulnerabilidade_routes
    from app.seguranca.routes.scan_routes import register_scan_routes
    from app.seguranca.routes.config_routes import register_config_routes
    from app.seguranca.routes.api_routes import register_api_routes

    register_dashboard_routes(bp)
    register_vulnerabilidade_routes(bp)
    register_scan_routes(bp)
    register_config_routes(bp)
    register_api_routes(bp)
