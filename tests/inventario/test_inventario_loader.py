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


def test_parse_xlsx_headers_reais_compilado_inv(db, ciclo, xlsx_headers_reais):
    """Headers da planilha fisica COMPILADO INV. 16.05.2026 1.xlsx.

    Garante que FB (DESCRIÇÃO com cedilha), CD (FINAL, DESC) e
    LF (QUANTIDADE/UN) carregam sem perder nenhuma aba nem nome_produto.
    Regressao do incidente 2026-05-27 (so FB carregou, 0 linhas com nome).
    """
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_headers_reais, criado_por='test')
    assert resultado['inseridos'] == 5, (
        f'esperava 5 (2 FB + 2 CD + 1 LF), veio {resultado}'
    )
    assert resultado['pulados'] == 0
    assert resultado['erros'] == []

    rows = InventarioBase.query.filter_by(ciclo_id=ciclo.id).all()
    por_emp = {}
    for r in rows:
        por_emp.setdefault(r.empresa, []).append(r)
    assert sorted(por_emp.keys()) == ['CD', 'FB', 'LF'], por_emp.keys()
    assert len(por_emp['FB']) == 2
    assert len(por_emp['CD']) == 2
    assert len(por_emp['LF']) == 1

    fb_azeitona = next(r for r in por_emp['FB'] if r.cod_produto == '4320147')
    assert fb_azeitona.qtd == Decimal('100')
    assert fb_azeitona.nome_produto == 'AZEITONA VD', (
        f'DESCRIÇÃO (cedilha) deve carregar nome, veio {fb_azeitona.nome_produto!r}'
    )

    cd_azeitona = next(r for r in por_emp['CD'] if r.cod_produto == '4320147')
    assert cd_azeitona.qtd == Decimal('200'), 'CD coluna FINAL deve ser qtd'
    assert cd_azeitona.nome_produto == 'AZEITONA VD', 'CD coluna DESC deve ser nome'

    lf_azeitona = por_emp['LF'][0]
    assert lf_azeitona.cod_produto == '4320147'
    assert lf_azeitona.qtd == Decimal('50'), 'LF coluna QUANTIDADE/UN deve ser qtd'
    assert lf_azeitona.nome_produto == 'AZEITONA VD'
