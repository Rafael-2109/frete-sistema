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


def test_devolver_ignora_devolucao_cancelada_cria_nova():
    """G-AUDIT-3 (N23): devolucao existente em state=cancel NAO e reutilizada.

    Move da devolucao cancelada tem qty=0 e nao restaura saldo. O fix segrega
    cancelados da idempotencia: como TODAS as existentes sao cancel, cria uma
    NOVA funcional (regressao do incidente IMP-2026-06-16-002, picking 325359 /
    devolucao cancelada 325674).
    """
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'name': 'PICK-001', 'state': 'done'}],
        [{'state': 'done'}],  # novo picking validado
    ]
    odoo.search_read.side_effect = [
        [{'id': 7777, 'state': 'cancel'}],  # so devolucao cancelada
        [{'id': 5001, 'quantity': 5.0, 'qty_done': 0}],  # MLs do novo picking
    ]
    odoo.execute_kw.side_effect = [1234, True, {'res_id': 8888}, True]
    svc = StockPickingService(odoo=odoo)
    result = svc.devolver(picking_id=9999)
    assert result == 8888  # NOVA devolucao, nao a cancelada 7777
    # Criou o wizard (nao reutilizou o cancelado)
    create_calls = [
        c for c in odoo.execute_kw.call_args_list
        if c.args[0] == 'stock.return.picking' and c.args[1] == 'create'
    ]
    assert len(create_calls) == 1


def test_devolver_prefere_viva_sobre_cancelada():
    """G-AUDIT-3 (N23): havendo mistura (cancelada + viva), reutiliza a viva."""
    odoo = MagicMock()
    odoo.read.return_value = [{'name': 'PICK-001', 'state': 'done'}]
    odoo.search_read.return_value = [
        {'id': 7777, 'state': 'cancel'},
        {'id': 9001, 'state': 'done'},  # devolucao viva
    ]
    svc = StockPickingService(odoo=odoo)
    result = svc.devolver(picking_id=9999)
    assert result == 9001  # a viva, nao a cancelada 7777
    # Nao cria wizard (idempotencia saudavel)
    for call in odoo.execute_kw.call_args_list:
        assert not (
            call.args[0] == 'stock.return.picking'
            and call.args[1] == 'create'
        )


# ============================================================================
# v15a — aplicar_peso_volumes_fallback (G018 v2)
# ============================================================================

def test_aplicar_peso_volumes_aplica_quando_zerado():
    """G018 v2: aplica fallback quando peso_liquido=0 e volumes=0."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_peso_liquido': 0,
        'l10n_br_peso_bruto': 0,
        'l10n_br_volumes': 0,
        'state': 'done',
    }]
    odoo.search_read.return_value = [{'quantity': 100.0}, {'quantity': 50.0}]
    svc = StockPickingService(odoo=odoo)
    r = svc.aplicar_peso_volumes_fallback(
        picking_id=9999, peso_unitario_fallback=0.001, volumes_fallback=2,
    )
    assert r['aplicado'] is True
    assert r['peso_liquido_antes'] == 0
    # peso = 150 * 0.001 = 0.15
    assert r['peso_liquido_depois'] == pytest.approx(0.15)
    assert r['volumes_antes'] == 0
    assert r['volumes_depois'] == 2
    # write tem que ter sido chamado com os campos certos
    write_call = odoo.write.call_args
    assert write_call[0][0] == 'stock.picking'
    assert write_call[0][1] == [9999]
    updates = write_call[0][2]
    assert updates['l10n_br_peso_liquido'] == pytest.approx(0.15)
    assert updates['l10n_br_peso_bruto'] == pytest.approx(0.15)
    assert updates['l10n_br_volumes'] == 2


def test_aplicar_peso_volumes_noop_quando_ja_setado():
    """G018 v2: nao sobrescreve quando peso e volumes ja preenchidos."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_peso_liquido': 10.0,
        'l10n_br_peso_bruto': 10.5,
        'l10n_br_volumes': 5,
        'state': 'done',
    }]
    svc = StockPickingService(odoo=odoo)
    r = svc.aplicar_peso_volumes_fallback(picking_id=9999)
    assert r['aplicado'] is False
    # NAO chama write
    odoo.write.assert_not_called()


