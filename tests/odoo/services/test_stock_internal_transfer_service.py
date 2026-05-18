"""Tests para StockInternalTransferService.

Cenarios cobertos:
- transferir_entre_lotes feliz (origem e destino existentes)
- transferir_entre_lotes criando quant destino (nao existia)
- transferir de lot_id_origem=None (quant sem lote) para lote especifico
- erro: qty <= 0
- erro: lot_id_origem == lot_id_destino
- erro: quant origem nao encontrado
- erro: qty solicitada > saldo do quant origem
- erro: saldo apos transferencia ficaria < reservada
- transferir_quantidade_para_lote (wrapper com criar_se_nao_existe)
"""
from unittest.mock import MagicMock

import pytest

from app.odoo.services.stock_internal_transfer_service import (
    StockInternalTransferService,
)


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def lot_svc_mock():
    m = MagicMock()
    m.criar_se_nao_existe.return_value = (999, False)
    return m


@pytest.fixture
def service(odoo_mock, lot_svc_mock):
    return StockInternalTransferService(odoo=odoo_mock, lot_svc=lot_svc_mock)


def test_transferir_feliz_quant_destino_existe(service, odoo_mock):
    """Cenario padrao: ambos quants existem, transfere qty parcial."""
    # Mock buscar_quant: origem (id=10, qty=100, reservada=0), destino (id=20, qty=50)
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'MIGRAÇÃO'], 'reserved_quantity': 0}],
        [{'id': 20, 'quantity': 50.0, 'value': 32.17, 'lot_id': [50000, '26014'], 'reserved_quantity': 0}],
    ]

    res = service.transferir_entre_lotes(
        product_id=28239, company_id=5, location_id=42,
        qty=35.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['quant_origem_id'] == 10
    assert res['quant_origem_qty_antes'] == 100.0
    assert res['quant_origem_qty_apos'] == 65.0
    assert res['quant_destino_id'] == 20
    assert res['quant_destino_qty_antes'] == 50.0
    assert res['quant_destino_qty_apos'] == 85.0
    assert res['qty_transferida'] == 35.0
    # 2 writes + 2 action_apply_inventory
    assert odoo_mock.write.call_count == 2
    assert odoo_mock.execute_kw.call_count == 2


def test_transferir_cria_quant_destino_quando_nao_existe(service, odoo_mock):
    """Quant destino nao existe → cria via create + inventory_quantity."""
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 0}],
        [],  # quant destino nao existe
    ]
    odoo_mock.create.return_value = 999  # id do novo quant

    res = service.transferir_entre_lotes(
        product_id=28239, company_id=5, location_id=42,
        qty=20.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['quant_destino_id'] == 999
    assert res['quant_destino_qty_antes'] == 0.0
    assert res['quant_destino_qty_apos'] == 20.0
    odoo_mock.create.assert_called_once()
    args = odoo_mock.create.call_args[0]
    assert args[0] == 'stock.quant'
    payload = args[1]
    assert payload['product_id'] == 28239
    assert payload['lot_id'] == 50000
    assert payload['inventory_quantity'] == 20.0


def test_transferir_origem_sem_lote(service, odoo_mock):
    """lot_id_origem=None busca quant com lot_id=False."""
    odoo_mock.search_read.side_effect = [
        [{'id': 32677, 'quantity': 39216.0, 'value': 25232.54, 'lot_id': False, 'reserved_quantity': 0}],
        [{'id': 20, 'quantity': 0.0, 'value': 0.0, 'lot_id': [50000, '26014'], 'reserved_quantity': 0}],
    ]
    res = service.transferir_entre_lotes(
        product_id=28239, company_id=5, location_id=42,
        qty=39216.0, lot_id_origem=None, lot_id_destino=50000,
    )
    assert res['quant_origem_id'] == 32677
    assert res['quant_origem_qty_apos'] == 0.0
    # search_read primeira chamada deveria ter usado lot_id=False
    primeira_chamada_domain = odoo_mock.search_read.call_args_list[0][0][1]
    assert ['lot_id', '=', False] in primeira_chamada_domain


def test_qty_invalida_zero(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=0, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_qty_invalida_negativa(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=-5, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_lot_origem_igual_destino(service):
    with pytest.raises(ValueError, match='lot_id_origem == lot_id_destino'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=10, lot_id_origem=50000, lot_id_destino=50000,
        )


def test_quant_origem_nao_encontrado(service, odoo_mock):
    odoo_mock.search_read.side_effect = [[], []]
    with pytest.raises(ValueError, match='Quant origem nao encontrado'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=10, lot_id_origem=99999, lot_id_destino=50000,
        )


def test_quant_origem_qty_insuficiente(service, odoo_mock):
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 5.0, 'value': 3.0, 'lot_id': [44098, 'X'], 'reserved_quantity': 0}],
    ]
    with pytest.raises(RuntimeError, match='tem 5.0 un mas pedido transferir 100'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=100, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_reserva_impediria_transferencia(service, odoo_mock):
    """Se transferir deixaria saldo < reservada, falha."""
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 80.0}],
    ]
    with pytest.raises(RuntimeError, match='80.0 un reservadas'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=30, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_wrapper_transferir_quantidade_para_lote(service, odoo_mock, lot_svc_mock):
    """Wrapper deve chamar criar_se_nao_existe e depois transferir."""
    lot_svc_mock.criar_se_nao_existe.return_value = (50000, True)  # criado agora
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 0}],
        [],  # destino nao existe
    ]
    odoo_mock.create.return_value = 999

    res = service.transferir_quantidade_para_lote(
        product_id=28239, company_id=5, location_id=42,
        qty=10.0, lot_id_origem=44098,
        nome_lote_destino='26014',
    )

    lot_svc_mock.criar_se_nao_existe.assert_called_once_with(
        '26014', 28239, 5, expiration_date=None,
    )
    assert res['lote_destino_nome'] == '26014'
    assert res['lote_destino_criado_agora'] is True
    assert res['lot_id_destino'] == 50000
    assert res['qty_transferida'] == 10.0


def test_buscar_quant_com_lote(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 0},
    ]
    q = service.buscar_quant(28239, 5, 42, lot_id=44098)
    assert q is not None
    assert q['id'] == 10
    # domain deveria incluir lot_id = 44098
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['lot_id', '=', 44098] in domain


def test_buscar_quant_sem_lote(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 32677, 'quantity': 39216.0, 'value': 25232.54, 'lot_id': False, 'reserved_quantity': 0},
    ]
    q = service.buscar_quant(28239, 5, 42, lot_id=None)
    assert q is not None
    assert q['lot_id'] is False
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['lot_id', '=', False] in domain


def test_buscar_quant_nao_encontrado(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    q = service.buscar_quant(28239, 5, 42, lot_id=99999)
    assert q is None


def test_listar_quants(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 1, 'quantity': 10.0, 'lot_id': [100, 'A'], 'reserved_quantity': 0},
        {'id': 2, 'quantity': 20.0, 'lot_id': [200, 'B'], 'reserved_quantity': 5.0},
    ]
    quants = service.listar_quants(28239, 5, 42)
    assert len(quants) == 2
    assert quants[0]['id'] == 1
    assert quants[1]['id'] == 2
