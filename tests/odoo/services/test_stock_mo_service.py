"""Testa StockMOService — wrapper para mrp.production (action_cancel).

Skill 4 `operando-mo-odoo`:
- V1 (2026-05-24 v5): cancelar_mo + cancelar_mos_em_massa + medir_consumo_mo.
- V6 (2026-05-27): medir_consumo_mo retorna dict {done, reservado, total};
  guard G-MO-01 distingue FURO REAL (done>0) de RESERVA FANTASMA (reservado>0,
  done=0); novos status DRY_RUN_OK_RESERVA_FANTASMA / OK_RESERVA_FANTASMA /
  FALHA_FURO_CONTABIL_REAL. Modos READ: listar_mos, detalhar_mo (sem WRITE).
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.mo import StockMOService, TOL_CONSUMO


# ============================================================
# medir_consumo_mo (helper batch — V6 dict)
# ============================================================

def test_medir_consumo_mo_vazio():
    odoo = MagicMock()
    svc = StockMOService(odoo=odoo)
    assert svc.medir_consumo_mo([]) == {}
    odoo.search_read.assert_not_called()


def test_medir_consumo_mo_retorna_dict_done_reservado_total():
    """V6: retorna {mo_id: {done, reservado, total}} particionando por state."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        # M1: 5 em done + 3 em assigned = 8 total (5 done, 3 reservado)
        {'raw_material_production_id': [100, 'M1'], 'state': 'done', 'quantity': 5.0},
        {'raw_material_production_id': [100, 'M1'], 'state': 'assigned', 'quantity': 3.0},
        # M2: 7 em waiting (so reservado)
        {'raw_material_production_id': [200, 'M2'], 'state': 'waiting', 'quantity': 7.0},
    ]
    svc = StockMOService(odoo=odoo)
    consumo = svc.medir_consumo_mo([100, 200, 300])
    assert consumo[100] == {'done': 5.0, 'reservado': 3.0, 'total': 8.0}
    assert consumo[200] == {'done': 0.0, 'reservado': 7.0, 'total': 7.0}
    assert consumo[300] == {'done': 0.0, 'reservado': 0.0, 'total': 0.0}


def test_medir_consumo_mo_partial_available_eh_reservado():
    """state='partially_available' classifica como reservado (G-MO-01 v6)."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'raw_material_production_id': [1, 'M'], 'state': 'partially_available', 'quantity': 12.0},
        {'raw_material_production_id': [1, 'M'], 'state': 'confirmed', 'quantity': 4.0},
    ]
    svc = StockMOService(odoo=odoo)
    consumo = svc.medir_consumo_mo([1])
    assert consumo[1]['done'] == 0.0
    assert consumo[1]['reservado'] == 16.0


def test_medir_consumo_mo_ignora_state_cancel():
    """Search domain deve filtrar state != cancel."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    svc.medir_consumo_mo([1, 2])
    call_args = odoo.search_read.call_args
    domain = call_args[0][1]
    assert any(d == ['state', '!=', 'cancel'] for d in domain), \
        f'Domain {domain} deveria incluir filtro state != cancel'


def test_medir_consumo_mo_quantity_none_seguro():
    """Quantity None nao quebra a soma."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'raw_material_production_id': [100, 'M1'], 'state': 'done', 'quantity': None},
        {'raw_material_production_id': [100, 'M1'], 'state': 'done', 'quantity': 5.0},
    ]
    svc = StockMOService(odoo=odoo)
    consumo = svc.medir_consumo_mo([100])
    assert consumo[100]['done'] == 5.0
    assert consumo[100]['total'] == 5.0


def test_medir_consumo_mo_legacy_retorna_total_float():
    """medir_consumo_mo_legacy retorna {mo_id: total float} (compat)."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'raw_material_production_id': [100, 'M1'], 'state': 'done', 'quantity': 5.0},
        {'raw_material_production_id': [100, 'M1'], 'state': 'assigned', 'quantity': 3.0},
    ]
    svc = StockMOService(odoo=odoo)
    legacy = svc.medir_consumo_mo_legacy([100])
    assert legacy[100] == 8.0  # total puro, float


