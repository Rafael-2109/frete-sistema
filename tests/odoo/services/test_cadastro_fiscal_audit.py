"""Tests para CadastroFiscalAuditService (sub-skill C5 v14b).

Cobertura V1 perfil 'inventario':
- G017 (NCM ausente) - BLOQUEIO
- G018 (weight=0) - WARN
- G035 (barcode invalido) - BLOQUEIO ou AUTO-FIX
- G014 (lote vencido com saldo) - WARN
- D-OPS-2 (duplicacao pipeline) - BLOQUEIO
- D-OPS-3 (tracking='none') - INFO

Mocka odoo (XML-RPC) e db_session (SQLAlchemy). Foco em logica de
classificacao bloqueio/warning e formato do output estruturado.
"""
from unittest.mock import MagicMock

import pytest

from app.odoo.estoque.scripts.cadastro_fiscal_audit import (
    CadastroFiscalAuditService,
    FASES_PIPELINE_ATIVA,
    STATUS_ATIVOS,
)


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def svc(odoo_mock):
    return CadastroFiscalAuditService(odoo=odoo_mock, db_session=None)


# ============================================================
# Resolucao de entrada (3 formas mutuamente exclusivas)
# ============================================================

def test_resolver_nenhuma_forma_raise(svc):
    """Sem produto_ids, cods_produto NEM ciclo -> ValueError."""
    with pytest.raises(ValueError, match='Forneca uma forma'):
        svc._resolver_produtos()


def test_resolver_duas_formas_raise(svc):
    """Mais de uma forma simultaneamente -> ValueError."""
    with pytest.raises(ValueError, match='mutuamente exclusivas'):
        svc._resolver_produtos(produto_ids=[1], cods_produto=['X'])


def test_resolver_ciclo_sem_db_session_raise(svc):
    """ciclo exige db_session -> ValueError."""
    with pytest.raises(ValueError, match='db_session'):
        svc._resolver_produtos(ciclo='CICLO_X')


def test_resolver_cods_marca_erro_resolucao_para_cods_inexistentes(svc, odoo_mock):
    """Cods sem product.product correspondente sao marcados com _erro_resolucao."""
    odoo_mock.search_read.return_value = [
        {'id': 100, 'default_code': '102020600'},
    ]
    produtos = svc._resolver_produtos(cods_produto=['102020600', 'INEXISTENTE'])
    cods_resolvidos = {p['default_code'] for p in produtos if p.get('id')}
    erros = [p for p in produtos if p.get('_erro_resolucao')]
    assert '102020600' in cods_resolvidos
    assert len(erros) == 1
    assert erros[0]['default_code'] == 'INEXISTENTE'


# ============================================================
# G017 + G018 + D-OPS-3 (NCM, weight, tracking)
# ============================================================

def test_check_ncm_weight_tracking_perfil_completo(svc, odoo_mock):
    """G017 bloqueia, G018 + D-OPS-3 viram warnings."""
    odoo_mock.read.return_value = [
        # produto SEM NCM (G017)
        {'id': 1, 'default_code': '102020600', 'name': 'AZEITONAS',
         'l10n_br_ncm_id': False, 'weight': 0.5, 'tracking': 'lot'},
        # produto com weight=0 (G018) + tracking='none' (D-OPS-3)
        {'id': 2, 'default_code': '103500105', 'name': 'PIMENTA JALAPENO',
         'l10n_br_ncm_id': [42, '0710.10.00'], 'weight': 0.0, 'tracking': 'none'},
        # produto sem nenhum problema
        {'id': 3, 'default_code': '4759598', 'name': 'OLEO SOJA',
         'l10n_br_ncm_id': [99, '1507.10.00'], 'weight': 0.92, 'tracking': 'lot'},
    ]
    res = svc._check_ncm_weight_tracking([1, 2, 3])
    # G017: so o id=1 (sem NCM)
    assert len(res['ncm_faltando']) == 1
    assert res['ncm_faltando'][0]['id'] == 1
    assert res['ncm_faltando'][0]['gotcha'] == 'G017'
    # G018: so o id=2 (weight=0)
    assert len(res['weight_zero']) == 1
    assert res['weight_zero'][0]['id'] == 2
    assert res['weight_zero'][0]['gotcha'] == 'G018'
    # D-OPS-3: so o id=2 (tracking='none')
    assert len(res['tracking_none']) == 1
    assert res['tracking_none'][0]['id'] == 2
    assert res['tracking_none'][0]['gotcha'] == 'D-OPS-3'


