"""Tests para app/odoo/constants/locations.py.

Valida as constantes-dado de localizacao e seus helpers. Fonte dos valores:
docs/inventario-2026-05/00-decisoes/D011-locais-indisponivel-por-empresa.md
"""
import pytest

from app.odoo.constants.locations import (
    COMPANY_LOCATIONS,
    LOCAIS_INDISPONIVEL,
    LOCAIS_PRE_PRODUCAO,
    LOTES_MIGRACAO_POR_COMPANY,
    get_local_indisponivel,
    get_location_id,
)


def test_company_locations_valores():
    assert COMPANY_LOCATIONS == {1: 8, 4: 32, 5: 42}


def test_locais_indisponivel_valores_d011():
    # D011:43-47 — inclui SC (3), cujo local existe mas esta fora de escopo operacional
    assert LOCAIS_INDISPONIVEL == {1: 31088, 3: 31089, 4: 31090, 5: 31091}


def test_lotes_migracao_so_fb_e_cd():
    # D011:104 — so FB e CD tem lote MIGRACAO; LF/SC nao
    assert LOTES_MIGRACAO_POR_COMPANY == {1: 30482, 4: 30856}
    assert 5 not in LOTES_MIGRACAO_POR_COMPANY  # LF nao usa MIGRACAO
    assert 3 not in LOTES_MIGRACAO_POR_COMPANY  # SC fora de escopo


def test_get_location_id_ok_e_erro():
    assert get_location_id(5) == 42
    with pytest.raises(ValueError, match='company_id=99'):
        get_location_id(99)


def test_get_local_indisponivel_ok_e_erro():
    assert get_local_indisponivel(1) == 31088
    assert get_local_indisponivel(3) == 31089  # SC tem local mesmo fora de escopo
    with pytest.raises(ValueError, match='company_id=99'):
        get_local_indisponivel(99)


def test_locais_pre_producao():
    # default canonico dos scripts 15 (FB) e 17 (LF)
    assert set(LOCAIS_PRE_PRODUCAO[1]) == {4066, 4067, 4068, 27458}
    assert set(LOCAIS_PRE_PRODUCAO[5]) == {53, 30710}
    assert 4 not in LOCAIS_PRE_PRODUCAO  # CD nao tem pre-producao mapeada