# ============================================================
# cancelar_mo — caminho feliz EXECUTADO
# ============================================================

def _mo_dict(state='confirmed', mo_id=42, name='FB/OP/TESTE/001', company_id=1):
    """Helper para criar dict de MO mock."""
    return {
        'id': mo_id, 'name': name, 'state': state,
        'company_id': [company_id, 'NACOM GOYA - FB'],
        'product_id': [1234, 'PRODUTO TESTE'],
        'product_qty': 10.0, 'qty_produced': 0.0,
        'create_date': '2025-01-01 10:00:00',
        'date_start': '2025-01-01 10:00:00',
    }


def test_cancelar_mo_executado():
    """Caminho feliz: state=confirmed, consumo=0, action_cancel funciona."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo (1a chamada)
        [],  # medir_consumo_mo (nenhum move)
        [_mo_dict(state='cancel')],  # _ler_mo (apos action_cancel)
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, motivo='teste')
    assert r['status'] == 'EXECUTADO'
    assert r['state_antes'] == 'confirmed'
    assert r['state_apos'] == 'cancel'
    assert r['consumo']['done'] == 0.0
    assert r['consumo']['reservado'] == 0.0
    assert r['consumo_total'] == 0.0  # compat alias
    assert r['acao'] == 'cancelled'
    odoo.execute_kw.assert_any_call('mrp.production', 'action_cancel', [[42]])


def test_cancelar_mo_noop_idempotente():
    """state pre='cancel' => NOOP sem chamar action_cancel."""
    odoo = MagicMock()
    odoo.search_read.return_value = [_mo_dict(state='cancel')]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'NOOP'
    assert r['state_antes'] == 'cancel'
    assert r['state_apos'] == 'cancel'
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_dry_run_noop_idempotente():
    """state pre='cancel' + dry_run=True => DRY_RUN_NOOP."""
    odoo = MagicMock()
    odoo.search_read.return_value = [_mo_dict(state='cancel')]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_NOOP'
    odoo.execute_kw.assert_not_called()


# ============================================================
# G-MO-01 v6: guard particionado done vs reservado
# ============================================================

def test_cancelar_mo_falha_furo_contabil_real_done_acima_tol():
    """V6: done > TOL_CONSUMO => FALHA_FURO_CONTABIL_REAL (furo CONTABIL real)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo
        # state='done' com quantity=100 -> done=100 (furo real)
        [{'raw_material_production_id': [42, 'M'], 'state': 'done', 'quantity': 100.0}],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA_FURO_CONTABIL_REAL'
    assert r['consumo']['done'] == 100.0
    assert r['consumo']['reservado'] == 0.0
    assert 'unbuild' in r['erro'].lower()
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_dry_run_falha_furo_contabil_real():
    """V6: done > 0 + dry_run => DRY_RUN_FALHA_FURO_CONTABIL_REAL."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [{'raw_material_production_id': [42, 'M'], 'state': 'done', 'quantity': 50.0}],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_FALHA_FURO_CONTABIL_REAL'
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_reserva_fantasma_passa_em_dry_run():
    """V6: done=0 e reservado>0 => DRY_RUN_OK_RESERVA_FANTASMA (nao bloqueia)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        # state='assigned' com quantity=120 -> reservado=120, done=0
        [{'raw_material_production_id': [42, 'M'], 'state': 'assigned', 'quantity': 120.0}],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_OK_RESERVA_FANTASMA'
    assert r['consumo']['done'] == 0.0
    assert r['consumo']['reservado'] == 120.0
    assert 'warning_reserva_fantasma' in r
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_reserva_fantasma_executa_real_sem_furo():
    """V6: done=0 e reservado>0 + --confirmar => OK_RESERVA_FANTASMA (executa)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo
        [{'raw_material_production_id': [42, 'M'], 'state': 'waiting', 'quantity': 50.0}],
        [_mo_dict(state='cancel')],  # _ler_mo apos
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'OK_RESERVA_FANTASMA'
    assert r['state_apos'] == 'cancel'
    odoo.execute_kw.assert_any_call('mrp.production', 'action_cancel', [[42]])


def test_cancelar_mo_forcar_consumo_bypass_g_mo_01():
    """forcar_consumo=True ignora guard G-MO-01 ate em furo real."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [{'raw_material_production_id': [42, 'M'], 'state': 'done', 'quantity': 100.0}],
        [_mo_dict(state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, forcar_consumo=True)
    assert r['status'] == 'EXECUTADO'
    assert r['consumo']['done'] == 100.0
    assert r['forcar_consumo'] is True


def test_cancelar_mo_consumo_abaixo_tol_nao_bloqueia():
    """done < TOL_CONSUMO (0.0001) NAO bloqueia (rounding)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [{'raw_material_production_id': [42, 'M'], 'state': 'done', 'quantity': 0.00005}],
        [_mo_dict(state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'EXECUTADO'


def test_cancelar_mo_aceita_consumo_total_float_legacy():
    """V6 compat: consumo_total=float ainda funciona (degrada para guard antigo)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [_mo_dict(state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    # Float legacy: tratado como total puro (sem particao); 0.0 = OK
    r = svc.cancelar_mo(42, consumo_total=0.0)
    assert r['status'] == 'EXECUTADO'
    assert r['consumo']['done'] == 0.0


# ============================================================
# State nao-cancelavel (done)
# ============================================================

def test_cancelar_mo_state_done_bloqueia():
    """state='done' => FALHA_STATE_NAO_CANCELAVEL (sugere unbuild)."""
    odoo = MagicMock()
    odoo.search_read.return_value = [_mo_dict(state='done')]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA_STATE_NAO_CANCELAVEL'
    assert 'unbuild' in r['erro'].lower()
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_dry_run_state_done():
    odoo = MagicMock()
    odoo.search_read.return_value = [_mo_dict(state='done')]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_FALHA_STATE_NAO_CANCELAVEL'


# ============================================================
# State inesperado pos
# ============================================================

def test_cancelar_mo_state_inesperado_apos_cancel():
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],
        [_mo_dict(state='confirmed')],  # state nao mudou
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA_STATE_INESPERADO'
    assert r['state_apos'] == 'confirmed'


def test_cancelar_mo_excecao_generica():
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],
    ]
    odoo.execute_kw.side_effect = Exception('Connection refused')
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA'
    assert 'Connection refused' in r['erro']


