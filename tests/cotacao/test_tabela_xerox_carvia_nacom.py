"""
Invariante CarVia = Nacom no snapshot de tabela de frete do EmbarqueItem.

Bug de origem (embarque 5807): itens CarVia nasciam com tabela_nome_tabela='0'
e valor_cotado=0 porque a rota incluir_em_embarque ZERAVA a tabela do item CarVia
"por design" (preparar_cotacao_vazia), enquanto o item Nacom do mesmo embarque,
mesma transportadora e mesmo destino recebia a tabela real.

Decisao (Rafael): "Frete Nacom = Subcontrato CarVia" — o item CarVia deve gravar
a tabela EXATAMENTE como o item Nacom, no mesmo ponto. A consistencia passa a ser
garantida por CONSTRUCAO: Nacom e CarVia chamam os MESMOS helpers
(`_aplicar_dados_tabela_no_item` + `_resolver_tabela_da_cotacao_sessao`), nas 3 rotas
de montagem de embarque.

Estes testes travam a invariante e pegam qualquer divergencia futura.
"""
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Aplicador unico — grava a tabela igual para qualquer EmbarqueItem
# ---------------------------------------------------------------------------

def test_aplicar_dados_tabela_grava_campos_no_item(app):
    from app.cotacao.routes import _aplicar_dados_tabela_no_item
    from app.embarques.models import EmbarqueItem

    with app.app_context():
        item = EmbarqueItem()
        dados = {'nome_tabela': 'CUIABA', 'valor_kg': 0.65, 'icms_destino': 0.07}

        aplicou = _aplicar_dados_tabela_no_item(item, dados)

        assert aplicou is True
        assert item.tabela_nome_tabela == 'CUIABA'
        assert item.tabela_valor_kg == 0.65
        assert item.icms_destino == 0.07


def test_aplicar_dados_tabela_none_nao_grava_nem_zera(app):
    """O bug: None virava '0'. O aplicador com None NAO deve gravar nada."""
    from app.cotacao.routes import _aplicar_dados_tabela_no_item
    from app.embarques.models import EmbarqueItem

    with app.app_context():
        item = EmbarqueItem()

        aplicou = _aplicar_dados_tabela_no_item(item, None)

        assert aplicou is False
        assert item.tabela_nome_tabela is None  # nunca '0'
        assert item.tabela_valor_kg is None


def test_invariante_carvia_recebe_mesma_tabela_que_nacom(app):
    """O aplicador NAO trata item CarVia diferente de item Nacom."""
    from app.cotacao.routes import _aplicar_dados_tabela_no_item
    from app.embarques.models import EmbarqueItem

    with app.app_context():
        dados = {'nome_tabela': 'CAMPO GRANDE', 'valor_kg': 0.55, 'icms_destino': 0.07}
        item_nacom = EmbarqueItem()                       # sem carvia_cotacao_id
        item_carvia = EmbarqueItem(carvia_cotacao_id=199)  # CarVia

        _aplicar_dados_tabela_no_item(item_nacom, dict(dados))
        _aplicar_dados_tabela_no_item(item_carvia, dict(dados))

        assert item_carvia.tabela_nome_tabela == item_nacom.tabela_nome_tabela == 'CAMPO GRANDE'
        assert item_carvia.tabela_valor_kg == item_nacom.tabela_valor_kg == 0.55
        assert item_carvia.icms_destino == item_nacom.icms_destino == 0.07


# ---------------------------------------------------------------------------
# Resolvedor da cotacao em sessao (rota incluir_em_embarque) — extraido do Nacom
# ---------------------------------------------------------------------------

def test_resolver_tabela_sessao_acha_melhor_opcao_da_transportadora(app):
    from app.cotacao.routes import _resolver_tabela_da_cotacao_sessao

    pedido = SimpleNamespace(cnpj_cpf='49366097000140', peso_total=188.3, num_pedido='P1')
    embarque = SimpleNamespace(transportadora_id=14)

    with app.test_request_context():
        from flask import session
        session['resultados'] = {'fracionadas': {'49366097000140': [
            {'transportadora_id': 99, 'nome_tabela': 'OUTRA', 'valor_kg': 1.0,
             'valor_liquido': 50.0, 'icms_destino': 0.12},
            {'transportadora_id': 14, 'nome_tabela': 'CUIABA', 'valor_kg': 0.65,
             'valor_liquido': 122.40, 'icms_destino': 0.07},
        ]}}

        dados = _resolver_tabela_da_cotacao_sessao(pedido, embarque, [pedido])

        assert dados is not None
        assert dados['nome_tabela'] == 'CUIABA'           # so a opcao da transp 14
        assert dados['valor_kg'] == 0.65
        assert dados['icms_destino'] == 0.07


def test_resolver_tabela_sessao_none_sem_opcao_da_transportadora(app):
    from app.cotacao.routes import _resolver_tabela_da_cotacao_sessao

    pedido = SimpleNamespace(cnpj_cpf='49366097000140', peso_total=188.3, num_pedido='P1')
    embarque = SimpleNamespace(transportadora_id=14)  # nao ha opcao para 14

    with app.test_request_context():
        from flask import session
        session['resultados'] = {'fracionadas': {'49366097000140': [
            {'transportadora_id': 99, 'nome_tabela': 'OUTRA', 'valor_liquido': 50.0},
        ]}}

        dados = _resolver_tabela_da_cotacao_sessao(pedido, embarque, [pedido])

        assert dados is None


def test_resolver_tabela_sessao_none_sem_resultados(app):
    from app.cotacao.routes import _resolver_tabela_da_cotacao_sessao

    pedido = SimpleNamespace(cnpj_cpf='49366097000140', peso_total=188.3, num_pedido='P1')
    embarque = SimpleNamespace(transportadora_id=14)

    with app.test_request_context():
        dados = _resolver_tabela_da_cotacao_sessao(pedido, embarque, [pedido])
        assert dados is None
