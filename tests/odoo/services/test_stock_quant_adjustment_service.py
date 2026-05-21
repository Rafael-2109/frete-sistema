"""Tests para StockQuantAdjustmentService.ajustar_quant.

Cobre o atomo de ajuste de inventario de 1 quant (consolidacao dos scripts
11/12/13/14/criar_saldo do inventario 2026-05):
- delta + e - (SOMA), valor_absoluto (SET), zerar (valor_absoluto=0)
- criar_se_faltar (quant inexistente)
- dry_run nao escreve
- validacoes anti-negativacao e anti-reserva
- resetar_reserva (corrigir reserved_quantity)
- identificacao por quant_id (read) vs por chave (search_read)
- NOOP (nada muda)
- erros de uso (ValueError)
"""
from unittest.mock import MagicMock

import pytest

from app.odoo.services.stock_quant_adjustment_service import (
    StockQuantAdjustmentService,
)


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def lot_svc_mock():
    return MagicMock()


@pytest.fixture
def service(odoo_mock, lot_svc_mock):
    return StockQuantAdjustmentService(odoo=odoo_mock, lot_svc=lot_svc_mock)


def _quant(qid=10, qty=100.0, reservada=0.0):
    return {
        'id': qid, 'quantity': qty, 'reserved_quantity': reservada,
        'lot_id': [44098, 'MIGRAÇÃO'], 'location_id': [42, 'LF/Estoque'],
    }


# ----------------------------------------------------------------------
# delta (SOMA) — quant existente
# ----------------------------------------------------------------------

def test_delta_positivo_atualiza(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=100.0)]
    r = service.ajustar_quant(
        product_id=28239, company_id=5, location_id=42, lot_id=44098, delta=35.0,
    )
    assert r['status'] == 'EXECUTADO'
    assert r['qty_antes'] == 100.0
    assert r['qty_apos'] == 135.0
    assert r['ajuste_aplicado'] == 35.0
    assert r['acao'] == 'updated'
    odoo_mock.write.assert_called_once_with('stock.quant', [10], {'inventory_quantity': 135.0})
    odoo_mock.execute_kw.assert_called_once_with('stock.quant', 'action_apply_inventory', [[10]])


def test_delta_negativo_atualiza(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=100.0)]
    r = service.ajustar_quant(
        product_id=28239, company_id=5, location_id=42, lot_id=44098, delta=-30.0,
    )
    assert r['status'] == 'EXECUTADO'
    assert r['qty_apos'] == 70.0
    odoo_mock.write.assert_called_once_with('stock.quant', [10], {'inventory_quantity': 70.0})


# ----------------------------------------------------------------------
# valor_absoluto (SET)
# ----------------------------------------------------------------------

def test_valor_absoluto_set(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=80.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098, valor_absoluto=12.3,
    )
    assert r['status'] == 'EXECUTADO'
    assert r['qty_apos'] == 12.3
    odoo_mock.write.assert_called_once_with('stock.quant', [10], {'inventory_quantity': 12.3})


def test_zerar_valor_absoluto_zero(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=66.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098, valor_absoluto=0,
    )
    assert r['status'] == 'EXECUTADO'
    assert r['qty_apos'] == 0
    odoo_mock.write.assert_called_once_with('stock.quant', [10], {'inventory_quantity': 0})


# ----------------------------------------------------------------------
# criar_se_faltar
# ----------------------------------------------------------------------

def test_criar_se_faltar_cria_quant(service, odoo_mock):
    odoo_mock.search_read.return_value = []  # quant nao existe
    odoo_mock.create.return_value = 999
    r = service.ajustar_quant(
        product_id=28239, company_id=5, location_id=42, lot_id=44098,
        delta=50.0, criar_se_faltar=True,
    )
    assert r['status'] == 'EXECUTADO'
    assert r['acao'] == 'created'
    assert r['qty_antes'] == 0.0
    assert r['qty_apos'] == 50.0
    assert r['quant_id'] == 999
    payload = odoo_mock.create.call_args[0][1]
    assert payload['product_id'] == 28239
    assert payload['lot_id'] == 44098
    assert payload['inventory_quantity'] == 50.0
    odoo_mock.execute_kw.assert_called_once_with('stock.quant', 'action_apply_inventory', [[999]])


