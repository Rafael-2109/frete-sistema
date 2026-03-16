"""
Routes do Modulo CarVia
"""


def register_routes(bp):
    """Registra todas as rotas no blueprint principal"""
    from app.carvia.routes.dashboard_routes import register_dashboard_routes
    from app.carvia.routes.importacao_routes import register_importacao_routes
    from app.carvia.routes.nf_routes import register_nf_routes
    from app.carvia.routes.operacao_routes import register_operacao_routes
    from app.carvia.routes.subcontrato_routes import register_subcontrato_routes
    from app.carvia.routes.fatura_routes import register_fatura_routes
    from app.carvia.routes.api_routes import register_api_routes
    from app.carvia.routes.despesa_routes import register_despesa_routes
    from app.carvia.routes.fluxo_caixa_routes import register_fluxo_caixa_routes
    from app.carvia.routes.sessao_cotacao_routes import register_sessao_cotacao_routes
    from app.carvia.routes.conciliacao_routes import register_conciliacao_routes
    from app.carvia.routes.config_routes import register_config_routes
    from app.carvia.routes.cte_complementar_routes import register_cte_complementar_routes
    from app.carvia.routes.custo_entrega_routes import register_custo_entrega_routes
    from app.carvia.routes.exportacao_routes import register_exportacao_routes
    from app.carvia.routes.tabela_carvia_routes import register_tabela_carvia_routes
    from app.carvia.routes.admin_routes import register_admin_routes

    register_dashboard_routes(bp)
    register_importacao_routes(bp)
    register_nf_routes(bp)
    register_operacao_routes(bp)
    register_subcontrato_routes(bp)
    register_fatura_routes(bp)
    register_api_routes(bp)
    register_despesa_routes(bp)
    register_fluxo_caixa_routes(bp)
    register_sessao_cotacao_routes(bp)
    register_conciliacao_routes(bp)
    register_config_routes(bp)
    register_cte_complementar_routes(bp)
    register_custo_entrega_routes(bp)
    register_exportacao_routes(bp)
    register_tabela_carvia_routes(bp)
    register_admin_routes(bp)
