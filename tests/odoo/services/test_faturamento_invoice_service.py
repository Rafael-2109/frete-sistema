"""Tests para FaturamentoInvoiceService v24+ (Skill 8 ATOMICA L2 — AP6 refator).

Cobertura — 1 atomo por bloco:
  validar_invoice_constants   - 4 testes
  liberar_faturamento         - 5 testes
  polling_invoice             - 4 testes
  validar_invoice_pos_robo    - 5 testes
  transmitir_sefaz            - 13 testes (inclui C1: ajuste_ids opcional +
                                idempotencia primaria intra-Odoo anti-SEFAZ)

C1 (v25+): transmitir_sefaz desacoplado de AjusteEstoqueInventario —
  ajuste_ids OPCIONAL; idempotencia primaria le o proprio account.move
  (l10n_br_situacao_nf / l10n_br_chave_nf); D8.3 vira camada de auditoria
  opcional (so quando ajuste_ids fornecido). Compat retroativa total.

Pattern: cada teste usa MagicMock(odoo) para simular XML-RPC + dry-run
sempre planeja (corrige AP4) + real-run idempotente. Mocks de:
  - picking_svc (Skill 5 LEGACY) para liberar_faturamento + aguardar_invoice
  - _invoice_helpers (G029/G007/G034)
  - transmitir_nfe_via_playwright (Playwright SEFAZ — imported lazy)
  - AjusteEstoqueInventario (modelo Flask-SQLAlchemy)
  - commit_resilient (G016)
"""
from unittest.mock import MagicMock, patch

import pytest

