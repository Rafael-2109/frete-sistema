"""Testes do snapshot freeze MOV/SIST (2026-05-27).

Garante:
1. Snapshot novo grava colunas mov_* alem dos campos Odoo
2. ConfrontoService.montar_linhas usa MOV do snapshot quando disponivel
3. Fallback live quando snapshot pre-freeze (mov_* todos zerados)
4. AJ permanece LIVE (edicao pos-snapshot reflete na hora)
5. mov_sist_total = sum total (sem filtro data); mov_compras = filtrado >= data_snapshot
"""
from decimal import Decimal
from datetime import date, datetime
import pytest
from app.inventario.models import (
    CicloInventario, InventarioSnapshotOdoo, AjusteManualInventario,
)
from app.inventario.services.confronto_service import ConfrontoService
from app.inventario.services.snapshot_odoo_service import SnapshotOdooService
from app.estoque.models import MovimentacaoEstoque


@pytest.fixture
def ciclo_fresh(db):
    """CicloInventario com data_snapshot=2026-05-16."""
    c = CicloInventario(
        codigo='TEST-FREEZE-CICLO', data_snapshot=date(2026, 5, 16),
        descricao='Test freeze', status='ATIVO', criado_por='pytest',
    )
    db.session.add(c)
    db.session.flush()
    return c


def _add_mov(db, cod, tipo, qtd, data, nome='Produto teste'):
    db.session.add(MovimentacaoEstoque(
        cod_produto=cod, nome_produto=nome, tipo_movimentacao=tipo,
        qtd_movimentacao=Decimal(str(qtd)), data_movimentacao=data,
        local_movimentacao='TESTE', ativo=True,
    ))


def test_baixar_movimentacoes_local_agrega_corretamente(db, ciclo_fresh):
    """_baixar_movimentacoes_local agrega ENTRADA/FATURAMENTO/CONSUMO/PRODUÇÃO
    a partir de data_snapshot, e sist_total acumula tudo sem filtro data.

    Usa cod_produto unico (TESTFRZ-xxx) para isolar de movs reais ja no banco.
    """
    import uuid
    cod = f'TESTFRZ-{uuid.uuid4().hex[:8]}'
    # 3 movs ANTES do snapshot (so contam pra sist_total)
    _add_mov(db, cod, 'ENTRADA', 50, date(2026, 5, 10))
    _add_mov(db, cod, 'FATURAMENTO', 20, date(2026, 5, 12))
    _add_mov(db, cod, 'PRODUÇÃO', 100, date(2026, 5, 14))
    # 4 movs A PARTIR do snapshot (contam pra mov_* periodo E sist_total)
    _add_mov(db, cod, 'ENTRADA', 30, date(2026, 5, 17))
    _add_mov(db, cod, 'FATURAMENTO', 10, date(2026, 5, 18))
    _add_mov(db, cod, 'CONSUMO', 5, date(2026, 5, 19))
    _add_mov(db, cod, 'PRODUÇÃO', 40, date(2026, 5, 20))
    db.session.flush()

    movs = SnapshotOdooService._baixar_movimentacoes_local(ciclo_fresh.data_snapshot)
    assert cod in movs
    m = movs[cod]
    # mov_* periodo (>=2026-05-16): 1 entrada(30) + 1 fatur(10) + 1 cons(5) + 1 prod(40)
    assert m['compras'] == Decimal('30')
    assert m['vendas'] == Decimal('10')
    assert m['consumo'] == Decimal('5')
    assert m['producao'] == Decimal('40')
    # sist_total = sum total ATIVO = 50 + 20 + 100 + 30 + 10 + 5 + 40 = 255
    assert m['sist_total'] == Decimal('255')


