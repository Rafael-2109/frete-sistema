"""Tests para faturamento_pipeline.py (orchestrator C3 macro Skill 8 v15b).

Pipeline A->B->C->D->E->F inter-company. v15b cobre A + B (F5a+F5b+F5c via
atomos Skill 5 v15a) + stubs C/D/E/F (v16/v17).

Cenarios cobertos (15):
1.  _commit_resilient OK na primeira tentativa
2.  _commit_resilient retry SSL com engine.dispose
3.  _resolver_picking_metadata PERDA_LF_FB OK
4.  _resolver_picking_metadata raise em acao desconhecida
5.  _agrupar_em_chunks por cod (max 30)
6.  _agrupar_por_direcao agrupa (co, tipo_op)
7.  _pre_flight_via_subskill_c5 parsea JSON OK
8.  _pre_flight_via_subskill_c5 stdout invalido vira PRE_FLIGHT_ERRO_PARSE
9.  _pre_flight_via_subskill_c5 raises FileNotFoundError sem CLI
10. executar_etapa_a dry-run NOOP retorna DRY_RUN_OK_ETAPA_A_NOOP
11. executar_etapa_a skip nenhum ajuste
12. executar_etapa_b dry-run com 1 ajuste -> invoca atomos Skill 5
13. executar_etapa_b skip nenhum ajuste
14. executar_pipeline_bulk bloqueia em PRE_FLIGHT_BLOQUEADO
15. Stubs C/D/E/F retornam NOT_IMPLEMENTED_v15b (D exige confirmar_sefaz)
"""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.odoo.estoque.orchestrators.faturamento_pipeline import (
    ACAO_PARA_DIRECAO,
    ACOES_PICKING,
    ETAPAS_VALIDAS,
    MAX_CODS_POR_PICKING,
    FaturamentoPipelineExecutor,
    _agrupar_em_chunks,
    _agrupar_por_direcao,
    _commit_resilient,
    _pre_flight_via_subskill_c5,
    _resolver_picking_metadata,
)


# ============================================================
# Helpers de mock
# ============================================================

def _ajuste_mock(
    *,
    ajuste_id=1,
    cod_produto='4310177',
    acao='PERDA_LF_FB',
    qtd_ajuste=10.0,
    lote_origem='LOTE_X',
    company_id=5,
):
    """Mock de AjusteEstoqueInventario com atributos minimos."""
    m = MagicMock()
    m.id = ajuste_id
    m.cod_produto = cod_produto
    m.acao_decidida = acao
    m.qtd_ajuste = qtd_ajuste
    m.qtd_inventario = qtd_ajuste
    m.qtd_odoo = 0.0
    m.lote_origem = lote_origem
    m.lote_destino = None
    m.company_id = company_id
    m.tipo_produto = 1
    m.lote_inventariado = None
    m.lote_odoo = None
    m.custo_medio = None
    m.fase_pipeline = None
    m.picking_id_odoo = None
    m.erro_msg = None
    return m


# ============================================================
# 1-2. _commit_resilient
# ============================================================

def test_commit_resilient_ok_primeira_tentativa(db):
    """Commit OK na primeira tentativa retorna True sem retry.

    Usa fixture `db` (conftest.py) para garantir Flask app_context.
    """
    with patch.object(db.session, 'commit', return_value=None) as mock_commit:
        assert _commit_resilient() is True
        mock_commit.assert_called_once()


def test_commit_resilient_retry_ssl_dispose(db):
    """SSL drop dispara rollback + close + engine.dispose + retry.

    Usa fixture `db` (conftest.py) para Flask app_context.
    """
    err = OperationalError(
        'SELECT ...',
        {},
        Exception('SSL connection has been closed unexpectedly'),
    )
    commit_side = [err, None]  # 1a falha, 2a OK

    with patch.object(db.session, 'commit', side_effect=commit_side) as mc, \
         patch.object(db.session, 'rollback') as mrb, \
         patch.object(db.session, 'close') as mclose, \
         patch.object(db.engine, 'dispose') as mdisp, \
         patch(
             'app.odoo.estoque.orchestrators.faturamento_pipeline.time.sleep'
         ):
        # Patch time.sleep para nao esperar 2s
        assert _commit_resilient() is True
        assert mc.call_count == 2  # 1 falha + 1 sucesso
        mrb.assert_called_once()
        mclose.assert_called_once()
        mdisp.assert_called_once()  # SSL drop detectado


