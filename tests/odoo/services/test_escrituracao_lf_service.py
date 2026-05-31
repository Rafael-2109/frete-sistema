"""Tests para EscrituracaoLfService (Skill 7 v17.5 + DeprecationWarning v20+).

V1 STRICT: SO LF->FB via RecebimentoLfOdooService externo (4562 LOC NAO MEXER).

Testes migrados de tests/odoo/services/test_faturamento_pipeline_orchestrator.py
(testes ETAPA E v17 que viviam no orchestrator — agora testam o atomo Skill 7
diretamente, alinhado com a constituicao §6).

Cobertura:
1. test_dry_run_planeja                 - dry-run reporta planejamento
2. test_skip_ajustes_vazios             - lista vazia -> SKIP
3. test_pre_cond_v1_strict_raise        - cnpj/company fora V1 -> NotImplementedError
4. test_real_run_sucesso_cria_reclf     - cria RecLf + invoca svc externo OK
5. test_idempotencia_processado_skip    - G-RECLF-3: ja processado -> IDEMPOTENT_PROCESSADO
6. test_high3_processando_retoma        - HIGH-3: status='processando' RETOMA
7. test_grecl2_transfer_erro_parcial    - G-RECLF-2: transfer_status='erro' = PARCIAL
8. test_high4_svc_instanciado_fresh     - svc externo eh fresh por invocacao
9. test_invoice_sumiu_odoo              - account.move sumiu -> FALHA
10. test_v20_deprecation_warning        - V20+ wrapper emite DeprecationWarning
"""
import warnings
from unittest.mock import MagicMock, patch

import pytest

from app.odoo.estoque.scripts.escrituracao import (
    CNPJ_LF_DEFAULT,
    COMPANY_ID_FB_DEFAULT,
    EscrituracaoLfService,
)


# ============================================================
# Helpers
# ============================================================

def _ajuste_mock(*, ajuste_id=1, cod_produto='999', acao='PERDA_LF_FB',
                 qtd_ajuste=10.0, lote_destino='MIGRAÇÃO',
                 chave_nfe='35260518467441000163550010000132451007099001'):
    """Mock simples de AjusteEstoqueInventario (atributos como ORM real)."""
    aj = MagicMock()
    aj.id = ajuste_id
    aj.cod_produto = cod_produto
    aj.acao_decidida = acao
    aj.qtd_ajuste = qtd_ajuste
    aj.lote_destino = lote_destino
    aj.chave_nfe = chave_nfe
    return aj


# ============================================================
# 1. Dry-run
# ============================================================

def test_dry_run_planeja():
    """dry_run=True NAO escreve; reporta planejamento."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    aj = _ajuste_mock()
    res = svc.criar_recebimento_orchestrado(
        invoice_id=700001,
        ajustes=[aj],
        ciclo='TEST_v175',
        usuario='test',
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['invoice_id'] == 700001
    assert res['ajustes_count'] == 1
    assert res['cods_distintos'] == ['999']
    assert res['rec_id'] is None
    assert res['odoo_invoice_id_fb'] is None
    assert 'observacao' in res
    assert res['erro'] is None


# ============================================================
# 2. Skip ajustes vazios
# ============================================================

def test_skip_ajustes_vazios():
    """ajustes=[] -> SKIP_AJUSTES_VAZIOS."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.criar_recebimento_orchestrado(
        invoice_id=700001,
        ajustes=[],
        ciclo='TEST_v175',
        usuario='test',
        dry_run=False,  # mesmo em real-run, vazio = skip
    )
    assert res['status'] == 'SKIP_AJUSTES_VAZIOS'
    assert res['rec_id'] is None
    assert res['erro'] is None


# ============================================================
# 3. Pre-cond V1 STRICT
# ============================================================

def test_pre_cond_v1_strict_cnpj_outro_raise():
    """cnpj_emitente != LF default -> NotImplementedError."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    aj = _ajuste_mock()
    with pytest.raises(NotImplementedError, match='V1 STRICT'):
        svc.criar_recebimento_orchestrado(
            invoice_id=700001,
            ajustes=[aj],
            ciclo='TEST_v175',
            usuario='test',
            dry_run=True,
            cnpj_emitente='61.724.241/0001-78',  # FB CNPJ — fora V1
        )


def test_pre_cond_v1_strict_company_outra_raise():
    """company_id_recebedor != FB default -> NotImplementedError."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    aj = _ajuste_mock()
    with pytest.raises(NotImplementedError, match='V1 STRICT'):
        svc.criar_recebimento_orchestrado(
            invoice_id=700001,
            ajustes=[aj],
            ciclo='TEST_v175',
            usuario='test',
            dry_run=True,
            company_id_recebedor=4,  # CD — fora V1
        )