def test_cancelar_mo_inexistente():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(99999)
    assert r['status'] == 'FALHA'
    assert 'nao existe' in r['erro']


def test_cancelar_mo_dry_run_ok_nao_chama_action_cancel():
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_OK'
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_consumo_total_passado_evita_query():
    """consumo_total dict passado evita medir_consumo_mo."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [_mo_dict(state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(
        42, consumo_total={'done': 0.0, 'reservado': 0.0, 'total': 0.0}
    )
    assert r['status'] == 'EXECUTADO'
    assert odoo.search_read.call_count == 2  # so 2 _ler_mo


# ============================================================
# cancelar_mos_em_massa
# ============================================================

def test_cancelar_mos_em_massa_filtra_so_furo_real_v6():
    """V6: consumo='zero' filtra apenas MOs com done>TOL (furo real).

    MOs com reservado>0 mas done=0 (reserva fantasma) PASSAM —
    action_cancel libera reservas sem furo.
    """
    odoo = MagicMock()
    mos_candidatas = [
        {'id': 1, 'name': 'M1', 'state': 'confirmed',
         'create_date': '2025-01-01', 'company_id': [1, 'FB']},
        {'id': 2, 'name': 'M2', 'state': 'confirmed',
         'create_date': '2025-01-02', 'company_id': [1, 'FB']},
        {'id': 3, 'name': 'M3', 'state': 'confirmed',
         'create_date': '2025-01-03', 'company_id': [1, 'FB']},
    ]
    odoo.search_read.side_effect = [
        mos_candidatas,
        # M1=limpa, M2=furo REAL (done=50), M3=reserva fantasma (assigned=30)
        [
            {'raw_material_production_id': [2, 'M2'], 'state': 'done', 'quantity': 50.0},
            {'raw_material_production_id': [3, 'M3'], 'state': 'assigned', 'quantity': 30.0},
        ],
        # cancelar_mo(M1): _ler_mo + apos
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
        # cancelar_mo(M3): _ler_mo + apos (reserva fantasma passa)
        [_mo_dict(mo_id=3, state='confirmed')],
        [_mo_dict(mo_id=3, state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(consumo='zero')

    assert res['total_pre_filtro'] == 3
    assert res['total_candidatas'] == 2  # M2 (furo real) excluida; M3 (fantasma) passa
    assert res['total_filtradas_por_consumo'] == 1
    # M1 EXECUTADO; M3 OK_RESERVA_FANTASMA
    assert res['contagem_status'] == {'EXECUTADO': 1, 'OK_RESERVA_FANTASMA': 1}


def test_cancelar_mos_em_massa_consumo_qualquer_inclui_todas():
    """consumo='qualquer' nao filtra (guard G-MO-01 ainda bloqueia por MO)."""
    odoo = MagicMock()
    mos = [
        {'id': 1, 'name': 'M1', 'state': 'confirmed',
         'create_date': '2025-01-01', 'company_id': [1, 'FB']},
        {'id': 2, 'name': 'M2', 'state': 'confirmed',
         'create_date': '2025-01-02', 'company_id': [1, 'FB']},
    ]
    odoo.search_read.side_effect = [
        mos,
        # M2 com done=50 (furo real)
        [{'raw_material_production_id': [2, 'M2'], 'state': 'done', 'quantity': 50.0}],
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
        [_mo_dict(mo_id=2, state='confirmed')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(consumo='qualquer')

    assert res['total_candidatas'] == 2
    assert res['contagem_status'] == {
        'EXECUTADO': 1, 'FALHA_FURO_CONTABIL_REAL': 1
    }


def test_cancelar_mos_em_massa_max_n_limite():
    odoo = MagicMock()
    mos = [
        {'id': i, 'name': f'M{i}', 'state': 'confirmed',
         'create_date': f'2025-01-0{i}', 'company_id': [1, 'FB']}
        for i in (1, 2, 3)
    ]
    odoo.search_read.side_effect = [
        mos,
        [],
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(max_n=1)
    assert res['total_candidatas'] == 1
    assert res['contagem_status'] == {'EXECUTADO': 1}


def test_cancelar_mos_em_massa_dry_run_nao_executa():
    odoo = MagicMock()
    mos = [{'id': 1, 'name': 'M1', 'state': 'confirmed',
            'create_date': '2025-01-01', 'company_id': [1, 'FB']}]
    odoo.search_read.side_effect = [
        mos,
        [],
        [_mo_dict(mo_id=1, state='confirmed')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(dry_run=True)
    assert res['contagem_status'] == {'DRY_RUN_OK': 1}
    odoo.execute_kw.assert_not_called()


def test_cancelar_mos_em_massa_consumo_invalido_raise():
    import pytest
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    with pytest.raises(ValueError, match="consumo deve ser"):
        svc.cancelar_mos_em_massa(consumo='invalido')


def test_cancelar_mos_em_massa_ordena_por_create_date_fifo():
    odoo = MagicMock()
    mos = [
        {'id': 3, 'name': 'M3', 'state': 'confirmed',
         'create_date': '2025-03-01', 'company_id': [1, 'FB']},
        {'id': 1, 'name': 'M1', 'state': 'confirmed',
         'create_date': '2025-01-01', 'company_id': [1, 'FB']},
        {'id': 2, 'name': 'M2', 'state': 'confirmed',
         'create_date': '2025-02-01', 'company_id': [1, 'FB']},
    ]
    odoo.search_read.side_effect = [
        mos,
        [],
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
        [_mo_dict(mo_id=2, state='confirmed')],
        [_mo_dict(mo_id=2, state='cancel')],
        [_mo_dict(mo_id=3, state='confirmed')],
        [_mo_dict(mo_id=3, state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa()
    ordem_ids = [r['mo_id'] for r in res['resultados']]
    assert ordem_ids == [1, 2, 3]


def test_cancelar_mos_em_massa_domain_inclui_filtros():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    svc.cancelar_mos_em_massa(
        create_de='2024-01-01', create_ate='2026-01-01',
        states=['confirmed', 'draft'], empresas=[1, 4],
    )
    domain = odoo.search_read.call_args[0][1]
    assert ['state', 'in', ['confirmed', 'draft']] in domain
    assert ['company_id', 'in', [1, 4]] in domain
    assert ['create_date', '>=', '2024-01-01'] in domain
    assert ['create_date', '<', '2026-01-01'] in domain


# ============================================================
# Code-review fixes (sessao 2026-05-24 v5)
# ============================================================

def test_cancelar_mo_mo_deletada_apos_cancel_eh_executado():
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],
        [],  # MO sumiu apos cancel
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'EXECUTADO'
    assert r['state_apos'] == 'cancel_deleted'
    assert r['acao'] == 'cancelled_and_deleted'


def test_cancelar_mos_em_massa_consumo_qualquer_sem_forcar_emite_warning(caplog):
    import logging
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    with caplog.at_level(logging.WARNING, logger='app.odoo.estoque.scripts.mo'):
        svc.cancelar_mos_em_massa(consumo='qualquer')
    assert any('qualquer' in r.message and 'forcar_consumo' in r.message
               for r in caplog.records)


def test_cancelar_mos_em_massa_search_read_usa_order_create_date_asc():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    svc.cancelar_mos_em_massa()
    primeira_call = odoo.search_read.call_args_list[0]
    assert primeira_call.kwargs.get('order') == 'create_date asc'


# ============================================================
# listar_mos (READ — V6 2026-05-27)
# ============================================================

def test_listar_mos_classifica_seguro_reserva_fantasma_furo_real():
    """listar_mos classifica cada item por SEGURO/RESERVA_FANTASMA/FURO_REAL."""
    odoo = MagicMock()
    mos = [
        {'id': 1, 'name': 'M1', 'state': 'draft',
         'create_date': '2025-01-01', 'company_id': [1, 'FB']},
        {'id': 2, 'name': 'M2', 'state': 'confirmed',
         'create_date': '2025-01-02', 'company_id': [1, 'FB']},
        {'id': 3, 'name': 'M3', 'state': 'progress',
         'create_date': '2025-01-03', 'company_id': [1, 'FB']},
    ]
    odoo.search_read.side_effect = [
        mos,
        # M2 reserva fantasma; M3 furo real
        [
            {'raw_material_production_id': [2, 'M2'], 'state': 'assigned', 'quantity': 50.0},
            {'raw_material_production_id': [3, 'M3'], 'state': 'done', 'quantity': 25.0},
        ],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.listar_mos()
    assert res['total'] == 3
    assert res['classificacao'] == {
        'SEGURO': 1, 'RESERVA_FANTASMA': 1, 'FURO_REAL': 1,
    }
    by_id = {it['id']: it for it in res['itens']}
    assert by_id[1]['classificacao'] == 'SEGURO'
    assert by_id[2]['classificacao'] == 'RESERVA_FANTASMA'
    assert by_id[3]['classificacao'] == 'FURO_REAL'


def test_listar_mos_nao_chama_action_cancel():
    """listar_mos e READ — nunca chama action_cancel/write/create."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [{'id': 1, 'name': 'M', 'state': 'draft',
          'create_date': '2025-01-01', 'company_id': [1, 'FB']}],
        [],
    ]
    svc = StockMOService(odoo=odoo)
    svc.listar_mos()
    odoo.execute_kw.assert_not_called()
    odoo.write.assert_not_called()
    odoo.create.assert_not_called()