# ============================================================
# 3-4. _resolver_picking_metadata
# ============================================================

def test_resolver_picking_metadata_perda_lf_fb():
    """PERDA_LF_FB resolve corretamente metadados."""
    res = _resolver_picking_metadata('PERDA_LF_FB')
    assert res['tipo_op'] == 'perda'
    assert res['company_origem_id'] == 5  # LF
    assert res['company_destino_id'] == 1  # FB
    assert res['picking_type_id'] == 94  # LF: Expedicao N Aplicado
    assert res['partner_id'] == 1  # FB partner
    assert res['location_origem_id'] == 42  # LF/Estoque
    assert res['location_destino_id'] == 5  # Parceiros (perda)


def test_resolver_picking_metadata_acao_invalida_raise():
    """Acao desconhecida raise ValueError com lista de validas."""
    with pytest.raises(ValueError) as exc_info:
        _resolver_picking_metadata('ACAO_INEXISTENTE')
    assert 'ACAO_INEXISTENTE' in str(exc_info.value)
    assert 'ACAO_PARA_DIRECAO' in str(exc_info.value)


# ============================================================
# 5. _agrupar_em_chunks
# ============================================================

def test_agrupar_em_chunks_max_cods():
    """Chunks tem ate max_cods cods distintos; mesmo cod nunca quebra."""
    # 35 cods distintos com 2 ajustes cada -> 2 chunks (30 + 5)
    ajustes = []
    for i in range(35):
        # 2 ajustes por cod
        ajustes.append(_ajuste_mock(ajuste_id=i * 2, cod_produto=f'COD_{i:03d}'))
        ajustes.append(
            _ajuste_mock(ajuste_id=i * 2 + 1, cod_produto=f'COD_{i:03d}')
        )
    chunks = _agrupar_em_chunks(ajustes, max_cods=MAX_CODS_POR_PICKING)
    assert len(chunks) == 2
    # 1o chunk: 30 cods * 2 ajustes = 60 ajustes
    assert len(chunks[0]) == 60
    # 2o chunk: 5 cods * 2 ajustes = 10 ajustes
    assert len(chunks[1]) == 10
    # Mesmo cod no mesmo chunk (verificar 1o ajuste de COD_000)
    cods_chunk_0 = {a.cod_produto for a in chunks[0]}
    assert len(cods_chunk_0) == 30  # 30 cods distintos no chunk


def test_agrupar_em_chunks_vazio():
    assert _agrupar_em_chunks([]) == []


# ============================================================
# 6. _agrupar_por_direcao
# ============================================================

def test_agrupar_por_direcao_agrupa_por_acao_decidida():
    """CR-C2 v15b: agrupa por acao_decidida (NAO (co, tipo_op)).

    DEV_LF_FB (co=5, cd=1) e DEV_LF_CD (co=5, cd=4) compartilham
    `(5, 'dev-industrializacao')` mas tem partner_id distintos — devem
    ficar em chunks SEPARADOS para nao gerar picking com partner errado.
    """
    a1 = _ajuste_mock(ajuste_id=1, acao='PERDA_LF_FB')
    a2 = _ajuste_mock(ajuste_id=2, acao='PERDA_LF_FB')
    a3 = _ajuste_mock(ajuste_id=3, acao='DEV_LF_FB')   # co=5, cd=1
    a4 = _ajuste_mock(ajuste_id=4, acao='DEV_LF_CD')   # co=5, cd=4 (mesmo tipo_op)
    a5 = _ajuste_mock(ajuste_id=5, acao='INDUSTRIALIZACAO_FB_LF')  # co=1
    grupos = _agrupar_por_direcao([a1, a2, a3, a4, a5])
    assert 'PERDA_LF_FB' in grupos
    assert len(grupos['PERDA_LF_FB']) == 2
    # CR-C2: DEV_LF_FB e DEV_LF_CD em chunks SEPARADOS
    assert 'DEV_LF_FB' in grupos
    assert 'DEV_LF_CD' in grupos
    assert len(grupos['DEV_LF_FB']) == 1
    assert len(grupos['DEV_LF_CD']) == 1
    assert 'INDUSTRIALIZACAO_FB_LF' in grupos