# ============================================================
# 4. Real-run sucesso cria RecLf
# ============================================================

def test_real_run_sucesso_cria_reclf(db):
    """real-run cria RecebimentoLf + invoca svc externo OK."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.recebimento.models import RecebimentoLf

    ciclo_test = 'TEST_v175_S7_REAL_OK'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700020).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700020,
        chave_nfe='35260518467441000163550010000132451007099020',
        lote_destino='MIGRAÇÃO',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{
        'name': 'RETNA/2026/00099',
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099020',
        'l10n_br_numero_nota_fiscal': '99',
        'company_id': [5, 'LF'],
    }]

    svc = EscrituracaoLfService(odoo=odoo)
    svc._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    mock_reclf_svc = MagicMock()
    mock_reclf_svc.processar_recebimento.return_value = {
        'status': 'processado',
        'recebimento_id': 999,
        'odoo_invoice_id': 800020,
        'transfer_status': 'concluido',
    }

    with patch(
        'app.recebimento.services.recebimento_lf_odoo_service.'
        'RecebimentoLfOdooService',
        return_value=mock_reclf_svc,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao._registrar_auditoria',
    ):
        res = svc.criar_recebimento_orchestrado(
            invoice_id=700020,
            ajustes=[aj],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    assert res['status'] == 'CRIADO'
    assert res['rec_id'] is not None
    assert res['odoo_invoice_id_fb'] == 800020
    assert res['transfer_status'] == 'concluido'
    assert res['erro'] is None
    # RecLf foi criado
    rec = RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700020).first()
    assert rec is not None
    assert rec.cnpj_emitente == CNPJ_LF_DEFAULT
    assert rec.company_id == COMPANY_ID_FB_DEFAULT

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700020).delete()
    db.session.commit()


# ============================================================
# 5. Idempotência G-RECLF-3
# ============================================================

def test_idempotencia_processado_skip(db):
    """G-RECLF-3: RecLf ja' em status='processado' -> IDEMPOTENT_PROCESSADO."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.recebimento.models import RecebimentoLf

    ciclo_test = 'TEST_v175_S7_IDEMP'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700030).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700030,
        chave_nfe='35260518467441000163550010000132451007099030',
    )
    db.session.add(aj)
    rec_existente = RecebimentoLf(
        odoo_lf_invoice_id=700030, numero_nf='99',
        chave_nfe='35260518467441000163550010000132451007099030',
        cnpj_emitente=CNPJ_LF_DEFAULT, company_id=COMPANY_ID_FB_DEFAULT,
        status='processado',  # ja' processado
        usuario='test', total_etapas=37,
    )
    db.session.add(rec_existente)
    db.session.commit()

    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)

    with patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ):
        res = svc.criar_recebimento_orchestrado(
            invoice_id=700030,
            ajustes=[aj],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    assert res['status'] == 'IDEMPOTENT_PROCESSADO'
    assert res['rec_id'] == rec_existente.id

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700030).delete()
    db.session.commit()


# ============================================================
# 6. HIGH-3 retomar processando
# ============================================================