# ============================================================
# G035 (barcode invalido) com auto-fix
# ============================================================

def test_check_barcode_auto_corrigir_dry_run_nao_escreve(svc, odoo_mock):
    """auto_corrigir=True + dry_run=True NAO chama clear (reporta apenas)."""
    odoo_mock.search_read.return_value = [
        # 1 barcode invalido (9 digitos)
        {'id': 1, 'default_code': '102020600', 'barcode': '210010347'},
    ]
    res = svc._check_barcode_invalido([1], auto_corrigir=True, dry_run=True)
    assert len(res['barcode_invalido']) == 1
    assert res['barcode_invalido'][0]['gotcha'] == 'G035'
    assert res['acao_aplicada'] is None
    # NAO chamou write em product.product (dry-run)
    odoo_mock.write.assert_not_called()


def test_check_barcode_auto_corrigir_real_chama_clear(svc, odoo_mock):
    """auto_corrigir=True + dry_run=False -> chama clear_invalid_barcodes."""
    odoo_mock.search_read.return_value = [
        {'id': 1, 'default_code': '102020600', 'barcode': '210010347'},
        {'id': 2, 'default_code': '103500105', 'barcode': 'SEMGTIN'},
    ]
    res = svc._check_barcode_invalido([1, 2], auto_corrigir=True, dry_run=False)
    # Apos limpeza, lista zerada
    assert res['barcode_invalido'] == []
    # acao registrada
    assert res['acao_aplicada'] is not None
    assert res['acao_aplicada']['tipo'] == 'clear_barcode'
    assert res['acao_aplicada']['count'] == 2
    # Write chamado UMA vez com ambos ids
    odoo_mock.write.assert_called_once_with(
        'product.product', [1, 2], {'barcode': False},
    )


# ============================================================
# Entry-point auditar_perfil_inventario — output estruturado
# ============================================================

def test_auditar_perfil_inventario_status_ok_sem_problemas(svc, odoo_mock):
    """Cadastro fiscal limpo -> PRE_FLIGHT_OK + pode_faturar=True."""
    # Resolver cods: 1 produto OK
    odoo_mock.search_read.side_effect = [
        # _resolver_produtos via cods_produto
        [{'id': 100, 'default_code': '4759598'}],
        # _check_lote_vencido: sem lotes vencidos
        [],
        # _check_barcode_invalido: sem barcodes invalidos
        [],
    ]
    odoo_mock.read.side_effect = [
        # _check_ncm_weight_tracking
        [{'id': 100, 'default_code': '4759598', 'name': 'OLEO SOJA',
          'l10n_br_ncm_id': [99, '1507.10.00'], 'weight': 0.92, 'tracking': 'lot'}],
    ]
    res = svc.auditar_perfil_inventario(
        cods_produto=['4759598'],
        verificar_duplicacao_pipeline=False,  # sem db_session
    )
    assert res['status_global'] == 'PRE_FLIGHT_OK'
    assert res['pode_faturar'] is True
    assert res['auditados'] == 1
    assert all(len(v) == 0 for v in res['bloqueios'].values())
    assert all(len(v) == 0 for v in res['warnings'].values())


def test_auditar_perfil_inventario_status_bloqueado_ncm_faltando(svc, odoo_mock):
    """G017 NCM ausente -> PRE_FLIGHT_BLOQUEADO + pode_faturar=False."""
    odoo_mock.search_read.side_effect = [
        [{'id': 100, 'default_code': '102020600'}],
        [],  # sem lotes vencidos
        [],  # sem barcodes invalidos
    ]
    odoo_mock.read.side_effect = [
        [{'id': 100, 'default_code': '102020600', 'name': 'AZEITONAS',
          'l10n_br_ncm_id': False, 'weight': 0.5, 'tracking': 'lot'}],
    ]
    res = svc.auditar_perfil_inventario(
        cods_produto=['102020600'],
        verificar_duplicacao_pipeline=False,
    )
    assert res['status_global'] == 'PRE_FLIGHT_BLOQUEADO'
    assert res['pode_faturar'] is False
    assert len(res['bloqueios']['ncm_faltando']) == 1


