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


# ============================================================
# consolidar_move_lines (G023) — Skill 5 baseline 2026-05-24
# ============================================================

def test_consolidar_move_lines_sem_linhas_esperadas_noop():
    """linhas_esperadas=None retorna 0 sem ler nada."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    assert svc.consolidar_move_lines(picking_id=9999, linhas_esperadas=None) == 0
    odoo.search_read.assert_not_called()
    odoo.write.assert_not_called()


def test_consolidar_move_lines_linhas_vazias_noop():
    """linhas_esperadas=[] tambem retorna 0 sem ler nada."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    assert svc.consolidar_move_lines(picking_id=9999, linhas_esperadas=[]) == 0
    odoo.search_read.assert_not_called()


def test_consolidar_move_lines_match_perfeito_sem_writes():
    """ML bate (pid, lot_name) com qty exata: nenhum write."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5001, 'product_id': [1001, 'P1'], 'quantity': 5.0,
         'qty_done': 5.0, 'lot_id': False, 'lot_name': 'LOT_A'},
    ]
    svc = StockPickingService(odoo=odoo)
    ajustes = svc.consolidar_move_lines(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    assert ajustes == 0
    odoo.write.assert_not_called()


def test_consolidar_move_lines_qty_divergente_ajusta():
    """ML com qty=10 mas esperado=5 → write qty+qty_done=5."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5001, 'product_id': [1001, 'P1'], 'quantity': 10.0,
         'qty_done': 0, 'lot_id': False, 'lot_name': 'LOT_A'},
    ]
    svc = StockPickingService(odoo=odoo)
    svc.consolidar_move_lines(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    odoo.write.assert_any_call(
        'stock.move.line', [5001], {'quantity': 5.0, 'qty_done': 5.0}
    )


def test_consolidar_move_lines_duplicata_zera_extra():
    """2 mls mesmo (pid, lot_name): 1a ajusta qty (se divergente), 2a zera."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        # 1a: qty=10, esperado=5 → write qty+qty_done=5
        {'id': 5001, 'product_id': [1001, 'P1'], 'quantity': 10.0,
         'qty_done': 0, 'lot_id': False, 'lot_name': 'LOT_A'},
        # 2a: duplicata com qty>0 → zerada
        {'id': 5002, 'product_id': [1001, 'P1'], 'quantity': 3.0,
         'qty_done': 3.0, 'lot_id': False, 'lot_name': 'LOT_A'},
    ]
    svc = StockPickingService(odoo=odoo)
    svc.consolidar_move_lines(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    odoo.write.assert_any_call(
        'stock.move.line', [5001], {'quantity': 5.0, 'qty_done': 5.0}
    )
    odoo.write.assert_any_call(
        'stock.move.line', [5002], {'quantity': 0, 'qty_done': 0}
    )


def test_consolidar_move_lines_lote_nao_esperado_zerado():
    """ML do produto esperado em lote DIFERENTE → zerado."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5001, 'product_id': [1001, 'P1'], 'quantity': 5.0,
         'qty_done': 5.0, 'lot_id': False, 'lot_name': 'LOT_A'},
        {'id': 5002, 'product_id': [1001, 'P1'], 'quantity': 7.0,
         'qty_done': 7.0, 'lot_id': [999, 'LOT_OUTRO'], 'lot_name': False},
    ]
    svc = StockPickingService(odoo=odoo)
    svc.consolidar_move_lines(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    odoo.write.assert_any_call(
        'stock.move.line', [5002], {'quantity': 0, 'qty_done': 0}
    )


def test_consolidar_move_lines_sem_match_nao_bloqueia():
    """Esperado tem (pid, lot) mas search_read vazio: sem raise, sem writes.

    Etapa 3 conta produto como "divergente" (soma_old=0 vs soma_esperada=5)
    → ajustes=1 (reporta), mas NAO escreve (etapa 1 fez continue por nao haver ml).
    Importante: nao levanta excecao.
    """
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockPickingService(odoo=odoo)
    ajustes = svc.consolidar_move_lines(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    # reporta divergencia mas sem write
    assert ajustes == 1
    odoo.write.assert_not_called()


def test_consolidar_move_lines_qty_zero_ou_negativa_ignorada():
    """quantity<=0 no input nao gera chave esperada: retorna 0."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    ajustes = svc.consolidar_move_lines(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 0, 'lot_name': 'LOT_A'},
            {'product_id': 1002, 'quantity': -5, 'lot_name': 'LOT_B'},
        ],
    )
    assert ajustes == 0
    # esperado vazio: nao ha search_read nem write
    odoo.search_read.assert_not_called()


# ============================================================
# ajustar_qty_done_pelo_disponivel — Skill 5 baseline 2026-05-24
# ============================================================

def test_ajustar_qty_done_pelo_disponivel_bate_no_op():
    """soma qty_done == demand → ajustadas=0 sem pendencias."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7001, 'product_id': [1001, 'P1'], 'product_uom_qty': 10.0,
         'state': 'assigned', 'move_line_ids': [5001]},
    ]
    odoo.read.return_value = [
        {'id': 5001, 'qty_done': 10.0, 'quantity': 10.0},
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.ajustar_qty_done_pelo_disponivel(picking_id=9999)
    assert res['ajustadas'] == 0
    assert res['pendencias'] == []
    odoo.write.assert_not_called()


def test_ajustar_qty_done_pelo_disponivel_reduz_demand_e_reporta_pendencia():
    """qty_done < demand → REDUZ demand para qty_done, reporta falta."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7001, 'product_id': [1001, 'P1'], 'product_uom_qty': 10.0,
         'state': 'assigned', 'move_line_ids': [5001]},
    ]
    odoo.read.return_value = [
        {'id': 5001, 'qty_done': 6.0, 'quantity': 6.0},
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.ajustar_qty_done_pelo_disponivel(picking_id=9999)
    assert res['ajustadas'] == 1
    assert len(res['pendencias']) == 1
    pend = res['pendencias'][0]
    assert pend['move_id'] == 7001
    assert pend['demand_orig'] == 10.0
    assert pend['qty_done'] == 6.0
    assert pend['falta'] == 4.0
    odoo.write.assert_called_with(
        'stock.move', [7001], {'product_uom_qty': 6.0}
    )


def test_ajustar_qty_done_pelo_disponivel_qty_done_acima_atualiza():
    """qty_done > demand (raro) → atualiza demand para qty_done."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7001, 'product_id': [1001, 'P1'], 'product_uom_qty': 5.0,
         'state': 'assigned', 'move_line_ids': [5001]},
    ]
    odoo.read.return_value = [
        {'id': 5001, 'qty_done': 8.0, 'quantity': 8.0},
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.ajustar_qty_done_pelo_disponivel(picking_id=9999)
    assert res['ajustadas'] == 1
    assert res['pendencias'] == []
    odoo.write.assert_called_with(
        'stock.move', [7001], {'product_uom_qty': 8.0}
    )


def test_ajustar_qty_done_pelo_disponivel_state_cancel_pula():
    """Moves em state=cancel sao ignorados."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7001, 'product_id': [1001, 'P1'], 'product_uom_qty': 10.0,
         'state': 'cancel', 'move_line_ids': [5001]},
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.ajustar_qty_done_pelo_disponivel(picking_id=9999)
    assert res['ajustadas'] == 0
    assert res['pendencias'] == []
    odoo.write.assert_not_called()


def test_ajustar_qty_done_pelo_disponivel_demand_zero_pula():
    """demand<=0 tambem e' pulado."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7001, 'product_id': [1001, 'P1'], 'product_uom_qty': 0,
         'state': 'assigned', 'move_line_ids': [5001]},
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.ajustar_qty_done_pelo_disponivel(picking_id=9999)
    assert res['ajustadas'] == 0
    assert res['pendencias'] == []
    odoo.write.assert_not_called()