def test_agrupar_por_direcao_acao_invalida_pula():
    """Ajuste com acao_decidida nao mapeada e' pulado (warning)."""
    a1 = _ajuste_mock(ajuste_id=1, acao='PERDA_LF_FB')
    a2 = _ajuste_mock(ajuste_id=2, acao='SEM_ACAO')  # nao em ACAO_PARA_DIRECAO
    grupos = _agrupar_por_direcao([a1, a2])
    # SEM_ACAO pulado, so' PERDA_LF_FB
    assert len(grupos) == 1
    assert 'PERDA_LF_FB' in grupos
    assert len(grupos['PERDA_LF_FB']) == 1


# ============================================================
# Code-review v15b fixes — CR-C1, CR-H4, CR-M3
# ============================================================

def test_executar_etapa_b_carrega_status_filter_default(db):
    """CR-C1 v15b: _carregar_ajustes default filter = ['PROPOSTO', 'APROVADO'].

    Cria 3 ajustes no DB local (PROPOSTO + APROVADO + CANCELADO) e verifica
    que CANCELADO eh excluido da carga.
    """
    from app.odoo.models import AjusteEstoqueInventario
    from app.odoo.estoque.orchestrators.faturamento_pipeline import (
        _carregar_ajustes,
    )

    ciclo_test = 'TEST_CR_C1_STATUS'
    # Cleanup defensivo (caso teste anterior tenha falhado)
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    base = dict(
        ciclo=ciclo_test,
        cod_produto='4310177',
        tipo_produto=1,
        company_id=5,
        qtd_inventario=10,
        qtd_odoo=0,
        qtd_ajuste=10,
        acao_decidida='PERDA_LF_FB',
        fase_pipeline=None,
        criado_por='test',
    )
    for st in ('PROPOSTO', 'APROVADO', 'CANCELADO', 'EXECUTADO'):
        aj = AjusteEstoqueInventario(**base, status=st)
        db.session.add(aj)
    db.session.flush()

    res = _carregar_ajustes(ciclo=ciclo_test)
    statuses = sorted({a.status for a in res})
    assert statuses == ['APROVADO', 'PROPOSTO']  # CANCELADO + EXECUTADO excluidos


def test_executar_pipeline_bulk_etapa_d_bloqueado_etapa_anterior_falhou():
    """CR-H4 v15b: ETAPA D bloqueada se ETAPA B falhou.

    Mock executar_etapa_b para retornar EXCECAO_NAO_TRATADA. ETAPA D nao
    deve executar — retorna BLOQUEADO_ETAPA_ANTERIOR_FALHOU.
    """
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch.object(
        executor, 'executar_etapa_a',
        return_value={'etapa': 'A', 'status': 'SKIP_NENHUM_AJUSTE'},
    ), patch.object(
        executor, 'executar_etapa_b',
        return_value={'etapa': 'B', 'status': 'EXCECAO_NAO_TRATADA',
                      'erro': 'erro mock'},
    ):
        res = executor.executar_pipeline_bulk(
            ciclo='TEST',
            etapas=('A', 'B', 'D'),
            confirmar_sefaz=True,  # mesmo com sefaz, B falhou
            pular_pre_flight=True,
        )
    assert (
        res['etapas_executadas']['D']['status']
        == 'BLOQUEADO_ETAPA_ANTERIOR_FALHOU'
    )
    assert res['status'] == 'DRY_RUN_PARCIAL'  # CR-M3: status agregado falha