def test_auditar_perfil_inventario_status_warn_weight_zero(svc, odoo_mock):
    """G018 weight=0 sozinho -> PRE_FLIGHT_WARN + pode_faturar=True."""
    odoo_mock.search_read.side_effect = [
        [{'id': 100, 'default_code': '103500105'}],
        [],  # sem lotes vencidos
        [],  # sem barcodes invalidos
    ]
    odoo_mock.read.side_effect = [
        [{'id': 100, 'default_code': '103500105', 'name': 'PIMENTA',
          'l10n_br_ncm_id': [42, '0710.10.00'], 'weight': 0.0, 'tracking': 'none'}],
    ]
    res = svc.auditar_perfil_inventario(
        cods_produto=['103500105'],
        verificar_duplicacao_pipeline=False,
    )
    assert res['status_global'] == 'PRE_FLIGHT_WARN'
    assert res['pode_faturar'] is True
    # G018 weight=0 e D-OPS-3 tracking=none ambos em warnings
    assert len(res['warnings']['weight_zero']) == 1
    assert len(res['warnings']['tracking_none']) == 1
    # Sem bloqueios
    assert all(len(v) == 0 for v in res['bloqueios'].values())


def test_auditar_perfil_inventario_erros_resolucao_bloqueia(svc, odoo_mock):
    """Cods sem product.product -> bloqueio (erros_resolucao nao vazio)."""
    odoo_mock.search_read.side_effect = [
        [],  # nenhum produto resolvido
        # demais checks nao chamados pois produto_ids_validos = []
    ]
    res = svc.auditar_perfil_inventario(
        cods_produto=['INEXISTENTE_123'],
        verificar_duplicacao_pipeline=False,
    )
    assert res['status_global'] == 'PRE_FLIGHT_BLOQUEADO'
    assert res['pode_faturar'] is False
    assert len(res['erros_resolucao']) == 1
    assert res['auditados'] == 0


def test_auditar_perfil_inventario_skip_lote_vencido(svc, odoo_mock):
    """verificar_lote_vencido=False NAO chama _check_lote_vencido."""
    odoo_mock.search_read.side_effect = [
        [{'id': 100, 'default_code': '102020600'}],
        # NAO ha chamada para lote vencido (skipado)
        [],  # _check_barcode_invalido
    ]
    odoo_mock.read.side_effect = [
        [{'id': 100, 'default_code': '102020600', 'name': 'X',
          'l10n_br_ncm_id': [42, 'NCM'], 'weight': 1.0, 'tracking': 'lot'}],
    ]
    res = svc.auditar_perfil_inventario(
        cods_produto=['102020600'],
        verificar_duplicacao_pipeline=False,
        verificar_lote_vencido=False,
    )
    assert res['warnings']['lote_vencido'] == []
    # Conta de search_read: 1 (resolve cods) + 1 (barcode) = 2
    # (sem chamada de lote vencido)
    assert odoo_mock.search_read.call_count == 2


# ============================================================
# Constantes exportadas
# ============================================================

def test_fases_pipeline_ativa_contem_f5a_a_f5e():
    """FASES_PIPELINE_ATIVA cobre F5a..F5e."""
    assert 'F5a_PICKING_CRIADO' in FASES_PIPELINE_ATIVA
    assert 'F5e_SEFAZ_OK' in FASES_PIPELINE_ATIVA


def test_status_ativos_inclui_aprovado_proposto_executado():
    """STATUS_ATIVOS cobre estados em vida."""
    assert 'APROVADO' in STATUS_ATIVOS
    assert 'PROPOSTO' in STATUS_ATIVOS
    assert 'EXECUTADO' in STATUS_ATIVOS