# ============================================================================
# v15a — criar_picking_inter_company (Skill 8 F5a, codifica D-OPS-3)
# ============================================================================

def test_criar_picking_inter_company_basico():
    """Fluxo feliz: cria picking, sem produtos tracking='none'."""
    odoo = MagicMock()
    # v15c F1: search_read por origin retorna [] (sem idempotente)
    odoo.search_read.return_value = []
    # 1 read tracking + 1 create picking
    odoo.read.return_value = [
        {'id': 1001, 'tracking': 'lot'},
        {'id': 1002, 'tracking': 'serial'},
    ]
    odoo.create.return_value = 5555
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[
            {'product_id': 1001, 'quantity': 10.0, 'lot_name': 'LOT_A'},
            {'product_id': 1002, 'quantity': 5.0, 'lot_id': 777},
        ],
        picking_type_id=94, partner_id=1,
        origin='TEST_ORIGIN_BASICO',  # v15c F1: obrigatorio
    )
    assert r['picking_id'] == 5555
    assert r['status'] == 'CRIADO'  # v15c F1
    assert r['tracking_none_pids'] == []
    assert len(r['linhas_planejadas']) == 2
    # Linhas mantem lot_name/lot_id (produto eh tracking != 'none')
    assert r['linhas_planejadas'][0].get('lot_name') == 'LOT_A'
    assert r['linhas_planejadas'][1].get('lot_id') == 777


def test_criar_picking_inter_company_company_iguais_raises():
    """Pre-cond: company_origem != company_destino."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='intra-company'):
        svc.criar_picking_inter_company(
            company_origem_id=1, company_destino_id=1,
            location_origem_id=8, location_destino_id=32,
            linhas=[{'product_id': 1, 'quantity': 1.0}],
            picking_type_id=51, partner_id=34,
            origin='X',
        )


def test_criar_picking_inter_company_partner_id_obrigatorio_raises():
    """Pre-cond: partner_id eh obrigatorio em inter-company."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='partner_id OBRIGATORIO'):
        svc.criar_picking_inter_company(
            company_origem_id=5, company_destino_id=1,
            location_origem_id=42, location_destino_id=5,
            linhas=[{'product_id': 1, 'quantity': 1.0}],
            picking_type_id=94, partner_id=0,
            origin='X',
        )


