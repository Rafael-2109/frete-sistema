"""Tests do orquestrador scripts/inventario_2026_05/ajuste_inventario.py.

Valida a LOGICA DE ORQUESTRACAO (sem tocar no Odoo): leitura de planilha
com --col-* customizaveis, filtros de empresa/sinal, tratamento de tracking,
resolucao de lote e delegacao correta a primitiva StockQuantAdjustmentService.

O script e carregado via importlib (nao e um modulo de pacote). A primitiva,
o lot_svc e o odoo sao mockados.
"""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

_RAIZ = Path(__file__).resolve().parents[2]
_SCRIPT = _RAIZ / 'scripts' / 'inventario_2026_05' / 'ajuste_inventario.py'


@pytest.fixture(scope='module')
def mod():
    spec = importlib.util.spec_from_file_location('ajuste_inventario_orq', _SCRIPT)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ----------------------------------------------------------------------
# helpers de normalizacao
# ----------------------------------------------------------------------

def test_norm_cod_remove_ponto_zero(mod):
    assert mod._norm_cod('123.0') == '123'
    assert mod._norm_cod(' 456 ') == '456'


def test_parse_qtd_vazio_e_nan_viram_none(mod):
    assert mod._parse_qtd(None) is None
    assert mod._parse_qtd(float('nan')) is None
    assert mod._parse_qtd('') is None
    assert mod._parse_qtd('abc') is None


def test_parse_qtd_numerico(mod):
    assert mod._parse_qtd('5') == 5.0
    assert mod._parse_qtd('-3.5') == -3.5
    assert mod._parse_qtd(10) == 10.0


def test_parse_qtd_decimal_brasileiro(mod):
    # vírgula decimal (BR) e formato BR completo com milhar — antes eram pulados
    assert mod._parse_qtd('5,5') == 5.5
    assert mod._parse_qtd('1.234,56') == 1234.56
    assert mod._parse_qtd('-2,5') == -2.5
    assert mod._parse_qtd('5.5') == 5.5  # EN continua válido


# ----------------------------------------------------------------------
# carregar_planilha — schema via --col-*
# ----------------------------------------------------------------------

def test_carregar_planilha_default(mod, tmp_path):
    p = tmp_path / 'aj.xlsx'
    pd.DataFrame([
        {'EMP': 'CD', 'COD': '123', 'LOTE': 'L1', 'AJUSTE': '5'},
        {'EMP': 'FB', 'COD': '456.0', 'LOTE': '', 'AJUSTE': '-2'},
    ]).to_excel(p, index=False)

    regs = mod.carregar_planilha(
        str(p), col_emp='EMP', col_cod='COD', col_lote='LOTE', col_qtd='AJUSTE',
    )
    assert len(regs) == 2
    assert regs[0] == {
        'idx': 1, 'emp': 'CD', 'cod': '123', 'lote_nome': 'L1',
        'qtd': 5.0, 'qtd_raw': '5',
    }
    assert regs[1]['cod'] == '456'      # .0 removido
    assert regs[1]['lote_nome'] is None  # vazio -> None
    assert regs[1]['qtd'] == -2.0


def test_carregar_planilha_coluna_qtd_alternativa(mod, tmp_path):
    """criar_saldo usa 'AJUSTE POSITIVO'; deve funcionar via --col-qtd."""
    p = tmp_path / 'aj.xlsx'
    pd.DataFrame([{'EMP': 'LF', 'COD': '9', 'LOTE': 'P-15/05', 'AJUSTE POSITIVO': '100'}]).to_excel(p, index=False)
    regs = mod.carregar_planilha(
        str(p), col_emp='EMP', col_cod='COD', col_lote='LOTE', col_qtd='AJUSTE POSITIVO',
    )
    assert regs[0]['qtd'] == 100.0


def test_carregar_planilha_sem_col_emp(mod, tmp_path):
    p = tmp_path / 'aj.xlsx'
    pd.DataFrame([{'COD': '1', 'LOTE': 'L', 'QTD': '3'}]).to_excel(p, index=False)
    regs = mod.carregar_planilha(
        str(p), col_emp='', col_cod='COD', col_lote='LOTE', col_qtd='QTD',
    )
    assert regs[0]['emp'] is None  # sem coluna EMP -> nao filtra


def test_carregar_planilha_coluna_obrigatoria_faltando(mod, tmp_path):
    p = tmp_path / 'aj.xlsx'
    pd.DataFrame([{'COD': '1'}]).to_excel(p, index=False)
    with pytest.raises(ValueError, match='colunas obrigatorias'):
        mod.carregar_planilha(
            str(p), col_emp='EMP', col_cod='COD', col_lote='LOTE', col_qtd='AJUSTE',
        )


# ----------------------------------------------------------------------
# processar_linha — fixtures de mocks
# ----------------------------------------------------------------------

@pytest.fixture
def mocks():
    odoo = MagicMock()
    lot_svc = MagicMock()
    svc_adj = MagicMock()
    return odoo, lot_svc, svc_adj


def _produto(odoo, *, tracking='lot', pid=100, active=True):
    odoo.search_read.return_value = [
        {'id': pid, 'active': active, 'tracking': tracking, 'name': 'PROD X'},
    ]


def _chamar(mod, mocks, item, *, empresa='CD', company_id=4, location_id=32,
            sinal='auto', dry_run=True):
    odoo, lot_svc, svc_adj = mocks
    return mod.processar_linha(
        svc_adj=svc_adj, lot_svc=lot_svc, odoo=odoo, item=item,
        empresa=empresa, company_id=company_id, location_id=location_id,
        sinal=sinal, dry_run=dry_run,
    )


