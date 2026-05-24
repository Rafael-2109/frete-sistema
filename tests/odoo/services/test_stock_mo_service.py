"""Testa StockMOService — wrapper para mrp.production (action_cancel).

Skill 4 `operando-mo-odoo` V1 (2026-05-24 v5):
- cancelar_mo: atomo unico, guard G-MO-01 (consumo>0=furo), idempotencia,
  re-le state pos (G019-like pattern).
- cancelar_mos_em_massa: composicao sobre cancelar_mo + filtros.
- medir_consumo_mo: soma stock.move.quantity (state != cancel) por MO.
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.mo import StockMOService, TOL_CONSUMO


# ============================================================
# medir_consumo_mo (helper batch)
# ============================================================

def test_medir_consumo_mo_vazio():
    odoo = MagicMock()
    svc = StockMOService(odoo=odoo)
    assert svc.medir_consumo_mo([]) == {}
    odoo.search_read.assert_not_called()


def test_medir_consumo_mo_soma_quantity_por_mo():
    odoo = MagicMock()
    # raw_material_production_id vem como [id, name] (Many2one)
    odoo.search_read.return_value = [
        {'raw_material_production_id': [100, 'M1'], 'quantity': 5.0},
        {'raw_material_production_id': [100, 'M1'], 'quantity': 3.0},
        {'raw_material_production_id': [200, 'M2'], 'quantity': 7.0},
    ]
    svc = StockMOService(odoo=odoo)
    consumo = svc.medir_consumo_mo([100, 200, 300])
    assert consumo[100] == 8.0
    assert consumo[200] == 7.0
    assert consumo[300] == 0.0  # nao apareceu nos moves


def test_medir_consumo_mo_ignora_state_cancel():
    """Search domain deve filtrar state != cancel."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    svc.medir_consumo_mo([1, 2])
    call_args = odoo.search_read.call_args
    domain = call_args[0][1]
    # Deve ter ['state', '!=', 'cancel']
    assert any(d == ['state', '!=', 'cancel'] for d in domain), \
        f'Domain {domain} deveria incluir filtro state != cancel'


def test_medir_consumo_mo_quantity_none_seguro():
    """Quantity None nao quebra a soma."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'raw_material_production_id': [100, 'M1'], 'quantity': None},
        {'raw_material_production_id': [100, 'M1'], 'quantity': 5.0},
    ]
    svc = StockMOService(odoo=odoo)
    consumo = svc.medir_consumo_mo([100])
    assert consumo[100] == 5.0


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
    assert r['consumo_total'] == 0.0
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
# G-MO-01: guard consumo > 0 = FURO CONTABIL
# ============================================================

def test_cancelar_mo_falha_furo_contabil_consumo_acima_tol():
    """consumo > TOL_CONSUMO + forcar_consumo=False (default) => FALHA_FURO_CONTABIL."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo
        [{'raw_material_production_id': [42, 'M'], 'quantity': 100.0}],  # consumo > 0
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA_FURO_CONTABIL'
    assert r['consumo_total'] == 100.0
    assert 'unbuild' in r['erro'].lower(), f'Erro deve mencionar unbuild: {r["erro"]}'
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_dry_run_falha_furo_contabil():
    """consumo > 0 + dry_run=True => DRY_RUN_FALHA_FURO_CONTABIL."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [{'raw_material_production_id': [42, 'M'], 'quantity': 50.0}],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_FALHA_FURO_CONTABIL'
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_forcar_consumo_bypass_g_mo_01():
    """forcar_consumo=True ignora guard G-MO-01 e executa cancel."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo
        [{'raw_material_production_id': [42, 'M'], 'quantity': 100.0}],  # consumo > 0
        [_mo_dict(state='cancel')],  # _ler_mo apos
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, forcar_consumo=True)
    assert r['status'] == 'EXECUTADO'
    assert r['consumo_total'] == 100.0
    assert r['forcar_consumo'] is True
    odoo.execute_kw.assert_any_call('mrp.production', 'action_cancel', [[42]])


def test_cancelar_mo_consumo_abaixo_tol_nao_bloqueia():
    """consumo entre 0 e TOL_CONSUMO (0.0001) NAO bloqueia (rounding)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [{'raw_material_production_id': [42, 'M'], 'quantity': 0.00005}],  # < TOL
        [_mo_dict(state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'EXECUTADO'


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
    """state='done' + dry_run => DRY_RUN_FALHA_STATE_NAO_CANCELAVEL."""
    odoo = MagicMock()
    odoo.search_read.return_value = [_mo_dict(state='done')]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_FALHA_STATE_NAO_CANCELAVEL'


# ============================================================
# State inesperado pos (action_cancel chamado mas state != cancel)
# ============================================================

def test_cancelar_mo_state_inesperado_apos_cancel():
    """action_cancel executado mas state pos != 'cancel' => FALHA_STATE_INESPERADO."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],  # consumo 0
        [_mo_dict(state='confirmed')],  # state nao mudou apos cancel
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA_STATE_INESPERADO'
    assert r['state_apos'] == 'confirmed'
    assert 'esperado' in r['erro'].lower()