def test_high3_processando_retoma(db):
    """HIGH-3 v17: RecLf em status='processando' (crash) -> RETOMADO (nao
    cria duplicado). Service suporta resume via etapa_atual>0."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.recebimento.models import RecebimentoLf

    ciclo_test = 'TEST_v175_S7_HIGH3'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700400).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700400,
        chave_nfe='35260518467441000163550010000132451007099400',
    )
    db.session.add(aj)
    rec_existente = RecebimentoLf(
        odoo_lf_invoice_id=700400, numero_nf='400',
        chave_nfe='35260518467441000163550010000132451007099400',
        cnpj_emitente=CNPJ_LF_DEFAULT, company_id=COMPANY_ID_FB_DEFAULT,
        status='processando',  # crash recovery
        etapa_atual=8,
        usuario='test', total_etapas=37,
    )
    db.session.add(rec_existente)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{
        'name': 'RETNA/2026/00104',
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099400',
        'l10n_br_numero_nota_fiscal': '104',
        'company_id': [5, 'LF'],
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    svc._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    mock_reclf_svc = MagicMock()
    mock_reclf_svc.processar_recebimento.return_value = {
        'status': 'processado',
        'recebimento_id': rec_existente.id,
        'odoo_invoice_id': 800400,
        'transfer_status': 'concluido',
    }

    with patch(
        'app.recebimento.services.recebimento_lf_odoo_service.'
        'RecebimentoLfOdooService',
        return_value=mock_reclf_svc,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao._registrar_auditoria',
    ):
        res = svc.criar_recebimento_orchestrado(
            invoice_id=700400,
            ajustes=[aj],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    assert res['status'] == 'RETOMADO'
    assert res['rec_id'] == rec_existente.id
    # NAO criou duplicado
    n_rec = RecebimentoLf.query.filter_by(
        odoo_lf_invoice_id=700400,
    ).count()
    assert n_rec == 1, f'Duplicado criado: {n_rec} RecLf (esperado 1)'

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700400).delete()
    db.session.commit()


# ============================================================
# 7. G-RECLF-2 transfer parcial
# ============================================================

def test_grecl2_transfer_erro_parcial(db):
    """G-RECLF-2: transfer_status='erro' (FB OK mas FASE 6+7 erro) -> PARCIAL."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.recebimento.models import RecebimentoLf

    ciclo_test = 'TEST_v175_S7_PARCIAL'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700040).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700040,
        chave_nfe='35260518467441000163550010000132451007099040',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{
        'name': 'RETNA/2026/00100',
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099040',
        'l10n_br_numero_nota_fiscal': '100',
        'company_id': [5, 'LF'],
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    svc._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    mock_reclf_svc = MagicMock()
    mock_reclf_svc.processar_recebimento.return_value = {
        'status': 'processado',
        'recebimento_id': 999,
        'odoo_invoice_id': 800040,
        'transfer_status': 'erro',  # FB OK mas FASE 6+7 falhou
    }

    with patch(
        'app.recebimento.services.recebimento_lf_odoo_service.'
        'RecebimentoLfOdooService',
        return_value=mock_reclf_svc,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao._registrar_auditoria',
    ):
        res = svc.criar_recebimento_orchestrado(
            invoice_id=700040,
            ajustes=[aj],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    assert res['status'] == 'PARCIAL'  # G-RECLF-2
    assert res['transfer_status'] == 'erro'
    assert res['odoo_invoice_id_fb'] == 800040

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700040).delete()
    db.session.commit()


# ============================================================
# 8. HIGH-4 svc instanciado fresh
# ============================================================

def test_high4_svc_instanciado_fresh(db):
    """HIGH-4: cada invocacao do atomo instancia RecebimentoLfOdooService
    nova vez (anti-vazamento de estado interno via Redis)."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.recebimento.models import RecebimentoLf

    ciclo_test = 'TEST_v175_S7_HIGH4'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700050).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700050,
        chave_nfe='35260518467441000163550010000132451007099050',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{
        'name': 'RETNA/2026/00200',
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099050',
        'l10n_br_numero_nota_fiscal': '200',
        'company_id': [5, 'LF'],
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    svc._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    mock_reclf_svc = MagicMock()
    mock_reclf_svc.processar_recebimento.return_value = {
        'status': 'processado',
        'odoo_invoice_id': 800050,
        'transfer_status': 'concluido',
    }

    with patch(
        'app.recebimento.services.recebimento_lf_odoo_service.'
        'RecebimentoLfOdooService',
        return_value=mock_reclf_svc,
    ) as mock_cls, patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.escrituracao._registrar_auditoria',
    ):
        svc.criar_recebimento_orchestrado(
            invoice_id=700050,
            ajustes=[aj],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    # HIGH-4: svc externo instanciado pelo menos uma vez por invocacao
    assert mock_cls.call_count >= 1, (
        f'HIGH-4 v17 violado: RecebimentoLfOdooService instanciado '
        f'{mock_cls.call_count}x (esperado >=1)'
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700050).delete()
    db.session.commit()


# ============================================================
# 9. Invoice sumiu Odoo
# ============================================================

def test_ajustes_refetch_vazio_falha(db):
    """F3 v17.5 (Reviewer 1 conf 82): D9 path FALHA — safe_session_get
    retorna None para todos os ajustes (crash + rollback deletou) ->
    status FALHA + erro=ajustes_refetch_vazio."""
    from app.odoo.models import AjusteEstoqueInventario

    ciclo_test = 'TEST_v175_S7_REFETCH_VAZIO'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    # Ajuste mock com id que NUNCA existira no DB ->
    # safe_session_get retorna None
    aj_fantasma = MagicMock()
    aj_fantasma.id = 99999999
    aj_fantasma.cod_produto = '999'
    aj_fantasma.acao_decidida = 'PERDA_LF_FB'
    aj_fantasma.chave_nfe = '35260518467441000163550010000132451007099088'

    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)

    with patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ):
        res = svc.criar_recebimento_orchestrado(
            invoice_id=700088,
            ajustes=[aj_fantasma],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    assert res['status'] == 'FALHA'
    assert res['erro'] == 'ajustes_refetch_vazio'
    assert res['rec_id'] is None
    db.session.commit()


def test_invoice_sumiu_odoo(db):
    """account.move sumiu (.read retorna []) -> FALHA."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.recebimento.models import RecebimentoLf

    ciclo_test = 'TEST_v175_S7_SUMIU'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    RecebimentoLf.query.filter_by(odoo_lf_invoice_id=700099).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700099,
        chave_nfe='35260518467441000163550010000132451007099099',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = []  # sumiu
    svc = EscrituracaoLfService(odoo=odoo)

    with patch(
        'app.odoo.estoque.scripts.escrituracao.commit_resilient',
        return_value=True,
    ):
        res = svc.criar_recebimento_orchestrado(
            invoice_id=700099,
            ajustes=[aj],
            ciclo=ciclo_test,
            usuario='test',
            dry_run=False,
        )

    assert res['status'] == 'FALHA'
    assert res['erro'] == 'invoice_sumiu_odoo'

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


# ============================================================
# v20+ — DeprecationWarning no wrapper V1 STRICT
# ============================================================

def test_v20_deprecation_warning_emitido():
    """v20+ (S5): wrapper V1 STRICT emite DeprecationWarning ao ser
    invocado (mesmo em dry-run). Fim de vida agendado v21+ ou v22+
    apos canary REAL PROD do FLUXO L3 1.2.x validar substituicao via
    executar_fluxo_l3_1_2_x.
    """
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter('always')
        res = svc.criar_recebimento_orchestrado(
            invoice_id=999,
            ajustes=[],  # vazio para sair rapido sem tocar Odoo
            ciclo='TEST_DEPRECATION_V20',
            usuario='test_v20',
            dry_run=True,
        )

    # Pelo menos 1 DeprecationWarning emitido
    dep_warnings = [
        w for w in recorded if issubclass(w.category, DeprecationWarning)
    ]
    assert len(dep_warnings) >= 1, (
        f'Esperado >=1 DeprecationWarning, recebido {len(dep_warnings)}. '
        f'Total warnings: {len(recorded)}.'
    )
    # Mensagem mencionar v20+ + AP1 + FLUXO L3
    msg = str(dep_warnings[0].message)
    assert 'V1 STRICT' in msg
    assert 'v20+' in msg or 'v21+' in msg or 'v22+' in msg
    assert 'executar_fluxo_l3_1_2_x' in msg
    # Atomo ainda funciona (nao quebra fluxo)
    assert res['status'] in ('SKIP_AJUSTES_VAZIOS', 'DRY_RUN_OK', 'FALHA')


def test_registrar_auditoria_escrituracao_nao_passa_etapa_string():
    """G-AUDIT-1 / N21 — 3a (e última) cópia do bug, em
    `escrituracao._registrar_auditoria` (descoberta pelo canary P6 2026-05-29 na
    ETAPA E). A coluna `operacao_odoo_auditoria.etapa` é Integer; os callsites
    passam `fase='F-E'` (string) → psycopg2 InvalidTextRepresentation. A fase vai
    em `pipeline_etapa` (String) + `etapa_descricao` — NUNCA em `etapa`.
    """
    from unittest.mock import patch
    from app.odoo.estoque.scripts import escrituracao

    with patch('app.odoo.models.OperacaoOdooAuditoria') as MockAud:
        escrituracao._registrar_auditoria(
            ajuste_id=180371, ciclo='TEST_CICLO', fase='F-E',
            acao='ESCRITURAR', status='EXECUTADO',
        )
        MockAud.registrar.assert_called_once()
        kwargs = MockAud.registrar.call_args.kwargs
        assert not isinstance(kwargs.get('etapa'), str), (
            f"etapa (Integer) nao pode ser string; recebeu {kwargs.get('etapa')!r}"
        )
        assert kwargs.get('pipeline_etapa') == 'F-E'
        assert 'F-E' in (kwargs.get('etapa_descricao') or '')
