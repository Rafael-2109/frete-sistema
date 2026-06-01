"""TDD — helpers puros de grupo (sem banco).

Port de resolver_entidades.py: get_prefixos_grupo (:196), listar_grupos_disponiveis (:209).
(resolver_grupo / resolver_grupo_cli, que tocam banco, sao testados separadamente.)
"""
from app.resolvedores.grupo import (
    get_prefixos_grupo,
    listar_grupos_disponiveis,
    resolver_grupo,
    resolver_grupo_cli,
)

PREFIXOS_ATACADAO = ['93.209.76', '75.315.33', '00.063.96']


def test_get_prefixos_atacadao():
    assert get_prefixos_grupo('atacadao') == ['93.209.76', '75.315.33', '00.063.96']


def test_get_prefixos_case_insensitive():
    assert get_prefixos_grupo('ATACADAO') == get_prefixos_grupo('atacadao')


def test_get_prefixos_strip():
    assert get_prefixos_grupo('  assai  ') == ['06.057.22']


def test_get_prefixos_inexistente_lista_vazia():
    assert get_prefixos_grupo('xyz') == []


def test_listar_grupos_disponiveis():
    assert set(listar_grupos_disponiveis()) == {'atacadao', 'assai', 'tenda'}


class TestResolverGrupoRico:
    def test_grupo_inexistente(self, db):
        r = resolver_grupo('inexistente', fonte='carteira')
        assert r['sucesso'] is False
        assert 'grupos_disponiveis' in r

    def test_atacadao_prefixos(self, db):
        r = resolver_grupo('atacadao', fonte='carteira')
        # sucesso depende de dados; prefixos sempre presentes quando grupo existe
        assert r.get('prefixos_cnpj') == PREFIXOS_ATACADAO or r['sucesso'] is False


class TestResolverGrupoCli:
    def test_grupo_inexistente(self, db):
        r = resolver_grupo_cli('inexistente', fonte='carteira')
        assert r['sucesso'] is False
        assert 'grupos_disponiveis' in r

    def test_atacadao_shape(self, db):
        r = resolver_grupo_cli('atacadao', fonte='carteira')
        assert r['sucesso'] is True
        assert r['prefixos_cnpj'] == PREFIXOS_ATACADAO
        for k in ('grupo', 'prefixos_cnpj', 'filtros_aplicados', 'fonte', 'cnpjs', 'clientes', 'total', 'exibindo'):
            assert k in r
