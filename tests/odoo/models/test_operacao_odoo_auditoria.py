"""Testa model OperacaoOdooAuditoria (polimorfico)."""
import pytest
from decimal import Decimal
from app import create_app, db
from app.odoo.models import OperacaoOdooAuditoria


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_registrar_basico(app_ctx):
    rec = OperacaoOdooAuditoria.registrar(
        external_id='TEST-AUDIT-001',
        tabela_origem='account_move',
        registro_id=42,
        acao='create',
        modelo_odoo='account.move',
        status='SUCESSO',
        executado_por='pytest',
    )
    assert rec.id is not None
    assert rec.external_id == 'TEST-AUDIT-001'
    assert rec.executado_em is not None
    db.session.rollback()


def test_registrar_sanitiza_json_com_decimal(app_ctx):
    """sanitize_for_json deve permitir Decimal em payload_json (regra global)."""
    rec = OperacaoOdooAuditoria.registrar(
        external_id='TEST-AUDIT-002',
        tabela_origem='account_move',
        registro_id=43,
        acao='create',
        modelo_odoo='account.move',
        status='SUCESSO',
        executado_por='pytest',
        payload_json={'valor': Decimal('100.50'), 'qty': 5},
    )
    db.session.flush()  # nao explode com Decimal
    assert rec.payload_json is not None
    db.session.rollback()


def test_external_id_unico(app_ctx):
    """Constraint UNIQUE em external_id garante idempotencia."""
    OperacaoOdooAuditoria.registrar(
        external_id='TEST-UNIQUE-001',
        tabela_origem='account_move',
        registro_id=1,
        acao='create',
        modelo_odoo='account.move',
        status='SUCESSO',
        executado_por='pytest',
    )
    db.session.flush()
    with pytest.raises(Exception):  # IntegrityError em flush
        OperacaoOdooAuditoria.registrar(
            external_id='TEST-UNIQUE-001',  # mesmo external_id
            tabela_origem='account_move',
            registro_id=2,
            acao='create',
            modelo_odoo='account.move',
            status='SUCESSO',
            executado_por='pytest',
        )
        db.session.flush()
    db.session.rollback()


def test_polimorfismo_3_tabelas_origem(app_ctx):
    """Mesma tabela auditoria registra operacoes em models distintos."""
    OperacaoOdooAuditoria.registrar(
        external_id='POLY-001-MOVE',
        tabela_origem='account_move', registro_id=1,
        acao='create', modelo_odoo='account.move',
        status='SUCESSO', executado_por='pytest',
    )
    OperacaoOdooAuditoria.registrar(
        external_id='POLY-001-PICKING',
        tabela_origem='stock_picking', registro_id=2,
        acao='validate', modelo_odoo='stock.picking',
        status='SUCESSO', executado_por='pytest',
    )
    OperacaoOdooAuditoria.registrar(
        external_id='POLY-001-LOT',
        tabela_origem='stock_lot', registro_id=3,
        acao='create', modelo_odoo='stock.lot',
        status='SUCESSO', executado_por='pytest',
    )
    db.session.flush()
    encontrados = (
        OperacaoOdooAuditoria.query
        .filter(OperacaoOdooAuditoria.external_id.like('POLY-001-%'))
        .all()
    )
    assert len(encontrados) == 3
    db.session.rollback()


def test_registrar_falha_nao_poisona_sessao_do_caller(app_ctx):
    """BUG-1 (avaliacao 360): savepoint isola a falha do flush da transacao
    do caller. Apos uma gravacao de auditoria falhar (ex: external_id dup),
    a MESMA sessao deve continuar utilizavel SEM rollback manual.

    Antes do fix: o flush abortado poisonava a transacao externa e a proxima
    operacao na mesma sessao estourava PendingRollbackError em cascata
    (Sentry PYTHON-FLASK-WX/WT/WS/WR/WQ). Agora begin_nested reverte apenas
    o savepoint — a transacao externa permanece sa.
    """
    # 1a gravacao OK (persiste na transacao via savepoint released)
    OperacaoOdooAuditoria.registrar(
        external_id='TEST-SAVEPOINT-001',
        tabela_origem='account_move', registro_id=1,
        acao='create', modelo_odoo='account.move',
        status='SUCESSO', executado_por='pytest',
    )
    # 2a gravacao com external_id DUPLICADO -> IntegrityError no flush interno.
    # begin_nested faz ROLLBACK TO SAVEPOINT e re-propaga a excecao.
    with pytest.raises(Exception):
        OperacaoOdooAuditoria.registrar(
            external_id='TEST-SAVEPOINT-001',  # duplicado de proposito
            tabela_origem='account_move', registro_id=2,
            acao='create', modelo_odoo='account.move',
            status='SUCESSO', executado_por='pytest',
        )
    # CRITICO: SEM rollback manual, uma nova gravacao deve funcionar.
    # No codigo antigo (sem savepoint) isto lancaria PendingRollbackError.
    rec3 = OperacaoOdooAuditoria.registrar(
        external_id='TEST-SAVEPOINT-002',
        tabela_origem='stock_picking', registro_id=3,
        acao='validate', modelo_odoo='stock.picking',
        status='SUCESSO', executado_por='pytest',
    )
    assert rec3.id is not None  # sessao NAO ficou abortada
    db.session.rollback()