from app.odoo.estoque.scripts.faturamento import (
    CONSTANTS_CAMPOS_VALIDAVEIS,
    HARD_FAIL_CONFIG_ERRORS,
    FaturamentoInvoiceService,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def odoo_mock():
    """Mock de OdooConnection."""
    return MagicMock()


@pytest.fixture
def picking_svc_mock():
    """Mock de StockPickingService (Skill 5 LEGACY)."""
    return MagicMock()


@pytest.fixture
def svc(odoo_mock, picking_svc_mock):
    """Service com mocks injetados."""
    return FaturamentoInvoiceService(odoo=odoo_mock, picking_svc=picking_svc_mock)


# ============================================================
# Atomo 1 — validar_invoice_constants
# ============================================================

def test_validar_constants_ok(svc, odoo_mock):
    """Todos campos batem -> status='OK', divergencias={}."""
    odoo_mock.read.return_value = [{
        'fiscal_position_id': [25, 'REMESSA P/ INDUSTRIALIZACAO'],
        'l10n_br_tipo_pedido': 'industrializacao',
        'payment_term_id': [1, 'Imediato'],
    }]
    res = svc.validar_invoice_constants(
        invoice_id=12345,
        constants_esperadas={
            'fiscal_position_id': 25,
            'l10n_br_tipo_pedido': 'industrializacao',
            'payment_term_id': 1,
        },
        dry_run=True,
    )
    assert res['status'] == 'OK'
    assert res['divergencias'] == {}
    assert set(res['campos_validados']) == {
        'fiscal_position_id', 'l10n_br_tipo_pedido', 'payment_term_id',
    }
    assert 'tempo_ms' in res


def test_validar_constants_divergencia(svc, odoo_mock):
    """Campo divergente -> status='FALHA_DIVERGENCIA' + divergencias populadas."""
    odoo_mock.read.return_value = [{
        'fiscal_position_id': [99, 'OUTRA FP'],   # esperado 25
        'l10n_br_tipo_pedido': 'transf-filial',   # esperado industrializacao
    }]
    res = svc.validar_invoice_constants(
        invoice_id=12345,
        constants_esperadas={
            'fiscal_position_id': 25,
            'l10n_br_tipo_pedido': 'industrializacao',
        },
    )
    assert res['status'] == 'FALHA_DIVERGENCIA'
    assert 'fiscal_position_id' in res['divergencias']
    assert res['divergencias']['fiscal_position_id']['esperado'] == 25
    assert res['divergencias']['fiscal_position_id']['atual'] == 99
    assert 'l10n_br_tipo_pedido' in res['divergencias']


def test_validar_constants_invoice_nao_existe(svc, odoo_mock):
    """read() retorna [] -> FALHA_INVOICE_NAO_EXISTE."""
    odoo_mock.read.return_value = []
    res = svc.validar_invoice_constants(
        invoice_id=99999,
        constants_esperadas={'fiscal_position_id': 25},
    )
    assert res['status'] == 'FALHA_INVOICE_NAO_EXISTE'
    assert 'nao encontrado' in res['erro']


def test_validar_constants_campo_invalido(svc, odoo_mock):
    """Campo nao suportado -> FALHA_CAMPO_INVALIDO (NAO chama Odoo)."""
    res = svc.validar_invoice_constants(
        invoice_id=12345,
        constants_esperadas={
            'fiscal_position_id': 25,
            'campo_inexistente': 'foo',  # nao em CONSTANTS_CAMPOS_VALIDAVEIS
        },
    )
    assert res['status'] == 'FALHA_CAMPO_INVALIDO'
    assert 'campo_inexistente' in res['erro']
    # NAO chamou Odoo
    odoo_mock.read.assert_not_called()


# ============================================================
# Atomo 2 — liberar_faturamento
# ============================================================

def test_liberar_dry_run_planeja(svc, odoo_mock, picking_svc_mock):
    """Dry-run le state mas NAO chama picking_svc.liberar_faturamento."""
    odoo_mock.read.return_value = [{'state': 'done', 'name': 'FB/SAI/IND/01001'}]
    res = svc.liberar_faturamento(
        picking_id=321600, ajuste_ids=[176013, 176014],
        ciclo='INVENTARIO_2026_05',
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['picking_state'] == 'done'
    assert res['picking_name'] == 'FB/SAI/IND/01001'
    picking_svc_mock.liberar_faturamento.assert_not_called()


def test_liberar_real_run_bloqueado_sem_confirmar(svc, odoo_mock, picking_svc_mock):
    """Real-run sem confirmar=True -> BLOQUEADO_SEM_CONFIRMAR."""
    res = svc.liberar_faturamento(
        picking_id=321600, ajuste_ids=[176013],
        dry_run=False, confirmar=False,
    )
    assert res['status'] == 'BLOQUEADO_SEM_CONFIRMAR'
    odoo_mock.read.assert_not_called()
    picking_svc_mock.liberar_faturamento.assert_not_called()


def test_liberar_picking_nao_done(svc, odoo_mock, picking_svc_mock):
    """Picking state != 'done' -> FALHA_PICKING_NAO_DONE."""
    odoo_mock.read.return_value = [{'state': 'assigned', 'name': 'FB/SAI/IND/01002'}]
    res = svc.liberar_faturamento(
        picking_id=321601, ajuste_ids=[176014],
        dry_run=False, confirmar=True,
    )
    assert res['status'] == 'FALHA_PICKING_NAO_DONE'
    assert 'assigned' in res['erro']
    picking_svc_mock.liberar_faturamento.assert_not_called()


def test_liberar_picking_nao_existe(svc, odoo_mock, picking_svc_mock):
    """odoo.read retorna [] -> FALHA_PICKING_NAO_EXISTE."""
    odoo_mock.read.return_value = []
    res = svc.liberar_faturamento(
        picking_id=99999, ajuste_ids=[176013],
        dry_run=False, confirmar=True,
    )
    assert res['status'] == 'FALHA_PICKING_NAO_EXISTE'


def test_liberar_ok_delega_picking_svc(svc, odoo_mock, picking_svc_mock):
    """Real-run com state=done -> delega picking_svc.liberar_faturamento."""
    odoo_mock.read.return_value = [{'state': 'done', 'name': 'FB/SAI/IND/01003'}]
    picking_svc_mock.liberar_faturamento.return_value = None
    res = svc.liberar_faturamento(
        picking_id=321602, ajuste_ids=[176015, 176016],
        dry_run=False, confirmar=True,
    )
    assert res['status'] == 'OK'
    picking_svc_mock.liberar_faturamento.assert_called_once_with(321602)


# ============================================================
# Atomo 3 — polling_invoice
# ============================================================

def test_polling_dry_run_planeja(svc, picking_svc_mock):
    """Dry-run NAO chama picking_svc.aguardar_invoice_do_robo."""
    res = svc.polling_invoice(
        picking_id=321600, ajuste_ids=[176013],
        timeout_s=600, dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['invoice_id'] is None
    picking_svc_mock.aguardar_invoice_do_robo.assert_not_called()


def test_polling_ok_retorna_invoice_id(svc, picking_svc_mock):
    """Real-run com invoice retornado -> status='OK' + invoice_id."""
    picking_svc_mock.aguardar_invoice_do_robo.return_value = 716448
    res = svc.polling_invoice(
        picking_id=321600, ajuste_ids=[176013, 176014],
        timeout_s=1800, dry_run=False,
    )
    assert res['status'] == 'OK'
    assert res['invoice_id'] == 716448
    picking_svc_mock.aguardar_invoice_do_robo.assert_called_once_with(
        321600, timeout=1800, poll_interval=40,
    )


def test_polling_timeout_retorna_none(svc, picking_svc_mock):
    """Real-run sem invoice no timeout -> status='TIMEOUT'."""
    picking_svc_mock.aguardar_invoice_do_robo.return_value = None
    res = svc.polling_invoice(
        picking_id=321600, ajuste_ids=[176013],
        timeout_s=60, dry_run=False,
    )
    assert res['status'] == 'TIMEOUT'
    assert res['invoice_id'] is None
    assert 'timeout' in res['erro'].lower()


def test_polling_excecao_falha(svc, picking_svc_mock):
    """Real-run com excecao -> status='FALHA'."""
    picking_svc_mock.aguardar_invoice_do_robo.side_effect = ValueError(
        'Picking nao encontrado'
    )
    res = svc.polling_invoice(
        picking_id=99999, ajuste_ids=[176013],
        dry_run=False,
    )
    assert res['status'] == 'FALHA'
    assert 'Picking nao encontrado' in res['erro']


# ============================================================
# Atomo 4 — validar_invoice_pos_robo
# ============================================================

def test_validar_pos_robo_dry_run(svc):
    """Dry-run NAO chama helpers."""
    res = svc.validar_invoice_pos_robo(
        invoice_id=716448, ajuste_id_primeiro=176013,
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    # Sub-etapas NAO foram contadas
    assert all(v == 0 for v in res['sub_etapas'].values())


def test_validar_pos_robo_real_run_bloqueado_sem_confirmar(svc):
    """Real-run sem confirmar=True -> BLOQUEADO_SEM_CONFIRMAR."""
    res = svc.validar_invoice_pos_robo(
        invoice_id=716448, ajuste_id_primeiro=176013,
        dry_run=False, confirmar=False,
    )
    assert res['status'] == 'BLOQUEADO_SEM_CONFIRMAR'


def test_validar_pos_robo_perfil_invalido(svc):
    """Perfil nao suportado -> FALHA_PERFIL_INVALIDO."""
    res = svc.validar_invoice_pos_robo(
        invoice_id=716448, ajuste_id_primeiro=176013,
        perfil='venda-cliente',  # planejado mas nao implementado
        dry_run=True,
    )
    assert res['status'] == 'FALHA_PERFIL_INVALIDO'


def test_validar_pos_robo_ok_todas_sub_etapas(svc):
    """Real-run sucesso em todas 3 sub-etapas (DEV_*) -> status=OK."""
    ajuste_mock = MagicMock()
    ajuste_mock.acao_decidida = 'DEV_LF_FB'
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        return_value=ajuste_mock,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.garantir_payment_provider',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.corrigir_price_zero_em_invoice',
        return_value=2,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.garantir_fiscal_setup',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ):
        res = svc.validar_invoice_pos_robo(
            invoice_id=716448, ajuste_id_primeiro=176013,
            dry_run=False, confirmar=True,
        )
    assert res['status'] == 'OK'
    assert res['sub_etapas']['f5d5_payment_provider_ok'] == 1
    assert res['sub_etapas']['f5d6_price_zero_corrigidas'] == 2
    assert res['sub_etapas']['f5d7_fiscal_setup_ok'] == 1
    assert res['sub_etapas']['f5d7_fiscal_setup_skip'] == 0


def test_validar_pos_robo_ok_parcial_com_falha(svc):
    """1 falha em sub-etapa -> status=OK_PARCIAL (D6 — falha individual nao derruba)."""
    ajuste_mock = MagicMock()
    ajuste_mock.acao_decidida = 'INDUSTRIALIZACAO_FB_LF'  # nao-DEV -> f5d7 skip
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        return_value=ajuste_mock,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.garantir_payment_provider',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.corrigir_price_zero_em_invoice',
        side_effect=RuntimeError('Odoo timeout'),
    ), patch(
        'app.odoo.estoque.scripts.faturamento.garantir_fiscal_setup',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ):
        res = svc.validar_invoice_pos_robo(
            invoice_id=716448, ajuste_id_primeiro=176013,
            dry_run=False, confirmar=True,
        )
    assert res['status'] == 'OK_PARCIAL'
    assert res['sub_etapas']['f5d6_price_zero_falha'] == 1
    assert res['sub_etapas']['f5d7_fiscal_setup_skip'] == 1  # nao-DEV


# ============================================================
# Atomo 5 — transmitir_sefaz
# ============================================================

def test_transmitir_dry_run_planeja(svc):
    """Dry-run NAO chama Playwright."""
    res = svc.transmitir_sefaz(
        invoice_id=716448, ajuste_ids=[176013, 176014],
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['chave_nfe'] is None


def test_transmitir_real_run_bloqueado_sem_confirmar_sefaz(svc):
    """Real-run sem confirmar_sefaz=True -> BLOQUEADO_SEM_CONFIRMAR_SEFAZ."""
    res = svc.transmitir_sefaz(
        invoice_id=716448, ajuste_ids=[176013],
        dry_run=False, confirmar_sefaz=False,
    )
    assert res['status'] == 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'


def test_transmitir_sem_ajustes_dry_run_ok(svc):
    """C1: ajuste_ids=None (remessa avulsa) -> DRY_RUN_OK (NAO mais
    FALHA_AJUSTES_VAZIOS). Idempotencia primaria vem do account.move."""
    res = svc.transmitir_sefaz(
        invoice_id=716448, ajuste_ids=None,
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['chave_nfe'] is None
    # observacao reflete 0 ajustes (camada de auditoria opcional ausente)
    assert '0 ajustes' in res['observacao']


def test_transmitir_lista_vazia_dry_run_ok(svc):
    """C1: ajuste_ids=[] (lista vazia) tambem -> DRY_RUN_OK (sem early-return)."""
    res = svc.transmitir_sefaz(
        invoice_id=716448, ajuste_ids=[],
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'


def test_transmitir_ok_sucesso_propaga_chave(svc):
    """Real-run sucesso -> propaga chave_nfe + status=EXECUTADO em todos ajustes."""
    chave = '35260561724241000178550010000945661007164482'
    ajuste1 = MagicMock(id=176013, fase_pipeline='F5d_INVOICE_GERADA', status='APROVADO', chave_nfe=None)
    ajuste2 = MagicMock(id=176014, fase_pipeline='F5d_INVOICE_GERADA', status='APROVADO', chave_nfe=None)
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        side_effect=[ajuste1, ajuste2, ajuste1, ajuste2],
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
        return_value={
            'sucesso': True,
            'chave_nf': chave,
            'situacao_nf': 'autorizado',
            'tentativas': 1,
        },
    ):
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=[176013, 176014],
            ciclo='INVENTARIO_2026_05',
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'OK'
    assert res['chave_nfe'] == chave
    assert res['situacao_nf'] == 'autorizado'
    # Ambos ajustes propagados (D-OPS-2b)
    assert ajuste1.fase_pipeline == 'F5e_SEFAZ_OK'
    assert ajuste1.chave_nfe == chave
    assert ajuste1.status == 'EXECUTADO'
    assert ajuste2.fase_pipeline == 'F5e_SEFAZ_OK'
    assert ajuste2.chave_nfe == chave


def test_transmitir_idempotent_skip(svc):
    """D8.3: 1 ajuste ja em F5e_SEFAZ_OK -> skip + retorna chave existente."""
    chave_existente = '35260561724241000178550010000945661007164482'
    ajuste1 = MagicMock(
        id=176013, fase_pipeline='F5e_SEFAZ_OK', status='EXECUTADO',
        chave_nfe=chave_existente,
    )
    ajuste2 = MagicMock(
        id=176014, fase_pipeline='F5d_INVOICE_GERADA', status='APROVADO',
        chave_nfe=None,
    )
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        side_effect=[ajuste1, ajuste2],
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
    ) as mock_playwright:
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=[176013, 176014],
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'IDEMPOTENT_SKIP'
    assert res['chave_nfe'] == chave_existente
    # Playwright NAO chamado (idempotencia)
    mock_playwright.assert_not_called()


def test_transmitir_idempotent_intra_odoo_sem_ajustes(svc, odoo_mock):
    """C1 (CRITICO SEFAZ): invoice JA autorizado no Odoo + ajuste_ids=None
    -> IDEMPOTENT_SKIP via leitura do proprio account.move (situacao_nf=
    'autorizado' / chave preenchida). Playwright NUNCA chamado (guarda
    anti-dupla-transmissao independente de ciclo/ajuste)."""
    chave = '35260561724241000178550010000945661007164482'
    odoo_mock.read.return_value = [{
        'l10n_br_situacao_nf': 'autorizado',
        'l10n_br_chave_nf': chave,
        'state': 'posted',
    }]
    with patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
    ) as mock_playwright:
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=None,
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'IDEMPOTENT_SKIP'
    assert res['chave_nfe'] == chave
    assert res['situacao_nf'] == 'autorizado'
    # Playwright NAO chamado (anti-dupla-transmissao SEFAZ)
    mock_playwright.assert_not_called()


def test_transmitir_idempotent_intra_odoo_so_chave(svc, odoo_mock):
    """C1: invoice com chave de 44 digitos preenchida (mesmo sem
    situacao_nf=='autorizado' literal) -> IDEMPOTENT_SKIP. Chave
    truthy de 44 digitos = NF JA transmitida (guarda robusta)."""
    chave = '35260518467441000163550010000132451007099999'
    odoo_mock.read.return_value = [{
        'l10n_br_situacao_nf': 'excecao_autorizado',
        'l10n_br_chave_nf': chave,
        'state': 'posted',
    }]
    with patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
    ) as mock_playwright:
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=None,
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'IDEMPOTENT_SKIP'
    assert res['chave_nfe'] == chave
    mock_playwright.assert_not_called()


def test_transmitir_compat_d83_idempotent_com_ajustes(svc, odoo_mock):
    """COMPAT C1: account.move AINDA NAO autorizado no Odoo, mas ajuste
    fornecido ja em F5e_SEFAZ_OK/EXECUTADO -> IDEMPOTENT_SKIP via D8.3
    (camada de auditoria preservada quando ajuste_ids fornecido)."""
    chave_existente = '35260561724241000178550010000945661007164482'
    # Odoo ainda nao mostra autorizado (so a fase do ajuste sabe)
    odoo_mock.read.return_value = [{
        'l10n_br_situacao_nf': False,
        'l10n_br_chave_nf': False,
        'state': 'posted',
    }]
    ajuste1 = MagicMock(
        id=176013, fase_pipeline='F5e_SEFAZ_OK', status='EXECUTADO',
        chave_nfe=chave_existente,
    )
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        side_effect=[ajuste1],
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
    ) as mock_playwright:
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=[176013],
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'IDEMPOTENT_SKIP'
    assert res['chave_nfe'] == chave_existente
    mock_playwright.assert_not_called()


def test_transmitir_avulsa_real_run_ok_sem_ajustes(svc, odoo_mock):
    """C1 (happy path AVULSO): real-run sucesso com ajuste_ids=None ->
    status=OK + chave, SEM tocar AjusteEstoqueInventario. account.move
    nao-autorizado de entrada (idempotencia intra-Odoo nao dispara),
    Playwright autoriza, resultado fica no proprio account.move."""
    chave = '35260561724241000178550010000945661007164482'
    # account.move ainda NAO autorizado (idempotencia intra-Odoo nao bloqueia)
    odoo_mock.read.return_value = [{
        'l10n_br_situacao_nf': False,
        'l10n_br_chave_nf': False,
    }]
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
    ) as mock_get, patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
        return_value={
            'sucesso': True,
            'chave_nf': chave,
            'situacao_nf': 'autorizado',
            'tentativas': 1,
        },
    ):
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=None,
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'OK'
    assert res['chave_nfe'] == chave
    assert res['situacao_nf'] == 'autorizado'
    # Sem ajustes: camada de auditoria NAO foi tocada
    mock_get.assert_not_called()


