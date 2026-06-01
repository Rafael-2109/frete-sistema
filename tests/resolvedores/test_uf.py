"""TDD — resolucao de UF (toca banco).

resolver_uf (rico) = port fiel de resolver_entidades.py:386.
resolver_uf_cli (achatado, +entregas) = port de resolvendo-entidades/scripts/resolver_uf.py.
"""
from app.resolvedores.uf import resolver_uf, resolver_uf_cli


class TestResolverUfRico:
    def test_uf_invalida(self, db):
        r = resolver_uf('XX', fonte='carteira')
        assert r['sucesso'] is False
        assert 'ufs_validas' in r

    def test_sp_shape(self, db):
        r = resolver_uf('SP', fonte='carteira')
        # SP tem dados na carteira; valida shape rico
        assert 'sucesso' in r and 'uf' in r
        if r['sucesso']:
            for k in ('pedidos', 'resumo'):
                assert k in r


class TestResolverUfCli:
    def test_uf_invalida(self, db):
        r = resolver_uf_cli('XX', fonte='carteira')
        assert r['sucesso'] is False
        assert 'ufs_validas' in r

    def test_sp_shape(self, db):
        r = resolver_uf_cli('SP', fonte='carteira')
        assert r['sucesso'] is True
        for k in ('uf', 'clientes', 'cidades', 'total', 'exibindo', 'fonte'):
            assert k in r

    def test_uf_uppercase(self, db):
        r = resolver_uf_cli('sp', fonte='carteira')
        assert r['uf'] == 'SP'