def test_criar_sem_lote_omite_lot_id(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    odoo_mock.create.return_value = 777
    r = service.ajustar_quant(
        product_id=28239, company_id=5, location_id=42, lot_id=None,
        delta=10.0, criar_se_faltar=True,
    )
    assert r['status'] == 'EXECUTADO'
    payload = odoo_mock.create.call_args[0][1]
    assert 'lot_id' not in payload  # sem lote => nao envia lot_id


def test_quant_inexistente_sem_criar_falha(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098, delta=10.0,
    )
    assert r['status'] == 'FALHA_QUANT_VAZIO'
    odoo_mock.write.assert_not_called()
    odoo_mock.create.assert_not_called()


def test_criar_se_faltar_qty_negativa_falha(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098,
        delta=-5.0, criar_se_faltar=True,
    )
    assert r['status'] == 'FALHA_QUANT_NEGATIVO'
    odoo_mock.create.assert_not_called()


# ----------------------------------------------------------------------
# dry_run
# ----------------------------------------------------------------------

def test_dry_run_nao_escreve(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=100.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098,
        delta=20.0, dry_run=True,
    )
    assert r['status'] == 'DRY_RUN_OK'
    assert r['qty_apos'] == 120.0
    odoo_mock.write.assert_not_called()
    odoo_mock.create.assert_not_called()
    odoo_mock.execute_kw.assert_not_called()


# ----------------------------------------------------------------------
# validacoes
# ----------------------------------------------------------------------

def test_validar_nao_negativar(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=10.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098, delta=-15.0,
    )
    assert r['status'] == 'FALHA_QUANT_NEGATIVO'
    odoo_mock.write.assert_not_called()


def test_validar_nao_abaixo_reserva(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=100.0, reservada=80.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098, valor_absoluto=50.0,
    )
    assert r['status'] == 'FALHA_RESERVADO'
    odoo_mock.write.assert_not_called()


def test_desligar_validacao_negativar(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=10.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098,
        delta=-15.0, validar_nao_negativar=False, validar_nao_abaixo_reserva=False,
    )
    assert r['status'] == 'EXECUTADO'
    assert r['qty_apos'] == -5.0


# ----------------------------------------------------------------------
# resetar_reserva
# ----------------------------------------------------------------------

def test_resetar_reserva_zera_antes(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=-3.0, reservada=-2.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098,
        valor_absoluto=0, resetar_reserva=True,
    )
    assert r['status'] == 'EXECUTADO'
    # 2 writes: reset reserva + inventory_quantity
    assert odoo_mock.write.call_count == 2
    primeira = odoo_mock.write.call_args_list[0][0]
    assert primeira[2] == {'reserved_quantity': 0}
    segunda = odoo_mock.write.call_args_list[1][0]
    assert segunda[2] == {'inventory_quantity': 0}


def test_resetar_reserva_ignora_validacao_reserva(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=5.0, reservada=80.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098,
        valor_absoluto=0, resetar_reserva=True,
    )
    assert r['status'] == 'EXECUTADO'  # nao bloqueia por reserva (vai ser zerada)


# ----------------------------------------------------------------------
# identificacao por quant_id
# ----------------------------------------------------------------------

def test_por_quant_id_usa_read(service, odoo_mock):
    odoo_mock.read.return_value = [_quant(qid=12073, qty=20.0)]
    r = service.ajustar_quant(quant_id=12073, valor_absoluto=0)
    assert r['status'] == 'EXECUTADO'
    assert r['qty_apos'] == 0
    odoo_mock.read.assert_called_once()
    odoo_mock.search_read.assert_not_called()
    odoo_mock.write.assert_called_once_with('stock.quant', [12073], {'inventory_quantity': 0})


def test_por_quant_id_inexistente_falha(service, odoo_mock):
    odoo_mock.read.return_value = []
    r = service.ajustar_quant(quant_id=99999, valor_absoluto=0)
    assert r['status'] == 'FALHA_QUANT_VAZIO'
    odoo_mock.write.assert_not_called()


# ----------------------------------------------------------------------
# NOOP
# ----------------------------------------------------------------------

def test_noop_delta_zero(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=100.0)]
    r = service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=44098, delta=0,
    )
    assert r['status'] == 'NOOP'
    odoo_mock.write.assert_not_called()


# ----------------------------------------------------------------------
# busca: lot_id=None -> lot_id=False no domain
# ----------------------------------------------------------------------

def test_busca_sem_lote_usa_false(service, odoo_mock):
    odoo_mock.search_read.return_value = [_quant(qty=100.0)]
    service.ajustar_quant(
        product_id=1, company_id=5, location_id=42, lot_id=None, delta=10.0,
    )
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['lot_id', '=', False] in domain


# ----------------------------------------------------------------------
# erros de uso (ValueError)
# ----------------------------------------------------------------------

def test_erro_sem_delta_nem_absoluto(service):
    with pytest.raises(ValueError, match='delta OU valor_absoluto'):
        service.ajustar_quant(product_id=1, company_id=5, location_id=42)


def test_erro_delta_e_absoluto_juntos(service):
    with pytest.raises(ValueError, match='delta OU valor_absoluto'):
        service.ajustar_quant(
            product_id=1, company_id=5, location_id=42, delta=1.0, valor_absoluto=2.0,
        )


def test_erro_sem_quant_id_e_sem_chave(service):
    with pytest.raises(ValueError, match='product_id/company_id/location_id'):
        service.ajustar_quant(delta=10.0)


def test_erro_criar_se_faltar_com_quant_id(service):
    with pytest.raises(ValueError, match='criar_se_faltar'):
        service.ajustar_quant(quant_id=10, delta=10.0, criar_se_faltar=True)
