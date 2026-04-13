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
    from app.carvia.routes.receita_routes import register_receita_routes
    from app.carvia.routes.fluxo_caixa_routes import register_fluxo_caixa_routes
    from app.carvia.routes.conciliacao_routes import register_conciliacao_routes
    from app.carvia.routes.config_routes import register_config_routes
    from app.carvia.routes.cte_complementar_routes import register_cte_complementar_routes
    from app.carvia.routes.custo_entrega_routes import register_custo_entrega_routes
    from app.carvia.routes.exportacao_routes import register_exportacao_routes
    from app.carvia.routes.importacao_config_routes import register_importacao_config_routes
    from app.carvia.routes.tabela_carvia_routes import register_tabela_carvia_routes
    from app.carvia.routes.admin_routes import register_admin_routes
    from app.carvia.routes.cliente_routes import register_cliente_routes
    from app.carvia.routes.cotacao_v2_routes import register_cotacao_v2_routes
    from app.carvia.routes.pedido_routes import register_pedido_routes
    from app.carvia.routes.frete_routes import register_frete_routes
    from app.carvia.routes.gerencial_routes import register_gerencial_routes
    from app.carvia.routes.comissao_routes import register_comissao_routes
    from app.carvia.routes.simulador_routes import register_simulador_routes
    from app.carvia.routes.scanner_routes import register_scanner_routes
    from app.carvia.routes.aprovacao_routes import register_aprovacao_routes
    from app.carvia.routes.conta_corrente_routes import register_conta_corrente_routes

    register_dashboard_routes(bp)
    register_importacao_routes(bp)
    register_nf_routes(bp)
    register_operacao_routes(bp)
    register_subcontrato_routes(bp)
    register_fatura_routes(bp)
    register_api_routes(bp)
    register_despesa_routes(bp)
    register_receita_routes(bp)
    register_fluxo_caixa_routes(bp)
    register_conciliacao_routes(bp)
    register_config_routes(bp)
    register_cte_complementar_routes(bp)
    register_custo_entrega_routes(bp)
    register_exportacao_routes(bp)
    register_importacao_config_routes(bp)
    register_tabela_carvia_routes(bp)
    register_admin_routes(bp)
    register_cliente_routes(bp)
    register_cotacao_v2_routes(bp)
    register_pedido_routes(bp)
    register_frete_routes(bp)
    register_gerencial_routes(bp)
    register_comissao_routes(bp)
    register_simulador_routes(bp)
    register_scanner_routes(bp)
    register_aprovacao_routes(bp)
    register_conta_corrente_routes(bp)
