"""Testa StockPickingService — wrapper para stock.picking de transferencia."""
import pytest
from unittest.mock import MagicMock
from app.odoo.services.stock_picking_service import StockPickingService


# ============================================================
# criar_transferencia (Task 3.1)
# ============================================================

def test_criar_transferencia_basico():
    odoo = MagicMock()
    odoo.create.return_value = 9999
    svc = StockPickingService(odoo=odoo)
    linhas = [
        {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'L1'},
        {'product_id': 1002, 'quantity': 10.0},
    ]
    picking_id = svc.criar_transferencia(
        company_origem_id=1, company_destino_id=4,
        location_origem_id=8, location_destino_id=32,
        linhas=linhas, picking_type_id=99,
    )
    assert picking_id == 9999
    args = odoo.create.call_args[0]
    assert args[0] == 'stock.picking'
    payload = args[1]
    assert payload['location_id'] == 8
    assert payload['location_dest_id'] == 32
    assert payload['picking_type_id'] == 99
    assert payload['company_id'] == 1
    assert len(payload['move_ids']) == 2
    # Defaults inter-company NACOM (G004): incoterm CIF + carrier 996
    assert payload['incoterm'] == 6
    assert payload['carrier_id'] == 996


def test_criar_transferencia_validacoes():
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='linhas'):
        svc.criar_transferencia(1, 4, 8, 32, linhas=[], picking_type_id=99)


def test_criar_transferencia_incoterm_carrier_custom():
    """Aceita incoterm_id e carrier_id customizados."""
    odoo = MagicMock()
    odoo.create.return_value = 8888
    svc = StockPickingService(odoo=odoo)
    svc.criar_transferencia(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[{'product_id': 1, 'quantity': 1.0}], picking_type_id=94,
        incoterm_id=17, carrier_id=12345,
    )
    payload = odoo.create.call_args[0][1]
    assert payload['incoterm'] == 17
    assert payload['carrier_id'] == 12345


def test_criar_transferencia_incoterm_carrier_none_nao_seta():
    """incoterm_id=None ou carrier_id=None NAO incluem no payload."""
    odoo = MagicMock()
    odoo.create.return_value = 7777
    svc = StockPickingService(odoo=odoo)
    svc.criar_transferencia(
        company_origem_id=1, company_destino_id=4,
        location_origem_id=8, location_destino_id=32,
        linhas=[{'product_id': 1, 'quantity': 1.0}], picking_type_id=51,
        incoterm_id=None, carrier_id=None,
    )
    payload = odoo.create.call_args[0][1]
    assert 'incoterm' not in payload
    assert 'carrier_id' not in payload


# ============================================================
# confirmar_e_reservar / preencher_qty_done / validar / cancelar (Task 3.2)
# ============================================================

def test_confirmar_e_reservar():
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    svc.confirmar_e_reservar(picking_id=9999)
    odoo.execute_kw.assert_any_call('stock.picking', 'action_confirm', [[9999]])
    odoo.execute_kw.assert_any_call('stock.picking', 'action_assign', [[9999]])


def test_validar_trata_cannot_marshal_none_com_state_done():
    """G019 FIX: 'cannot marshal None' so e' sucesso se state=done apos."""
    odoo = MagicMock()
    odoo.execute_kw.side_effect = Exception('cannot marshal None')
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    assert svc.validar(picking_id=9999) is True


def test_validar_marshal_none_mas_state_assigned_raises():
    """G019 FIX: marshal None + state=assigned NAO e' sucesso (raise)."""
    odoo = MagicMock()
    odoo.execute_kw.side_effect = Exception('cannot marshal None')
    odoo.read.return_value = [{'state': 'assigned'}]
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='button_validate retornou marshal None'):
        svc.validar(picking_id=9999)


def test_validar_state_done_apos_button_validate_sucesso():
    """G019 FIX: button_validate sem erro + state=done."""
    odoo = MagicMock()
    odoo.execute_kw.return_value = True  # button_validate OK
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    assert svc.validar(picking_id=9999) is True


def test_validar_state_nao_done_raises():
    """G019 FIX: button_validate sem erro mas state=assigned raises."""
    odoo = MagicMock()
    odoo.execute_kw.return_value = True
    odoo.read.return_value = [{'state': 'assigned'}]
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='apos button_validate'):
        svc.validar(picking_id=9999)


