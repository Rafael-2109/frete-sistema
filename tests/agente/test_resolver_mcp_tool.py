from app.agente.tools import resolver_mcp_tool as rt


def test_produto_encontrado(monkeypatch):
    monkeypatch.setattr(rt, '_resolver_produto',
                        lambda termo, limit=10: [{'cod_produto': '12345', 'nome_produto': 'PALMITO', 'score': 9}])
    r = rt._resolver_entidade('produto', 'palmito')
    assert r['encontrado'] is True
    assert r['candidatos'][0]['cod_produto'] == '12345'


def test_produto_inexistente_marca_nao_encontrado(monkeypatch):
    monkeypatch.setattr(rt, '_resolver_produto', lambda termo, limit=10: [])
    r = rt._resolver_entidade('produto', 'xyz_produto_inexistente_999')
    assert r['encontrado'] is False
    assert r['candidatos'] == []


def test_transportadora_encontrada(monkeypatch):
    monkeypatch.setattr(rt, '_resolver_transportadora',
                        lambda termo, limite=10: {'sucesso': True, 'transportadoras': [{'id': 338, 'razao_social': 'ANDRE SILVA BARROS'}], 'total': 1})
    r = rt._resolver_entidade('transportadora', 'andre silva')
    assert r['encontrado'] is True
    assert r['candidatos'][0]['id'] == 338


def test_cliente_usa_funcao_cli_e_chave_clientes(monkeypatch):
    # B1 guard: _resolver_cliente DEVE chamar resolver_cliente_cli (chave 'clientes'),
    # nao resolver_cliente (chave 'clientes_encontrados'). Mock na funcao-fonte CERTA.
    import app.resolvedores.cliente as cli
    monkeypatch.setattr(cli, 'resolver_cliente_cli',
                        lambda termo: {'sucesso': True, 'clientes': [{'cnpj': '123', 'nome': 'ACME'}], 'total': 1})
    r = rt._resolver_entidade('cliente', 'acme')
    assert r['encontrado'] is True
    assert r['candidatos'][0]['nome'] == 'ACME'


def test_tipo_invalido():
    r = rt._resolver_entidade('banana', 'x')
    assert r['encontrado'] is False
    assert 'erro' in r