def test_executar_pipeline_bulk_d_bloqueado_sefaz_status_agregado_falha():
    """CR-M3 v15b: BLOQUEADO_SEM_CONFIRMAR_SEFAZ conta como falha agregada."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_pipeline_bulk(
        ciclo='TEST',
        etapas=('D',),
        confirmar_sefaz=False,
        pular_pre_flight=True,
    )
    assert (
        res['etapas_executadas']['D']['status']
        == 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'
    )
    # CR-M3 v15b: BLOQUEADO_* conta como falha — status DRY_RUN_PARCIAL
    assert res['status'] == 'DRY_RUN_PARCIAL'


def test_compensatorio_preserva_acao_decidida_origem(db):
    """CR-H2 v15b: compensatorio mantem acao_decidida do origem (nao hardcode).

    Smoke unit-test: verifica que _criar_compensatorios_g_etb preserva
    acao_decidida do ajuste origem.
    """
    from app.odoo.models import AjusteEstoqueInventario

    ciclo_test = 'TEST_CR_H2_COMP'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    origem = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='4310177',
        tipo_produto=1,
        company_id=5,
        qtd_inventario=100,
        qtd_odoo=0,
        qtd_ajuste=100,
        acao_decidida='PERDA_LF_FB',
        status='APROVADO',
        criado_por='test',
    )
    db.session.add(origem)
    db.session.flush()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    # Pendencia que dispara compensatorio
    pendencias = [{
        'product_id': 9999,
        'qty_demand': 100.0,
        'qty_done': 30.0,  # restante 70
    }]
    cods_para_pid = {'4310177': 9999}

    comps = executor._criar_compensatorios_g_etb(
        ajustes_chunk=[origem],
        pendencias=pendencias,
        ciclo=ciclo_test,
        cods_para_pid=cods_para_pid,
        usuario='test',
    )

    assert len(comps) == 1
    novo_id = comps[0]['novo_ajuste_id']
    novo = db.session.get(AjusteEstoqueInventario, novo_id)
    # CR-H2: acao_decidida preservada do origem (NAO hardcode 'INDUSTRIALIZACAO_FB_LF')
    assert novo.acao_decidida == 'PERDA_LF_FB'
    assert novo.qtd_ajuste == 70
    assert '[COMPENSATORIO_FALTA_ESTOQUE]' in novo.erro_msg


def test_carregar_ajustes_intersecao_vazia_retorna_vazio(db):
    """CR-M1 v15b: company_origem + acoes com intersecao vazia retorna []."""
    from app.odoo.models import AjusteEstoqueInventario
    from app.odoo.estoque.orchestrators.faturamento_pipeline import (
        _carregar_ajustes,
    )

    ciclo_test = 'TEST_CR_M1_EMPTY'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='4310177', tipo_produto=1, company_id=5,
        qtd_inventario=10, qtd_odoo=0, qtd_ajuste=10,
        acao_decidida='PERDA_LF_FB', status='PROPOSTO',
        criado_por='test',
    )
    db.session.add(aj)
    db.session.flush()

    # PERDA_LF_FB tem co=5. Filtrar por co=1 + acao=PERDA_LF_FB:
    # intersecao vazia (PERDA_LF_FB nao esta entre as acoes de co=1).
    res = _carregar_ajustes(
        ciclo=ciclo_test,
        company_origem_id=1,
        acoes=['PERDA_LF_FB'],
    )
    assert res == []


# ============================================================
# 7-9. _pre_flight_via_subskill_c5
# ============================================================

def test_pre_flight_subskill_parseia_json_ok(tmp_path):
    """Sub-skill retorna JSON valido -> exit 0 + parseado."""
    # Criar fake CLI script que retorna JSON valido (Python True maiusculo)
    fake_cli = tmp_path / 'auditar.py'
    fake_cli.write_text(
        'import json\n'
        'print(json.dumps({'
        '"status_global":"PRE_FLIGHT_OK",'
        '"pode_faturar":True,'
        '"auditados":6,'
        '"bloqueios":{},'
        '"warnings":{}}))'
    )
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline.'
        'SUB_SKILL_C5_CLI', str(fake_cli),
    ), patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._project_root',
        return_value='/',
    ):
        result = _pre_flight_via_subskill_c5(ciclo='TESTE')
    assert result['status_global'] == 'PRE_FLIGHT_OK'
    assert result['pode_faturar'] is True
    assert result['auditados'] == 6
    assert result['exit_code'] == 0


def test_pre_flight_subskill_stdout_invalido_vira_erro_parse(tmp_path):
    """Sub-skill retorna texto nao-JSON -> PRE_FLIGHT_ERRO_PARSE."""
    fake_cli = tmp_path / 'auditar.py'
    fake_cli.write_text(
        'print("isso nao e JSON")'
    )
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline.'
        'SUB_SKILL_C5_CLI', str(fake_cli),
    ), patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._project_root',
        return_value='/',
    ):
        result = _pre_flight_via_subskill_c5(ciclo='TESTE')
    assert result['status_global'] == 'PRE_FLIGHT_ERRO_PARSE'
    assert result['pode_faturar'] is False
    assert 'erro_parse' in result


def test_pre_flight_subskill_cli_ausente_raise():
    """CLI nao encontrado -> FileNotFoundError actionable."""
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline.'
        'SUB_SKILL_C5_CLI', 'caminho/inexistente.py',
    ), patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._project_root',
        return_value='/',
    ):
        with pytest.raises(FileNotFoundError) as exc_info:
            _pre_flight_via_subskill_c5(ciclo='TESTE')
    assert 'auditando-cadastro-fiscal-odoo' in str(exc_info.value)


# ============================================================
# 10-11. executar_etapa_a
# ============================================================

def test_executar_etapa_a_dry_run_noop():
    """ETAPA A v15b: dry-run com ajustes existentes retorna DRY_RUN_OK_ETAPA_A_NOOP."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    ajustes = [_ajuste_mock(ajuste_id=1)]
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._carregar_ajustes',
        return_value=ajustes,
    ):
        res = executor.executar_etapa_a(ciclo='TESTE')
    assert res['etapa'] == 'A'
    assert res['status'] == 'DRY_RUN_OK_ETAPA_A_NOOP'
    assert res['ajustes_total'] == 1