def _item(**kw):
    base = {'idx': 1, 'emp': None, 'cod': '123', 'lote_nome': 'L1', 'qtd': 5.0, 'qtd_raw': '5'}
    base.update(kw)
    return base


def test_skip_empresa_diferente(mod, mocks):
    r = _chamar(mod, mocks, _item(emp='FB'), empresa='CD')
    assert r['status'] == 'SKIP_EMP'
    mocks[2].ajustar_quant.assert_not_called()


def test_skip_fora_escopo_pos(mod, mocks):
    r = _chamar(mod, mocks, _item(qtd=-5.0), sinal='pos')
    assert r['status'] == 'SKIP_FORA_ESCOPO'


def test_skip_fora_escopo_neg(mod, mocks):
    r = _chamar(mod, mocks, _item(qtd=5.0), sinal='neg')
    assert r['status'] == 'SKIP_FORA_ESCOPO'


def test_falha_qtd_nao_numerica(mod, mocks):
    r = _chamar(mod, mocks, _item(qtd=None, qtd_raw='xx'))
    assert r['status'] == 'FALHA_QTD'


def test_falha_product(mod, mocks):
    mocks[0].search_read.return_value = []  # produto nao encontrado
    r = _chamar(mod, mocks, _item())
    assert r['status'] == 'FALHA_PRODUCT'


def test_bloqueado_serial(mod, mocks):
    _produto(mocks[0], tracking='serial')
    r = _chamar(mod, mocks, _item())
    assert r['status'] == 'BLOQUEADO_SERIAL'
    mocks[2].ajustar_quant.assert_not_called()


def test_lote_existe_pos_delega_primitiva(mod, mocks):
    odoo, lot_svc, svc_adj = mocks
    _produto(odoo, tracking='lot', pid=100)
    lot_svc.buscar_por_nome.return_value = 555  # lote existe
    svc_adj.ajustar_quant.return_value = {
        'status': 'EXECUTADO', 'qty_antes': 10.0, 'qty_apos': 15.0,
        'acao': 'updated', 'quant_id': 1, 'ajuste_aplicado': 5.0,
    }
    r = _chamar(mod, mocks, _item(qtd=5.0), sinal='pos', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert r['lote_acao'] == 'reused'
    # delegou com os args certos
    kwargs = svc_adj.ajustar_quant.call_args.kwargs
    assert kwargs['product_id'] == 100
    assert kwargs['company_id'] == 4
    assert kwargs['location_id'] == 32
    assert kwargs['lot_id'] == 555
    assert kwargs['delta'] == 5.0
    assert kwargs['criar_se_faltar'] is True  # qtd>0 cria


def test_lote_inexistente_neg_falha(mod, mocks):
    odoo, lot_svc, svc_adj = mocks
    _produto(odoo, tracking='lot')
    lot_svc.buscar_por_nome.return_value = None  # lote nao existe
    r = _chamar(mod, mocks, _item(qtd=-5.0), sinal='neg', dry_run=False)
    assert r['status'] == 'FALHA_LOTE'
    svc_adj.ajustar_quant.assert_not_called()
    lot_svc.criar_se_nao_existe.assert_not_called()  # neg nunca cria lote


def test_lote_inexistente_pos_dryrun_sintetiza(mod, mocks):
    odoo, lot_svc, svc_adj = mocks
    _produto(odoo, tracking='lot')
    lot_svc.buscar_por_nome.return_value = None
    r = _chamar(mod, mocks, _item(qtd=7.0), sinal='pos', dry_run=True)
    assert r['status'] == 'DRY_RUN_OK'
    assert r['lote_acao'] == 'will_create'
    assert r['quant_acao'] == 'will_create'
    assert r['qty_antes'] == 0.0
    assert r['qty_apos'] == 7.0
    svc_adj.ajustar_quant.assert_not_called()  # dry-run nao chama primitiva p/ lote novo
    lot_svc.criar_se_nao_existe.assert_not_called()  # dry-run nao cria lote


def test_lote_inexistente_pos_real_cria_e_delega(mod, mocks):
    odoo, lot_svc, svc_adj = mocks
    _produto(odoo, tracking='lot', pid=100)
    lot_svc.buscar_por_nome.return_value = None
    lot_svc.criar_se_nao_existe.return_value = (888, True)
    svc_adj.ajustar_quant.return_value = {'status': 'EXECUTADO', 'qty_apos': 7.0, 'acao': 'created'}
    r = _chamar(mod, mocks, _item(qtd=7.0), sinal='pos', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert r['lote_acao'] == 'created'
    lot_svc.criar_se_nao_existe.assert_called_once()
    assert svc_adj.ajustar_quant.call_args.kwargs['lot_id'] == 888


def test_tracking_none_passa_lot_id_none(mod, mocks):
    odoo, lot_svc, svc_adj = mocks
    _produto(odoo, tracking='none', pid=100)
    svc_adj.ajustar_quant.return_value = {'status': 'EXECUTADO', 'qty_apos': 5.0, 'acao': 'updated'}
    r = _chamar(mod, mocks, _item(lote_nome='IGNORADO', qtd=5.0), sinal='pos', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert 'warning_lote_ignorado' in r
    assert svc_adj.ajustar_quant.call_args.kwargs['lot_id'] is None
    lot_svc.buscar_por_nome.assert_not_called()  # tracking none nao busca lote