# ============================================================
# Excecao generica em action_cancel
# ============================================================

def test_cancelar_mo_excecao_generica():
    """action_cancel raises => FALHA com erro."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],  # consumo 0
    ]
    odoo.execute_kw.side_effect = Exception('Connection refused')
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'FALHA'
    assert 'Connection refused' in r['erro']


def test_cancelar_mo_inexistente():
    """MO sem _ler_mo retorno => FALHA com erro."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(99999)
    assert r['status'] == 'FALHA'
    assert 'nao existe' in r['erro']


# ============================================================
# Dry-run nao chama execute_kw (action_cancel)
# ============================================================

def test_cancelar_mo_dry_run_ok_nao_chama_action_cancel():
    """state=confirmed + dry_run=True + consumo=0 => DRY_RUN_OK sem chamar action."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],
        [],  # consumo 0
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, dry_run=True)
    assert r['status'] == 'DRY_RUN_OK'
    assert r['state_apos_esperado'] == 'cancel'
    odoo.execute_kw.assert_not_called()


def test_cancelar_mo_consumo_total_passado_evita_query():
    """Se consumo_total e' passado, nao chama medir_consumo_mo."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo
        [_mo_dict(state='cancel')],     # _ler_mo apos
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42, consumo_total=0.0)
    assert r['status'] == 'EXECUTADO'
    # Apenas 2 search_read (sem medir_consumo)
    assert odoo.search_read.call_count == 2


# ============================================================
# cancelar_mos_em_massa
# ============================================================

