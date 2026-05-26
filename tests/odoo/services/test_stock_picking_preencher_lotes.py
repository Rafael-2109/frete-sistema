"""Tests para StockPickingService.preencher_lotes_picking (atomo v19+ S2).

Cobertura:
  - dry_run reporta plano (writes + creates) sem escrever
  - real_run com 1 lote por produto: atualiza ML existente
  - real_run com 2 lotes para mesmo produto: atualiza 1a + cria 2a
  - lote_default cobre produtos sem mapping explicito
  - sem lote_default + produtos sem cobertura -> FALHA com mls_pendentes
  - picking sem MLs -> FALHA
  - pre-cond invalido nao raise (AP4)
"""
from unittest.mock import MagicMock

from app.odoo.estoque.scripts.picking import StockPickingService


def _ml(ml_id, pid, qty=10.0, move_id=1001):
    """Mock dict de stock.move.line."""
    return {
        'id': ml_id,
        'product_id': [pid, f'Produto {pid}'],
        'move_id': [move_id, f'Move {move_id}'],
        'qty_done': 0.0,
        'quantity': qty,
        'product_uom_id': [1, 'unit'],
        'location_id': [100, 'Origem'],
        'location_dest_id': [200, 'Destino'],
        'lot_id': False,
        'lot_name': False,
    }


def test_preencher_lotes_dry_run_planeja():
    """dry_run=True NAO escreve; reporta plano com counts."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=1, pid=12345, qty=10.0),
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=777,
        lotes_data=[{
            'product_id': 12345,
            'lote_nome': 'LOTE-A',
            'quantidade': 10.0,
        }],
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['mls_atualizadas'] == 1
    assert res['mls_criadas'] == 0
    assert res['plano']['writes_count'] == 1
    # NAO chamou write/create
    assert not odoo.write.called
    assert not odoo.create.called


def test_preencher_lotes_real_1lote_por_produto():
    """real-run: 1 lote por produto -> atualiza 1 ML existente."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=10, pid=999, qty=5.0),
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=888,
        lotes_data=[{
            'product_id': 999,
            'lote_nome': 'MIGRAÇÃO',
            'quantidade': 5.0,
        }],
        dry_run=False,
    )
    assert res['status'] == 'PREENCHIDO'
    assert res['mls_atualizadas'] == 1
    assert res['mls_criadas'] == 0
    # write chamado com lot_name + qtys
    odoo.write.assert_called_once_with(
        'stock.move.line', [10],
        {'qty_done': 5.0, 'quantity': 5.0, 'lot_name': 'MIGRAÇÃO'},
    )
    assert not odoo.create.called


def test_preencher_lotes_real_2lotes_mesmo_produto():
    """2 entradas para mesmo product_id: atualiza ML[0] + cria ML novo."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=20, pid=888, qty=10.0),
    ]
    odoo.create.return_value = 21  # id da ML nova
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=999,
        lotes_data=[
            {'product_id': 888, 'lote_nome': 'LOTE-A', 'quantidade': 6.0},
            {'product_id': 888, 'lote_nome': 'LOTE-B', 'quantidade': 4.0},
        ],
        dry_run=False,
    )
    assert res['status'] == 'PREENCHIDO'
    assert res['mls_atualizadas'] == 1
    assert res['mls_criadas'] == 1
    # 1 write (LOTE-A) + 1 create (LOTE-B)
    odoo.write.assert_called_once()
    odoo.create.assert_called_once()
    create_args = odoo.create.call_args[0]
    assert create_args[0] == 'stock.move.line'
    assert create_args[1]['lot_name'] == 'LOTE-B'
    assert create_args[1]['qty_done'] == 4.0


def test_preencher_lotes_default_para_produtos_sem_mapping():
    """lote_default cobre produtos do picking sem entry em lotes_data."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=30, pid=111, qty=7.0),
        _ml(ml_id=31, pid=222, qty=3.0),  # nao tem mapping
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=1000,
        lotes_data=[
            {'product_id': 111, 'lote_nome': 'EXPLICITO',
             'quantidade': 7.0},
        ],
        lote_default='MIGRAÇÃO',
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    # 2 writes: 111 com EXPLICITO + 222 com MIGRAÇÃO (default)
    assert res['mls_atualizadas'] == 2
    # Plano contem ambos
    samples_writes = res['plano']['writes_sample']
    lotes_aplicados = {s[1].get('lot_name') for s in samples_writes}
    assert lotes_aplicados == {'EXPLICITO', 'MIGRAÇÃO'}


def test_preencher_lotes_sem_default_produtos_sem_cobertura_falha():
    """Sem lote_default e produtos sem mapping -> FALHA + mls_pendentes."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=40, pid=444, qty=5.0),
        _ml(ml_id=41, pid=555, qty=2.0),  # sem mapping
    ]
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=1100,
        lotes_data=[
            {'product_id': 444, 'lote_nome': 'X', 'quantidade': 5.0},
        ],
        dry_run=False,  # mesmo em real-run, ABORTA antes de escrever
    )
    assert res['status'] == 'FALHA'
    assert 555 in res['mls_pendentes']
    assert 'produtos_sem_cobertura' in (res['erro'] or '')
    # NAO escreveu nada
    assert not odoo.write.called
    assert not odoo.create.called


def test_preencher_lotes_picking_sem_mls_falha():
    """picking sem stock.move.line -> FALHA."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=1200,
        lotes_data=[{
            'product_id': 1,
            'lote_nome': 'L', 'quantidade': 1.0,
        }],
        dry_run=False,
    )
    assert res['status'] == 'FALHA'
    assert res['erro'] == 'picking_sem_move_lines'


def test_preencher_lotes_pre_cond_picking_id_invalido_nao_raise():
    """AP4: picking_id invalido NAO raise — retorna {erro}."""
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    res = svc.preencher_lotes_picking(
        picking_id=0,
        lotes_data=[],
        dry_run=True,
    )
    assert res['status'] == 'FALHA'
    assert res['erro'] == 'picking_id_invalido'
    assert not odoo.search_read.called
