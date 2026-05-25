"""Testa StockReservaService — Skill 2.4 `operando-reservas-odoo`.

Cobertura nova v7 (2026-05-24):
- unreserve_picking: wrapper sobre stock.picking.do_unreserve (validado AO VIVO).
- find_orphan_mls: cross-ref via Skill 9 + filtra quants zerados.

Mocks: padrao das skills 4, 5, 6, 9.
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.reserva import StockReservaService


# ============================================================
# unreserve_picking (NOVO v7)
# ============================================================

def test_unreserve_picking_dry_run_default():
    """Default dry_run=True → DRY_RUN_OK sem chamar do_unreserve."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 320753, 'name': 'FB/INT/08022', 'state': 'assigned',
         'move_line_ids': [217657766, 217657767, 217657769]},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(320753)
    assert res['status'] == 'DRY_RUN_OK'
    assert res['n_mls_antes'] == 3
    assert 'do_unreserve' in res['acao']
    # NAO chamou execute_kw
    odoo.execute_kw.assert_not_called()


def test_unreserve_picking_picking_inexistente():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(999999)
    assert res['status'] == 'FALHA_PICKING_NAO_EXISTE'
    odoo.execute_kw.assert_not_called()


def test_unreserve_picking_state_done_recusado():
    """do_unreserve so opera em assigned/partial/confirmed/waiting."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'name': 'PKG', 'state': 'done', 'move_line_ids': [1]},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(100, dry_run=False)
    assert res['status'] == 'FALHA_PICKING_STATE_INVALIDO'
    assert 'done' in res['erro']
    odoo.execute_kw.assert_not_called()


def test_unreserve_picking_state_cancel_recusado():
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'name': 'PKG', 'state': 'cancel', 'move_line_ids': []},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(100, dry_run=False)
    assert res['status'] == 'FALHA_PICKING_STATE_INVALIDO'


def test_unreserve_picking_state_draft_recusado():
    """CR1-H1 v7-fix: guard cobre 'draft' (docstring promete; codigo original omitia)."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'name': 'PKG', 'state': 'draft', 'move_line_ids': [1, 2]},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(100, dry_run=False)
    assert res['status'] == 'FALHA_PICKING_STATE_INVALIDO'
    assert 'draft' in res['erro']
    odoo.execute_kw.assert_not_called()


def test_unreserve_picking_sem_mls_noop():
    """Picking valido mas sem MLs → NOOP."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'name': 'PKG', 'state': 'confirmed', 'move_line_ids': []},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(100, dry_run=False)
    assert res['status'] == 'NOOP'
    assert res['n_mls_antes'] == 0
    odoo.execute_kw.assert_not_called()


def test_unreserve_picking_confirmar_executa_e_releitura():
    """Confirmar real: chama do_unreserve + re-le state."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # 1a: estado antes
        [{'id': 320753, 'name': 'FB/INT/08022', 'state': 'assigned',
          'move_line_ids': [217657766, 217657767, 217657769]}],
        # 2a: estado depois
        [{'id': 320753, 'state': 'confirmed', 'move_line_ids': []}],
    ]
    odoo.execute_kw.return_value = None  # do_unreserve retorna None
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(320753, dry_run=False)
    assert res['status'] == 'PICKING_UNRESERVED'
    assert res['picking_state_antes'] == 'assigned'
    assert res['picking_state_depois'] == 'confirmed'
    assert res['n_mls_antes'] == 3
    assert res['n_mls_depois'] == 0
    odoo.execute_kw.assert_called_once_with(
        'stock.picking', 'do_unreserve', [[320753]],
    )


