"""Tests para StockPickingService.preencher_lotes_picking (atomo v19+ S2).

Cobertura:
  - dry_run reporta plano (writes + creates) sem escrever
  - real_run com 1 lote por produto: atualiza ML existente
  - real_run com 2 lotes para mesmo produto: atualiza 1a + cria 2a
  - lote_default cobre produtos sem mapping explicito
  - sem lote_default + produtos sem cobertura -> FALHA com mls_pendentes
  - picking sem MLs -> FALHA
  - pre-cond invalido nao raise (AP4)
  - C3/G-ENT-6: resolve/cria stock.lot na company DESTINO + lot_id explicito
"""
from unittest.mock import MagicMock, patch

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


# ============================================================================
# C3 / G-ENT-6 — lote resolvido/criado na company DESTINO + lot_id explicito
# ============================================================================

_LOT_SVC_PATH = (
    'app.odoo.estoque.scripts.picking.StockLotService'
)


def test_preencher_lotes_company_destino_resolve_lot_na_company():
    """C3/G-ENT-6: com company_destino, busca stock.lot na company destino
    e passa lot_id explicito no write (nao so lot_name)."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=10, pid=999, qty=5.0),
    ]
    lot_svc = MagicMock()
    # lote ja existe na company destino (id=4242)
    lot_svc.criar_se_nao_existe.return_value = (4242, False)
    # guard pos-condicao: read do lote confirma company destino
    odoo.read.return_value = [{'id': 4242, 'company_id': [5, 'LF']}]
    with patch(_LOT_SVC_PATH, return_value=lot_svc):
        svc = StockPickingService(odoo=odoo)
        res = svc.preencher_lotes_picking(
            picking_id=888,
            lotes_data=[{
                'product_id': 999,
                'lote_nome': 'MIGRAÇÃO',
                'quantidade': 5.0,
            }],
            company_destino=5,
            dry_run=False,
        )
    assert res['status'] == 'PREENCHIDO'
    # resolveu o lote na company destino (nome + product_id + company_id)
    lot_svc.criar_se_nao_existe.assert_called_once()
    _args, kwargs = lot_svc.criar_se_nao_existe.call_args
    # company_destino propagado para a resolucao/criacao do lote
    passed = {**dict(zip(['nome', 'product_id', 'company_id'], _args)), **kwargs}
    assert passed.get('company_id', _args[2] if len(_args) > 2 else None) == 5
    assert passed.get('product_id', _args[1] if len(_args) > 1 else None) == 999
    # write da move.line recebeu lot_id explicito (nao so lot_name)
    write_call = odoo.write.call_args
    assert write_call[0][0] == 'stock.move.line'
    wdata = write_call[0][2]
    assert wdata['lot_id'] == 4242


def test_preencher_lotes_company_destino_cria_lote_inexistente():
    """C3: lote ainda nao existe na company destino -> cria com company destino."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=20, pid=777, qty=8.0),
    ]
    lot_svc = MagicMock()
    lot_svc.criar_se_nao_existe.return_value = (5151, True)  # criado agora
    odoo.read.return_value = [{'id': 5151, 'company_id': [5, 'LF']}]
    with patch(_LOT_SVC_PATH, return_value=lot_svc):
        svc = StockPickingService(odoo=odoo)
        res = svc.preencher_lotes_picking(
            picking_id=900,
            lotes_data=[{
                'product_id': 777,
                'lote_nome': 'LOTE-LF-NOVO',
                'quantidade': 8.0,
            }],
            company_destino=5,
            dry_run=False,
        )
    assert res['status'] == 'PREENCHIDO'
    _args, kwargs = lot_svc.criar_se_nao_existe.call_args
    passed = {**dict(zip(['nome', 'product_id', 'company_id'], _args)), **kwargs}
    assert passed.get('nome', _args[0] if _args else None) == 'LOTE-LF-NOVO'
    assert passed.get('company_id', _args[2] if len(_args) > 2 else None) == 5
    assert odoo.write.call_args[0][2]['lot_id'] == 5151


