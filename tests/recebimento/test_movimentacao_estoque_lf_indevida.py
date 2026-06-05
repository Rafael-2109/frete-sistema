"""
Testes da PREVENCAO de MovimentacaoEstoque indevidas no fluxo Recebimento LF.

Contexto (2026-06-05):
    O Recebimento LF (industrializacao LF -> entrada FB -> transferencia FB->CD)
    estava gerando MovimentacaoEstoque automaticas que DUPLICAVAM / OSCILAVAM o
    estoque, porque o controle do produto acabado da LF e feito APENAS pelo
    lancamento manual de PRODUCAO (tipo_movimentacao='PRODUCAO', tipo_origem='MANUAL').

    Lancamentos indevidos (devem deixar de ser criados):
      (2) ENTRADA / local='COMPRA'        -> entrada LF->FB  (_criar_movimentacoes_estoque)
      (3) SAIDA+ENTRADA / local='TRANSFERENCIA' -> FB->CD     (_criar_movimentacoes_transferencia)

    A etapa 18 deve PRESERVAR apenas a garantia de CadastroPalletizacao (ACABADO_LF)
    do produto acabado — sem criar MovimentacaoEstoque.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import app.recebimento.services.recebimento_lf_odoo_service as mod
from app.estoque.models import MovimentacaoEstoque
from app.producao.models import CadastroPalletizacao
from app.recebimento.models import RecebimentoLf, RecebimentoLfLote


PRODUCT_ID = 990127
MOVE_LINE_ID = 880127
MOVE_ID = 550127


def _fake_commit(session):
    """Substitui commit_with_retry por flush — isola o savepoint do conftest."""
    session.flush()
    return True


def _odoo_mock():
    """Mock de conexao Odoo respondendo product.product e stock.move.line."""
    odoo = MagicMock()

    def execute_kw(model, method, args, kwargs=None):
        if model == 'product.product':
            ids = args[0]
            return [{'id': pid, 'default_code': str(pid)} for pid in ids]
        if model == 'stock.move.line':
            ids = args[0]
            return [{'id': mlid, 'move_id': [MOVE_ID, 'WH/MOVE']} for mlid in ids]
        return []

    odoo.execute_kw.side_effect = execute_kw
    return odoo


def _criar_rec(db, **rec_kwargs):
    rec = RecebimentoLf(
        numero_nf='TESTNFLF',
        odoo_picking_id=770127,
        odoo_picking_name='FB/IN/TESTLF',
        odoo_po_name='CTESTLF',
        company_id=1,
        status='processado',
        etapa_atual=0,
        total_etapas=37,
        usuario='pytest',
        **rec_kwargs,
    )
    db.session.add(rec)
    db.session.flush()
    return rec


def _add_lote_acabado(db, rec, product_id=PRODUCT_ID, move_line_id=MOVE_LINE_ID):
    lote = RecebimentoLfLote(
        recebimento_lf_id=rec.id,
        odoo_product_id=product_id,
        odoo_product_name='PRODUTO ACABADO LF TESTE',
        cfop='1949',  # NAO e retorno (1902/5902/1903/5903)
        tipo='manual',  # produto acabado
        lote_nome='154/26',
        quantidade=Decimal('126'),
        data_validade=None,
        processado=True,
        odoo_move_line_id=move_line_id,
    )
    db.session.add(lote)
    db.session.flush()
    return lote


# =====================================================================
# (2) ENTRADA / COMPRA — entrada LF->FB
# =====================================================================

def test_etapa18_nao_cria_movimentacao_compra(db, monkeypatch):
    """A etapa 18 NAO deve criar MovimentacaoEstoque local='COMPRA' (duplicaria a producao)."""
    monkeypatch.setattr(mod, 'commit_with_retry', _fake_commit)
    rec = _criar_rec(db)
    _add_lote_acabado(db, rec)

    service = mod.RecebimentoLfOdooService()
    service._recebimento_id = rec.id

    service._criar_movimentacoes_estoque(_odoo_mock())

    qtd_compra = MovimentacaoEstoque.query.filter_by(
        cod_produto=str(PRODUCT_ID), local_movimentacao='COMPRA'
    ).count()
    assert qtd_compra == 0, (
        "Recebimento LF NAO deve criar MovimentacaoEstoque COMPRA — "
        "o controle do produto acabado e o lancamento manual de PRODUCAO"
    )


def test_etapa18_preserva_garantia_de_cadastro(db, monkeypatch):
    """A etapa 18 deve PRESERVAR a garantia de CadastroPalletizacao ACABADO_LF."""
    monkeypatch.setattr(mod, 'commit_with_retry', _fake_commit)
    rec = _criar_rec(db)
    _add_lote_acabado(db, rec)

    assert CadastroPalletizacao.query.filter_by(cod_produto=str(PRODUCT_ID)).first() is None

    service = mod.RecebimentoLfOdooService()
    service._recebimento_id = rec.id
    service._criar_movimentacoes_estoque(_odoo_mock())

    cad = CadastroPalletizacao.query.filter_by(cod_produto=str(PRODUCT_ID)).first()
    assert cad is not None, "Etapa 18 deve garantir CadastroPalletizacao do produto acabado LF"


# =====================================================================
# (3) SAIDA + ENTRADA / TRANSFERENCIA — FB->CD
# =====================================================================

def test_etapa37_nao_cria_movimentacao_transferencia(db, monkeypatch):
    """Finalizar o recebimento CD (etapa 37) NAO deve criar MovimentacaoEstoque TRANSFERENCIA."""
    monkeypatch.setattr(mod, 'commit_with_retry', _fake_commit)
    # mock da conexao Odoo usada por _criar_movimentacoes_transferencia (import local)
    monkeypatch.setattr(
        'app.odoo.utils.connection.get_odoo_connection', lambda: _odoo_mock()
    )

    rec = _criar_rec(
        db,
        odoo_transfer_out_picking_id=773510,
        odoo_transfer_out_picking_name='FB/SAI/INT/TEST',
        odoo_transfer_in_picking_id=773540,
        odoo_transfer_in_picking_name='CD/IN/TEST',
    )
    _add_lote_acabado(db, rec)

    service = mod.RecebimentoLfOdooService()
    service._recebimento_id = rec.id
    # isolar infra: redis + checkpoint (commit no banco real)
    monkeypatch.setattr(service, '_atualizar_redis', lambda *a, **k: None)
    monkeypatch.setattr(service, '_checkpoint', lambda *a, **k: rec)

    service._step_37_finalizar_recebimento_cd(_odoo_mock())

    qtd_transfer = MovimentacaoEstoque.query.filter_by(
        local_movimentacao='TRANSFERENCIA'
    ).filter(MovimentacaoEstoque.cod_produto == str(PRODUCT_ID)).count()
    assert qtd_transfer == 0, (
        "Finalizar recebimento CD NAO deve criar MovimentacaoEstoque TRANSFERENCIA "
        "(FB->CD e transferencia entre filiais, nao movimenta o saldo do produto)"
    )
