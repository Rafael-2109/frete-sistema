"""TDD — resolucao de cidade (toca banco).

resolver_cidade (rico) = port fiel de resolver_entidades.py:930 (accent-insensitive REAL via Python).
resolver_cidades_multiplas = port de :1058.
resolver_cidade_cli (achatado, +entregas) = port da split COM correcao do bug de acento
  (a split casava accent-SENSITIVE; o _cli usa normalizar_texto no match).
"""
from app.resolvedores.cidade import resolver_cidade, resolver_cidades_multiplas, resolver_cidade_cli

REGEX_ACENTO = '[áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]'


def _cidade_acentuada_com_saldo():
    from app.carteira.models import CarteiraPrincipal
    return CarteiraPrincipal.query.with_entities(CarteiraPrincipal.nome_cidade).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
        CarteiraPrincipal.nome_cidade.op('~')(REGEX_ACENTO),
    ).first()


class TestResolverCidadeRico:
    def test_vazio_erro(self, db):
        assert resolver_cidade('', fonte='carteira')['sucesso'] is False

    def test_shape(self, db):
        r = resolver_cidade('xqzwinexistente', fonte='carteira')
        for k in ('sucesso', 'termo_original', 'termo_normalizado', 'cidades_encontradas', 'pedidos', 'total_pedidos'):
            assert k in r

    def test_accent_insensitive(self, db):
        from app.resolvedores.normalizacao import normalizar_texto
        row = _cidade_acentuada_com_saldo()
        assert row is not None, "esperado >=1 cidade acentuada com saldo na carteira"
        cidade_acento = row[0]
        r = resolver_cidade(normalizar_texto(cidade_acento), fonte='carteira')
        assert cidade_acento in r['cidades_encontradas']


class TestResolverCidadeCli:
    def test_vazio_erro(self, db):
        r = resolver_cidade_cli('', fonte='carteira')
        assert r['sucesso'] is False and 'erro' in r

    def test_shape(self, db):
        r = resolver_cidade_cli('xqzwinexistente', fonte='carteira')
        for k in ('sucesso', 'cidade_original', 'termo_normalizado', 'cidades_encontradas', 'clientes', 'total'):
            assert k in r

    def test_accent_insensitive_corrige_bug(self, db):
        from app.resolvedores.normalizacao import normalizar_texto
        row = _cidade_acentuada_com_saldo()
        assert row is not None
        cidade_acento = row[0]
        # termo SEM acento deve casar a cidade COM acento (a split NAO casava — bug corrigido)
        r = resolver_cidade_cli(normalizar_texto(cidade_acento), fonte='carteira')
        nomes = [c['cidade'] for c in r['cidades_encontradas']]
        assert cidade_acento in nomes
        assert r['sucesso'] is True


class TestResolverCidadesMultiplas:
    def test_shape(self, db):
        r = resolver_cidades_multiplas(['xqzwinexistente'], fonte='carteira')
        for k in ('sucesso', 'cidades_buscadas', 'cidades_encontradas', 'pedidos', 'total_pedidos', 'por_cidade'):
            assert k in r