def test_criar_picking_inter_company_linhas_vazias_raises():
    """Pre-cond: linhas nao vazia."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='linhas'):
        svc.criar_picking_inter_company(
            company_origem_id=5, company_destino_id=1,
            location_origem_id=42, location_destino_id=5,
            linhas=[],
            picking_type_id=94, partner_id=1,
            origin='X',
        )


def test_criar_picking_inter_company_tracking_none_remove_lot_name():
    """D-OPS-3 fix: produto tracking='none' tem lot_name/lot_id removidos."""
    odoo = MagicMock()
    odoo.search_read.return_value = []  # v15c F1: nao idempotente
    odoo.read.return_value = [
        {'id': 103500105, 'tracking': 'none'},  # PIMENTA JALAPENO sem rastreio
        {'id': 1002, 'tracking': 'lot'},
    ]
    odoo.create.return_value = 6666
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[
            # Caller passa lote (workaround SEMLOTE no script v14a-ops)
            {'product_id': 103500105, 'quantity': 41.56, 'lot_name': 'SEMLOTE'},
            {'product_id': 1002, 'quantity': 5.0, 'lot_name': 'LOT_B'},
        ],
        picking_type_id=94, partner_id=1,
        origin='TEST_ORIGIN_TRACKING_NONE',
    )
    assert r['picking_id'] == 6666
    assert r['status'] == 'CRIADO'
    assert r['tracking_none_pids'] == [103500105]
    # Produto 103500105 (tracking='none'): lot_name removido
    linha_none = next(
        l for l in r['linhas_planejadas'] if l['product_id'] == 103500105
    )
    assert 'lot_name' not in linha_none
    assert 'lot_id' not in linha_none
    # Produto 1002 (tracking='lot'): lot_name preservado
    linha_lot = next(
        l for l in r['linhas_planejadas'] if l['product_id'] == 1002
    )
    assert linha_lot.get('lot_name') == 'LOT_B'


def test_criar_picking_inter_company_tracking_por_pid_passed_skip_read():
    """tracking_por_pid pre-fetched evita 1 read em batch (otim bulk)."""
    odoo = MagicMock()
    odoo.search_read.return_value = []  # v15c F1: nao idempotente
    odoo.create.return_value = 7777
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[
            {'product_id': 1001, 'quantity': 10.0, 'lot_name': 'L'},
        ],
        picking_type_id=94, partner_id=1,
        origin='TEST_ORIGIN_TRACKING_PRE',
        tracking_por_pid={1001: 'lot'},  # caller pre-fetched
    )
    assert r['picking_id'] == 7777
    # NAO chamou odoo.read('product.product', ...) — caller forneceu o map
    read_calls = [
        c for c in odoo.read.call_args_list
        if c[0] and c[0][0] == 'product.product'
    ]
    assert read_calls == []


# ============================================================================
# v15c F1 — Idempotencia via origin (CRITICAL anti-duplicacao SEFAZ)
# ============================================================================

def test_criar_picking_inter_company_origin_obrigatorio_raises():
    """v15c F1 (CRITICAL): origin obrigatorio para idempotencia."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='origin OBRIGATORIO'):
        svc.criar_picking_inter_company(
            company_origem_id=5, company_destino_id=1,
            location_origem_id=42, location_destino_id=5,
            linhas=[{'product_id': 1, 'quantity': 1.0}],
            picking_type_id=94, partner_id=1,
            # origin omitido — deve raise
        )


def test_criar_picking_inter_company_idempotent_done():
    """v15c F1: re-execucao com mesmo origin + picking ja done retorna IDEMPOTENT_DONE."""
    odoo = MagicMock()
    # Picking ja existe com origin EXATO em state='done'
    odoo.search_read.return_value = [{'id': 5555, 'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[{'product_id': 1001, 'quantity': 10.0, 'lot_name': 'X'}],
        picking_type_id=94, partner_id=1,
        origin='INV-CYC-SAIDA-INDUSTRI-000123',
    )
    assert r['picking_id'] == 5555
    assert r['status'] == 'IDEMPOTENT_DONE'
    assert r['state'] == 'done'
    assert r['tracking_none_pids'] == []
    assert r['linhas_planejadas'] == []
    # NAO criou nada
    odoo.create.assert_not_called()


def test_criar_picking_inter_company_idempotent_other_state():
    """v15c F1: re-execucao + picking existe mas state != done = IDEMPOTENT_OTHER."""
    odoo = MagicMock()
    odoo.search_read.return_value = [{'id': 7777, 'state': 'assigned'}]
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[{'product_id': 1001, 'quantity': 10.0, 'lot_name': 'X'}],
        picking_type_id=94, partner_id=1,
        origin='INV-CYC-SAIDA-PERDA-000999',
    )
    assert r['picking_id'] == 7777
    assert r['status'] == 'IDEMPOTENT_OTHER'
    assert r['state'] == 'assigned'
    odoo.create.assert_not_called()