def test_transmitir_hard_fail_config_aborta(svc):
    """D7: HARD_FAIL_CONFIG_ERRORS (tentativas=0 + erro config) -> FALHA_CONFIG."""
    ajuste1 = MagicMock(id=176013, fase_pipeline='F5d_INVOICE_GERADA', status='APROVADO', chave_nfe=None)
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        return_value=ajuste1,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
        return_value={
            'sucesso': False,
            'tentativas': 0,
            'erro': 'playwright_indisponivel',
        },
    ):
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=[176013],
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'FALHA_CONFIG'
    assert res['erro_config'] == 'playwright_indisponivel'
    assert ajuste1.fase_pipeline == 'F5e_FALHA'


def test_transmitir_critical1_commit_pos_sefaz_falha(svc):
    """CRITICAL-1 v17: commit POS-SEFAZ falha -> FALHA_COMMIT_POS_SEFAZ_OK
    (SEFAZ autorizada mas DB nao persistido — operador investiga manualmente).
    """
    chave = '35260518467441000163550010000132451007099999'
    ajuste1 = MagicMock(id=176013, fase_pipeline='F5d_INVOICE_GERADA', status='APROVADO', chave_nfe=None)
    # commit_resilient retorna True (pre) e False (pos-Playwright)
    commit_calls = [True, False]  # pre OK, pos FAIL
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        side_effect=[ajuste1, ajuste1],
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        side_effect=lambda: commit_calls.pop(0),
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
        return_value={
            'sucesso': True,
            'chave_nf': chave,
            'situacao_nf': 'autorizado',
            'tentativas': 1,
        },
    ):
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=[176013],
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'FALHA_COMMIT_POS_SEFAZ_OK'
    assert chave in res['erro']