def test_confronto_usa_snapshot_quando_freezado(db, ciclo_fresh):
    """Quando snapshot tem mov_* != 0, montar_linhas le MOV do snapshot
    (nao toca em MovimentacaoEstoque live)."""
    # Snapshot freezado com valores FIXOS no momento T0
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo_fresh.id, cod_produto='4320147',
        nome_produto='Produto teste',
        estoque_fb=Decimal('100'), estoque_cd=0, estoque_lf=0,
        mov_compras=Decimal('30'), mov_vendas=Decimal('10'),
        mov_consumo=Decimal('5'), mov_producao=Decimal('40'),
        mov_sist_total=Decimal('255'), refresh_em=datetime(2026, 5, 27, 10, 0),
    ))
    # AGORA insere movs LIVE depois do snapshot — NAO devem aparecer
    _add_mov(db, '4320147', 'ENTRADA', 999, date(2026, 5, 27))
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo_fresh.id)
    cod = next(l for l in linhas if l['cod_produto'] == '4320147')
    assert cod['compras'] == Decimal('30'), 'snapshot value, NAO o 999 live'
    assert cod['vendas'] == Decimal('10')
    assert cod['consumo'] == Decimal('5')
    assert cod['producao'] == Decimal('40')
    assert cod['sist'] == Decimal('255')


def test_confronto_fallback_live_quando_snapshot_pre_freeze(db, ciclo_fresh):
    """Snapshot antigo (mov_* todos 0 = pre-freeze) → cai no agregado LIVE."""
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo_fresh.id, cod_produto='4320147',
        estoque_fb=Decimal('100'),  # Odoo populado
        # mov_* todos 0 (default — snapshot pre-freeze)
    ))
    # Movs LIVE devem aparecer
    _add_mov(db, '4320147', 'ENTRADA', 77, date(2026, 5, 20))
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo_fresh.id)
    cod = next(l for l in linhas if l['cod_produto'] == '4320147')
    assert cod['compras'] == Decimal('77'), 'fallback LIVE deveria ler MovimentacaoEstoque'


def test_aj_permanece_live_apos_snapshot(db, ciclo_fresh):
    """AjusteManualInventario NAO eh snapshotado — edicao pos-snapshot reflete na hora."""
    # Snapshot freezado SEM ajuste
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo_fresh.id, cod_produto='4320147',
        estoque_fb=Decimal('100'), mov_compras=Decimal('30'),
        mov_sist_total=Decimal('130'),
    ))
    db.session.flush()

    linhas1 = ConfrontoService.montar_linhas(ciclo_fresh.id)
    cod1 = next(l for l in linhas1 if l['cod_produto'] == '4320147')
    assert cod1.get('ajuste_qtd') is None, 'sem ajuste ainda'

    # Insere ajuste APOS snapshot
    db.session.add(AjusteManualInventario(
        ciclo_id=ciclo_fresh.id, cod_produto='4320147',
        local='Estoque', qtd=Decimal('55'), criado_por='pytest',
    ))
    db.session.flush()

    linhas2 = ConfrontoService.montar_linhas(ciclo_fresh.id)
    cod2 = next(l for l in linhas2 if l['cod_produto'] == '4320147')
    assert cod2['ajuste_qtd'] == Decimal('55'), 'AJ deve estar LIVE, refletindo edicao pos-snapshot'
    assert cod2['ajuste_local'] == 'Estoque'


def test_snapshot_tem_mov_freezado_detecta_corretamente(db, ciclo_fresh):
    """Helper que decide snapshot vs live."""
    snap_vazio = {}
    assert ConfrontoService._snapshot_tem_mov_freezado(snap_vazio) is False

    snap_pre_freeze = {'4320147': {
        'mov_compras': Decimal('0'), 'mov_vendas': Decimal('0'),
        'mov_consumo': Decimal('0'), 'mov_producao': Decimal('0'),
        'mov_sist_total': Decimal('0'),
    }}
    assert ConfrontoService._snapshot_tem_mov_freezado(snap_pre_freeze) is False

    snap_freezado = {'4320147': {
        'mov_compras': Decimal('30'), 'mov_vendas': Decimal('0'),
        'mov_consumo': Decimal('0'), 'mov_producao': Decimal('0'),
        'mov_sist_total': Decimal('0'),
    }}
    assert ConfrontoService._snapshot_tem_mov_freezado(snap_freezado) is True

    # Sist != 0 tambem conta (caso de cod com saldo mas sem mov no periodo)
    snap_so_sist = {'4320147': {
        'mov_compras': Decimal('0'), 'mov_vendas': Decimal('0'),
        'mov_consumo': Decimal('0'), 'mov_producao': Decimal('0'),
        'mov_sist_total': Decimal('100'),
    }}
    assert ConfrontoService._snapshot_tem_mov_freezado(snap_so_sist) is True