# ============================================================
# detalhar_mo (READ — V6 2026-05-27)
# ============================================================

def test_detalhar_mo_retorna_estrutura_completa():
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # 1) MO
        [{**_mo_dict(state='confirmed'),
          'reservation_state': 'assigned',
          'date_deadline': '2025-01-02', 'date_finished': False,
          'origin': 'VCD123', 'bom_id': [88, 'BOM-X'],
          'move_raw_ids': [101], 'move_finished_ids': [102]}],
        # 2) medir_consumo
        [{'raw_material_production_id': [42, 'M'], 'state': 'assigned', 'quantity': 60.0}],
        # 3) moves (raws + finished)
        [
            {'id': 101, 'state': 'assigned', 'product_id': [999, 'AGUA'],
             'product_uom_qty': 60.0, 'quantity': 60.0, 'picked': True,
             'location_id': [10, 'FB/Pre/Linha'], 'location_dest_id': [11, 'Virtual/Prod'],
             'move_line_ids': [201], 'raw_material_production_id': [42, 'M']},
            {'id': 102, 'state': 'confirmed', 'product_id': [1234, 'ACABADO'],
             'product_uom_qty': 10.0, 'quantity': 0.0, 'picked': False,
             'location_id': [11, 'Virtual/Prod'], 'location_dest_id': [12, 'FB/Pos'],
             'move_line_ids': [], 'raw_material_production_id': False},
        ],
        # 4) MLs
        [{'id': 201, 'state': 'assigned', 'quantity': 60.0, 'picked': True,
          'location_id': [10, 'FB/Pre/Linha'], 'lot_id': [501, 'LOTE-A'],
          'move_id': [101, 'raw']}],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.detalhar_mo(42)
    assert r['id'] == 42
    assert r['classificacao'] == 'RESERVA_FANTASMA'
    assert r['consumo']['reservado'] == 60.0
    assert r['consumo']['done'] == 0.0
    assert len(r['details']['raws']) == 1
    raw = r['details']['raws'][0]
    assert raw['product_name'] == 'AGUA'
    assert raw['picked'] is True
    assert raw['move_lines'][0]['lot'] == 'LOTE-A'
    assert len(r['details']['finished']) == 1
    odoo.execute_kw.assert_not_called()


