"""Testa IndisponibilizacaoEstoqueService — canary + indispor/reverter."""
from unittest.mock import MagicMock

import pytest

from app.odoo.services.indisponibilizacao_estoque_service import (
    IndisponibilizacaoEstoqueService,
)


# ============================================================
# indisponibilizar_lote / reverter_lote
# ============================================================

def test_indisponibilizar_lote_chama_inativar():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    assert svc.indisponibilizar_lote(lot_id=123, canary_passou=True) is True
    odoo.write.assert_called_with('stock.lot', [123], {'active': False})


def test_indisponibilizar_lote_bloqueado_sem_canary():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    with pytest.raises(RuntimeError, match='canary'):
        svc.indisponibilizar_lote(lot_id=123, canary_passou=False)
    odoo.write.assert_not_called()


def test_reverter_lote():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    assert svc.reverter_lote(lot_id=123) is True
    odoo.write.assert_called_with('stock.lot', [123], {'active': True})


# ============================================================
# indisponibilizar_local / reverter_local
# ============================================================

def test_indisponibilizar_local():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    assert svc.indisponibilizar_local(location_id=99, canary_passou=True) is True
    odoo.write.assert_called_with('stock.location', [99], {'active': False})


def test_indisponibilizar_local_bloqueado_sem_canary():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    with pytest.raises(RuntimeError, match='canary'):
        svc.indisponibilizar_local(location_id=99, canary_passou=False)
    odoo.write.assert_not_called()


def test_reverter_local():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    assert svc.reverter_local(location_id=99) is True
    odoo.write.assert_called_with('stock.location', [99], {'active': True})


# ============================================================
# canary_lote — estrutural (com mocks)
# ============================================================

def test_canary_lote_sem_saldo_retorna_passou_false():
    """Se lote nao tem saldo positivo, canary retorna False imediatamente."""
    odoo = MagicMock()
    odoo.search_read.return_value = []  # sem quants positivos
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    res = svc.canary_lote(lot_id=123, product_id=42, partner_id=1)
    assert res['passou'] is False
    assert 'saldo' in res['detalhes']
    # Nao chega a inativar
    odoo.write.assert_not_called()


def test_canary_lote_passou_quando_lote_nao_atribuido():
    """Canary OK: lote inativo nao aparece em move_line_ids do picking."""
    odoo = MagicMock()
    # 1a chamada search_read: quants (saldo)
    # 2a chamada search_read: pickings
    odoo.search_read.side_effect = [
        [{'id': 1, 'quantity': 5.0, 'location_id': [42, 'LF/Estoque']}],
        [{'id': 7000, 'move_line_ids': [501, 502]}],
    ]
    odoo.read.return_value = [
        {'id': 501, 'lot_id': [999, 'OUTRO_LOTE']},
        {'id': 502, 'lot_id': False},
    ]
    odoo.create.return_value = 8000  # sale.order id

    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    res = svc.canary_lote(lot_id=123, product_id=42, partner_id=1)

    assert res['passou'] is True
    assert res['sale_order_id'] == 8000
    # Verifica try/finally: lote foi inativado E reativado
    assert ('stock.lot', [123], {'active': False}) in [
        c.args for c in odoo.write.call_args_list
    ]
    assert ('stock.lot', [123], {'active': True}) in [
        c.args for c in odoo.write.call_args_list
    ]


def test_canary_lote_falha_quando_lote_ainda_atribuido():
    """Canary FAIL: Odoo ainda atribuiu o lote inativo (hipotese errada)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [{'id': 1, 'quantity': 5.0, 'location_id': [42, 'LF/Estoque']}],
        [{'id': 7000, 'move_line_ids': [501]}],
    ]
    odoo.read.return_value = [
        {'id': 501, 'lot_id': [123, 'LOTE_TESTE']},  # mesmo lote que inativamos
    ]
    odoo.create.return_value = 8000

    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    res = svc.canary_lote(lot_id=123, product_id=42, partner_id=1)

    assert res['passou'] is False
    # Reverte mesmo em failure
    assert ('stock.lot', [123], {'active': True}) in [
        c.args for c in odoo.write.call_args_list
    ]


def test_canary_lote_reverte_mesmo_se_excecao_no_meio():
    """try/finally garante que lote NUNCA fica inativo se canary explodir."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [{'id': 1, 'quantity': 5.0, 'location_id': [42, 'LF/Estoque']}],
    ]
    # create da SO explode
    odoo.create.side_effect = Exception('Odoo timeout no create SO')

    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    with pytest.raises(Exception, match='timeout'):
        svc.canary_lote(lot_id=123, product_id=42, partner_id=1)

    # GARANTIA CRITICA: lote foi inativado E depois reativado
    write_calls = [c.args for c in odoo.write.call_args_list]
    assert ('stock.lot', [123], {'active': False}) in write_calls
    assert ('stock.lot', [123], {'active': True}) in write_calls


# ============================================================
# canary_local — estrutural
# ============================================================

def test_canary_local_passou_quando_local_nao_atribuido():
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7100, 'move_line_ids': [601]},
    ]
    odoo.read.return_value = [
        {'id': 601, 'location_id': [8, 'FB/Estoque']},  # diferente do canary
    ]
    odoo.create.return_value = 8100

    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    res = svc.canary_local(location_id=99, product_id=42, partner_id=1)

    assert res['passou'] is True
    # try/finally reverte location
    write_calls = [c.args for c in odoo.write.call_args_list]
    assert ('stock.location', [99], {'active': False}) in write_calls
    assert ('stock.location', [99], {'active': True}) in write_calls


def test_canary_local_reverte_mesmo_se_excecao_no_meio():
    odoo = MagicMock()
    odoo.create.side_effect = Exception('Odoo timeout no create SO')

    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    with pytest.raises(Exception, match='timeout'):
        svc.canary_local(location_id=99, product_id=42, partner_id=1)

    write_calls = [c.args for c in odoo.write.call_args_list]
    assert ('stock.location', [99], {'active': False}) in write_calls
    assert ('stock.location', [99], {'active': True}) in write_calls