def test_criar_picking_inter_company_g_audit_3_pula_pickings_cancelados():
    """G-AUDIT-3 v22+: se TODOS pickings com origin EXATO sao state=cancel,
    cria NOVO (nao reaproveita). Codifica invariante descoberta no retry
    pipeline v21+ INVENTARIO_2026_05 (picking 321600 cancel impedia F5b).
    """
    odoo = MagicMock()
    # 1a search_read (idempotencia por origin): so cancelados
    # 2a search_read (caso criar_transferencia faca mais buscas): []
    odoo.search_read.side_effect = [
        [{'id': 321600, 'state': 'cancel'}],
        [],
    ]
    odoo.read.return_value = [{'id': 1001, 'tracking': 'lot'}]
    odoo.create.return_value = 321999  # picking NOVO
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[{'product_id': 1001, 'quantity': 10.0, 'lot_name': 'X'}],
        picking_type_id=94, partner_id=1,
        origin='INV-INVENTARIO_2026_05-SAIDA-INDUSTRI-176013',
    )
    # NOVO picking criado, nao reaproveitou 321600 cancelado
    assert r['picking_id'] == 321999
    assert r['status'] == 'CRIADO'  # nao IDEMPOTENT_*
    odoo.create.assert_called()  # create FOI chamado


def test_criar_picking_inter_company_g_audit_3_prefere_vivo_sobre_cancel():
    """G-AUDIT-3 v22+: se ha mistura (cancelados + vivos), reaproveita o
    primeiro nao-cancelado (idempotencia saudavel preservada). Cancelados
    sao logados mas ignorados.
    """
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 321600, 'state': 'cancel'},
        {'id': 321999, 'state': 'assigned'},  # vivo
    ]
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_inter_company(
        company_origem_id=5, company_destino_id=1,
        location_origem_id=42, location_destino_id=5,
        linhas=[{'product_id': 1001, 'quantity': 10.0, 'lot_name': 'X'}],
        picking_type_id=94, partner_id=1,
        origin='INV-INVENTARIO_2026_05-SAIDA-INDUSTRI-176014',
    )
    # Reaproveitou o vivo, NAO criou novo
    assert r['picking_id'] == 321999
    assert r['status'] == 'IDEMPOTENT_OTHER'
    assert r['state'] == 'assigned'
    odoo.create.assert_not_called()


# ============================================================================
# v15a — validar_picking_inter_company (Skill 8 F5b)
# ============================================================================

def test_validar_picking_inter_company_fluxo_completo():
    """Fluxo completo: confirmar + qty_done + ajustar + validar + G018."""
    odoo = MagicMock()
    # search_read para preencher_qty_done (find move_lines por produto)
    # search_read para ajustar_qty_done_pelo_disponivel (moves)
    # read para ajustar... (move_lines de cada move)
    # search_read para consolidar_move_lines (G023)
    # read state apos button_validate (validar G019)
    # read state final (return)
    # read picking peso (aplicar_peso_volumes)
    # search_read move para somar quantity
    odoo.search_read.side_effect = [
        # 1. preencher_qty_done — search_read move_lines
        [{'id': 5001, 'product_id': [1001, 'P1']}],
        # 2. ajustar_qty_done — moves
        [{
            'id': 4001, 'product_id': [1001, 'P1'],
            'product_uom_qty': 10.0, 'state': 'assigned',
            'move_line_ids': [5001],
        }],
        # 3. consolidar_move_lines — search_read MLs do picking
        [{
            'id': 5001, 'product_id': [1001, 'P1'],
            'quantity': 10.0, 'qty_done': 10.0,
            'lot_id': False, 'lot_name': 'LOT_A',
        }],
        # 4. aplicar_peso_volumes — search_read moves
        [{'quantity': 10.0}],
    ]
    odoo.read.side_effect = [
        # ajustar_qty_done — read MLs de cada move
        [{'id': 5001, 'qty_done': 10.0, 'quantity': 10.0}],
        # validar — read state pos-button_validate
        [{'state': 'done'}],
        # validar_picking_inter_company — read state final p/ output
        [{'state': 'done'}],
        # aplicar_peso_volumes — read picking
        [{
            'l10n_br_peso_liquido': 0, 'l10n_br_peso_bruto': 0,
            'l10n_br_volumes': 0, 'state': 'done',
        }],
    ]
    svc = StockPickingService(odoo=odoo)
    r = svc.validar_picking_inter_company(
        picking_id=9999,
        linhas_esperadas=[
            {'product_id': 1001, 'quantity': 10.0, 'lot_name': 'LOT_A'},
        ],
    )
    assert r['picking_id'] == 9999
    assert r['state_apos_validate'] == 'done'
    assert r['g023_aplicado'] is True
    assert r['peso_volumes']['aplicado'] is True
    # confirmar + reservar foram chamados
    odoo.execute_kw.assert_any_call(
        'stock.picking', 'action_confirm', [[9999]],
    )
    odoo.execute_kw.assert_any_call(
        'stock.picking', 'action_assign', [[9999]],
    )