def test_preencher_lotes_company_destino_derivada_do_picking():
    """C3: company_destino=None -> deriva de picking.company_id (read)."""
    odoo = MagicMock()
    # 1o read = stock.picking company; depois search_read das MLs
    odoo.read.side_effect = [
        [{'id': 900, 'company_id': [5, 'LF']}],   # read picking
        [{'id': 6262, 'company_id': [5, 'LF']}],  # read guard pos-cond do lote
    ]
    odoo.search_read.return_value = [
        _ml(ml_id=30, pid=555, qty=3.0),
    ]
    lot_svc = MagicMock()
    lot_svc.criar_se_nao_existe.return_value = (6262, False)
    with patch(_LOT_SVC_PATH, return_value=lot_svc):
        svc = StockPickingService(odoo=odoo)
        res = svc.preencher_lotes_picking(
            picking_id=900,
            lotes_data=[{
                'product_id': 555,
                'lote_nome': 'L-DERIV',
                'quantidade': 3.0,
            }],
            company_destino=None,  # derivar do picking
            dry_run=False,
        )
    assert res['status'] == 'PREENCHIDO'
    _args, kwargs = lot_svc.criar_se_nao_existe.call_args
    passed = {**dict(zip(['nome', 'product_id', 'company_id'], _args)), **kwargs}
    assert passed.get('company_id', _args[2] if len(_args) > 2 else None) == 5


def test_preencher_lotes_guard_lote_company_divergente_aborta():
    """C3/G-ENT-6 GUARD: se lote resolvido pertence a outra company -> FALHA
    sem escrever (codifica 'Empresas incompatíveis')."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=40, pid=333, qty=2.0),
    ]
    lot_svc = MagicMock()
    lot_svc.criar_se_nao_existe.return_value = (9090, False)
    # guard pos-cond: lote pertence a company 1 (FB), mas destino e 5 (LF)
    odoo.read.return_value = [{'id': 9090, 'company_id': [1, 'FB']}]
    with patch(_LOT_SVC_PATH, return_value=lot_svc):
        svc = StockPickingService(odoo=odoo)
        res = svc.preencher_lotes_picking(
            picking_id=1000,
            lotes_data=[{
                'product_id': 333,
                'lote_nome': 'L-ERRADO',
                'quantidade': 2.0,
            }],
            company_destino=5,
            dry_run=False,
        )
    assert res['status'] == 'FALHA'
    assert res['erro'] == 'FALHA_LOTE_COMPANY_DIVERGENTE'
    # NAO escreveu/criou move.line
    assert not odoo.write.called
    assert not odoo.create.called


def test_preencher_lotes_company_destino_lot_id_em_creates():
    """C3: 2 lotes mesmo produto com company_destino -> ambos com lot_id."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        _ml(ml_id=50, pid=222, qty=10.0),
    ]
    odoo.create.return_value = 51
    lot_svc = MagicMock()
    # resolve lotes distintos por nome
    lot_svc.criar_se_nao_existe.side_effect = [
        (700, False),  # LOTE-A
        (701, True),   # LOTE-B
    ]
    # guard read confirma company destino para ambos
    odoo.read.side_effect = [
        [{'id': 700, 'company_id': [5, 'LF']}],
        [{'id': 701, 'company_id': [5, 'LF']}],
    ]
    with patch(_LOT_SVC_PATH, return_value=lot_svc):
        svc = StockPickingService(odoo=odoo)
        res = svc.preencher_lotes_picking(
            picking_id=1100,
            lotes_data=[
                {'product_id': 222, 'lote_nome': 'LOTE-A', 'quantidade': 6.0},
                {'product_id': 222, 'lote_nome': 'LOTE-B', 'quantidade': 4.0},
            ],
            company_destino=5,
            dry_run=False,
        )
    assert res['status'] == 'PREENCHIDO'
    assert res['mls_atualizadas'] == 1
    assert res['mls_criadas'] == 1
    # write (LOTE-A) com lot_id=700
    assert odoo.write.call_args[0][2]['lot_id'] == 700
    # create (LOTE-B) com lot_id=701
    create_data = odoo.create.call_args[0][1]
    assert create_data['lot_id'] == 701