def test_executar_etapa_a_skip_nenhum_ajuste():
    """ETAPA A sem ajustes retorna SKIP_NENHUM_AJUSTE."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._carregar_ajustes',
        return_value=[],
    ):
        res = executor.executar_etapa_a(ciclo='TESTE')
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'
    assert res['ajustes_total'] == 0


# ============================================================
# 12-13. executar_etapa_b
# ============================================================

def test_executar_etapa_b_dry_run_invoca_atomos_skill5():
    """ETAPA B dry-run NAO invoca atomos Skill 5 (so' planeja).

    Em dry-run, _processar_chunk_etapa_b retorna picking_planejado mas NAO
    chama criar_picking_inter_company nem validar nem liberar.
    """
    odoo = MagicMock()
    # 1 ajuste PERDA_LF_FB com cod resolvivel
    odoo.search_read.return_value = [
        {'id': 9999, 'default_code': '4310177'}
    ]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    ajustes = [_ajuste_mock(
        ajuste_id=1, cod_produto='4310177', acao='PERDA_LF_FB',
        qtd_ajuste=10.0,
    )]
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._carregar_ajustes',
        return_value=ajustes,
    ):
        res = executor.executar_etapa_b(ciclo='TESTE', dry_run=True)
    assert res['etapa'] == 'B'
    assert res['status'] == 'DRY_RUN_OK_ETAPA_B'
    assert res['ajustes_total'] == 1
    assert len(res['pickings_planejados']) == 1
    plano = res['pickings_planejados'][0]
    assert plano['tipo_op'] == 'perda'
    assert plano['company_origem_id'] == 5
    assert plano['company_destino_id'] == 1
    assert plano['n_linhas'] == 1
    # NAO chama atomos em dry-run
    svc.criar_picking_inter_company.assert_not_called()
    svc.validar_picking_inter_company.assert_not_called()
    svc.liberar_faturamento.assert_not_called()


def test_executar_etapa_b_real_invoca_atomos_skill5():
    """ETAPA B real: invoca criar+validar+liberar de Skill 5 em sequencia."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 9999, 'default_code': '4310177'}
    ]
    svc = MagicMock()
    # Mocks dos 3 atomos
    svc.criar_picking_inter_company.return_value = {
        'picking_id': 12345,
        'tracking_none_pids': [],
        'linhas_planejadas': [{'product_id': 9999, 'quantity': 10.0}],
        'tempo_ms': 1500,
    }
    svc.validar_picking_inter_company.return_value = {
        'picking_id': 12345,
        'state_apos_validate': 'done',
        'mls_pendencias': [],
        'g023_aplicado': True,
        'peso_volumes': {'aplicado': True},
        'tempo_ms': 800,
    }
    svc.liberar_faturamento.return_value = None
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    ajuste = _ajuste_mock(
        ajuste_id=1, cod_produto='4310177', acao='PERDA_LF_FB',
        qtd_ajuste=10.0,
    )
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._carregar_ajustes',
        return_value=[ajuste],
    ), patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._registrar_auditoria',
    ), patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline.time.sleep'
    ):
        res = executor.executar_etapa_b(ciclo='TESTE', dry_run=False)
    assert res['status'] == 'EXECUTADO_ETAPA_B'
    assert res['pickings_criados'] == [12345]
    assert res['pickings_validados'] == [12345]
    assert res['pickings_liberados'] == [12345]
    # Atomos invocados na ordem
    svc.criar_picking_inter_company.assert_called_once()
    svc.validar_picking_inter_company.assert_called_once()
    svc.liberar_faturamento.assert_called_once_with(12345)
    # fase_pipeline progrediu F5a -> F5b -> F5c
    assert ajuste.fase_pipeline == 'F5c_LIBERADO'
    assert ajuste.picking_id_odoo == 12345


