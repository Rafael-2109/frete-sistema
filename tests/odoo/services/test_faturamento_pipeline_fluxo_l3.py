"""Tests para FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x (v19+).

Cobertura mockada (sem DB):
  - caminho A (DFe processado) -> FLUXO_OK skip
  - caminho A (DFe pendente) -> dry-run reporta passos
  - caminho B (DFe ausente) -> dry-run cria DFe + escritura + gera PO (passos B)
  - invoice SAIDA sem chave_nfe -> FALHA

Smoke do dispatch (caminho A vs B) sem hit Odoo real.
"""
from unittest.mock import MagicMock

from app.odoo.estoque.orchestrators.faturamento_pipeline import (
    FaturamentoPipelineExecutor,
)


def _patch_buscar_dfe(executor, *, encontrado, dfe_id=None, status='ausente'):
    """Stub EscrituracaoLfService.buscar_dfe interno (via lazy import)."""
    # O EscrituracaoLfService eh importado lazy dentro do metodo;
    # patch direto na classe via sys.modules.
    from app.odoo.estoque.scripts import escrituracao as escr_mod
    original_cls = escr_mod.EscrituracaoLfService

    class _FakeEscrSvc:
        def __init__(self, odoo=None):
            self.odoo = odoo

        def buscar_dfe(self, *, chave_nfe, company_id):
            return {
                'encontrado': encontrado,
                'dfe_id': dfe_id,
                'status': status,
                'raw': {},
                'tempo_ms': 1,
                'erro': None,
            }

        def criar_dfe_a_partir_do_invoice_saida(
            self, *, invoice_id_saida, company_destino, dry_run=True,
        ):
            return {
                'status': 'DRY_RUN_OK' if dry_run else 'CRIADO',
                'dfe_id': dfe_id or 7777,
                'chave_nfe': 'X' * 44,
                'tempo_ms': 1,
                'erro': None,
            }

        def escriturar_dfe(self, **kw):
            return {
                'status': 'DRY_RUN_OK' if kw.get('dry_run') else 'ESCRITURADO',
                'dfe_id': kw.get('dfe_id'),
                'l10n_br_tipo_pedido': kw.get('l10n_br_tipo_pedido'),
                'data_entrada': '2026-05-26',
                'tempo_ms': 1,
                'erro': None,
            }

        def gerar_po_from_dfe(self, **kw):
            return {
                'status': 'DRY_RUN_OK' if kw.get('dry_run') else 'CRIADO',
                'po_id': None if kw.get('dry_run') else 888,
                'tempo_ms': 1,
                'erro': None,
            }

        def preencher_po(self, **kw):
            return {
                'status': 'DRY_RUN_OK' if kw.get('dry_run') else 'PREENCHIDO',
                'po_id': kw.get('po_id'),
                'tempo_ms': 1,
                'erro': None,
            }

        def confirmar_po(self, **kw):
            return {
                'status': 'DRY_RUN_OK' if kw.get('dry_run') else 'CONFIRMADO',
                'po_id': kw.get('po_id'),
                'state_final': 'purchase',
                'tempo_ms': 1,
                'erro': None,
            }

        def criar_invoice_from_po(self, **kw):
            return {
                'status': 'DRY_RUN_OK' if kw.get('dry_run') else 'CRIADO',
                'invoice_id': None if kw.get('dry_run') else 9999,
                'tempo_ms': 1,
                'erro': None,
            }

    escr_mod.EscrituracaoLfService = _FakeEscrSvc  # type: ignore[misc]
    return original_cls


def _restore_escrituracao(original_cls):
    from app.odoo.estoque.scripts import escrituracao as escr_mod
    escr_mod.EscrituracaoLfService = original_cls  # type: ignore[misc]