def test_validar_picking_inter_company_sem_linhas_esperadas():
    """Sem linhas_esperadas — pula preencher_qty_done e G023."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # ajustar_qty_done — moves
        [{
            'id': 4001, 'product_id': [1001, 'P1'],
            'product_uom_qty': 10.0, 'state': 'assigned',
            'move_line_ids': [5001],
        }],
        # aplicar_peso_volumes — search_read moves
        [{'quantity': 10.0}],
    ]
    odoo.read.side_effect = [
        # ajustar_qty_done — read MLs
        [{'id': 5001, 'qty_done': 10.0, 'quantity': 10.0}],
        # validar — read state pos button_validate
        [{'state': 'done'}],
        # validar_picking_inter_company — read state final
        [{'state': 'done'}],
        # aplicar_peso_volumes — read picking
        [{
            'l10n_br_peso_liquido': 0, 'l10n_br_peso_bruto': 0,
            'l10n_br_volumes': 0, 'state': 'done',
        }],
    ]
    svc = StockPickingService(odoo=odoo)
    r = svc.validar_picking_inter_company(picking_id=9999, linhas_esperadas=[])
    assert r['g023_aplicado'] is False
    # NAO chamou preencher_qty_done (precisaria de search_read move_lines)
    # Como search_read side_effect tem 2 retornos esperados (ajustar + peso),
    # se preencher fosse chamado, daria StopIteration. Estavel.


def test_validar_picking_inter_company_peso_volumes_desativado():
    """aplicar_peso_volumes=False pula G018 fallback."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # ajustar_qty_done — moves
        [{
            'id': 4001, 'product_id': [1001, 'P1'],
            'product_uom_qty': 5.0, 'state': 'assigned',
            'move_line_ids': [5001],
        }],
    ]
    odoo.read.side_effect = [
        # ajustar_qty_done — read MLs
        [{'id': 5001, 'qty_done': 5.0, 'quantity': 5.0}],
        # validar — read state pos button_validate
        [{'state': 'done'}],
        # validar_picking_inter_company — read state final
        [{'state': 'done'}],
    ]
    svc = StockPickingService(odoo=odoo)
    r = svc.validar_picking_inter_company(
        picking_id=9999, linhas_esperadas=[], aplicar_peso_volumes=False,
    )
    assert r['peso_volumes'] == {}