def test_transmitir_falha_sefaz_com_cstat(svc):
    """MED C-2: SEFAZ falha persiste cstat+xmotivo em erro_msg."""
    ajuste1 = MagicMock(id=176013, fase_pipeline='F5d_INVOICE_GERADA', status='APROVADO', chave_nfe=None)
    with patch(
        'app.odoo.estoque.scripts.faturamento.safe_session_get',
        side_effect=[ajuste1, ajuste1],
    ), patch(
        'app.odoo.estoque.scripts.faturamento.commit_resilient',
        return_value=True,
    ), patch(
        'app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright',
        return_value={
            'sucesso': False,
            'tentativas': 15,
            'erro': 'sefaz_rejeitou',
            'ultimo_estado': {'cstat': '225', 'xmotivo': 'NCM invalido'},
        },
    ):
        res = svc.transmitir_sefaz(
            invoice_id=716448, ajuste_ids=[176013],
            dry_run=False, confirmar_sefaz=True,
        )
    assert res['status'] == 'FALHA'
    assert res['erro'] == 'sefaz_rejeitou'
    # erro_msg persistido no ajuste tem cstat+xmotivo
    assert ajuste1.fase_pipeline == 'F5e_FALHA'
    assert 'cstat=225' in ajuste1.erro_msg
    assert 'NCM invalido' in ajuste1.erro_msg