def test_detalhar_mo_inexistente_retorna_erro():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    r = svc.detalhar_mo(99999)
    assert 'erro' in r
    assert 'nao existe' in r['erro']


# ============================================================
# Audit pre/pos (V6 2026-05-27)
# ============================================================

def test_snapshot_mo_retorna_dict_com_mo_moves_mls_quants():
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [{'id': 42, 'name': 'M', 'state': 'confirmed', 'reservation_state': 'assigned',
          'qty_produced': 0.0, 'move_raw_ids': [101], 'move_finished_ids': []}],
        # moves
        [{'id': 101, 'state': 'assigned',
          'product_id': [999, 'P'], 'product_uom_qty': 1.0, 'quantity': 1.0,
          'picked': True, 'location_id': [10, 'L'], 'move_line_ids': [201, 202]}],
        # quants origem (1 produto+location)
        [{'product_id': [999, 'P'], 'location_id': [10, 'L'], 'lot_id': [5, 'LOTE'],
          'quantity': 100.0, 'reserved_quantity': 1.0}],
    ]
    svc = StockMOService(odoo=odoo)
    snap = svc._snapshot_mo(42)
    assert snap is not None
    assert snap['mo']['state'] == 'confirmed'
    assert snap['mls_count'] == 2  # len(move_line_ids)
    assert len(snap['quants_origem']) == 1