def test_cancelar_mos_em_massa_filtra_consumo_zero_default():
    """Default consumo='zero' exclui MOs com consumo > TOL."""
    odoo = MagicMock()
    # search_read 1: lista MOs candidatas (3 MOs)
    # search_read 2: medir_consumo_mo (uma MO com consumo)
    # search_read 3-4 (por MO): _ler_mo individual (2 MOs canceladas)
    # search_read 5-6 (apos cancel): _ler_mo individual (2 MOs canceladas)
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
        # medir_consumo: M2 tem consumo > 0 (filtrada)
        [{'raw_material_production_id': [2, 'M2'], 'quantity': 50.0}],
        # cancelar_mo(M1): _ler_mo + (consumo passado) + _ler_mo apos
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
        # cancelar_mo(M3): _ler_mo + (consumo passado) + _ler_mo apos
        [_mo_dict(mo_id=3, state='confirmed')],
        [_mo_dict(mo_id=3, state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(consumo='zero')

    assert res['total_pre_filtro'] == 3
    assert res['total_candidatas'] == 2  # M2 excluida
    assert res['total_filtradas_por_consumo'] == 1
    assert res['contagem_status'] == {'EXECUTADO': 2}
    assert len(res['resultados']) == 2


def test_cancelar_mos_em_massa_consumo_qualquer_inclui_todas():
    """consumo='qualquer' nao filtra (mas guard G-MO-01 ainda bloqueia por MO)."""
    odoo = MagicMock()
    mos = [
        {'id': 1, 'name': 'M1', 'state': 'confirmed',
         'create_date': '2025-01-01', 'company_id': [1, 'FB']},
        {'id': 2, 'name': 'M2', 'state': 'confirmed',
         'create_date': '2025-01-02', 'company_id': [1, 'FB']},
    ]
    odoo.search_read.side_effect = [
        mos,
        [{'raw_material_production_id': [2, 'M2'], 'quantity': 50.0}],
        # cancelar_mo(M1): _ler_mo + apos
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
        # cancelar_mo(M2): _ler_mo (NAO apos — bloqueia em G-MO-01)
        [_mo_dict(mo_id=2, state='confirmed')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(consumo='qualquer')

    assert res['total_candidatas'] == 2
    assert res['total_filtradas_por_consumo'] == 0
    # M1 EXECUTADO, M2 FALHA_FURO_CONTABIL (guard ainda bloqueia)
    assert res['contagem_status'] == {'EXECUTADO': 1, 'FALHA_FURO_CONTABIL': 1}


def test_cancelar_mos_em_massa_max_n_limite():
    """max_n=1 limita a 1 MO mesmo com 3 candidatas."""
    odoo = MagicMock()
    mos = [
        {'id': i, 'name': f'M{i}', 'state': 'confirmed',
         'create_date': f'2025-01-0{i}', 'company_id': [1, 'FB']}
        for i in (1, 2, 3)
    ]
    odoo.search_read.side_effect = [
        mos,
        [],  # consumo 0 em todas
        # cancelar_mo(M1): _ler_mo + apos
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(max_n=1)
    assert res['total_candidatas'] == 1
    assert res['contagem_status'] == {'EXECUTADO': 1}


def test_cancelar_mos_em_massa_dry_run_nao_executa():
    """dry_run=True: sem chamar action_cancel."""
    odoo = MagicMock()
    mos = [{'id': 1, 'name': 'M1', 'state': 'confirmed',
            'create_date': '2025-01-01', 'company_id': [1, 'FB']}]
    odoo.search_read.side_effect = [
        mos,
        [],  # consumo 0
        # cancelar_mo dry_run: 1 _ler_mo (sem apos)
        [_mo_dict(mo_id=1, state='confirmed')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa(dry_run=True)
    assert res['contagem_status'] == {'DRY_RUN_OK': 1}
    odoo.execute_kw.assert_not_called()


def test_cancelar_mos_em_massa_consumo_invalido_raise():
    """consumo != 'zero'/'qualquer' => ValueError."""
    import pytest
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    with pytest.raises(ValueError, match="consumo deve ser"):
        svc.cancelar_mos_em_massa(consumo='invalido')


def test_cancelar_mos_em_massa_ordena_por_create_date_fifo():
    """MOs ordenadas por create_date ascendente (mais antigas primeiro)."""
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
        # cancelar_mo(1): 2 calls
        [_mo_dict(mo_id=1, state='confirmed')],
        [_mo_dict(mo_id=1, state='cancel')],
        # cancelar_mo(2): 2 calls
        [_mo_dict(mo_id=2, state='confirmed')],
        [_mo_dict(mo_id=2, state='cancel')],
        # cancelar_mo(3): 2 calls
        [_mo_dict(mo_id=3, state='confirmed')],
        [_mo_dict(mo_id=3, state='cancel')],
    ]
    svc = StockMOService(odoo=odoo)
    res = svc.cancelar_mos_em_massa()
    ordem_ids = [r['mo_id'] for r in res['resultados']]
    assert ordem_ids == [1, 2, 3], f'FIFO esperado [1,2,3], recebido {ordem_ids}'


def test_cancelar_mos_em_massa_domain_inclui_filtros():
    """Filtros (create_de, create_ate, states, empresas) viram domain."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    svc.cancelar_mos_em_massa(
        create_de='2024-01-01', create_ate='2026-01-01',
        states=['confirmed', 'draft'], empresas=[1, 4],
    )
    domain = odoo.search_read.call_args[0][1]
    # Deve ter pelo menos: state in, company_id in, create_date >=, create_date <
    assert ['state', 'in', ['confirmed', 'draft']] in domain
    assert ['company_id', 'in', [1, 4]] in domain
    assert ['create_date', '>=', '2024-01-01'] in domain
    assert ['create_date', '<', '2026-01-01'] in domain


# ============================================================
# Code-review fixes (sessao 2026-05-24 v5)
# ============================================================

def test_cancelar_mo_mo_deletada_apos_cancel_eh_executado():
    """M1 fix: se _ler_mo retorna None apos action_cancel (MO deletada por
    cascade customizado), tratar como EXECUTADO (action_cancel nao raised)."""
    odoo = MagicMock()
    odoo.search_read.side_effect = [
        [_mo_dict(state='confirmed')],  # _ler_mo (1a)
        [],  # consumo 0
        [],  # _ler_mo apos retorna [] (MO sumiu)
    ]
    svc = StockMOService(odoo=odoo)
    r = svc.cancelar_mo(42)
    assert r['status'] == 'EXECUTADO'
    assert r['state_apos'] == 'cancel_deleted'
    assert r['acao'] == 'cancelled_and_deleted'
    odoo.execute_kw.assert_any_call('mrp.production', 'action_cancel', [[42]])


def test_cancelar_mos_em_massa_consumo_qualquer_sem_forcar_emite_warning(caplog):
    """M3 fix: warning quando consumo='qualquer' sem forcar_consumo=True."""
    import logging
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    with caplog.at_level(logging.WARNING, logger='app.odoo.estoque.scripts.mo'):
        svc.cancelar_mos_em_massa(consumo='qualquer')
    assert any('qualquer' in r.message and 'forcar_consumo' in r.message
               for r in caplog.records), \
        f'Esperado warning sobre qualquer/forcar_consumo, recebido: {[r.message for r in caplog.records]}'


def test_cancelar_mos_em_massa_search_read_usa_order_create_date_asc():
    """H1 fix: search_read deve usar order='create_date asc' (FIFO server-side)."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockMOService(odoo=odoo)
    svc.cancelar_mos_em_massa()
    # primeira chamada (mrp.production search) deve ter order kwarg
    primeira_call = odoo.search_read.call_args_list[0]
    assert primeira_call.kwargs.get('order') == 'create_date asc', \
        f'order esperado="create_date asc", recebido kwargs={primeira_call.kwargs}'


# ============================================================
# TOL_CONSUMO export
# ============================================================

def test_tol_consumo_pequeno_mas_nao_zero():
    """TOL_CONSUMO bate com pattern dos scripts-fonte (0.0001)."""
    assert TOL_CONSUMO == 0.0001