def test_fluxo_l3_caminho_a_dfe_processado_NAO_RETORNA_EARLY():
    """CR-v19+-HIGH-3: DFe status='processado' NAO retorna early.
    Caminho A com status processado segue passos 3-9 (atomos a jusante
    idempotentes via campos Odoo). 'processado' significa apenas XML
    parseado pelo robo; nao garante que PO/picking/invoice existem."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099001',
        'state': 'posted',
    }]
    executor = FaturamentoPipelineExecutor(
        odoo=odoo, picking_svc=MagicMock(),
    )
    original = _patch_buscar_dfe(
        executor, encontrado=True, dfe_id=4321, status='processado',
    )
    try:
        res = executor.executar_fluxo_l3_1_2_x(
            invoice_id_saida=607443,
            company_destino=5,
            l10n_br_tipo_pedido_dfe='compra',
            l10n_br_tipo_pedido_po='serv-industrializacao',
            team_id=119,
            payment_term_id=2791,
            picking_type_id=1,
            payment_provider_id=92,
            dry_run=True,
        )
    finally:
        _restore_escrituracao(original)

    # Apos fix CR-v19+-HIGH-3: dry_run continua passos 3-4
    assert res['status'] == 'DRY_RUN_OK'
    assert res['caminho'] == 'A'
    assert res['dfe_id'] == 4321
    # Confirmar que passos 3+4 foram executados
    passos_nomes = [p['passo'] for p in res['passos']]
    assert '3_escriturar_dfe' in passos_nomes
    assert '4_gerar_po_from_dfe' in passos_nomes


def test_fluxo_l3_caminho_a_dry_run_planeja():
    """Caminho A: DFe pendente + dry_run -> DRY_RUN_OK reporta passos."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099002',
        'state': 'posted',
    }]
    executor = FaturamentoPipelineExecutor(
        odoo=odoo, picking_svc=MagicMock(),
    )
    original = _patch_buscar_dfe(
        executor, encontrado=True, dfe_id=4321, status='pendente',
    )
    try:
        res = executor.executar_fluxo_l3_1_2_x(
            invoice_id_saida=607443,
            company_destino=5,
            l10n_br_tipo_pedido_dfe='compra',
            l10n_br_tipo_pedido_po='serv-industrializacao',
            team_id=119,
            payment_term_id=2791,
            picking_type_id=1,
            payment_provider_id=92,
            dry_run=True,
        )
    finally:
        _restore_escrituracao(original)

    assert res['status'] == 'DRY_RUN_OK'
    assert res['caminho'] == 'A'
    # Em dry-run caminho A executa passos 1-4 (sem passo 2 criar_dfe)
    passos_nomes = [p['passo'] for p in res['passos']]
    assert '1_buscar_dfe' in passos_nomes
    assert '3_escriturar_dfe' in passos_nomes
    assert '4_gerar_po_from_dfe' in passos_nomes
    # Caminho A NAO faz passo 2_criar_dfe
    assert '2_criar_dfe_a_partir_do_invoice_saida' not in passos_nomes


def test_fluxo_l3_caminho_b_cria_dfe_dry_run():
    """Caminho B: DFe ausente + dry_run -> cria DFe via XML SAIDA."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099003',
        'state': 'posted',
    }]
    executor = FaturamentoPipelineExecutor(
        odoo=odoo, picking_svc=MagicMock(),
    )
    original = _patch_buscar_dfe(
        executor, encontrado=False, dfe_id=None, status='ausente',
    )
    try:
        res = executor.executar_fluxo_l3_1_2_x(
            invoice_id_saida=607444,
            company_destino=1,
            l10n_br_tipo_pedido_dfe='retorno',
            l10n_br_tipo_pedido_po='retorno',
            team_id=119,
            payment_term_id=2791,
            picking_type_id=1,
            payment_provider_id=92,
            dry_run=True,
        )
    finally:
        _restore_escrituracao(original)

    assert res['status'] == 'DRY_RUN_OK'
    assert res['caminho'] == 'B'
    # Caminho B inclui passo 2_criar_dfe
    passos_nomes = [p['passo'] for p in res['passos']]
    assert '2_criar_dfe_a_partir_do_invoice_saida' in passos_nomes
    assert res['dfe_id'] == 7777  # mockado


def test_fluxo_l3_invoice_sem_chave_nfe_falha():
    """invoice SAIDA sem chave_nfe -> FALHA antes de buscar_dfe."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_chave_nf': '',  # vazio
        'state': 'posted',
    }]
    executor = FaturamentoPipelineExecutor(
        odoo=odoo, picking_svc=MagicMock(),
    )
    res = executor.executar_fluxo_l3_1_2_x(
        invoice_id_saida=607445,
        company_destino=5,
        l10n_br_tipo_pedido_dfe='compra',
        l10n_br_tipo_pedido_po='serv-industrializacao',
        team_id=119,
        payment_term_id=2791,
        picking_type_id=1,
        payment_provider_id=92,
        dry_run=True,
    )
    assert res['status'] == 'FALHA_PASSO_1_BUSCAR_DFE'
    assert res['erro'] == 'invoice_saida_sem_chave_nfe'
    # Nenhum passo executado
    assert res['passos'] == []