def test_validar_picking_inter_company_propaga_g019_raise():
    """G019 false-positive: state != 'done' apos button_validate cascateia."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # ajustar_qty_done — moves
        [],
    ]
    odoo.read.side_effect = [
        # validar — read state pos button_validate
        [{'state': 'assigned'}],
    ]
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='apos button_validate'):
        svc.validar_picking_inter_company(
            picking_id=9999, linhas_esperadas=[],
        )


# ============================================================================
# v15a — criar_picking_entrada_destino_manual (ETAPA F G023)
# ============================================================================

def test_criar_picking_entrada_destino_manual_basico():
    """Fluxo feliz: cria + G023 company_id + assign + G011 lot_name + validate."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # idempotencia: nao existe origin
        [],
        # G011: MLs do picking criado
        [{
            'id': 5001, 'product_id': [205460830, 'TESTE'],
            'quantity': 35.0, 'lot_id': False, 'lot_name': False,
        }],
    ]
    odoo.create.return_value = 9999  # picking_id
    odoo.search.return_value = [4001]  # moves do picking (p/ G023 write)
    odoo.read.return_value = [{'state': 'done'}]  # G019 re-le state
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_entrada_destino_manual(
        company_destino_id=5,
        location_origem_id=26489,
        location_destino_id=42,
        moves_data=[
            {'product_id': 205460830, 'quantity': 35.0,
             'lot_dest_name': 'INV-205460830-20260525'},
        ],
        picking_type_id=19,
        origin='INV-INVENTARIO_2026_05-ENTRADA-LF-NF608629',
    )
    assert r['picking_id'] == 9999
    assert r['status'] == 'CRIADO'
    assert r['state'] == 'done'
    assert r['n_moves'] == 1
    # G023: company_id forcado em moves
    odoo.write.assert_any_call(
        'stock.move', [4001], {'company_id': 5},
    )
    # G011: lot_name aplicado na ML (era False)
    write_calls_ml = [
        c for c in odoo.write.call_args_list
        if c[0] and c[0][0] == 'stock.move.line'
    ]
    assert len(write_calls_ml) == 1
    ml_update = write_calls_ml[0][0][2]
    assert ml_update['lot_name'] == 'INV-205460830-20260525'
    assert ml_update['quantity'] == 35.0
    # G011 (CR v15a Issue 2 fix): qty_done tambem setado
    assert ml_update['qty_done'] == 35.0
    # button_validate chamado COM context skip_backorder (CR v15a Issue 1 fix)
    odoo.execute_kw.assert_any_call(
        'stock.picking', 'button_validate', [[9999]],
        {'context': {
            'skip_backorder': True,
            'picking_ids_not_to_backorder': [9999],
        }},
    )


def test_criar_picking_entrada_destino_manual_moves_vazios_raises():
    """Pre-cond: moves_data nao vazio."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='moves_data'):
        svc.criar_picking_entrada_destino_manual(
            company_destino_id=5, location_origem_id=26489,
            location_destino_id=42, moves_data=[],
            picking_type_id=19, origin='X',
        )


def test_criar_picking_entrada_destino_manual_origin_vazio_raises():
    """Pre-cond: origin obrigatorio (idempotencia)."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='origin'):
        svc.criar_picking_entrada_destino_manual(
            company_destino_id=5, location_origem_id=26489,
            location_destino_id=42,
            moves_data=[{'product_id': 1, 'quantity': 1.0}],
            picking_type_id=19, origin='',
        )


def test_criar_picking_entrada_destino_manual_idempotente_done():
    """Idempotencia: origin ja existe em state='done' — retorna existente."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 1234, 'name': 'LF/IN/01733', 'state': 'done'},
    ]
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=26489,
        location_destino_id=42,
        moves_data=[{'product_id': 1, 'quantity': 1.0}],
        picking_type_id=19,
        origin='INV-X-ENTRADA-LF-NF999',
    )
    assert r['picking_id'] == 1234
    assert r['status'] == 'IDEMPOTENT_DONE'
    assert r['state'] == 'done'
    assert r['n_moves'] == 0
    # NAO criou picking novo
    odoo.create.assert_not_called()


def test_criar_picking_entrada_destino_manual_idempotente_outro_state():
    """Idempotencia: origin ja existe em state!=done — retorna p/ investigacao."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5678, 'name': 'LF/IN/01999', 'state': 'assigned'},
    ]
    svc = StockPickingService(odoo=odoo)
    r = svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=26489,
        location_destino_id=42,
        moves_data=[{'product_id': 1, 'quantity': 1.0}],
        picking_type_id=19,
        origin='INV-X-ENTRADA-LF-NF999',
    )
    assert r['picking_id'] == 5678
    assert r['status'] == 'IDEMPOTENT_OTHER'
    assert r['state'] == 'assigned'
    odoo.create.assert_not_called()


