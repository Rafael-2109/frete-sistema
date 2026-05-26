"""Testes do parser xlsx de inventário base."""
from decimal import Decimal
from app.inventario.models import InventarioBase
from app.inventario.services.inventario_loader import InventarioLoader


def test_parse_xlsx_valido(db, ciclo, xlsx_valido):
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_valido, criado_por='test')
    assert resultado['inseridos'] == 5
    assert resultado['pulados'] == 0
    assert len(resultado['erros']) == 0

    rows = InventarioBase.query.filter_by(ciclo_id=ciclo.id).all()
    assert len(rows) == 5
    fb_4320147 = next(r for r in rows if r.cod_produto == '4320147' and r.empresa == 'FB')
    assert fb_4320147.qtd == Decimal('100.000')


def test_parse_xlsx_pula_codigo_invalido(db, ciclo, xlsx_com_invalidos):
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_com_invalidos, criado_por='test')
    assert resultado['pulados'] == 1
    assert resultado['inseridos'] == 1
    assert any('CHAVE-X' in e or 'pulado' in e.lower() for e in resultado['erros'])


def test_parse_xlsx_qtd_negativa_erro(db, ciclo, xlsx_com_invalidos):
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_com_invalidos, criado_por='test')
    assert any('-5' in e or 'negativ' in e.lower() for e in resultado['erros'])


def test_reupload_substitui_linhas(db, ciclo, xlsx_valido):
    InventarioLoader.carregar(ciclo.id, xlsx_valido, criado_por='test')
    assert InventarioBase.query.filter_by(ciclo_id=ciclo.id).count() == 5

    from tests.inventario.conftest import _make_test_xlsx
    novo = _make_test_xlsx({'FB': [('NOVO_PROD', '', 999)], 'CD': [], 'LF': []})
    InventarioLoader.carregar(ciclo.id, novo, criado_por='test')
    assert InventarioBase.query.filter_by(ciclo_id=ciclo.id).count() == 0
