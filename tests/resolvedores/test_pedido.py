"""TDD — resolucao de pedido (toca banco: carteira_principal + separacao).

resolver_pedido (tupla) = port fiel de resolver_entidades.py:688.
resolver_pedido_cli (JSON achatado) = port de resolvendo-entidades/scripts/resolver_pedido.py
  (mesma logica/estrategias, ORM em vez de raw SQL — elimina interpolacao da estrategia 4).
"""
from app.resolvedores.pedido import resolver_pedido, resolver_pedido_cli

TERMO_INEXISTENTE = 'zzqxwinexistente999'


class TestResolverPedidoTupla:
    def test_retorna_tupla_3(self, db):
        r = resolver_pedido(TERMO_INEXISTENTE, fonte='carteira')
        assert isinstance(r, tuple) and len(r) == 3

    def test_inexistente_nao_encontrado(self, db):
        itens, num, info = resolver_pedido(TERMO_INEXISTENTE, fonte='carteira')
        assert itens == [] and num is None
        assert info['estrategia'] == 'NAO_ENCONTRADO'

    def test_info_tem_chaves(self, db):
        _, _, info = resolver_pedido(TERMO_INEXISTENTE, fonte='carteira')
        for k in ('termo_original', 'estrategia', 'multiplos_encontrados', 'pedidos_candidatos'):
            assert k in info

    def test_numero_exato_caminho_feliz(self, db):
        from app.carteira.models import CarteiraPrincipal
        item = CarteiraPrincipal.query.filter(CarteiraPrincipal.qtd_saldo_produto_pedido > 0).first()
        assert item is not None, "esperado >=1 item na carteira local"
        itens, num, info = resolver_pedido(item.num_pedido, fonte='carteira')
        assert num == item.num_pedido
        assert info['estrategia'] == 'NUMERO_EXATO'
        assert len(itens) >= 1


class TestResolverPedidoCli:
    def test_termo_vazio_erro(self, db):
        r = resolver_pedido_cli('')
        assert r['sucesso'] is False
        assert 'erro' in r

    def test_inexistente_nao_encontrado(self, db):
        r = resolver_pedido_cli(TERMO_INEXISTENTE, fonte='carteira')
        assert r['sucesso'] is False
        assert r['estrategia'] == 'NAO_ENCONTRADO'
        assert 'erro' in r and 'sugestao' in r

    def test_numero_exato_shape(self, db):
        from app.carteira.models import CarteiraPrincipal
        item = CarteiraPrincipal.query.filter(CarteiraPrincipal.qtd_saldo_produto_pedido > 0).first()
        assert item is not None
        r = resolver_pedido_cli(item.num_pedido, fonte='carteira')
        assert r['sucesso'] is True
        assert r['estrategia'] == 'NUMERO_EXATO'
        assert r['pedidos']
        for k in ('num_pedido', 'cnpj', 'cliente', 'cidade', 'uf', 'fonte'):
            assert k in r['pedidos'][0]

    def test_shape_topo(self, db):
        r = resolver_pedido_cli(TERMO_INEXISTENTE, fonte='carteira')
        for k in ('sucesso', 'termo_original', 'estrategia', 'pedidos', 'multiplos', 'total'):
            assert k in r