def test_diff_snapshots_detecta_mudancas_e_quants_delta():
    pre = {
        'mo': {'state': 'confirmed', 'reservation_state': 'assigned'},
        'moves_raw': [{'id': 101, 'state': 'assigned', 'quantity': 10.0}],
        'moves_finished': [{'id': 102, 'state': 'confirmed'}],
        'mls_count': 5,
        'quants_origem': [
            {'product_id': [999, 'P'], 'lot_id': [5, 'L'], 'reserved_quantity': 10.0}
        ],
    }
    pos = {
        'mo': {'state': 'cancel', 'reservation_state': False},
        'moves_raw': [{'id': 101, 'state': 'cancel', 'quantity': 0.0}],
        'moves_finished': [{'id': 102, 'state': 'cancel'}],
        'mls_count': 0,
        'quants_origem': [
            {'product_id': [999, 'P'], 'lot_id': [5, 'L'], 'reserved_quantity': 0.0}
        ],
    }
    diff = StockMOService._diff_snapshots(pre, pos)
    assert diff['mo_state'] == {'pre': 'confirmed', 'pos': 'cancel'}
    assert diff['mls_count']['pre'] == 5 and diff['mls_count']['pos'] == 0
    assert len(diff['quants_reserved_delta']) == 1
    assert diff['quants_reserved_delta'][0]['delta'] == -10.0


