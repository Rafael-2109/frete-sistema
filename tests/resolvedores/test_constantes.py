"""TDD — constantes do modulo app/resolvedores (puras, sem banco).

GRUPOS_EMPRESARIAIS e UFS_VALIDAS: 1 fonte unica (port do monolito).
ABREVIACOES_PRODUTO: dedup real — reexporta o dict de product_search (sem 3a copia).
"""
from app.resolvedores import constantes


def test_grupos_empresariais_tem_3_grupos():
    assert set(constantes.GRUPOS_EMPRESARIAIS.keys()) == {'atacadao', 'assai', 'tenda'}


def test_atacadao_prefixos_formato_monolito():
    # Prefixos curtos (sem barra) — NAO o formato de app/utils/grupo_empresarial.py (incompativel).
    assert constantes.GRUPOS_EMPRESARIAIS['atacadao'] == ['93.209.76', '75.315.33', '00.063.96']


def test_assai_prefixo():
    assert constantes.GRUPOS_EMPRESARIAIS['assai'] == ['06.057.22']


def test_tenda_prefixo():
    assert constantes.GRUPOS_EMPRESARIAIS['tenda'] == ['01.157.55']


def test_ufs_validas_27():
    assert len(constantes.UFS_VALIDAS) == 27
    assert 'SP' in constantes.UFS_VALIDAS
    assert 'XX' not in constantes.UFS_VALIDAS


def test_abreviacoes_dedup_mesmo_objeto_de_product_search():
    # Dedup real: constantes reexporta o MESMO dict de product_search (1 fonte de runtime).
    from app.embeddings import product_search
    assert constantes.ABREVIACOES_PRODUTO is product_search.ABREVIACOES_PRODUTO
