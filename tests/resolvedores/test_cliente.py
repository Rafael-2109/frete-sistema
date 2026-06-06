"""TDD — resolucao de cliente (toca banco).

resolver_cliente (rico, carteira/separacao) = port fiel de resolver_entidades.py:506.
resolver_cliente_cli (achatado, +entregas) = port de resolvendo-entidades/scripts/resolver_cliente.py.
"""
from app.resolvedores.cliente import resolver_cliente, resolver_cliente_cli

TERMO_INEXISTENTE = 'zzqxwclienteinexistente'


def _nome_cliente_carteira():
    from app.carteira.models import CarteiraPrincipal
    return CarteiraPrincipal.query.with_entities(CarteiraPrincipal.raz_social_red).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
        CarteiraPrincipal.raz_social_red.isnot(None),
    ).first()


class TestResolverClienteRico:
    def test_vazio_erro(self, db):
        r = resolver_cliente('', fonte='carteira')
        assert r['sucesso'] is False

    def test_inexistente(self, db):
        r = resolver_cliente(TERMO_INEXISTENTE, fonte='carteira')
        assert r['sucesso'] is False
        assert 'erro' in r and 'sugestao' in r

    def test_shape_inexistente(self, db):
        r = resolver_cliente(TERMO_INEXISTENTE, fonte='carteira')
        for k in ('sucesso', 'termo_original', 'estrategia', 'clientes_encontrados', 'pedidos', 'resumo'):
            assert k in r

    def test_caminho_feliz(self, db):
        row = _nome_cliente_carteira()
        assert row is not None
        r = resolver_cliente(row[0], fonte='carteira')
        assert r['sucesso'] is True
        assert r['clientes_encontrados']
        for k in ('total_clientes', 'total_pedidos', 'total_valor'):
            assert k in r['resumo']


class TestResolverClienteCli:
    def test_vazio_erro(self, db):
        r = resolver_cliente_cli('', fonte='carteira')
        assert r['sucesso'] is False and 'erro' in r

    def test_inexistente(self, db):
        r = resolver_cliente_cli(TERMO_INEXISTENTE, fonte='carteira')
        assert r['sucesso'] is False
        assert 'erro' in r and 'sugestao' in r

    def test_caminho_feliz_shape(self, db):
        row = _nome_cliente_carteira()
        assert row is not None
        r = resolver_cliente_cli(row[0], fonte='carteira')
        assert r['sucesso'] is True
        for k in ('sucesso', 'termo_original', 'estrategia', 'clientes', 'total', 'fonte'):
            assert k in r
        for k in ('cnpj', 'nome', 'cidade', 'uf'):
            assert k in r['clientes'][0]

    def test_cnpj_estrategia(self, db):
        # termo com 8+ digitos -> estrategia CNPJ
        r = resolver_cliente_cli('12345678', fonte='carteira')
        assert r['estrategia'] == 'CNPJ'