def test_ajustar_qty_done_pelo_disponivel_sem_move_line_pula():
    """Move sem move_line_ids: pula."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 7001, 'product_id': [1001, 'P1'], 'product_uom_qty': 10.0,
         'state': 'assigned', 'move_line_ids': []},
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.ajustar_qty_done_pelo_disponivel(picking_id=9999)
    assert res['ajustadas'] == 0
    odoo.write.assert_not_called()


# ============================================================
# validar() com linhas_esperadas (G023 inline) — Skill 5 baseline 2026-05-24
# ============================================================

def test_validar_com_linhas_esperadas_chama_consolidar_antes():
    """validar(linhas_esperadas=) consolida ML antes de button_validate."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5001, 'product_id': [1001, 'P1'], 'quantity': 10.0,
         'qty_done': 0, 'lot_id': False, 'lot_name': 'LOT_A'},
    ]
    odoo.execute_kw.return_value = True
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    result = svc.validar(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    assert result is True
    # consolidar ajustou ML
    odoo.write.assert_any_call(
        'stock.move.line', [5001], {'quantity': 5.0, 'qty_done': 5.0}
    )
    # button_validate foi chamado APOS o write
    odoo.execute_kw.assert_any_call(
        'stock.picking', 'button_validate', [[9999]],
        {'context': {
            'skip_backorder': True,
            'picking_ids_not_to_backorder': [9999],
        }},
    )


def test_validar_consolidar_falha_nao_bloqueia_button_validate():
    """consolidar_move_lines explode: validar continua (warn + button_validate)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = Exception('rede caiu')
    odoo.execute_kw.return_value = True
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    result = svc.validar(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        ],
    )
    assert result is True
    # button_validate foi chamado mesmo com consolidar falhando
    odoo.execute_kw.assert_any_call(
        'stock.picking', 'button_validate', [[9999]],
        {'context': {
            'skip_backorder': True,
            'picking_ids_not_to_backorder': [9999],
        }},
    )


# ============================================================
# devolver() — Skill 5 NOVO atomo 2026-05-24
# (derivado de fat_lf_cleanup.reverter_picking PROD 2026-05-20)
# ============================================================

def test_devolver_picking_inexistente_raises():
    """read vazio → RuntimeError."""
    odoo = MagicMock()
    odoo.read.return_value = []
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='nao existe'):
        svc.devolver(picking_id=9999)


def test_devolver_state_nao_done_raises():
    """picking state=assigned → RuntimeError (pre-cond done falha)."""
    odoo = MagicMock()
    odoo.read.return_value = [{'name': 'PICK-001', 'state': 'assigned'}]
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='esperado "done"'):
        svc.devolver(picking_id=9999)


def test_devolver_idempotente_se_devolucao_existe():
    """Idempotencia: ja existe picking com origin ilike 'Devolução de NAME'."""
    odoo = MagicMock()
    odoo.read.return_value = [{'name': 'PICK-001', 'state': 'done'}]
    odoo.search_read.return_value = [{'id': 7777}]  # ja existe
    svc = StockPickingService(odoo=odoo)
    result = svc.devolver(picking_id=9999)
    assert result == 7777
    # Nao chama create do wizard
    for call in odoo.execute_kw.call_args_list:
        args = call.args
        assert not (args[0] == 'stock.return.picking' and args[1] == 'create')


def test_devolver_fluxo_completo_state_done():
    """Fluxo: read picking → create wizard → write → create_returns → MLs → validate."""
    odoo = MagicMock()
    # read: 1a chamada do picking origem, 2a chamada do novo picking
    odoo.read.side_effect = [
        [{'name': 'PICK-001', 'state': 'done'}],
        [{'state': 'done'}],
    ]
    # search_read: 1a chamada idempotencia (vazio), 2a chamada MLs do novo
    odoo.search_read.side_effect = [
        [],  # nao existe devolucao
        [{'id': 5001, 'quantity': 5.0, 'qty_done': 0}],  # MLs do novo
    ]
    # execute_kw: stock.return.picking.create -> wid; write -> True;
    # create_returns -> {'res_id': 8888}; button_validate -> True
    odoo.execute_kw.side_effect = [
        1234,  # wizard create
        True,  # wizard write
        {'res_id': 8888},  # create_returns
        True,  # button_validate
    ]
    svc = StockPickingService(odoo=odoo)
    result = svc.devolver(picking_id=9999)
    assert result == 8888
    # qty_done foi setado nas MLs
    odoo.write.assert_any_call(
        'stock.move.line', [5001], {'qty_done': 5.0}
    )


def test_devolver_state_final_nao_done_raises():
    """Devolucao criada mas state != done apos button_validate → RuntimeError.

    CR1#2 (2026-05-24 v3): MLs realistas na 2a search_read para refletir
    fluxo real (write qty_done acontece antes do button_validate; raise
    final ocorre na verificacao de state).
    """
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'name': 'PICK-001', 'state': 'done'}],
        [{'state': 'assigned'}],  # state final NAO done
    ]
    # 1a search_read: idempotencia vazia; 2a: MLs do novo picking realistas
    odoo.search_read.side_effect = [
        [],
        [{'id': 5001, 'quantity': 5.0, 'qty_done': 0}],
    ]
    odoo.execute_kw.side_effect = [1234, True, {'res_id': 8888}, True]
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='state=\'assigned\''):
        svc.devolver(picking_id=9999)
    # qty_done DEVE ter sido setado antes do button_validate
    odoo.write.assert_any_call(
        'stock.move.line', [5001], {'qty_done': 5.0}
    )


def test_devolver_create_returns_invalido_raises():
    """create_returns retornou dict sem res_id ou int<=0 → RuntimeError."""
    odoo = MagicMock()
    odoo.read.return_value = [{'name': 'PICK-001', 'state': 'done'}]
    odoo.search_read.return_value = []
    odoo.execute_kw.side_effect = [1234, True, {}, True]  # {} sem res_id
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='create_returns retornou'):
        svc.devolver(picking_id=9999)


def test_devolver_create_returns_int_retorna_pid_direto():
    """create_returns que retorna int direto (alguns Odoo) usa esse valor."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'name': 'PICK-001', 'state': 'done'}],
        [{'state': 'done'}],
    ]
    odoo.search_read.side_effect = [[], []]
    # create_returns retorna int 8888 direto
    odoo.execute_kw.side_effect = [1234, True, 8888, True]
    svc = StockPickingService(odoo=odoo)
    result = svc.devolver(picking_id=9999)
    assert result == 8888