def test_cancelar_mo_com_audit_inclui_pre_pos_diff_em_real():
    """cancelar_mo_com_audit (real) inclui audit.pre + audit.pos + audit.diff.

    Quando move_raw_ids=[] e move_finished_ids=[], _snapshot_mo curto-circuita
    em moves (sem search_read de stock.move) — sequencia: 1 PRE + 3 cancelar
    (_ler_mo + medir + _ler_mo POS) + 1 POS = 5 search_reads.
    """
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # PRE snapshot mo (sem moves -> curto-circuita)
        [{'id': 42, 'name': 'M', 'state': 'confirmed', 'reservation_state': 'assigned',
          'qty_produced': 0.0, 'move_raw_ids': [], 'move_finished_ids': []}],
        # cancelar_mo._ler_mo (1a)
        [_mo_dict(state='confirmed')],
        # cancelar_mo.medir_consumo
        [],
        # cancelar_mo._ler_mo (pos)
        [_mo_dict(state='cancel')],
        # POS snapshot mo (sem moves -> curto-circuita)
        [{'id': 42, 'name': 'M', 'state': 'cancel', 'reservation_state': False,
          'qty_produced': 0.0, 'move_raw_ids': [], 'move_finished_ids': []}],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo_com_audit(42)
    assert r['status'] == 'EXECUTADO', f"status={r.get('status')} erro={r.get('erro')}"
    assert 'audit' in r
    assert r['audit']['pre'] is not None
    assert r['audit']['pos'] is not None
    assert 'diff' in r['audit']
    assert r['audit']['diff']['mo_state'] == {'pre': 'confirmed', 'pos': 'cancel'}


def test_cancelar_mo_com_audit_dry_run_so_captura_pre():
    """Em dry_run, audit so inclui 'pre' (sem chamar action_cancel)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        # PRE snapshot mo (sem moves curto-circuita)
        [{'id': 42, 'name': 'M', 'state': 'confirmed', 'reservation_state': 'assigned',
          'qty_produced': 0.0, 'move_raw_ids': [], 'move_finished_ids': []}],
        # cancelar_mo._ler_mo
        [_mo_dict(state='confirmed')],
        # cancelar_mo.medir_consumo
        [],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo_com_audit(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_OK', f"status={r.get('status')} erro={r.get('erro')}"
    assert 'pre' in r['audit']
    assert 'pos' not in r['audit']
    odoo.execute_kw.assert_not_called()


# ============================================================
# TOL_CONSUMO export
# ============================================================

def test_tol_consumo_pequeno_mas_nao_zero():
    assert TOL_CONSUMO == 0.0001