def test_unreserve_picking_aviso_se_continua_assigned():
    """G_UNRESERVE_TRAVA: se state pos == assigned, emitir aviso."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [{'id': 320753, 'name': 'PKG', 'state': 'assigned',
          'move_line_ids': [1, 2]}],
        [{'id': 320753, 'state': 'assigned', 'move_line_ids': []}],
    ]
    odoo.execute_kw.return_value = None
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(320753, dry_run=False)
    assert res['status'] == 'PICKING_UNRESERVED'
    assert res['picking_state_depois'] == 'assigned'
    assert 'aviso' in res
    assert 'G_UNRESERVE_TRAVA' in res['aviso']


def test_unreserve_picking_excecao_odoo_propaga_status():
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'name': 'PKG', 'state': 'assigned', 'move_line_ids': [1]},
    ]
    odoo.execute_kw.side_effect = Exception('XML-RPC timeout')
    svc = StockReservaService(odoo=odoo)
    res = svc.unreserve_picking(100, dry_run=False)
    assert res['status'] == 'FALHA_ODOO'
    assert 'timeout' in res['erro'].lower()


# ============================================================
# find_orphan_mls (NOVO v7)
# ============================================================

def test_find_orphan_quant_ids_vazio():
    odoo = MagicMock()
    svc = StockReservaService(odoo=odoo)
    res = svc.find_orphan_mls([])
    assert res['status'] == 'ORPHAN_MLS_LISTED'
    assert res['total_orfaos'] == 0
    odoo.read.assert_not_called()
    odoo.search_read.assert_not_called()


def test_find_orphan_classifica_zerado_vs_com_saldo():
    """Quant com qty=0 + ML ativa = orfa; quant com qty>0 = saldo legitimo."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # 1a: quants alvo (2 quants: 1 zerado + 1 com saldo)
        [
            {'id': 100, 'product_id': [10, 'P1'], 'lot_id': [20, 'L1'],
             'location_id': [30, 'Loc'], 'quantity': 0.0,
             'reserved_quantity': 0.0, 'company_id': [1, 'FB']},
            {'id': 101, 'product_id': [11, 'P2'], 'lot_id': [21, 'L2'],
             'location_id': [30, 'Loc'], 'quantity': 50.0,
             'reserved_quantity': 0.0, 'company_id': [1, 'FB']},
        ],
        # Skill 9 vai chamar read em stock.quant tambem
        [
            {'id': 100, 'product_id': [10, 'P1'], 'lot_id': [20, 'L1'],
             'location_id': [30, 'Loc'], 'company_id': [1, 'FB']},
            {'id': 101, 'product_id': [11, 'P2'], 'lot_id': [21, 'L2'],
             'location_id': [30, 'Loc'], 'company_id': [1, 'FB']},
        ],
        # 2a chamada read (picking states)
        [{'id': 500, 'state': 'assigned'}],
    ]
    odoo.search_read.return_value = [
        # ML apontando para quant 100 (zerado) — ORFA
        {'id': 1, 'product_id': [10, 'P1'], 'lot_id': [20, 'L1'],
         'location_id': [30, 'Loc'], 'location_dest_id': False,
         'quantity': 1, 'state': 'assigned', 'company_id': [1, 'FB'],
         'picking_id': [500, 'PKG'], 'move_id': False, 'production_id': False},
        # ML apontando para quant 101 (com saldo) — LEGITIMA
        {'id': 2, 'product_id': [11, 'P2'], 'lot_id': [21, 'L2'],
         'location_id': [30, 'Loc'], 'location_dest_id': False,
         'quantity': 1, 'state': 'assigned', 'company_id': [1, 'FB'],
         'picking_id': [500, 'PKG'], 'move_id': False, 'production_id': False},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.find_orphan_mls([100, 101])
    assert res['status'] == 'ORPHAN_MLS_LISTED'
    # 1 orfa (apontando quant zerado)
    assert res['total_orfaos'] == 1
    assert res['mls_orfas'][0]['id'] == 1
    assert res['mls_orfas'][0]['quant_id'] == 100
    assert 100 in res['quants_zerados_com_mls']
    assert 101 in res['quants_com_saldo']


def test_find_orphan_quants_sem_mls_retorna_vazio():
    """Quants existem mas sem MLs ativas — sem orfas."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # 1a: quants
        [{'id': 100, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
          'location_id': [30, 'Loc'], 'quantity': 0,
          'reserved_quantity': 0, 'company_id': [1, 'FB']}],
        # Skill 9 tambem le quants
        [{'id': 100, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
          'location_id': [30, 'Loc'], 'company_id': [1, 'FB']}],
    ]
    odoo.search_read.return_value = []  # sem MLs
    svc = StockReservaService(odoo=odoo)
    res = svc.find_orphan_mls([100])
    assert res['total_orfaos'] == 0
    assert res['quants_zerados_com_mls'] == []


def test_find_orphan_states_padrao_assigned_partial():
    """Default states = ['assigned', 'partially_available']."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'id': 100, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
          'location_id': [30, 'Loc'], 'quantity': 0, 'reserved_quantity': 0,
          'company_id': [1, 'FB']}],
        [{'id': 100, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
          'location_id': [30, 'Loc'], 'company_id': [1, 'FB']}],
    ]
    odoo.search_read.return_value = []
    svc = StockReservaService(odoo=odoo)
    svc.find_orphan_mls([100])
    # Skill 9 chama search_read('stock.move.line', domain, [...])
    # Domain deve ter state in [assigned, partially_available]
    sr_call = odoo.search_read.call_args
    domain = sr_call[0][1]
    state_filter = [
        d for d in domain
        if isinstance(d, tuple) and d[0] == 'state'
    ]
    assert state_filter == [('state', 'in', ['assigned', 'partially_available'])]


