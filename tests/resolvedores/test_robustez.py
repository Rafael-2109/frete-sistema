"""TDD — robustez/edge-cases (achados dos reviewers B/C, 2026-06-01).

1. termo/uf/grupo=None nao deve levantar AttributeError (guard defensivo) — todas as funcoes.
2. resolver_produto_cli deve cair em fallback (BLOB+AND) se buscar_produtos_hibrido lancar
   (restaura a rede de seguranca que a split tinha).
"""
import pytest

from app.resolvedores.pedido import resolver_pedido_cli
from app.resolvedores.cliente import resolver_cliente, resolver_cliente_cli
from app.resolvedores.uf import resolver_uf, resolver_uf_cli
from app.resolvedores.grupo import resolver_grupo, resolver_grupo_cli, get_prefixos_grupo
from app.resolvedores.transportadora import resolver_transportadora
from app.resolvedores.produto import resolver_produto_cli


class TestNoneNaoCrasha:
    def test_get_prefixos_grupo_none(self):
        assert get_prefixos_grupo(None) == []

    def test_resolver_grupo_none(self, db):
        assert resolver_grupo(None, fonte='carteira')['sucesso'] is False

    def test_resolver_grupo_cli_none(self, db):
        assert resolver_grupo_cli(None, fonte='carteira')['sucesso'] is False

    def test_resolver_uf_none(self, db):
        assert resolver_uf(None, fonte='carteira')['sucesso'] is False

    def test_resolver_uf_cli_none(self, db):
        assert resolver_uf_cli(None, fonte='carteira')['sucesso'] is False

    def test_resolver_cliente_none(self, db):
        assert resolver_cliente(None, fonte='carteira')['sucesso'] is False

    def test_resolver_cliente_cli_none(self, db):
        assert resolver_cliente_cli(None, fonte='carteira')['sucesso'] is False

    def test_resolver_transportadora_none(self, db):
        assert resolver_transportadora(None)['sucesso'] is False

    def test_resolver_pedido_cli_none(self, db):
        assert resolver_pedido_cli(None, fonte='carteira')['sucesso'] is False


class TestProdutoCliFallback:
    def test_fallback_quando_hibrido_lanca(self, db, monkeypatch):
        import app.embeddings.product_search as ps

        def boom(*a, **k):
            raise RuntimeError('embeddings down')

        monkeypatch.setattr(ps, 'buscar_produtos_hibrido', boom)
        # Nao deve crashar; cai no fallback BLOB+AND (sem embeddings) e acha azeitonas
        r = resolver_produto_cli('azeitona', modo='texto')
        assert 'sucesso' in r
        assert r['sucesso'] is True
        assert r['produtos']
