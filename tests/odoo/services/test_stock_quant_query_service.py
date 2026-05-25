"""Testa StockQuantQueryService — atomos READ-only (Skill 9 `consultando-quant-odoo`).

Cobertura nova v7 (2026-05-24):
- listar_move_lines_por_quant: cross-ref reverso ML→quant via TUPLA
  (product_id, lot_id, location_id, company_id) — G030 GOTCHA:
  quant_id direto e' computed store:False, filtro IGNORADO pelo Odoo.
- listar_pickings_por_quant: agrupa MLs por picking + enriquece metadados.

Pattern: mocks de odoo.search_read/.read seguindo skills 4, 5, 6.

Mock setup IMPORTANTE: side_effect agora segue ordem:
  1) odoo.read('stock.quant', quant_ids, [...]) → metadados quants
  2) odoo.search_read('stock.move.line', domain_compound, [...]) → MLs
  3) [opcional] odoo.read('stock.picking', pkg_ids, ['state']) → enriq picking_state
  4) [pickings_por_quant] odoo.search_read('stock.picking', [...], [...]) → metadados
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.consulta_quant import StockQuantQueryService


# ============================================================
# Helper: stub padrão do odoo.read para stock.quant (tuplas)
# ============================================================

def _quants_stub(quants_data):
    """Constroi side_effect de odoo.read pra simular leitura de stock.quant.
    quants_data: lista de tuplas (qid, pid, lot_id, loc_id, cid)."""
    return [
        {
            'id': qid, 'product_id': [pid, f'Prod {pid}'],
            'lot_id': [lid, f'L{lid}'] if lid else False,
            'location_id': [loc, f'Loc {loc}'],
            'company_id': [cid, {1: 'FB', 4: 'CD', 5: 'LF'}.get(cid, '?')],
        }
        for qid, pid, lid, loc, cid in quants_data
    ]


# ============================================================
# listar_move_lines_por_quant
# ============================================================

def test_listar_move_lines_quant_ids_vazio_retorna_vazio_sem_rpc():
    """Quant_ids vazio deve retornar sem chamar Odoo."""
    odoo = MagicMock()
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([])
    assert res == {'total_mls': 0, 'mls': []}
    odoo.search_read.assert_not_called()
    odoo.read.assert_not_called()


def test_listar_move_lines_quants_inexistentes_retorna_vazio():
    """Se quants nao encontrados (read vazio), retorna vazio sem chamar search."""
    odoo = MagicMock()
    odoo.read.return_value = []  # nenhum quant
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([999999])
    assert res == {'total_mls': 0, 'mls': []}
    odoo.search_read.assert_not_called()


def test_listar_move_lines_default_filtra_assigned_partial():
    """Default states = [assigned, partially_available]."""
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    svc.listar_move_lines_por_quant([100])
    # 1a call: search_read MLs (com domain compound + state)
    call = odoo.search_read.call_args
    domain = call[0][1]
    # State filter no inicio (G024 — sem reserved_uom_qty)
    state_filter = [d for d in domain if isinstance(d, tuple) and d[0] == 'state']
    assert state_filter == [('state', 'in', ['assigned', 'partially_available'])]


def test_listar_move_lines_states_explicito_sobrescreve_default():
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    svc.listar_move_lines_por_quant([100], states=['done'])
    domain = odoo.search_read.call_args[0][1]
    state_filter = [d for d in domain if isinstance(d, tuple) and d[0] == 'state']
    assert state_filter == [('state', 'in', ['done'])]


def test_listar_move_lines_states_vazio_sem_filtro():
    """states=[] significa SEM filtro de state."""
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    svc.listar_move_lines_por_quant([100], states=[])
    domain = odoo.search_read.call_args[0][1]
    assert not any(
        isinstance(d, tuple) and d[0] == 'state' for d in domain
    )


def test_listar_move_lines_domain_compound_or_para_n_quants():
    """N quants → N domains AND unidos por N-1 OR ('|') no prefixo."""
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([
        (100, 10, 20, 30, 1),
        (101, 11, 21, 31, 1),
        (102, 12, 22, 32, 1),
    ])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    svc.listar_move_lines_por_quant([100, 101, 102], states=[])
    domain = odoo.search_read.call_args[0][1]
    # 3 tuplas → 2 OR prefixados
    or_count = sum(1 for d in domain if d == '|')
    assert or_count == 2, f'Esperava 2 OR, achou {or_count}. Domain={domain}'
    # 3x AND prefixado por tupla
    and_count = sum(1 for d in domain if d == '&')
    assert and_count == 3 * 3, f'Esperava 9 AND, achou {and_count}'  # 3 tuplas x 3 AND/tupla


def test_listar_move_lines_resolve_quant_id_via_tupla():
    """MLs resultantes tem quant_id resolvido via tupla (G030)."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # 1a call: read stock.quant
        _quants_stub([(261590, 27858, 59396, 8, 1)]),  # quant -> prod 27858, lot 59396, loc 8, FB
        # 2a call: read picking states
        [{'id': 320753, 'state': 'assigned'}],
    ]
    odoo.search_read.return_value = [
        # ML com tupla bate
        {'id': 217657766, 'product_id': [27858, 'MOLHO PARMESAO'],
         'lot_id': [59396, '13206'], 'location_id': [8, 'FB/Estoque'],
         'location_dest_id': False, 'quantity': 319.083, 'state': 'assigned',
         'company_id': [1, 'FB'], 'picking_id': [320753, 'FB/INT/08022']},
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([261590])
    assert res['total_mls'] == 1
    ml = res['mls'][0]
    assert ml['quant_id'] == 261590  # resolvido via tupla
    assert ml['picking_state'] == 'assigned'
    assert ml['empresa'] == 'FB'


def test_listar_move_lines_picking_state_batch_unico_read():
    """N pickings: 1 read batch para mapear states (perf)."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        _quants_stub([(100, 10, 20, 30, 1), (101, 11, 21, 31, 1)]),
        [{'id': 500, 'state': 'assigned'}, {'id': 501, 'state': 'waiting'}],
    ]
    odoo.search_read.return_value = [
        {'id': 1, 'product_id': [10, ''], 'lot_id': [20, ''],
         'location_id': [30, ''], 'location_dest_id': False,
         'quantity': 1, 'state': 'assigned', 'company_id': [1, 'FB'],
         'picking_id': [500, 'PKG1']},
        {'id': 2, 'product_id': [11, ''], 'lot_id': [21, ''],
         'location_id': [31, ''], 'location_dest_id': False,
         'quantity': 2, 'state': 'assigned', 'company_id': [1, 'FB'],
         'picking_id': [501, 'PKG2']},
        {'id': 3, 'product_id': [10, ''], 'lot_id': [20, ''],
         'location_id': [30, ''], 'location_dest_id': False,
         'quantity': 3, 'state': 'assigned', 'company_id': [1, 'FB'],
         'picking_id': [500, 'PKG1']},  # 2 MLs em PKG1
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([100, 101])
    assert res['total_mls'] == 3
    # 2x read: 1) quants + 2) picking states (batch)
    assert odoo.read.call_count == 2
    # 2a chamada batch de pickings
    pkg_ids_lidos = odoo.read.call_args_list[1][0][1]
    assert sorted(pkg_ids_lidos) == [500, 501]


def test_listar_move_lines_sem_picking_id():
    """ML sem picking_id (MO direto): picking_state vazio."""
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = [
        {'id': 1, 'product_id': [10, 'P'], 'lot_id': [20, 'L'],
         'location_id': [30, 'Loc'], 'location_dest_id': False, 'quantity': 1,
         'state': 'assigned', 'company_id': [1, 'FB'],
         'picking_id': False},
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([100])
    ml = res['mls'][0]
    # Sem picking_id → NAO faz read extra de picking (so o de quants)
    assert odoo.read.call_count == 1
    assert ml['picking_id'] is None
    assert ml['picking_state'] == ''


def test_listar_move_lines_incluir_move_adiciona_campos():
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    svc.listar_move_lines_por_quant([100], incluir_move=True)
    fields = odoo.search_read.call_args[0][2]
    assert 'move_id' in fields
    assert 'production_id' in fields


def test_listar_move_lines_incluir_picking_false_skip_picking_read():
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    svc.listar_move_lines_por_quant([100], incluir_picking=False)
    fields = odoo.search_read.call_args[0][2]
    assert 'picking_id' not in fields
    # 1 read (quants), NAO 2 (sem picking states)
    assert odoo.read.call_count == 1


def test_listar_move_lines_quantity_none_seguro():
    """Quantity None vira 0 (defensive)."""
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = [
        {'id': 1, 'product_id': [10, ''], 'lot_id': [20, ''],
         'location_id': [30, ''], 'location_dest_id': False, 'quantity': None,
         'state': 'assigned', 'company_id': [1, 'FB'], 'picking_id': False},
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([100])
    assert res['mls'][0]['quantity'] == 0.0


def test_listar_move_lines_lot_id_false_no_quant():
    """Quant sem lote (lot_id=False) — tupla aceita None/False."""
    odoo = MagicMock()
    odoo.read.return_value = [
        {'id': 100, 'product_id': [10, 'Prod'],
         'lot_id': False,  # SEM LOTE
         'location_id': [30, 'Loc'], 'company_id': [1, 'FB']},
    ]
    odoo.search_read.return_value = [
        {'id': 1, 'product_id': [10, 'Prod'], 'lot_id': False,
         'location_id': [30, 'Loc'], 'location_dest_id': False, 'quantity': 5,
         'state': 'assigned', 'company_id': [1, 'FB'], 'picking_id': False},
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_move_lines_por_quant([100])
    assert res['total_mls'] == 1
    assert res['mls'][0]['quant_id'] == 100  # resolveu via tupla (pid, False, loc, cid)


# ============================================================
# listar_pickings_por_quant
# ============================================================

def test_listar_pickings_quant_ids_vazio():
    """Quant_ids vazio: forma completa zerada."""
    odoo = MagicMock()
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_pickings_por_quant([])
    assert res == {
        'total_pickings': 0,
        'total_mls': 0,
        'pickings': [],
        'mls_sem_picking': [],
    }
    odoo.search_read.assert_not_called()


def test_listar_pickings_agrupa_3_mls_em_1_picking():
    """Caso real lote 13206 — 3 MLs no mesmo picking FB/INT/08022."""
    odoo = MagicMock()
    # read calls: 1) quants  2) picking_states  3) pickings metadados (via search_read)
    odoo.read.side_effect = [
        _quants_stub([
            (261590, 27858, 59396, 8, 1),
            (261594, 27862, 59398, 8, 1),
            (261598, 35889, 59400, 8, 1),
        ]),
        [{'id': 320753, 'state': 'assigned'}],
    ]
    odoo.search_read.side_effect = [
        # 1a search: MLs
        [
            {'id': 217657766, 'product_id': [27858, 'MOLHO PARMESAO'],
             'lot_id': [59396, '13206'], 'location_id': [8, 'FB/Estoque'],
             'location_dest_id': False, 'quantity': 319.083, 'state': 'assigned',
             'company_id': [1, 'FB'], 'picking_id': [320753, 'FB/INT/08022']},
            {'id': 217657767, 'product_id': [27862, 'MOLHO MOSTARDA'],
             'lot_id': [59398, '13206'], 'location_id': [8, 'FB/Estoque'],
             'location_dest_id': False, 'quantity': 269.0, 'state': 'assigned',
             'company_id': [1, 'FB'], 'picking_id': [320753, 'FB/INT/08022']},
            {'id': 217657769, 'product_id': [35889, 'MOLHO PESTO'],
             'lot_id': [59400, '13206'], 'location_id': [8, 'FB/Estoque'],
             'location_dest_id': False, 'quantity': 447.0, 'state': 'assigned',
             'company_id': [1, 'FB'], 'picking_id': [320753, 'FB/INT/08022']},
        ],
        # 2a search: pickings metadados
        [
            {'id': 320753, 'name': 'FB/INT/08022', 'state': 'assigned',
             'origin': False, 'partner_id': False,
             'picking_type_id': [60, 'FB: Transferências Internas (FB)'],
             'scheduled_date': '2026-05-23 10:00:00',
             'create_date': '2026-05-22 14:00:00',
             'company_id': [1, 'FB']},
        ],
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_pickings_por_quant([261590, 261594, 261598])
    assert res['total_pickings'] == 1
    assert res['total_mls'] == 3
    pkg = res['pickings'][0]
    assert pkg['id'] == 320753
    assert pkg['name'] == 'FB/INT/08022'
    assert pkg['n_mls'] == 3
    assert abs(pkg['qty_total'] - 1035.083) < 0.001  # 319.083 + 269 + 447
    assert pkg['lotes_envolvidos'] == ['13206']
    assert pkg['empresa'] == 'FB'
    assert pkg['picking_type_name'].startswith('FB: Transferências')


def test_listar_pickings_separa_mls_sem_picking():
    """MLs de MO (sem picking_id) vao em mls_sem_picking."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        _quants_stub([(100, 10, 20, 30, 1), (101, 11, 21, 31, 1)]),
        [{'id': 500, 'state': 'assigned'}],
    ]
    odoo.search_read.side_effect = [
        [
            {'id': 1, 'product_id': [10, ''], 'lot_id': [20, ''],
             'location_id': [30, ''], 'location_dest_id': False, 'quantity': 1,
             'state': 'assigned', 'company_id': [1, 'FB'],
             'picking_id': False},  # SEM PICKING
            {'id': 2, 'product_id': [11, ''], 'lot_id': [21, ''],
             'location_id': [31, ''], 'location_dest_id': False, 'quantity': 2,
             'state': 'assigned', 'company_id': [1, 'FB'],
             'picking_id': [500, 'PKG']},
        ],
        [{'id': 500, 'name': 'PKG', 'state': 'assigned',
          'origin': False, 'partner_id': False, 'picking_type_id': False,
          'scheduled_date': False, 'create_date': False, 'company_id': [1, 'FB']}],
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_pickings_por_quant([100, 101])
    assert res['total_pickings'] == 1
    assert len(res['mls_sem_picking']) == 1
    assert res['mls_sem_picking'][0]['id'] == 1


def test_listar_pickings_ordem_assigned_antes_done():
    """Pickings ordenados por state-priority + create_date."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        _quants_stub([(100, 10, 20, 30, 1), (101, 11, 21, 31, 1)]),
        [{'id': 500, 'state': 'assigned'}, {'id': 600, 'state': 'done'}],
    ]
    odoo.search_read.side_effect = [
        [
            {'id': 1, 'product_id': [10, ''], 'lot_id': [20, ''],
             'location_id': [30, ''], 'location_dest_id': False, 'quantity': 1,
             'state': 'done', 'company_id': [1, 'FB'],
             'picking_id': [600, 'PKG_DONE']},
            {'id': 2, 'product_id': [11, ''], 'lot_id': [21, ''],
             'location_id': [31, ''], 'location_dest_id': False, 'quantity': 2,
             'state': 'assigned', 'company_id': [1, 'FB'],
             'picking_id': [500, 'PKG_ASS']},
        ],
        [
            {'id': 500, 'name': 'PKG_ASS', 'state': 'assigned',
             'origin': False, 'partner_id': False, 'picking_type_id': False,
             'scheduled_date': False, 'create_date': '2026-05-20',
             'company_id': [1, 'FB']},
            {'id': 600, 'name': 'PKG_DONE', 'state': 'done',
             'origin': False, 'partner_id': False, 'picking_type_id': False,
             'scheduled_date': False, 'create_date': '2026-05-15',
             'company_id': [1, 'FB']},
        ],
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_pickings_por_quant([100, 101], states=['assigned', 'done'])
    assert res['total_pickings'] == 2
    # PKG_ASS (assigned) DEVE vir antes de PKG_DONE
    assert res['pickings'][0]['name'] == 'PKG_ASS'
    assert res['pickings'][1]['name'] == 'PKG_DONE'


def test_listar_pickings_enriquece_partner_origin_picking_type():
    """Caso real FB/OUT/01046 (devolucao para LF/LA FAMIGLIA)."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        _quants_stub([(258944, 30, 58804, 8, 1)]),  # lot MIGRACAO id=58804
        [{'id': 320846, 'state': 'assigned'}],
    ]
    odoo.search_read.side_effect = [
        [
            {'id': 100, 'product_id': [30, 'PIMENTA BIQUINHO B'],
             'lot_id': [58804, 'MIGRACAO'],
             'location_id': [8, 'FB/Estoque'],
             'location_dest_id': [9, 'Parceiros/Estoque LF'],
             'quantity': 620.32, 'state': 'assigned', 'company_id': [1, 'FB'],
             'picking_id': [320846, 'FB/OUT/01046']},
        ],
        [
            {'id': 320846, 'name': 'FB/OUT/01046', 'state': 'assigned',
             'origin': 'Devolução de FB/IN/13196',
             'partner_id': [222, 'LA FAMIGLIA - LF'],
             'picking_type_id': [70, 'FB: Expedição (FB)'],
             'scheduled_date': '2026-05-23 09:00:00',
             'create_date': '2026-05-21 16:00:00',
             'company_id': [1, 'FB']},
        ],
    ]
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_pickings_por_quant([258944])
    pkg = res['pickings'][0]
    assert pkg['origin'] == 'Devolução de FB/IN/13196'
    assert pkg['partner_name'] == 'LA FAMIGLIA - LF'
    assert pkg['picking_type_name'] == 'FB: Expedição (FB)'
    assert pkg['mls'][0]['location_dest_name'] == 'Parceiros/Estoque LF'


def test_listar_pickings_zero_mls():
    """Sem MLs encontradas: retorna vazio."""
    odoo = MagicMock()
    odoo.read.return_value = _quants_stub([(100, 10, 20, 30, 1)])
    odoo.search_read.return_value = []
    svc = StockQuantQueryService(odoo=odoo)
    res = svc.listar_pickings_por_quant([100])
    assert res['total_pickings'] == 0
    assert res['total_mls'] == 0
    assert res['pickings'] == []
    assert res['mls_sem_picking'] == []
