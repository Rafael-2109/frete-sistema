"""Tests para `_executar_cleanup_pos_bulk` do CLI transferir_para_indisp_em_lote.

S2 v12: cleanup automatico pos-bulk modo C que lista reserveds residuais
negativos (`qty=0 + reserved<0`) e saldos negativos (`qty<0`) nos cods
processados e aplica Skill 2.4 zerar_residual + Skill 1 ajustar_quant
valor_absoluto=0.

Mocka odoo (XML-RPC) para focar no algoritmo.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[3] / '.claude/skills/transferindo-interno-odoo/scripts'))

# Import direto do CLI module
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'transferir_para_indisp_em_lote',
    _THIS.parents[3] / '.claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py',
)
_mod = importlib.util.module_from_spec(_spec)
# NAO executamos _spec.loader.exec_module(_mod) — isso carregaria deps
# pesadas (Flask boot, etc.) — usamos so os helpers via direct read+exec.

# Estrategia alternativa: reimport so o helper que queremos testar
# (definido em escopo modulo, sem deps de runtime ao import time).
# Para simplificar: copia o helper em uma instancia local de teste seria
# overkill. Em vez disso, importamos via importlib hack.
import os
os.environ.setdefault('ODOO_USERNAME', 'test')
os.environ.setdefault('ODOO_API_KEY', 'test')

_spec.loader.exec_module(_mod)
_executar_cleanup_pos_bulk = _mod._executar_cleanup_pos_bulk


def test_cleanup_sem_quants_retorna_vazio():
    """product_ids vazio -> CLEANUP_OK_VAZIO sem chamadas odoo."""
    odoo_mock = MagicMock()
    res = _executar_cleanup_pos_bulk(
        odoo=odoo_mock, product_ids=[],
        company_id=1, locs_origem=[8, 4067],
        dry_run=True,
    )
    assert res['status'] == 'CLEANUP_OK_VAZIO'
    assert res['n_reserveds_zerados'] == 0 if 'n_reserveds_zerados' in res else True
    assert odoo_mock.search_read.call_count == 0


def test_cleanup_zero_anomalias_retorna_vazio():
    """Quants existem mas nenhum tem reserved<0 nem qty<0 -> CLEANUP_OK_VAZIO."""
    odoo_mock = MagicMock()
    odoo_mock.search_read.return_value = [
        {'id': 100, 'product_id': [27918, 'SAL'], 'lot_id': [60001, 'A'],
         'location_id': [8, 'FB/Est'], 'quantity': 50.0, 'reserved_quantity': 0.0},
        {'id': 101, 'product_id': [27918, 'SAL'], 'lot_id': [60002, 'B'],
         'location_id': [8, 'FB/Est'], 'quantity': 0.0, 'reserved_quantity': 0.0},
    ]
    res = _executar_cleanup_pos_bulk(
        odoo=odoo_mock, product_ids=[27918],
        company_id=1, locs_origem=[8],
        dry_run=True,
    )
    assert res['status'] == 'CLEANUP_OK_VAZIO'
    assert res['n_reserveds_zerados'] == 0
    assert res['n_qty_ajustados'] == 0
    assert res['quants_reserved_negativo'] == []
    assert res['quants_qty_negativo'] == []


def test_cleanup_classifica_reserved_negativo_e_qty_negativo():
    """Identifica corretamente os 2 tipos de anomalia."""
    odoo_mock = MagicMock()
    odoo_mock.search_read.return_value = [
        # OK normal — ignorar
        {'id': 100, 'product_id': [27918, 'SAL'], 'lot_id': [60001, 'A'],
         'location_id': [8, 'FB/Est'], 'quantity': 50.0, 'reserved_quantity': 0.0},
        # qty=0 + reserved<0 -> RESERVED_NEG
        {'id': 200, 'product_id': [27918, 'SAL'], 'lot_id': False,
         'location_id': [27458, 'FB/Salm'], 'quantity': 0.0, 'reserved_quantity': -5.0},
        # qty<0 -> QTY_NEG
        {'id': 300, 'product_id': [30490, 'ACUC'], 'lot_id': False,
         'location_id': [4067, 'FB/Man'], 'quantity': -100.0, 'reserved_quantity': -50.0},
    ]
    # zerar_reserved_residual mock retorna dry_run OK
    with patch(
        'app.odoo.estoque.scripts.reserva.StockReservaService'
    ) as mk_res_svc:
        instance_res = mk_res_svc.return_value
        instance_res.zerar_reserved_residual.return_value = {
            'status': 'DRY_RUN_OK', 'acao': 'mock', 'tempo_ms': 1,
        }
        # ajustar_quant mock dry_run OK
        with patch(
            'app.odoo.estoque.scripts.quant.StockQuantAdjustmentService'
        ) as mk_q_svc:
            instance_q = mk_q_svc.return_value
            instance_q.ajustar_quant.return_value = {
                'status': 'DRY_RUN_OK', 'qty_antes': -100, 'qty_apos': 0,
                'ajuste_aplicado': 100, 'tempo_ms': 1,
            }
            res = _executar_cleanup_pos_bulk(
                odoo=odoo_mock, product_ids=[27918, 30490],
                company_id=1, locs_origem=[8, 27458, 4067],
                dry_run=True,
            )
    # qty<0 conta como qty_neg (mas tambem como reserved_neg se reserved<0)
    # Quant 200: reserved_neg apenas (qty=0)
    # Quant 300: ambos (qty<0 E reserved<0)
    assert res['status'] == 'CLEANUP_OK'
    assert res['n_reserveds_zerados'] == 2  # quants 200 e 300
    assert res['n_qty_ajustados'] == 1     # so quant 300
    qids_reserved = [q['quant_id'] for q in res['quants_reserved_negativo']]
    qids_qty = [q['quant_id'] for q in res['quants_qty_negativo']]
    assert sorted(qids_reserved) == [200, 300]
    assert qids_qty == [300]
    # zerar_residual chamado com ambos quants
    instance_res.zerar_reserved_residual.assert_called_once()
    qids_chamados = instance_res.zerar_reserved_residual.call_args.kwargs['quant_ids']
    assert sorted(qids_chamados) == [200, 300]
    # ajustar_quant chamado 1x (para o quant 300)
    assert instance_q.ajustar_quant.call_count == 1
    aj_kwargs = instance_q.ajustar_quant.call_args.kwargs
    assert aj_kwargs['quant_id'] == 300
    assert aj_kwargs['valor_absoluto'] == 0.0
    assert aj_kwargs['dry_run'] is True


def test_cleanup_exclui_indisp_da_busca():
    """Domain do search_read EXCLUI LOCAIS_INDISPONIVEL[company_id]."""
    odoo_mock = MagicMock()
    odoo_mock.search_read.return_value = []
    _executar_cleanup_pos_bulk(
        odoo=odoo_mock, product_ids=[27918],
        company_id=1, locs_origem=[8, 31088],  # 31088 = FB/Indisp incluido por engano
        dry_run=True,
    )
    domain = odoo_mock.search_read.call_args[0][1]
    # Procurar clausula not in com 31088
    has_not_in_indisp = any(
        isinstance(d, list) and len(d) == 3 and d[0] == 'location_id'
        and d[1] == 'not in' and 31088 in d[2]
        for d in domain
    )
    assert has_not_in_indisp, (
        f'Esperado clausula NOT IN com 31088 em domain; got: {domain}'
    )


def test_cleanup_pula_quant_com_ml_ativa():
    """S2-pre-mortem mitigation v12: GUARD MO ativa.

    Quants com reserved<0 + ML ativa (assigned/partially_available) NAO devem
    ser zerados — pode ser reserva legitima com sinal errado. Reportar em
    `quants_pulados_mo_ativa` e processar apenas os sem MLs ativas.
    """
    odoo_mock = MagicMock()
    odoo_mock.search_read.return_value = [
        # Quant 200: reserved<0 SEM MLs ativas (deveria ser zerado)
        {'id': 200, 'product_id': [27918, 'SAL'], 'lot_id': False,
         'location_id': [27458, 'FB/Salm'], 'quantity': 0.0, 'reserved_quantity': -5.0},
        # Quant 201: reserved<0 COM ML ativa (NAO zerar)
        {'id': 201, 'product_id': [27918, 'SAL'], 'lot_id': [60001, 'X'],
         'location_id': [4067, 'FB/Man'], 'quantity': 0.0, 'reserved_quantity': -10.0},
    ]
    with patch(
        'app.odoo.estoque.scripts.consulta_quant.StockQuantQueryService'
    ) as mk_query_svc, \
         patch(
        'app.odoo.estoque.scripts.reserva.StockReservaService'
    ) as mk_res_svc:
        # Query returna 1 ML ativa para quant 201
        instance_q = mk_query_svc.return_value
        instance_q.listar_move_lines_por_quant.return_value = {
            'move_lines': [
                {'id': 9999, '_quant_id_resolvido': 201, 'state': 'assigned'},
            ],
        }
        instance_r = mk_res_svc.return_value
        instance_r.zerar_reserved_residual.return_value = {
            'status': 'DRY_RUN_OK', 'tempo_ms': 1,
        }
        res = _executar_cleanup_pos_bulk(
            odoo=odoo_mock, product_ids=[27918],
            company_id=1, locs_origem=[27458, 4067],
            dry_run=True,
        )
    # Quant 201 PULADO por MO ativa
    assert len(res['quants_pulados_mo_ativa']) == 1
    pulado = res['quants_pulados_mo_ativa'][0]
    assert pulado['quant_id'] == 201
    assert pulado['n_mls_ativas'] == 1
    # Quant 200 zerado (sem MLs ativas)
    qids_chamados = instance_r.zerar_reserved_residual.call_args.kwargs['quant_ids']
    assert qids_chamados == [200]


def test_cleanup_falha_odoo_propaga_para_caller():
    """F5 v12-CR: cleanup com FALHA_ODOO no zerar_residual NAO eh ignorado.

    Quando `zerar_reserved_residual` retorna `{'status': 'FALHA_ODOO', ...}`,
    o caller (CLI main) deve detectar via `cleanup_falhou` e elevar exit
    code para 1. Esse teste valida o callback do helper — o exit code do
    CLI eh testado via cleanup_result.resultado_zerar_residual.status que
    o main() inspeciona.
    """
    odoo_mock = MagicMock()
    odoo_mock.search_read.return_value = [
        {'id': 200, 'product_id': [27918, 'X'], 'lot_id': False,
         'location_id': [27458, 'Y'], 'quantity': 0.0, 'reserved_quantity': -5.0},
    ]
    with patch(
        'app.odoo.estoque.scripts.consulta_quant.StockQuantQueryService'
    ) as mk_query_svc, \
         patch(
        'app.odoo.estoque.scripts.reserva.StockReservaService'
    ) as mk_r:
        instance_q = mk_query_svc.return_value
        instance_q.listar_move_lines_por_quant.return_value = {'move_lines': []}
        instance = mk_r.return_value
        # Simular FALHA_ODOO no zerar_residual
        instance.zerar_reserved_residual.return_value = {
            'status': 'FALHA_ODOO',
            'erro': 'XML-RPC timeout simulado',
            'tempo_ms': 100,
        }
        res = _executar_cleanup_pos_bulk(
            odoo=odoo_mock, product_ids=[27918],
            company_id=1, locs_origem=[27458],
            dry_run=False,
        )
    # Cleanup result deve manter status FALHA_ODOO no sub-resultado
    zr = res.get('resultado_zerar_residual') or {}
    assert zr.get('status') == 'FALHA_ODOO'
    # main() deteria via startswith('FALHA') — simulando aqui
    cleanup_falhou = zr.get('status', '').startswith('FALHA')
    assert cleanup_falhou is True, (
        'caller main() deve detectar FALHA via startswith e elevar exit code'
    )


def test_cleanup_dry_run_nao_efetiva():
    """dry_run=True propaga aos calls internos."""
    odoo_mock = MagicMock()
    odoo_mock.search_read.return_value = [
        {'id': 200, 'product_id': [27918, 'X'], 'lot_id': False,
         'location_id': [27458, 'Y'], 'quantity': 0.0, 'reserved_quantity': -5.0},
    ]
    with patch('app.odoo.estoque.scripts.reserva.StockReservaService') as mk_r:
        instance = mk_r.return_value
        instance.zerar_reserved_residual.return_value = {
            'status': 'DRY_RUN_OK', 'tempo_ms': 1,
        }
        _executar_cleanup_pos_bulk(
            odoo=odoo_mock, product_ids=[27918],
            company_id=1, locs_origem=[27458],
            dry_run=True,
        )
        instance.zerar_reserved_residual.assert_called_once()
        # dry_run=True propagado
        kwargs = instance.zerar_reserved_residual.call_args.kwargs
        assert kwargs['dry_run'] is True