# ============================================================
# Tests sanity de constants exportadas
# ============================================================

def test_hard_fail_config_errors_imutavel():
    """HARD_FAIL_CONFIG_ERRORS eh frozenset (imutavel)."""
    assert isinstance(HARD_FAIL_CONFIG_ERRORS, frozenset)
    assert 'playwright_indisponivel' in HARD_FAIL_CONFIG_ERRORS
    assert 'odoo_password_ausente' in HARD_FAIL_CONFIG_ERRORS
    assert 'odoo_username_ausente' in HARD_FAIL_CONFIG_ERRORS


def test_constants_campos_validaveis_inclui_essenciais():
    """CONSTANTS_CAMPOS_VALIDAVEIS inclui campos essenciais SEFAZ."""
    essenciais = {
        'fiscal_position_id', 'l10n_br_tipo_pedido', 'payment_term_id',
        'journal_id', 'company_id', 'partner_id',
    }
    assert essenciais.issubset(CONSTANTS_CAMPOS_VALIDAVEIS)


def test_registrar_auditoria_nao_passa_etapa_string_para_coluna_integer():
    """G-AUDIT-1 / N21 — 2a cópia do bug em `_invoice_helpers._registrar_auditoria`
    (descoberta pelo canary P6 2026-05-29). A coluna `operacao_odoo_auditoria.etapa`
    é `db.Integer`; passar `etapa=fase` (string 'F5d.5') estoura
    `psycopg2.InvalidTextRepresentation` e envenena a session do pipeline (SEFAZ).
    A fase deve ir em `pipeline_etapa` (String) + `etapa_descricao` — NUNCA em `etapa`.
    """
    from unittest.mock import patch
    from app.odoo.estoque.scripts import _invoice_helpers

    with patch('app.odoo.models.OperacaoOdooAuditoria') as MockAud:
        _invoice_helpers._registrar_auditoria(
            ciclo='TEST_CICLO', ajuste_id=180371, fase='F5d.5',
            acao='LIBERAR_FAT', status='EXECUTADO', modelo_odoo='account.move',
        )
        MockAud.registrar.assert_called_once()
        kwargs = MockAud.registrar.call_args.kwargs
        # 'etapa' (coluna Integer) NÃO pode receber a string de fase
        assert not isinstance(kwargs.get('etapa'), str), (
            f"etapa (Integer) nao pode ser string; recebeu {kwargs.get('etapa')!r}"
        )
        # a fase vai em pipeline_etapa (String) + etapa_descricao
        assert kwargs.get('pipeline_etapa') == 'F5d.5'
        assert 'F5d.5' in (kwargs.get('etapa_descricao') or '')
