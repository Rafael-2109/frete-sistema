"""Testa model AjusteEstoqueInventario."""
import pytest
from decimal import Decimal
from app import create_app, db
from app.odoo.models import (
    AjusteEstoqueInventario,
    STATUS_VALIDOS,
    ACOES_VALIDAS,
)


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_modelo_basico_status_default_proposto(app_ctx):
    rec = AjusteEstoqueInventario(
        ciclo='INVENTARIO_TEST',
        cod_produto='101001001',
        tipo_produto=1,
        company_id=5,
        qtd_inventario=Decimal('100.0000'),
        qtd_odoo=Decimal('95.0000'),
        qtd_ajuste=Decimal('5.0000'),
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        criado_por='pytest',
    )
    db.session.add(rec)
    db.session.flush()
    assert rec.id is not None
    assert rec.status == 'PROPOSTO'  # default
    assert rec.canary_passou is False  # default
    db.session.rollback()


def test_acoes_validas_completas():
    """ACOES_VALIDAS inclui as 8 acoes principais + DEV CD/LF + indispo + rename + sem_acao."""
    assert 'TRANSFERIR_CD_FB' in ACOES_VALIDAS
    assert 'TRANSFERIR_FB_CD' in ACOES_VALIDAS
    assert 'INDUSTRIALIZACAO_FB_LF' in ACOES_VALIDAS
    assert 'PERDA_LF_FB' in ACOES_VALIDAS
    assert 'DEV_CD_LF' in ACOES_VALIDAS
    assert 'DEV_LF_CD' in ACOES_VALIDAS
    assert 'DEV_FB_LF' in ACOES_VALIDAS  # P011 simetria
    assert 'DEV_LF_FB' in ACOES_VALIDAS  # P011 simetria
    assert 'INDISPONIBILIZAR_LOTE' in ACOES_VALIDAS
    assert 'INDISPONIBILIZAR_LOCAL' in ACOES_VALIDAS
    assert 'RENOMEAR_LOTE' in ACOES_VALIDAS
    assert 'SEM_ACAO' in ACOES_VALIDAS
    assert len(ACOES_VALIDAS) == 12


def test_status_validos_completos():
    assert STATUS_VALIDOS == {'PROPOSTO', 'APROVADO', 'EXECUTADO', 'FALHA', 'CANCELADO'}


def test_filtro_por_ciclo(app_ctx):
    """Multiplos ciclos coexistem na mesma tabela."""
    db.session.add(AjusteEstoqueInventario(
        ciclo='INVENTARIO_2026_05',
        cod_produto='C1', tipo_produto=1, company_id=5,
        qtd_inventario=Decimal('10'), qtd_odoo=Decimal('10'),
        qtd_ajuste=Decimal('0'), acao_decidida='SEM_ACAO',
        criado_por='pytest',
    ))
    db.session.add(AjusteEstoqueInventario(
        ciclo='INVENTARIO_2026_08',
        cod_produto='C2', tipo_produto=2, company_id=5,
        qtd_inventario=Decimal('20'), qtd_odoo=Decimal('20'),
        qtd_ajuste=Decimal('0'), acao_decidida='SEM_ACAO',
        criado_por='pytest',
    ))
    db.session.flush()
    do_ciclo_05 = AjusteEstoqueInventario.query.filter_by(ciclo='INVENTARIO_2026_05').all()
    do_ciclo_08 = AjusteEstoqueInventario.query.filter_by(ciclo='INVENTARIO_2026_08').all()
    assert len(do_ciclo_05) >= 1
    assert len(do_ciclo_08) >= 1
    db.session.rollback()