def test_executar_etapa_b_skip_nenhum_ajuste():
    """ETAPA B sem ajustes -> SKIP."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._carregar_ajustes',
        return_value=[],
    ):
        res = executor.executar_etapa_b(ciclo='TESTE')
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'


# ============================================================
# 14. executar_pipeline_bulk PRE-FLIGHT bloqueia
# ============================================================

def test_executar_pipeline_bulk_pre_flight_bloqueia():
    """PRE-FLIGHT C5 retorna pode_faturar=False -> BLOQUEADO."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch.object(
        executor, 'pre_flight',
        return_value={
            'status_global': 'PRE_FLIGHT_BLOQUEADO',
            'pode_faturar': False,
            'bloqueios': {'ncm_faltando': [9999]},
        },
    ):
        res = executor.executar_pipeline_bulk(ciclo='TESTE')
    assert res['status'] == 'BLOQUEADO_PRE_FLIGHT'
    assert 'ncm_faltando' in res['erro']


def test_executar_pipeline_bulk_pular_pre_flight_executa_etapas():
    """--pular-pre-flight executa etapas direto, mesmo sem sub-skill."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch(
        'app.odoo.estoque.orchestrators.faturamento_pipeline._carregar_ajustes',
        return_value=[],  # sem ajustes -> SKIP
    ):
        res = executor.executar_pipeline_bulk(
            ciclo='TESTE',
            etapas=('A',),  # so' ETAPA A
            pular_pre_flight=True,
        )
    assert res['pre_flight'] is None
    assert 'A' in res['etapas_executadas']
    assert res['etapas_executadas']['A']['status'] == 'SKIP_NENHUM_AJUSTE'


# ============================================================
# 15. Stubs C/D/E/F retornam NOT_IMPLEMENTED_v15b
# ============================================================

def test_etapa_c_stub_not_implemented():
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_c(ciclo='TESTE')
    assert res['status'] == 'NOT_IMPLEMENTED_v15b'
    assert 'v16' in res['roadmap']


def test_etapa_d_sem_confirmar_sefaz_bloqueado():
    """ETAPA D exige --confirmar-sefaz mesmo em stub."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_d(ciclo='TESTE', confirmar_sefaz=False)
    assert res['status'] == 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'
    assert 'IRREVERSIVEL' in res['erro']


def test_etapa_d_com_confirmar_sefaz_stub():
    """ETAPA D com confirmar_sefaz=True ainda retorna NOT_IMPLEMENTED v17."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_d(ciclo='TESTE', confirmar_sefaz=True)
    assert res['status'] == 'NOT_IMPLEMENTED_v15b'
    assert 'v17' in res['roadmap']


def test_etapas_e_f_stubs():
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    assert (
        executor.executar_etapa_e(ciclo='X')['status']
        == 'NOT_IMPLEMENTED_v15b'
    )
    assert (
        executor.executar_etapa_f(ciclo='X')['status']
        == 'NOT_IMPLEMENTED_v15b'
    )


# ============================================================
# Sanity: constantes batem com Skill 5 v15a / pre_etapa_executor
# ============================================================

def test_acoes_picking_tem_8_entradas():
    """ACOES_PICKING == 8 acoes do ACAO_PARA_DIRECAO (D17)."""
    assert len(ACOES_PICKING) == 8
    assert ACOES_PICKING == frozenset(ACAO_PARA_DIRECAO.keys())


def test_etapas_validas_ordem_A_F():
    """ETAPAS_VALIDAS na ordem fixa A->F."""
    assert ETAPAS_VALIDAS == ('A', 'B', 'C', 'D', 'E', 'F')


def test_executar_pipeline_bulk_etapa_invalida_falha_uso():
    """Etapa fora de A-F retorna FALHA_USO."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_pipeline_bulk(
        ciclo='TESTE',
        etapas=('A', 'Z'),  # Z invalida
        pular_pre_flight=True,
    )
    assert res['status'] == 'FALHA_USO'
    assert "['Z']" in res['erro']