def test_find_orphan_states_customizado_propagado():
    """Caller pode passar states=['done'] etc."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'id': 100, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
          'location_id': [30, 'Loc'], 'quantity': 0, 'reserved_quantity': 0,
          'company_id': [1, 'FB']}],
        [{'id': 100, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
          'location_id': [30, 'Loc'], 'company_id': [1, 'FB']}],
    ]
    odoo.search_read.return_value = []
    svc = StockReservaService(odoo=odoo)
    svc.find_orphan_mls([100], states=['done'])
    sr_call = odoo.search_read.call_args
    domain = sr_call[0][1]
    state_filter = [
        d for d in domain
        if isinstance(d, tuple) and d[0] == 'state'
    ]
    assert state_filter == [('state', 'in', ['done'])]


def test_find_orphan_tol_arredondamento_0001():
    """Quant qty=0.00005 (< TOL 1e-4) considera zerado; 0.001 considera saldo."""
    odoo = MagicMock()
    # 2 quants: 1 com qty quase 0 (< TOL) e 1 com 0.001 (> TOL)
    odoo.read.side_effect = [
        [
            {'id': 100, 'product_id': [10, 'P1'], 'lot_id': [20, 'L1'],
             'location_id': [30, 'Loc'], 'quantity': 0.00005,
             'reserved_quantity': 0, 'company_id': [1, 'FB']},
            {'id': 101, 'product_id': [11, 'P2'], 'lot_id': [21, 'L2'],
             'location_id': [30, 'Loc'], 'quantity': 0.001,
             'reserved_quantity': 0, 'company_id': [1, 'FB']},
        ],
        [
            {'id': 100, 'product_id': [10, 'P1'], 'lot_id': [20, 'L1'],
             'location_id': [30, 'Loc'], 'company_id': [1, 'FB']},
            {'id': 101, 'product_id': [11, 'P2'], 'lot_id': [21, 'L2'],
             'location_id': [30, 'Loc'], 'company_id': [1, 'FB']},
        ],
    ]
    odoo.search_read.return_value = [
        {'id': 1, 'product_id': [10, 'P1'], 'lot_id': [20, 'L1'],
         'location_id': [30, 'Loc'], 'location_dest_id': False, 'quantity': 1,
         'state': 'assigned', 'company_id': [1, 'FB'], 'picking_id': False,
         'move_id': False, 'production_id': False},
        {'id': 2, 'product_id': [11, 'P2'], 'lot_id': [21, 'L2'],
         'location_id': [30, 'Loc'], 'location_dest_id': False, 'quantity': 1,
         'state': 'assigned', 'company_id': [1, 'FB'], 'picking_id': False,
         'move_id': False, 'production_id': False},
    ]
    svc = StockReservaService(odoo=odoo)
    res = svc.find_orphan_mls([100, 101])
    # 100 (qty=0.00005 < TOL): zerado → ORFA
    # 101 (qty=0.001 >= TOL): com saldo → LEGITIMA
    assert res['total_orfaos'] == 1
    assert res['mls_orfas'][0]['id'] == 1
    assert 100 in res['quants_zerados_com_mls']
    assert 101 in res['quants_com_saldo']
