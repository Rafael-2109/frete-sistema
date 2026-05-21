"""Tests para app/odoo/constants/picking_types.py."""
import pytest

from app.odoo.constants.picking_types import (
    LOCATION_DESTINO_POR_DIRECAO,
    PICKING_TYPE_POR_DIRECAO,
    get_picking_type,
)


def test_picking_type_valores_chave():
    assert PICKING_TYPE_POR_DIRECAO[(1, 'industrializacao')] == 53
    assert PICKING_TYPE_POR_DIRECAO[(5, 'perda')] == 94
    assert PICKING_TYPE_POR_DIRECAO[(5, 'dev-industrializacao')] == 97  # G034 (nao 66)


def test_location_destino_valores_chave():
    assert LOCATION_DESTINO_POR_DIRECAO[(5, 'perda')] == 5          # Parceiros/Clientes
    assert LOCATION_DESTINO_POR_DIRECAO[(1, 'industrializacao')] == 26489  # Em Transito Industr


def test_coerencia_picking_tem_location_destino():
    # toda direcao com picking_type deve ter location de destino mapeada
    faltando = [k for k in PICKING_TYPE_POR_DIRECAO if k not in LOCATION_DESTINO_POR_DIRECAO]
    assert faltando == [], f'direcoes sem LOCATION_DESTINO: {faltando}'


def test_get_picking_type_ok_e_erro():
    assert get_picking_type(1, 'transf-filial') == 51
    with pytest.raises(ValueError, match='company=9'):
        get_picking_type(9, 'transf-filial')