def test_criar_picking_entrada_destino_manual_g019_state_nao_done_raises():
    """G019/G020: state != 'done' apos button_validate raises RuntimeError."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # idempotencia: nao existe
        [],
        # G011: MLs do picking
        [{
            'id': 5001, 'product_id': [1001, 'P'],
            'quantity': 10.0, 'lot_id': False, 'lot_name': False,
        }],
    ]
    odoo.create.return_value = 8888
    odoo.search.return_value = [4001]
    # G019 read state apos button_validate
    odoo.read.return_value = [{'state': 'assigned'}]  # NAO done!
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(RuntimeError, match='button_validate'):
        svc.criar_picking_entrada_destino_manual(
            company_destino_id=5, location_origem_id=26489,
            location_destino_id=42,
            moves_data=[{'product_id': 1001, 'quantity': 10.0,
                         'lot_dest_name': 'LOTE_X'}],
            picking_type_id=19,
            origin='INV-Y-ENTRADA-LF-NF111',
        )


def test_criar_picking_entrada_destino_manual_g023_company_id_forcado_em_moves():
    """G023 critico: company_id eh escrito em moves apos create (XML-RPC nao
    herda — gotcha L17 script L1637-1640)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [],  # idempotencia vazio
        [{
            'id': 5001, 'product_id': [1001, 'P'],
            'quantity': 1.0, 'lot_id': False, 'lot_name': False,
        }],
    ]
    odoo.create.return_value = 9111
    odoo.search.return_value = [4001, 4002, 4003]  # 3 moves criados
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=26489,
        location_destino_id=42,
        moves_data=[
            {'product_id': 1001, 'quantity': 1.0, 'lot_dest_name': 'L'},
        ],
        picking_type_id=19,
        origin='INV-Z-ENTRADA-LF-NF222',
    )
    # G023: company_id=5 escrito em TODOS os 3 moves
    odoo.write.assert_any_call(
        'stock.move', [4001, 4002, 4003], {'company_id': 5},
    )


# ============================================================================
# C9 (2026-06-02) — purchase_line_id por move (entrada manual VINCULADA a PO)
# ----------------------------------------------------------------------------
# Canary INDUSTRIALIZACAO_FB_LF provou: DFe-resumo (status 06) NAO gera picking
# nativo no confirm da PO (mesmo com route/account/picking_type/team corretos).
# O fallback manual da folha 1.3.1 PASSO 8 precisa VINCULAR o picking a PO
# (purchase_line_id) p/ que criar_invoice_from_po (Skill 7) gere a in_invoice
# de entrada (CFOP 1901). Sem o campo, a PO fica orfa. Arg opcional +
# retrocompativel (moves_data[i]['purchase_line_id']).
# ============================================================================

def test_criar_picking_entrada_manual_purchase_line_id_vinculado():
    """C9: moves_data com purchase_line_id -> stock.move criado o inclui no
    payload (vincula a PO.line p/ qty_received + criar_invoice_from_po)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [],  # idempotencia vazio
        [{'id': 5001, 'product_id': [27914, 'AROMA'],
          'quantity': 30.56, 'lot_id': False, 'lot_name': False}],
    ]
    odoo.create.return_value = 9777
    odoo.search.return_value = [4001]
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=26489,
        location_destino_id=42,
        moves_data=[
            {'product_id': 27914, 'quantity': 30.56,
             'lot_dest_name': 'P-02/06', 'purchase_line_id': 129982},
        ],
        picking_type_id=19,
        origin='REMESSA-AVULSA-FB-LF-2026-06-02-ENTRADA',
    )
    create_calls = [
        c for c in odoo.create.call_args_list
        if c[0] and c[0][0] == 'stock.picking'
    ]
    assert len(create_calls) == 1
    picking_data = create_calls[0][0][1]
    moves = picking_data['move_ids_without_package']
    move_dict = moves[0][2]
    assert move_dict.get('purchase_line_id') == 129982


def test_criar_picking_entrada_manual_sem_purchase_line_id_retrocompat():
    """C9 retrocompat: sem purchase_line_id, o move_dict NAO inclui o campo
    (comportamento atual preservado p/ os callsites legados da ETAPA F)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [],
        [{'id': 5001, 'product_id': [1001, 'P'],
          'quantity': 1.0, 'lot_id': False, 'lot_name': False}],
    ]
    odoo.create.return_value = 9778
    odoo.search.return_value = [4001]
    odoo.read.return_value = [{'state': 'done'}]
    svc = StockPickingService(odoo=odoo)
    svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=26489,
        location_destino_id=42,
        moves_data=[
            {'product_id': 1001, 'quantity': 1.0, 'lot_dest_name': 'L'},
        ],
        picking_type_id=19,
        origin='INV-Z-ENTRADA-LF-NF333',
    )
    create_calls = [
        c for c in odoo.create.call_args_list
        if c[0] and c[0][0] == 'stock.picking'
    ]
    move_dict = create_calls[0][0][1]['move_ids_without_package'][0][2]
    assert 'purchase_line_id' not in move_dict