def test_validar_propaga_outras_excecoes():
    odoo = MagicMock()
    odoo.execute_kw.side_effect = Exception('Quality checks pending')
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(Exception, match='Quality checks'):
        svc.validar(picking_id=9999)


def test_preencher_qty_done_por_linha():
    """Preenche qty_done em cada move_line. Suporta lot_id ou lot_name."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5001, 'product_id': [1001, 'P1']},
        {'id': 5002, 'product_id': [1002, 'P2']},
    ]
    svc = StockPickingService(odoo=odoo)
    linhas = [
        {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        {'product_id': 1002, 'quantity': 10.0, 'lot_id': 777},
    ]
    svc.preencher_qty_done(picking_id=9999, linhas=linhas)
    odoo.write.assert_any_call(
        'stock.move.line', [5001], {'qty_done': 5.0, 'lot_name': 'LOT_A'}
    )
    odoo.write.assert_any_call(
        'stock.move.line', [5002], {'qty_done': 10.0, 'lot_id': 777}
    )


def test_preencher_qty_done_sem_move_line_raises():
    odoo = MagicMock()
    odoo.search_read.return_value = []  # picking sem move_lines
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='sem move_line'):
        svc.preencher_qty_done(
            picking_id=9999,
            linhas=[{'product_id': 1001, 'quantity': 5.0}],
        )


def test_cancelar():
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    assert svc.cancelar(picking_id=9999, motivo='teste') is True
    odoo.execute_kw.assert_called_with(
        'stock.picking', 'action_cancel', [[9999]]
    )


# ============================================================
# liberar_faturamento (Task 3.3)
# ============================================================

def test_liberar_faturamento_chama_action():
    """G020 FIX: pre-cond state=done verificada antes de chamar."""
    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    svc.liberar_faturamento(picking_id=9999)
    odoo.execute_kw.assert_called_with(
        'stock.picking', 'action_liberar_faturamento', [[9999]]
    )


def test_liberar_faturamento_state_nao_done_raises():
    """G020 FIX: picking nao em done deve raise (false-positive G019 cascateia)."""
    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'assigned'}]
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='esperado "done"'):
        svc.liberar_faturamento(picking_id=9999)
    # NAO deve ter chamado action_liberar_faturamento
    for call in odoo.execute_kw.call_args_list:
        assert call[0][1] != 'action_liberar_faturamento'


def test_liberar_faturamento_propaga_erro_negocio():
    """Erros de negocio do Odoo propagam apos pre-cond state=done."""
    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'done'}]
    odoo.execute_kw.side_effect = Exception('Picking nao validado')
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(Exception, match='nao validado'):
        svc.liberar_faturamento(picking_id=9999)


# ============================================================
# aguardar_invoice_do_robo (Task 3.4)
# ============================================================

def test_aguardar_invoice_acha_imediatamente():
    """Se invoice ja existe na 1a tentativa, retorna sem esperar."""
    odoo = MagicMock()
    odoo.read.return_value = [{'name': 'PICK-001', 'company_id': [1, 'NACOM']}]
    odoo.search_read.return_value = [
        {'id': 555, 'name': 'INV-001', 'state': 'draft'}
    ]
    svc = StockPickingService(odoo=odoo)
    invoice_id = svc.aguardar_invoice_do_robo(
        picking_id=9999, timeout=5, poll_interval=1
    )
    assert invoice_id == 555


def test_aguardar_invoice_timeout():
    """Se invoice nao aparece em timeout, retorna None."""
    odoo = MagicMock()
    odoo.read.return_value = [{'name': 'PICK-002', 'company_id': [1, 'NACOM']}]
    odoo.search_read.return_value = []
    svc = StockPickingService(odoo=odoo)
    invoice_id = svc.aguardar_invoice_do_robo(
        picking_id=9999, timeout=2, poll_interval=1
    )
    assert invoice_id is None


def test_aguardar_invoice_picking_inexistente_raises():
    """Se picking_id nao existe (read retorna vazio), raises ValueError."""
    odoo = MagicMock()
    odoo.read.return_value = []
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='nao encontrado'):
        svc.aguardar_invoice_do_robo(picking_id=9999, timeout=1, poll_interval=1)
