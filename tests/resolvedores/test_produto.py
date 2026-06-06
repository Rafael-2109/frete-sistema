"""TDD — resolucao de produto (toca banco: cadastro_palletizacao + carteira).

Port fiel de resolver_entidades.py: resolver_produto (:1129, BLOB+AND), resolver_produto_unico (:1222),
resolver_produtos_na_carteira_cliente (:1269). + resolver_produto_cli (achatado, delega product_search).
Usa modo='texto' onde quero isolar o AND deterministico (sem fallback semantico).
"""
from app.resolvedores.produto import (
    resolver_produto,
    resolver_produto_unico,
    resolver_produtos_na_carteira_cliente,
    resolver_produto_cli,
)

CAMPOS_BLOB = ('nome_produto', 'categoria_produto', 'tipo_materia_prima', 'tipo_embalagem', 'cod_produto')


class TestResolverProduto:
    def test_termo_vazio_lista_vazia(self, db):
        assert resolver_produto('') == []

    def test_retorna_lista(self, db):
        assert isinstance(resolver_produto('azeitona', limit=5), list)

    def test_shape_dos_itens(self, db):
        r = resolver_produto('azeitona', limit=5, modo='texto')
        assert r, "esperado >=1 azeitona no cadastro local"
        item = r[0]
        for chave in ('cod_produto', 'nome_produto', 'tipo_embalagem', 'tipo_materia_prima',
                      'categoria_produto', 'subcategoria', 'palletizacao', 'peso_bruto', 'score', 'matches'):
            assert chave in item

    def test_and_multi_termo(self, db):
        # AND: todo resultado contem AMBOS os tokens no blob (modo texto = sem fallback semantico)
        r = resolver_produto('azeitona verde', limit=20, modo='texto')
        for p in r:
            blob = ' '.join(str(p.get(c) or '') for c in CAMPOS_BLOB).lower()
            assert 'azeitona' in blob and 'verde' in blob

    def test_ordenado_por_cod_produto(self, db):
        r = resolver_produto('azeitona', limit=20, modo='texto')
        cods = [p['cod_produto'] for p in r]
        assert cods == sorted(cods)

    def test_stemming_plural(self, db):
        # 'azeitonas' (plural) casa o mesmo universo de 'azeitona' (stemming-s)
        sing = resolver_produto('azeitona', limit=50, modo='texto')
        plur = resolver_produto('azeitonas', limit=50, modo='texto')
        assert sorted(p['cod_produto'] for p in sing) == sorted(p['cod_produto'] for p in plur)


class TestResolverProdutoUnico:
    def test_inexistente_retorna_none(self, db):
        prod, info = resolver_produto_unico('xqzwk_produto_inexistente_999', modo='texto')
        assert prod is None
        assert info['encontrado'] is False

    def test_info_tem_chaves(self, db):
        _, info = resolver_produto_unico('azeitona', modo='texto')
        for k in ('termo_original', 'encontrado', 'multiplos', 'candidatos'):
            assert k in info


class TestResolverProdutosNaCarteiraCliente:
    def test_produto_inexistente_sucesso_false(self, db):
        r = resolver_produtos_na_carteira_cliente('xqzwk_inexistente_999', ['00.000.00'])
        assert r['sucesso'] is False
        for k in ('candidatos_cadastro', 'itens_carteira', 'total_skus', 'ia_decide'):
            assert k in r


class TestResolverProdutoCli:
    def test_termo_vazio_erro(self, db):
        r = resolver_produto_cli('')
        assert r['sucesso'] is False
        assert 'erro' in r

    def test_shape_sucesso(self, db):
        r = resolver_produto_cli('azeitona', limite=5, modo='texto')
        for k in ('sucesso', 'termo_original', 'modo', 'abreviacoes_detectadas', 'produtos', 'total'):
            assert k in r

    def test_abreviacao_detectada(self, db):
        r = resolver_produto_cli('AZ VF', modo='texto')
        assert any('Azeitona Verde Fatiada' in a for a in r['abreviacoes_detectadas'])