# ============================================================================
# C9.1 (2026-06-02) — warehouse_id (do picking_type) + partner_id no picking
# ----------------------------------------------------------------------------
# Canary FB->LF provou: o picking MANUAL precisa dos mesmos campos do picking
# NATIVO p/ o button_validate funcionar. Faltavam warehouse_id (gold tem
# [4,LF]) e partner_id (gold tem FB=1) -> Fault "Source Location not set" na
# cadeia de validacao do motor. O atomo passa a DERIVAR warehouse_id do
# picking_type + aceitar partner_id (opcional). Retrocompativel.
# ============================================================================

def test_criar_picking_entrada_manual_c91_warehouse_derivado_e_partner():
    """C9.1: deriva warehouse_id do picking_type + seta partner_id no picking
    (replica o picking nativo p/ button_validate nao falhar)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [],  # idempotencia
        [{'id': 5001, 'product_id': [27914, 'AROMA'],
          'quantity': 30.56, 'lot_id': False, 'lot_name': False}],
    ]
    odoo.read.side_effect = [
        [{'id': 19, 'warehouse_id': [4, 'LF']}],  # C9.1 le picking_type
        [{'state': 'done'}],                       # G019 re-le state
    ]
    odoo.create.return_value = 9991
    odoo.search.return_value = [4001]
    svc = StockPickingService(odoo=odoo)
    svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=4, location_destino_id=42,
        moves_data=[{'product_id': 27914, 'quantity': 30.56,
                     'lot_dest_name': 'P-02/06', 'purchase_line_id': 129984}],
        picking_type_id=19, origin='REMESSA-C91-ENTRADA', partner_id=1,
    )
    cc = [c for c in odoo.create.call_args_list
          if c[0] and c[0][0] == 'stock.picking']
    picking_data = cc[0][0][1]
    # partner_id setado no picking (replica gold)
    assert picking_data.get('partner_id') == 1
    # warehouse_id derivado do picking_type, setado nos moves
    move_dict = picking_data['move_ids_without_package'][0][2]
    assert move_dict.get('warehouse_id') == 4


def test_criar_picking_entrada_manual_c91_sem_partner_retrocompat():
    """C9.1 retrocompat: sem partner_id, o picking_data NAO inclui o campo
    (callsites legados ETAPA F preservados)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [],
        [{'id': 5001, 'product_id': [1001, 'P'],
          'quantity': 1.0, 'lot_id': False, 'lot_name': False}],
    ]
    odoo.read.side_effect = [
        [{'id': 19, 'warehouse_id': False}],  # picking_type sem warehouse
        [{'state': 'done'}],
    ]
    odoo.create.return_value = 9992
    odoo.search.return_value = [4001]
    svc = StockPickingService(odoo=odoo)
    svc.criar_picking_entrada_destino_manual(
        company_destino_id=5, location_origem_id=26489, location_destino_id=42,
        moves_data=[{'product_id': 1001, 'quantity': 1.0, 'lot_dest_name': 'L'}],
        picking_type_id=19, origin='INV-LEGADO-NF999',
    )
    cc = [c for c in odoo.create.call_args_list
          if c[0] and c[0][0] == 'stock.picking']
    picking_data = cc[0][0][1]
    assert 'partner_id' not in picking_data
    move_dict = picking_data['move_ids_without_package'][0][2]
    assert 'warehouse_id' not in move_dict  # picking_type sem wh -> nao seta
