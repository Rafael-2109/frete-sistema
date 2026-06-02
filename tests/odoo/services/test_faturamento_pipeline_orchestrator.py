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

from app.odoo.estoque.orchestrators.inventario_pipeline import (
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
             'app.odoo.estoque.orchestrators.inventario_pipeline.time.sleep'
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
    from app.odoo.estoque.orchestrators.inventario_pipeline import (
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
    """CR-M3 v15b: BLOQUEADO_SEM_CONFIRMAR_SEFAZ conta como falha agregada.

    v17: bloqueio so ocorre em real-run (dry_run=False) sem confirmar_sefaz.
    """
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_pipeline_bulk(
        ciclo='TEST',
        etapas=('D',),
        dry_run=False,           # v17: real-run para acionar guard SEFAZ
        confirmar_sefaz=False,
        pular_pre_flight=True,
    )
    assert (
        res['etapas_executadas']['D']['status']
        == 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'
    )
    # CR-M3: BLOQUEADO_* conta como falha em real-run -> EXECUTADO_PARCIAL.
    assert res['status'] == 'EXECUTADO_PARCIAL'


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
    from app.odoo.estoque.orchestrators.inventario_pipeline import (
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
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        'SUB_SKILL_C5_CLI', str(fake_cli),
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._project_root',
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
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        'SUB_SKILL_C5_CLI', str(fake_cli),
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._project_root',
        return_value='/',
    ):
        result = _pre_flight_via_subskill_c5(ciclo='TESTE')
    assert result['status_global'] == 'PRE_FLIGHT_ERRO_PARSE'
    assert result['pode_faturar'] is False
    assert 'erro_parse' in result


def test_pre_flight_subskill_cli_ausente_raise():
    """CLI nao encontrado -> FileNotFoundError actionable."""
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        'SUB_SKILL_C5_CLI', 'caminho/inexistente.py',
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._project_root',
        return_value='/',
    ):
        with pytest.raises(FileNotFoundError) as exc_info:
            _pre_flight_via_subskill_c5(ciclo='TESTE')
    assert 'auditando-cadastro-fiscal-odoo' in str(exc_info.value)


# ============================================================
# 10-11. executar_etapa_a
# ============================================================

def test_executar_etapa_a_dry_run_noop():
    """ETAPA A v16: dry-run com ajustes ACOES_LOTE retorna DRY_RUN_OK_ETAPA_A."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    # v16: ACOES_LOTE = {RENOMEAR_LOTE, TRANSFERIR_LOTE} (NAO ACOES_PICKING)
    ajustes = [_ajuste_mock(ajuste_id=1, acao='RENOMEAR_LOTE')]
    ajustes[0].lote_destino = 'LOT_NOVO'
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=ajustes,
    ):
        res = executor.executar_etapa_a(ciclo='TESTE')
    assert res['etapa'] == 'A'
    assert res['status'] == 'DRY_RUN_OK_ETAPA_A'  # v16 (sem _NOOP)
    assert res['ajustes_total'] == 1
    assert 'ajustes_planejados' in res  # preview v16


def test_executar_etapa_a_skip_nenhum_ajuste():
    """ETAPA A sem ajustes retorna SKIP_NENHUM_AJUSTE."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
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
    # v16: mockar G014 retornando vazio (testa apenas Skill 5 invocacao)
    executor._g014_pre_check_lotes_vencidos = MagicMock(return_value={
        'lote_novo_por_cod': {}, 'cods_com_lote_vencido': [],
        'transferencias_executadas': [], 'transferencias_planejadas': [],
        'erros': [],
    })
    ajustes = [_ajuste_mock(
        ajuste_id=1, cod_produto='4310177', acao='PERDA_LF_FB',
        qtd_ajuste=10.0,
    )]
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
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
    # v16: mockar G014 retornando vazio (teste foca em F5a/F5b/F5c invocacao)
    executor._g014_pre_check_lotes_vencidos = MagicMock(return_value={
        'lote_novo_por_cod': {}, 'cods_com_lote_vencido': [],
        'transferencias_executadas': [], 'transferencias_planejadas': [],
        'erros': [],
    })
    ajuste = _ajuste_mock(
        ajuste_id=1, cod_produto='4310177', acao='PERDA_LF_FB',
        qtd_ajuste=10.0,
    )
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[ajuste],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._registrar_auditoria',
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.time.sleep'
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
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
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
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
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

def test_etapa_c_v16_dry_run_skip_nenhum_ajuste():
    """ETAPA C v16: dry-run sem ajustes F5c_LIBERADO retorna SKIP_NENHUM_AJUSTE."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[],
    ):
        res = executor.executar_etapa_c(ciclo='TESTE')
    assert res['etapa'] == 'C'
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'
    assert res['ajustes_total'] == 0


def test_etapa_c_v16_dry_run_com_ajustes_planeja():
    """ETAPA C v16: dry-run com ajustes F5c_LIBERADO retorna DRY_RUN_OK_ETAPA_C.

    Em dry-run NAO faz polling — so' reporta pickings_pendentes esperados.
    picking_svc.aguardar_invoice_do_robo NAO chamado.
    """
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj1 = _ajuste_mock(ajuste_id=10, acao='PERDA_LF_FB')
    aj1.picking_id_odoo = 12345
    aj1.fase_pipeline = 'F5c_LIBERADO'
    aj2 = _ajuste_mock(ajuste_id=11, acao='PERDA_LF_FB')
    aj2.picking_id_odoo = 12345  # mesmo picking (2 ajustes)
    aj2.fase_pipeline = 'F5c_LIBERADO'
    aj3 = _ajuste_mock(ajuste_id=12, acao='PERDA_LF_FB')
    aj3.picking_id_odoo = 67890  # picking distinto
    aj3.fase_pipeline = 'F5c_LIBERADO'
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj1, aj2, aj3],
    ):
        res = executor.executar_etapa_c(ciclo='TESTE', dry_run=True)
    assert res['etapa'] == 'C'
    assert res['status'] == 'DRY_RUN_OK_ETAPA_C'
    assert res['ajustes_total'] == 3
    assert res['ajustes_sem_picking'] == 0
    # 2 pickings esperados (12345 com 2 ajustes + 67890 com 1)
    assert sorted(res['pickings_pendentes']) == [12345, 67890]
    # NAO invoca aguardar_invoice_do_robo em dry-run
    svc.aguardar_invoice_do_robo.assert_not_called()


def test_etapa_c_v16_ajustes_sem_picking_id_sao_pulados():
    """ETAPA C v16: ajustes em F5c_LIBERADO sem picking_id_odoo sao filtrados."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj_ok = _ajuste_mock(ajuste_id=10, acao='PERDA_LF_FB')
    aj_ok.picking_id_odoo = 12345
    aj_ok.fase_pipeline = 'F5c_LIBERADO'
    aj_anomalo = _ajuste_mock(ajuste_id=11, acao='PERDA_LF_FB')
    aj_anomalo.picking_id_odoo = None  # anomalia
    aj_anomalo.fase_pipeline = 'F5c_LIBERADO'
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj_ok, aj_anomalo],
    ):
        res = executor.executar_etapa_c(ciclo='TESTE', dry_run=True)
    assert res['ajustes_total'] == 1  # so o aj_ok
    assert res['ajustes_sem_picking'] == 1  # aj_anomalo filtrado
    assert res['pickings_pendentes'] == [12345]


def test_etapa_c_v16_real_resolve_invoice_invoca_sub_etapas():
    """ETAPA C v16 real-run: aguardar_invoice retorna ID + sub-etapas .5/.6/.7
    sao chamadas via helpers em _invoice_helpers.

    Patcha helpers via target em faturamento_pipeline (re-export).
    """
    odoo = MagicMock()
    svc = MagicMock()
    svc.aguardar_invoice_do_robo.return_value = 99999  # invoice resolvida

    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=10, acao='DEV_LF_FB')
    aj.picking_id_odoo = 12345
    aj.fase_pipeline = 'F5c_LIBERADO'

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.safe_session_get',
        return_value=aj,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._registrar_auditoria',
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.garantir_payment_provider',
        return_value=True,
    ) as mock_f5d5, patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.corrigir_price_zero_em_invoice',
        return_value=2,  # 2 linhas corrigidas
    ) as mock_f5d6, patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.garantir_fiscal_setup',
        return_value=True,
    ) as mock_f5d7, patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.time.sleep'
    ):
        res = executor.executar_etapa_c(
            ciclo='TESTE', dry_run=False,
            timeout_polling=10, poll_interval=1,
        )

    assert res['etapa'] == 'C'
    assert res['status'] == 'EXECUTADO_ETAPA_C'
    assert res['pickings_resolvidos'] == {12345: 99999}
    assert res['pickings_timeout'] == []
    # Sub-etapas chamadas 1 vez cada
    mock_f5d5.assert_called_once()
    mock_f5d6.assert_called_once()
    mock_f5d7.assert_called_once()
    # F5d.5 OK + F5d.6 retornou 2 + F5d.7 OK (DEV_LF_FB)
    assert res['sub_etapas']['f5d5_payment_provider_ok'] == 1
    assert res['sub_etapas']['f5d6_price_zero_corrigidas'] == 2
    assert res['sub_etapas']['f5d7_fiscal_setup_ok'] == 1
    # ajuste marcado F5d_INVOICE_GERADA + invoice_id_odoo
    assert aj.fase_pipeline == 'F5d_INVOICE_GERADA'
    assert aj.invoice_id_odoo == 99999
    assert aj.external_id_operacao is not None
    assert aj.external_id_operacao.startswith('INV-TESTE-A000010-F5d_INVOICE_GERADA-')


def test_etapa_c_v16_real_timeout_total_marca_pickings():
    """ETAPA C v16: timeout sem invoice retorna FALHA_TIMEOUT_TOTAL."""
    odoo = MagicMock()
    svc = MagicMock()
    svc.aguardar_invoice_do_robo.return_value = None  # nunca resolve

    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=10, acao='PERDA_LF_FB')
    aj.picking_id_odoo = 12345
    aj.fase_pipeline = 'F5c_LIBERADO'

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.safe_session_get',
        return_value=aj,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._registrar_auditoria',
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.time.sleep'
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.time.time',
        side_effect=[
            0, 0,           # t0 + start_polling
            5, 100,          # check timeout: 5 < 10 (rodada 1), 100 > 10 (sai)
            100, 100, 100, 100, 100, 100, 100, 100,  # demais time.time() calls
        ],
    ):
        res = executor.executar_etapa_c(
            ciclo='TESTE', dry_run=False,
            timeout_polling=10, poll_interval=1,
        )

    assert res['status'] == 'FALHA_TIMEOUT_TOTAL'
    assert res['pickings_resolvidos'] == {}
    assert res['pickings_timeout'] == [12345]


def test_etapa_c_v16_perfil_invalido_retorna_falha_uso():
    """ETAPA C v16: perfil invalido validado ANTES do polling -> FALHA_PERFIL_INVALIDO.

    CR-FIX R1F1 v16 (CRITICAL 95): em vez de propagar NotImplementedError no
    meio do polling (que poisonava session apos primeira invoice resolvida),
    validar perfil ANTES do polling iniciar. Erro retornado como `status` no
    out — fail-fast sem efeitos colaterais.
    """
    odoo = MagicMock()
    svc = MagicMock()
    svc.aguardar_invoice_do_robo.return_value = 99999

    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=10, acao='PERDA_LF_FB')
    aj.picking_id_odoo = 12345
    aj.fase_pipeline = 'F5c_LIBERADO'

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.time.sleep'
    ):
        res = executor.executar_etapa_c(
            ciclo='TESTE', dry_run=False,
            timeout_polling=10, poll_interval=1,
            perfil_invoice_helpers='venda-cliente',  # NAO implementado V1
        )
    assert res['status'] == 'FALHA_PERFIL_INVALIDO'
    assert 'venda-cliente' in res['erro']
    # aguardar_invoice_do_robo NAO chamado (fail-fast antes do polling)
    svc.aguardar_invoice_do_robo.assert_not_called()


def test_etapa_d_real_run_sem_confirmar_sefaz_bloqueado():
    """v17: ETAPA D real-run exige --confirmar-sefaz (D18 2 niveis)."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_d(
        ciclo='TESTE', dry_run=False, confirmar_sefaz=False,
    )
    assert res['status'] == 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'
    assert 'IRREVERSIVEL' in res['erro']


def test_etapa_d_dry_run_sem_ajustes_skip(db):
    """v17: ETAPA D dry-run sem ajustes em F5d_INVOICE_GERADA -> SKIP."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_D_SKIP'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_d(ciclo=ciclo_test, dry_run=True)
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'
    assert res['ajustes_total'] == 0


def test_etapa_e_dry_run_sem_ajustes_skip(db):
    """v17: ETAPA E dry-run sem ajustes F5e_SEFAZ_OK -> SKIP."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_E_SKIP'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_e(ciclo=ciclo_test, dry_run=True)
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'


def test_etapa_f_dry_run_sem_ajustes_skip(db):
    """v17: ETAPA F dry-run sem ajustes F5e_SEFAZ_OK -> SKIP."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_F_SKIP'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=True)
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'


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


# ============================================================
# Code-review v15c fixes — CR-F5, CR-F15, CR-F1 integration
# ============================================================

def test_executar_etapa_a_v16_real_run_invoca_skill2():
    """ETAPA A v16: real-run invoca Skill 2 v2 transferir_quantidade_para_lote_v2.

    Substitui v15c raise NotImplementedError — agora ha implementacao real.
    Ajuste com acao RENOMEAR_LOTE + lote_destino preenchido + Skill 2 mockada.
    """
    odoo = MagicMock()
    odoo.search_read.return_value = [{'id': 999, 'default_code': 'C'}]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(
        ajuste_id=1, cod_produto='C', acao='RENOMEAR_LOTE',
        qtd_ajuste=50.0, lote_origem='LOT_ANTIGO',
    )
    aj.lote_destino = 'LOT_NOVO'
    aj.qtd_inventario = 50.0

    mock_transfer = MagicMock()
    mock_transfer.transferir_quantidade_para_lote_v2.return_value = {
        'status': 'EXECUTADO',
        'lote_destino_nome': 'LOT_NOVO',
        'lote_destino_criado_agora': False,
    }
    mock_lot_svc = MagicMock()
    mock_lot_svc.buscar_por_nome.return_value = 555  # lot_id_origem

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._registrar_auditoria',
    ), patch(
        'app.odoo.estoque.scripts.transfer.StockInternalTransferService',
        return_value=mock_transfer,
    ), patch(
        'app.odoo.services.stock_lot_service.StockLotService',
        return_value=mock_lot_svc,
    ):
        res = executor.executar_etapa_a(ciclo='TESTE', dry_run=False)

    assert res['status'] == 'EXECUTADO_ETAPA_A'
    assert res['ajustes_transferidos'] == 1
    assert res['ajustes_falha'] == []
    assert aj.fase_pipeline == 'TRANSF_OK'
    assert aj.external_id_operacao is not None
    assert aj.external_id_operacao.startswith('INV-TESTE-A000001-TRANSF_OK-')
    # Skill 2 v2 invocada 1 vez
    mock_transfer.transferir_quantidade_para_lote_v2.assert_called_once()
    call_kwargs = mock_transfer.transferir_quantidade_para_lote_v2.call_args.kwargs
    assert call_kwargs['product_id'] == 999
    assert call_kwargs['qty'] == 50.0
    assert call_kwargs['lot_id_origem'] == 555
    assert call_kwargs['nome_lote_destino'] == 'LOT_NOVO'
    assert call_kwargs['dry_run'] is False


def test_executar_etapa_a_v16_skip_ja_transf_ok():
    """ETAPA A v16: ajuste ja em TRANSF_OK eh skipado (idempotencia)."""
    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=2, acao='RENOMEAR_LOTE')
    aj.fase_pipeline = 'TRANSF_OK'  # ja feito
    aj.lote_destino = 'LOT_NOVO'

    # _carregar_ajustes ja' filtra fase NULL/TRANSF_PENDENTE; mas o test
    # quer mockar caso fase venha como TRANSF_OK por race (defensive).
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ):
        res = executor.executar_etapa_a(ciclo='TESTE', dry_run=False)

    assert res['ajustes_skip_ja_ok'] == 1
    assert res['ajustes_transferidos'] == 0


def test_executar_etapa_a_v16_falha_skill2_marca_transf_falha():
    """ETAPA A v16: falha em Skill 2 marca fase=TRANSF_FALHA + erro_msg."""
    odoo = MagicMock()
    odoo.search_read.return_value = [{'id': 999, 'default_code': 'C'}]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(
        ajuste_id=3, cod_produto='C', acao='TRANSFERIR_LOTE',
        qtd_ajuste=10.0, lote_origem='LOT_X',
    )
    aj.lote_destino = 'LOT_Y'
    aj.qtd_inventario = 10.0

    mock_transfer = MagicMock()
    mock_transfer.transferir_quantidade_para_lote_v2.side_effect = (
        RuntimeError('Skill 2 erro: lote destino conflito empresa')
    )
    mock_lot_svc = MagicMock()
    mock_lot_svc.buscar_por_nome.return_value = 777

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._registrar_auditoria',
    ), patch(
        'app.odoo.estoque.scripts.transfer.StockInternalTransferService',
        return_value=mock_transfer,
    ), patch(
        'app.odoo.services.stock_lot_service.StockLotService',
        return_value=mock_lot_svc,
    ):
        res = executor.executar_etapa_a(ciclo='TESTE', dry_run=False)

    assert res['status'] == 'FALHA_TOTAL_ETAPA_A'
    assert res['ajustes_transferidos'] == 0
    assert len(res['ajustes_falha']) == 1
    assert res['ajustes_falha'][0]['ajuste_id'] == 3
    assert 'conflito' in res['ajustes_falha'][0]['erro']
    assert aj.fase_pipeline == 'TRANSF_FALHA'
    assert 'conflito' in (aj.erro_msg or '')


def test_g014_pre_check_sem_lote_vencido_retorna_vazio():
    """G014 v16: cod com saldo livre suficiente em lote valido nao migra."""
    odoo = MagicMock()
    # quant com lote NAO vencido (exp futuro) e qty suficiente
    odoo.search_read.return_value = [
        {'id': 11, 'lot_id': [101, 'LOT_VALIDO'],
         'quantity': 100.0, 'reserved_quantity': 0.0},
    ]
    odoo.read.return_value = [
        {'id': 101, 'expiration_date': '2030-01-01'},  # futuro
    ]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=1, cod_produto='C', qtd_ajuste=50.0)

    res = executor._g014_pre_check_lotes_vencidos(
        ajustes_chunk=[aj],
        cods_para_pid={'C': 999},
        location_origem_id=42,
        dry_run=True,
    )
    assert res['lote_novo_por_cod'] == {}
    assert res['cods_com_lote_vencido'] == []
    assert res['transferencias_planejadas'] == []


def test_g014_pre_check_lote_vencido_dry_run_planeja():
    """G014 v16: lote vencido com saldo livre vira lote_novo planejado em dry-run."""
    odoo = MagicMock()
    # 2 quants: 1 valido + 1 vencido. livre_validos=10 < demand=50
    odoo.search_read.return_value = [
        {'id': 11, 'lot_id': [101, 'LOT_VAL'],
         'quantity': 10.0, 'reserved_quantity': 0.0},
        {'id': 12, 'lot_id': [102, 'LOT_VENC'],
         'quantity': 60.0, 'reserved_quantity': 0.0},
    ]
    # LOT_VAL futuro, LOT_VENC vencido
    odoo.read.return_value = [
        {'id': 101, 'expiration_date': '2030-01-01'},
        {'id': 102, 'expiration_date': '2024-01-01'},  # vencido
    ]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=1, cod_produto='C', qtd_ajuste=50.0)

    res = executor._g014_pre_check_lotes_vencidos(
        ajustes_chunk=[aj],
        cods_para_pid={'C': 999},
        location_origem_id=42,
        dry_run=True,
    )
    assert res['cods_com_lote_vencido'] == ['C']
    assert 'C' in res['lote_novo_por_cod']
    # Nome formato: INV-C-YYYYMMDD
    assert res['lote_novo_por_cod']['C'].startswith('INV-C-')
    assert len(res['transferencias_planejadas']) == 1
    plano = res['transferencias_planejadas'][0]
    assert plano['cod'] == 'C'
    # qty_a_migrar = min(demand - livre_validos, livre_vencidos)
    #              = min(50 - 10, 60) = 40
    assert plano['qty_a_migrar'] == 40.0


def test_g014_pre_check_lote_vencido_real_invoca_skill2():
    """G014 v16 real-run: lote vencido com saldo livre invoca Skill 2 v2."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 11, 'lot_id': [102, 'LOT_VENC'],
         'quantity': 60.0, 'reserved_quantity': 0.0},
    ]
    odoo.read.return_value = [
        {'id': 102, 'expiration_date': '2024-01-01'},  # vencido
    ]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=1, cod_produto='C', qtd_ajuste=30.0)

    mock_transfer = MagicMock()
    mock_transfer.transferir_quantidade_para_lote_v2.return_value = {
        'status': 'EXECUTADO',
    }
    with patch(
        'app.odoo.estoque.scripts.transfer.StockInternalTransferService',
        return_value=mock_transfer,
    ):
        res = executor._g014_pre_check_lotes_vencidos(
            ajustes_chunk=[aj],
            cods_para_pid={'C': 999},
            location_origem_id=42,
            dry_run=False,
        )

    assert res['cods_com_lote_vencido'] == ['C']
    assert 'C' in res['lote_novo_por_cod']
    assert len(res['transferencias_executadas']) == 1
    transf = res['transferencias_executadas'][0]
    assert transf['cod'] == 'C'
    assert transf['qty_migrada'] == 30.0  # min(60, 30) — demand=30
    assert transf['lote_origem_nome'] == 'LOT_VENC'
    # Skill 2 v2 invocada com lot_id_origem=102 + nome_lote_novo
    mock_transfer.transferir_quantidade_para_lote_v2.assert_called_once()
    call_kwargs = mock_transfer.transferir_quantidade_para_lote_v2.call_args.kwargs
    assert call_kwargs['lot_id_origem'] == 102
    assert call_kwargs['qty'] == 30.0
    assert call_kwargs['nome_lote_destino'].startswith('INV-C-')


def test_g014_pre_check_quant_sem_lote_eh_nao_vencido():
    """G014 v16: quant sem lot_id (tracking='none') NAO conta como vencido."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 11, 'lot_id': False,  # sem lote (D-OPS-5)
         'quantity': 100.0, 'reserved_quantity': 0.0},
    ]
    odoo.read.return_value = []
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    aj = _ajuste_mock(ajuste_id=1, cod_produto='C', qtd_ajuste=50.0)

    res = executor._g014_pre_check_lotes_vencidos(
        ajustes_chunk=[aj],
        cods_para_pid={'C': 999},
        location_origem_id=42,
        dry_run=True,
    )
    assert res['cods_com_lote_vencido'] == []
    assert res['lote_novo_por_cod'] == {}


# v28+ cleanup: test_executar_etapa_a_v16_flag_deprecated_noop_funciona
# REMOVIDO junto com o flag `permitir_etapa_a_noop_real` da assinatura de
# `executar_etapa_a` (DEPRECATED v16 ~12 sessoes; zero callers reais).
# Cenario coberto pelo restante dos testes ETAPA A (dry-run + real-run com
# Skill 2 v2). Status `EXECUTADO_ETAPA_A_NOOP_DEPRECATED` removido tambem.


def test_etapa_b_compensatorio_sem_falhas_vira_auto_corrigido(db):
    """CR-F15 v15c (Reviewer A H2 conf 82): se compensatorio criado E
    zero falhas E real-run, status = EXECUTADO_AUTO_CORRIGIDO.
    """
    from app.odoo.models import AjusteEstoqueInventario

    ciclo_test = 'TEST_CR_F15_AUTO'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='C', tipo_produto=1, company_id=5,
        qtd_inventario=100, qtd_odoo=0, qtd_ajuste=100,
        acao_decidida='PERDA_LF_FB', status='PROPOSTO',
        lote_origem='LOT_X',
        criado_por='test',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    # Mock diferenciado por model (idempotencia picking vazia + resolve pid)
    def search_read_side(*args, **kwargs):
        model = args[0] if args else kwargs.get('model')
        if model == 'product.product':
            return [{'id': 999, 'default_code': 'C'}]
        return []  # stock.picking (idempotencia F1): sem existente
    odoo.search_read.side_effect = search_read_side
    odoo.read.return_value = [{'id': 999, 'tracking': 'lot'}]
    odoo.create.return_value = 9999
    svc = MagicMock()
    svc.criar_picking_inter_company.return_value = {
        'picking_id': 9999, 'status': 'CRIADO',
        'tracking_none_pids': [], 'linhas_planejadas': [], 'tempo_ms': 100,
    }
    # F5b retorna pendencia com qty_done < demand -> compensatorio cria
    svc.validar_picking_inter_company.return_value = {
        'picking_id': 9999, 'state_apos_validate': 'done',
        'mls_pendencias': [{'product_id': 999, 'qty_demand': 100.0,
                            'qty_done': 30.0}],
        'g023_aplicado': True, 'peso_volumes': {'aplicado': True},
        'tempo_ms': 50,
    }
    svc.liberar_faturamento.return_value = None

    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    # v16: G014 mock — testa apenas compensatorio (CR-F15)
    executor._g014_pre_check_lotes_vencidos = MagicMock(return_value={
        'lote_novo_por_cod': {}, 'cods_com_lote_vencido': [],
        'transferencias_executadas': [], 'transferencias_planejadas': [],
        'erros': [],
    })
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.time.sleep'
    ):
        res = executor.executar_etapa_b(
            ciclo=ciclo_test, dry_run=False,
        )
    # CR-F15: compensatorio criado + 0 falhas + real-run -> AUTO_CORRIGIDO
    assert res['status'] == 'EXECUTADO_AUTO_CORRIGIDO'
    assert len(res['compensatorios_criados']) == 1
    assert len(res['falhas']) == 0
    # CR-F14: contadores estruturados presentes
    assert 'contadores' in res
    assert res['contadores']['compensatorios_criados'] == 1
    assert res['contadores']['falhas'] == 0


def test_etapa_b_atomo_skill5_idempotent_done_pula_f5b_f5c():
    """CR-F1 v15c integration: se F5a retorna IDEMPOTENT_DONE, orchestrator
    pula F5b/F5c e marca ajustes como F5c_LIBERADO (picking ja' done).
    """
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 9999, 'default_code': 'C'}
    ]
    svc = MagicMock()
    # F1 v15a/c: F5a retorna IDEMPOTENT_DONE (picking ja existia)
    svc.criar_picking_inter_company.return_value = {
        'picking_id': 12345,
        'status': 'IDEMPOTENT_DONE',
        'state': 'done',
        'tracking_none_pids': [],
        'linhas_planejadas': [],
        'tempo_ms': 10,
    }
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    # v16: G014 mock — testa apenas idempotencia F5a
    executor._g014_pre_check_lotes_vencidos = MagicMock(return_value={
        'lote_novo_por_cod': {}, 'cods_com_lote_vencido': [],
        'transferencias_executadas': [], 'transferencias_planejadas': [],
        'erros': [],
    })
    aj = _ajuste_mock(ajuste_id=1, cod_produto='C', acao='PERDA_LF_FB')
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline._carregar_ajustes',
        return_value=[aj],
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_b(ciclo='TESTE', dry_run=False)
    # F5a chamado
    svc.criar_picking_inter_company.assert_called_once()
    # F5b/F5c NAO chamados (IDEMPOTENT_DONE skip)
    svc.validar_picking_inter_company.assert_not_called()
    svc.liberar_faturamento.assert_not_called()
    # Ajuste marcado como F5c_LIBERADO (picking ja' done no Odoo)
    assert aj.fase_pipeline == 'F5c_LIBERADO'
    assert aj.picking_id_odoo == 12345


# ============================================================
# v17 — ETAPA D (F5e SEFAZ Playwright)
# ============================================================


def test_etapa_d_dry_run_com_ajustes_planeja(db):
    """v17: ETAPA D dry-run reporta planejamento (invoices_pendentes)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_D_DRY_PLAN'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='APROVADO',
        fase_pipeline='F5d_INVOICE_GERADA', company_id=5,
        invoice_id_odoo=700001,
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_d(ciclo=ciclo_test, dry_run=True)

    assert res['status'] == 'DRY_RUN_OK_ETAPA_D'
    assert 700001 in res['invoices_pendentes']
    assert res['ajustes_total'] == 1
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_d_real_run_sucesso_sefaz(db):
    """v17: ETAPA D real-run com Playwright mockado sucesso -> F5e_SEFAZ_OK."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_D_REAL_OK'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='APROVADO',
        fase_pipeline='F5d_INVOICE_GERADA', company_id=5,
        invoice_id_odoo=700002,
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    with patch(
        'app.recebimento.services.playwright_nfe_transmissao.'
        'transmitir_nfe_via_playwright',
        return_value={
            'sucesso': True,
            'chave_nf': '35260518467441000163550010000132451007099890',
            'situacao_nf': 'autorizado',
            'inv_name': 'RETNA/2026/00090',
            'tentativa': 1,
        },
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_d(
            ciclo=ciclo_test, dry_run=False, confirmar_sefaz=True,
        )

    assert res['status'] == 'EXECUTADO_ETAPA_D'
    assert res['contadores']['sucesso'] == 1
    assert res['invoices_resolvidas'][700002] == (
        '35260518467441000163550010000132451007099890'
    )

    # Assertions via in-memory (mock _commit_resilient nao comita; identity
    # map garante que safe_session_get retorna a mesma instancia atualizada).
    aj_check = AjusteEstoqueInventario.query.filter_by(
        ciclo=ciclo_test
    ).first()
    assert aj_check.fase_pipeline == 'F5e_SEFAZ_OK'
    assert aj_check.chave_nfe == (
        '35260518467441000163550010000132451007099890'
    )
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_d_hard_fail_config_aborta_batch(db):
    """v17 D7: HARD_FAIL_CONFIG_ERRORS aborta batch (status FALHA_CONFIG)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_D_HARDFAIL'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    for i in range(2):
        aj = AjusteEstoqueInventario(
            ciclo=ciclo_test, cod_produto=f'99{i}', acao_decidida='PERDA_LF_FB',
            qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='APROVADO',
            fase_pipeline='F5d_INVOICE_GERADA', company_id=5,
            invoice_id_odoo=700003 + i,
        )
        db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    with patch(
        'app.recebimento.services.playwright_nfe_transmissao.'
        'transmitir_nfe_via_playwright',
        return_value={
            'sucesso': False,
            'erro': 'playwright_indisponivel',
            'tentativas': 0,
        },
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_d(
            ciclo=ciclo_test, dry_run=False, confirmar_sefaz=True,
        )

    assert res['status'] == 'FALHA_CONFIG'
    assert res['erro_config'] == 'playwright_indisponivel'
    # 1a invoice = falha; 2a invoice NAO foi processada (abort batch)
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_d_idempotencia_persistente_skip(db):
    """v17 D8.3: ajuste ja F5e_SEFAZ_OK -> SKIP (skip_idempotent)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_D_IDEMP_PERSIST'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    # Ajuste em F5d_INVOICE_GERADA mas ja com chave_nfe (re-run pos-crash)
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK',  # ja' transmitida em rodada anterior
        company_id=5,
        invoice_id_odoo=700005,
        chave_nfe='35260518467441000163550010000XXX',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    # _carregar_ajustes filtra por F5d_INVOICE_GERADA — ajuste em F5e nao
    # entra; status SKIP_NENHUM_AJUSTE esperado
    res = executor.executar_etapa_d(ciclo=ciclo_test, dry_run=True)
    assert res['status'] == 'SKIP_NENHUM_AJUSTE'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_d_falha_sefaz_com_cstat(db):
    """v17 MED C-2: SEFAZ falha persiste cstat+xmotivo (campo acionavel)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_D_FALHA_CSTAT'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='APROVADO',
        fase_pipeline='F5d_INVOICE_GERADA', company_id=5,
        invoice_id_odoo=700006,
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    with patch(
        'app.recebimento.services.playwright_nfe_transmissao.'
        'transmitir_nfe_via_playwright',
        return_value={
            'sucesso': False,
            'erro': 'rejeicao_sefaz',
            'tentativas': 3,
            'ultimo_estado': {'cstat': '225', 'xmotivo': 'Falha no Schema XML'},
        },
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_d(
            ciclo=ciclo_test, dry_run=False, confirmar_sefaz=True,
        )

    assert res['status'] == 'FALHA_ETAPA_D'
    assert res['contadores']['falha'] == 1
    aj_check = AjusteEstoqueInventario.query.filter_by(
        ciclo=ciclo_test
    ).first()
    assert aj_check.fase_pipeline == 'F5e_FALHA'
    assert 'cstat=225' in aj_check.erro_msg
    assert 'Falha no Schema XML' in aj_check.erro_msg
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


# ============================================================
# v17 — ETAPA E (RecebimentoLf X->FB)
# ============================================================


def test_etapa_e_dry_run_com_ajustes_planeja(db):
    """v17: ETAPA E dry-run reporta invoices_pendentes filtrados ACOES_ENTRADA_FB."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_E_DRY_PLAN'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    # PERDA_LF_FB elegivel para ETAPA E
    aj1 = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700010,
        chave_nfe='35260518467441000163550010000132451007099001',
    )
    # INDUSTRIALIZACAO_FB_LF NAO elegivel (e' ETAPA F)
    aj2 = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='888', acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700011,
        chave_nfe='35260518467441000163550010000132451007099002',
    )
    db.session.add(aj1)
    db.session.add(aj2)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_e(ciclo=ciclo_test, dry_run=True)

    assert res['status'] == 'DRY_RUN_OK_ETAPA_E'
    assert 700010 in res['invoices_pendentes']
    assert 700011 not in res['invoices_pendentes']  # FB->X descartado
    assert res['ajustes_descartados_fb_x'] == 1
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


# ============================================================
# v17.5 — ETAPA E DELEGA atomo Skill 7 escriturando-odoo
# Testes profundos (G-RECLF-3 idempotencia, HIGH-3 retoma, G-RECLF-2 parcial,
# HIGH-4 svc fresh, invoice sumiu) migrados para
# tests/odoo/services/test_escrituracao_lf_service.py (atomo Skill 7).
# Aqui testamos APENAS a delegacao + mapeamento de status -> contadores.
# ============================================================


def test_etapa_e_v175_delega_atomo_skill7_status_criado(db):
    """v17.5: orchestrator chama EscrituracaoLfService.criar_recebimento_orchestrado
    e mapeia status='CRIADO' para invoices_ok + contador ok."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v175_E_DELEGA_CRIADO'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=5,
        invoice_id_odoo=700020,
        chave_nfe='35260518467441000163550010000132451007099020',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    mock_skill7 = MagicMock()
    mock_skill7.criar_recebimento_orchestrado.return_value = {
        'status': 'CRIADO',
        'rec_id': 555,
        'odoo_invoice_id_fb': 800020,
        'transfer_status': 'concluido',
        'tempo_ms': 100,
        'erro': None,
    }

    with patch(
        'app.odoo.estoque.scripts.escrituracao.EscrituracaoLfService',
        return_value=mock_skill7,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ):
        res = executor.executar_etapa_e(ciclo=ciclo_test, dry_run=False)

    assert res['status'] == 'EXECUTADO_ETAPA_E'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['falha'] == 0
    assert 700020 in res['invoices_ok']
    assert res['invoices_ok'][700020] == 555
    # Atomo Skill 7 invocado com args corretos
    mock_skill7.criar_recebimento_orchestrado.assert_called_once()
    call_kwargs = mock_skill7.criar_recebimento_orchestrado.call_args.kwargs
    assert call_kwargs['invoice_id'] == 700020
    assert call_kwargs['ciclo'] == ciclo_test
    assert call_kwargs['dry_run'] is False

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_e_v175_mapeia_status_idempotent_retomado_parcial(db):
    """v17.5: 3 invoices testam mapeamento de status atomo Skill 7:
    IDEMPOTENT_PROCESSADO -> skip; RETOMADO -> ok+retomado; PARCIAL -> ok+parcial.
    """
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v175_E_DELEGA_MIX'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    # 3 invoices distintos (cada um dispara 1 chamada ao atomo)
    for n, invoice_id in enumerate([700100, 700101, 700102], start=1):
        aj = AjusteEstoqueInventario(
            ciclo=ciclo_test, cod_produto=f'99{n}', acao_decidida='PERDA_LF_FB',
            qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
            tipo_produto=1, criado_por='test', status='EXECUTADO',
            fase_pipeline='F5e_SEFAZ_OK', company_id=5,
            invoice_id_odoo=invoice_id,
            chave_nfe=f'35260518467441000163550010000132451007{invoice_id}',
        )
        db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    mock_skill7 = MagicMock()
    # Cada chamada retorna status diferente (por invoice_id)
    def side_effect(*, invoice_id, **kwargs):
        if invoice_id == 700100:
            return {'status': 'IDEMPOTENT_PROCESSADO', 'rec_id': 100,
                    'odoo_invoice_id_fb': None, 'transfer_status': None,
                    'tempo_ms': 5, 'erro': None}
        if invoice_id == 700101:
            return {'status': 'RETOMADO', 'rec_id': 101,
                    'odoo_invoice_id_fb': 800101, 'transfer_status': 'concluido',
                    'tempo_ms': 50, 'erro': None}
        if invoice_id == 700102:
            return {'status': 'PARCIAL', 'rec_id': 102,
                    'odoo_invoice_id_fb': 800102, 'transfer_status': 'erro',
                    'tempo_ms': 80, 'erro': None}
        raise AssertionError(f'invoice inesperado: {invoice_id}')
    mock_skill7.criar_recebimento_orchestrado.side_effect = side_effect

    with patch(
        'app.odoo.estoque.scripts.escrituracao.EscrituracaoLfService',
        return_value=mock_skill7,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ):
        res = executor.executar_etapa_e(ciclo=ciclo_test, dry_run=False)

    assert res['status'] == 'EXECUTADO_ETAPA_E'
    # IDEMPOTENT_PROCESSADO conta como skip
    assert res['contadores']['skip'] == 1
    assert 700100 in res['invoices_skip']
    # RETOMADO conta como ok + retomado
    assert 700101 in res['invoices_ok']
    assert 700101 in res['invoices_retomados']
    assert res['contadores']['retomado'] == 1
    # PARCIAL conta como ok + parcial_fb_ok_transfer_erro
    assert 700102 in res['invoices_ok']
    assert res['contadores']['parcial_fb_ok_transfer_erro'] == 1
    # ok total = 2 (RETOMADO + PARCIAL)
    assert res['contadores']['ok'] == 2
    assert res['contadores']['falha'] == 0

    # 3 chamadas ao atomo
    assert mock_skill7.criar_recebimento_orchestrado.call_count == 3

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


# ============================================================
# v17 — ETAPA F (atomo Skill 5)
# ============================================================


def test_etapa_f_dry_run_com_ajustes_planeja(db):
    """v17: ETAPA F dry-run reporta invoices_pendentes filtrados ACOES_ENTRADA_DESTINO_MANUAL."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_F_DRY_PLAN'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700050,
        chave_nfe='35260518467441000163550010000132451007099050',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=True)

    assert res['status'] == 'DRY_RUN_OK_ETAPA_F'
    assert 700050 in res['invoices_pendentes']
    assert len(res['planejamento']) == 1
    assert res['planejamento'][0]['acao'] == 'INDUSTRIALIZACAO_FB_LF'
    assert res['planejamento'][0]['destino_label'] == 'LF'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_real_run_sucesso_atomo(db):
    """v17: ETAPA F real-run DELEGA atomo Skill 5; sucesso CRIADO -> F5f_OK."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_F_REAL_OK'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700060,
        chave_nfe='35260518467441000163550010000132451007099060',
        lote_destino='MIGRAÇÃO',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{
        'state': 'posted',
        'l10n_br_situacao_nf': 'autorizado',
    }]
    svc = MagicMock()
    svc.criar_picking_entrada_destino_manual.return_value = {
        'picking_id': 999999,
        'status': 'CRIADO',
        'state': 'done',
        'n_moves': 1,
        'tempo_ms': 500,
    }
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    executor._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=False)

    assert res['status'] == 'EXECUTADO_ETAPA_F'
    assert res['contadores']['ok'] == 1
    assert res['invoices_ok'][700060] == 999999
    # Atomo Skill 5 foi invocado
    svc.criar_picking_entrada_destino_manual.assert_called_once()
    call_kwargs = svc.criar_picking_entrada_destino_manual.call_args.kwargs
    assert call_kwargs['company_destino_id'] == 5  # LF
    assert call_kwargs['picking_type_id'] == 19   # LF Recebimento
    assert 'INV-TEST_v17_F_REAL_OK-ENTRADA-LF-NF700060' == call_kwargs['origin']

    aj_check = AjusteEstoqueInventario.query.filter_by(
        ciclo=ciclo_test
    ).first()
    assert aj_check.fase_pipeline == 'F5f_ENTRADA_OK'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_v175_dev_fb_lf_canary_em_dry_run(db):
    """v17.5: DEV_FB_LF AGORA esta em ACOES_ENTRADA_DESTINO_MANUAL (canary).
    Em dry-run, eh planejado normalmente (flag canary_v175=True).
    """
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v175_F_DEV_FB_LF_DRY'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='DEV_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700070,
        chave_nfe='35260518467441000163550010000132451007099070',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=True)

    # v17.5: DEV_FB_LF agora eh elegivel (canary)
    assert res['status'] == 'DRY_RUN_OK_ETAPA_F'
    assert 700070 in res['invoices_pendentes']
    assert res['invoices_canary_count'] == 1
    assert len(res['planejamento']) == 1
    assert res['planejamento'][0]['acao'] == 'DEV_FB_LF'
    assert res['planejamento'][0]['canary_v175'] is True

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_v175_canary_bloqueado_sem_flag(db):
    """v17.5: real-run de DEV_FB_LF SEM `auto_confirma_direcao_nova=True`
    -> direcao_canary_bloqueada (nao executa atomo)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v175_F_CANARY_BLOQ'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='DEV_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700071,
        chave_nfe='35260518467441000163550010000132451007099071',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ):
        res = executor.executar_etapa_f(
            ciclo=ciclo_test, dry_run=False,
            # auto_confirma_direcao_nova default False
        )

    # DEV_FB_LF eh canary -> bloqueado sem flag
    assert res['contadores']['canary_bloqueado'] == 1
    assert 700071 in res['invoices_canary_bloqueado']
    assert 'direcao_canary_bloqueada' in res['invoices_canary_bloqueado'][700071]
    # Atomo NAO foi invocado (canary bloqueia antes)
    svc.criar_picking_entrada_destino_manual.assert_not_called()
    # Status EXECUTADO_PARCIAL (canary >0 mas sem falhas)
    assert res['status'] == 'EXECUTADO_PARCIAL'

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_v175_canary_habilitado_com_flag(db):
    """v17.5: real-run de TRANSFERIR_FB_CD COM `auto_confirma_direcao_nova=True`
    -> processa normal (atomo invocado com location_origem=6 PT 50 CD=4)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v175_F_CANARY_OK'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='TRANSFERIR_FB_CD',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700072,
        chave_nfe='35260518467441000163550010000132451007099072',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{
        'state': 'posted',
        'l10n_br_situacao_nf': 'autorizado',
    }]
    svc = MagicMock()
    svc.criar_picking_entrada_destino_manual.return_value = {
        'picking_id': 999900,
        'status': 'CRIADO',
        'state': 'done',
        'n_moves': 1,
        'tempo_ms': 100,
    }
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    executor._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_f(
            ciclo=ciclo_test, dry_run=False,
            auto_confirma_direcao_nova=True,
        )

    # TRANSFERIR_FB_CD canary habilitado -> processou
    assert res['status'] == 'EXECUTADO_ETAPA_F'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['canary_bloqueado'] == 0
    assert 700072 in res['invoices_ok']
    # Atomo invocado com args corretos v17.5 (TRANSFERIR_FB_CD)
    svc.criar_picking_entrada_destino_manual.assert_called_once()
    call_kwargs = svc.criar_picking_entrada_destino_manual.call_args.kwargs
    assert call_kwargs['company_destino_id'] == 4   # CD
    assert call_kwargs['location_origem_id'] == 6   # Em Transito Filiais
    assert call_kwargs['location_destino_id'] == 32  # CD/Estoque
    assert call_kwargs['picking_type_id'] == 50      # CD/IN/INTER

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_idempotente_done_skip(db):
    """v17: atomo retorna IDEMPOTENT_DONE -> skip contador + F5f_ENTRADA_OK."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_F_IDEMP_DONE'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700080,
        chave_nfe='35260518467441000163550010000132451007099080',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'posted', 'l10n_br_situacao_nf': 'autorizado'}]
    svc = MagicMock()
    svc.criar_picking_entrada_destino_manual.return_value = {
        'picking_id': 317306,  # PROD validado historico
        'status': 'IDEMPOTENT_DONE',
        'state': 'done',
        'n_moves': 0,
        'tempo_ms': 50,
    }
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    executor._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=False)

    assert res['status'] == 'EXECUTADO_ETAPA_F'
    assert res['contadores']['skip'] == 1
    assert 700080 in res['invoices_skip']
    aj_check = AjusteEstoqueInventario.query.filter_by(
        ciclo=ciclo_test
    ).first()
    assert aj_check.fase_pipeline == 'F5f_ENTRADA_OK'  # idempotente marca fase
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_idempotent_other_investigacao_manual(db):
    """v17: atomo IDEMPOTENT_OTHER (state != done) -> FALHA investigacao."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_F_IDEMP_OTHER'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700090,
        chave_nfe='35260518467441000163550010000132451007099090',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'posted', 'l10n_br_situacao_nf': 'autorizado'}]
    svc = MagicMock()
    svc.criar_picking_entrada_destino_manual.return_value = {
        'picking_id': 999998,
        'status': 'IDEMPOTENT_OTHER',
        'state': 'assigned',  # NOT done — investigacao
        'n_moves': 0,
        'tempo_ms': 80,
    }
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    executor._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=False)

    assert res['status'] == 'FALHA_ETAPA_F'
    assert res['contadores']['falha'] == 1
    assert 700090 in res['invoices_falha']
    assert 'IDEMPOTENT_OTHER' in res['invoices_falha'][700090]
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_invoice_nao_posted_pula(db):
    """v17: invoice state != 'posted' (ex cancel) -> skip + falha."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_F_NAO_POSTED'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0, tipo_produto=1, criado_por='test', status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700100,
        chave_nfe='35260518467441000163550010000132451007099100',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'cancel', 'l10n_br_situacao_nf': 'cancelado'}]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    executor._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=False)

    assert res['status'] == 'FALHA_ETAPA_F'
    assert 'invoice_nao_posted' in res['invoices_falha'][700100]
    svc.criar_picking_entrada_destino_manual.assert_not_called()
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


# ============================================================
# v17 POS-FIXES (code-review 3 reviewers paralelos)
# ============================================================


def test_etapa_d_critical1_commit_pos_playwright_falha(db):
    """CRITICAL-1 v17 (Reviewer 1 conf 95): commit POS-Playwright falha ->
    NAO conta como sucesso; marca FALHA_COMMIT_POS_SEFAZ_OK (SEFAZ ja
    autorizada mas DB nao atualizado — operador investigar)."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_CR1'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999', acao_decidida='PERDA_LF_FB',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test',
        status='APROVADO',
        fase_pipeline='F5d_INVOICE_GERADA', company_id=5,
        invoice_id_odoo=700200,
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)

    # commit_resilient retorna True nos 2 primeiros + False POS-NF
    # Sequencia: pre-loop OK -> pre-NF OK -> pos-NF FAIL
    commit_calls = [True, True, False]

    with patch(
        'app.recebimento.services.playwright_nfe_transmissao.'
        'transmitir_nfe_via_playwright',
        return_value={
            'sucesso': True,
            'chave_nf': '35260518467441000163550010000132451007099200',
            'situacao_nf': 'autorizado',
        },
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        side_effect=lambda: commit_calls.pop(0) if commit_calls else True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_d(
            ciclo=ciclo_test, dry_run=False, confirmar_sefaz=True,
        )

    # SEFAZ deu OK mas commit falhou -> contador FALHA, nao SUCESSO
    assert res['contadores']['falha'] == 1
    assert res['contadores']['sucesso'] == 0
    assert 700200 in res['invoices_falha']
    assert 'FALHA_COMMIT_POS_SEFAZ_OK' in res['invoices_falha'][700200]
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


def test_etapa_f_critical4_situacao_nf_nao_autorizado_pula(db):
    """CRITICAL-4 v17 (Reviewer 3 conf 92): NF cancelada SEFAZ (state ainda
    'posted' no Odoo) -> NAO criar picking de entrada."""
    from app.odoo.models import AjusteEstoqueInventario
    ciclo_test = 'TEST_v17_CR4'
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.flush()

    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='999',
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_ajuste=10.0, qtd_inventario=10.0, qtd_odoo=0.0,
        tipo_produto=1, criado_por='test',
        status='EXECUTADO',
        fase_pipeline='F5e_SEFAZ_OK', company_id=1,
        invoice_id_odoo=700300,
        chave_nfe='35260518467441000163550010000132451007099300',
    )
    db.session.add(aj)
    db.session.commit()

    odoo = MagicMock()
    # State posted MAS SEFAZ cancelada
    odoo.read.return_value = [{
        'state': 'posted',
        'l10n_br_situacao_nf': 'cancelado',
    }]
    svc = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo, picking_svc=svc)
    executor._resolver_pids_em_batch = MagicMock(return_value={'999': 12345})

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_registrar_auditoria',
    ):
        res = executor.executar_etapa_f(ciclo=ciclo_test, dry_run=False)

    # NF SEFAZ-cancelada -> NAO chama atomo Skill 5
    assert res['contadores']['falha'] == 1
    assert 700300 in res['invoices_falha']
    assert 'invoice_nao_autorizado_sefaz' in res['invoices_falha'][700300]
    svc.criar_picking_entrada_destino_manual.assert_not_called()
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()


# test_etapa_e_high3_status_processando_retoma migrado para
# tests/odoo/services/test_escrituracao_lf_service.py::test_high3_processando_retoma
# (atomo Skill 7 — RETOMAR direto sem duplicar). Orchestrator delegado
# valida apenas o mapeamento status='RETOMADO' -> ok+retomado em
# test_etapa_e_v175_mapeia_status_idempotent_retomado_parcial.


# ============================================================
# v18 — Recovery `executar_pipeline_resume` (C14)
# ============================================================

def test_resume_apenas_etapa_invalida_retorna_falha_uso():
    """apenas_etapa='A' nao eh suportada em resume (A nao precisa recovery
    iterativo — Skill 2 ja tem retomada propria via fase_pipeline=TRANSF_OK).
    """
    executor = FaturamentoPipelineExecutor()
    result = executor.executar_pipeline_resume(
        ciclo='TEST_RESUME',
        apenas_etapa='A',
        dry_run=True,
    )
    assert result['status'] == 'FALHA_USO'
    assert result['motivo_parada'] == 'FALHA_USO'
    assert 'invalida' in result['erro']
    assert result['iteracoes_executadas'] == 0


def test_resume_etapa_d_real_sem_confirmar_sefaz_bloqueia():
    """ETAPA D em real-run exige --confirmar-sefaz (IRREVERSIVEL).

    Resume reusa o guard CR-H4 do bulk, mas valida ANTES de invocar para
    evitar loop inutil.
    """
    executor = FaturamentoPipelineExecutor()
    result = executor.executar_pipeline_resume(
        ciclo='TEST_RESUME',
        apenas_etapa='D',
        dry_run=False,
        confirmar_sefaz=False,
    )
    assert result['status'] == 'FALHA_USO'
    assert result['motivo_parada'] == 'FALHA_USO'
    assert 'confirmar-sefaz' in result['erro']


def test_resume_tudo_ok_inicial_quando_nao_ha_pendentes():
    """Contagem inicial 0 -> TUDO_OK_INICIAL sem invocar bulk.

    Util quando operador re-roda recovery por inercia depois que processo
    ja concluiu.
    """
    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_contar_pendentes_por_etapa', return_value=0,
    ), patch.object(executor, 'executar_pipeline_bulk') as mock_bulk:
        result = executor.executar_pipeline_resume(
            ciclo='TEST_RESUME',
            apenas_etapa='D',
            dry_run=True,
        )
    assert result['status'] == 'DRY_RUN_OK'
    assert result['motivo_parada'] == 'TUDO_OK_INICIAL'
    assert result['restantes_iniciais'] == 0
    assert result['iteracoes_executadas'] == 0
    mock_bulk.assert_not_called()


def test_resume_tudo_ok_apos_2_iteracoes():
    """Pendentes 5 -> 2 -> 0 — TUDO_OK na iter 2.

    Bulk invocado 2x; restantes_por_iter tem 2 entradas com tempo_ms e
    status do bulk; ultima_invocacao_bulk preserva ultimo dict.
    """
    executor = FaturamentoPipelineExecutor()
    # Contagem inicial 5, depois 2 (apos iter 1), depois 0 (apos iter 2).
    contagens = [5, 2, 0]
    with patch.object(
        executor, '_contar_pendentes_por_etapa',
        side_effect=lambda **kw: contagens.pop(0),
    ), patch.object(
        executor, 'executar_pipeline_bulk',
        return_value={'status': 'EXECUTADO_OK', 'etapas_executadas': {'D': {}}},
    ) as mock_bulk:
        result = executor.executar_pipeline_resume(
            ciclo='TEST_RESUME',
            apenas_etapa='D',
            dry_run=False,
            confirmar_sefaz=True,
            max_iter=5,
        )
    assert result['status'] == 'EXECUTADO_OK'
    assert result['motivo_parada'] == 'TUDO_OK'
    assert result['iteracoes_executadas'] == 2
    assert result['restantes_iniciais'] == 5
    assert len(result['restantes_por_iter']) == 2
    assert result['restantes_por_iter'][0]['restantes'] == 2
    assert result['restantes_por_iter'][1]['restantes'] == 0
    assert mock_bulk.call_count == 2
    # confirmar_sefaz propagado para bulk
    _, kw = mock_bulk.call_args
    assert kw['confirmar_sefaz'] is True
    assert kw['etapas'] == ('D',)
    assert kw['pular_pre_flight'] is True


def test_resume_stagnation_detector_para_quando_pendentes_nao_diminui():
    """Pendentes 5 -> 5 (mesmo) -> STAGNATION.

    Operador deve investigar (SEFAZ rejeicao, robo CIEL IT travado,
    cadastro fiscal pendente apos pre-flight).
    """
    executor = FaturamentoPipelineExecutor()
    contagens = [5, 5]  # iter 1 retorna 5 (mesmo de prev)
    with patch.object(
        executor, '_contar_pendentes_por_etapa',
        side_effect=lambda **kw: contagens.pop(0),
    ), patch.object(
        executor, 'executar_pipeline_bulk',
        return_value={'status': 'DRY_RUN_OK', 'etapas_executadas': {'E': {}}},
    ):
        result = executor.executar_pipeline_resume(
            ciclo='TEST_RESUME',
            apenas_etapa='E',
            dry_run=True,
            detector_stagnation=True,
            max_iter=5,
        )
    assert result['status'] == 'DRY_RUN_PARCIAL'
    assert result['motivo_parada'] == 'STAGNATION'
    assert result['iteracoes_executadas'] == 1
    assert result['restantes_iniciais'] == 5
    assert result['restantes_por_iter'][0]['restantes'] == 5


def test_resume_max_iter_atingido_sem_zerar_pendentes():
    """Pendentes diminui mas nunca chega a 0 dentro de max_iter -> MAX_ITER.

    Cenario realista: ETAPA E com gargalo no robo CIEL IT (G-RECLF-1) —
    100 invoices podem demorar 50-100h, max_iter=2 nao chega ao fim.
    """
    executor = FaturamentoPipelineExecutor()
    contagens = [10, 7, 5]  # inicial 10, iter1=7, iter2=5
    with patch.object(
        executor, '_contar_pendentes_por_etapa',
        side_effect=lambda **kw: contagens.pop(0),
    ), patch.object(
        executor, 'executar_pipeline_bulk',
        return_value={'status': 'EXECUTADO_OK', 'etapas_executadas': {'E': {}}},
    ) as mock_bulk:
        result = executor.executar_pipeline_resume(
            ciclo='TEST_RESUME',
            apenas_etapa='E',
            dry_run=False,
            max_iter=2,
        )
    assert result['status'] == 'EXECUTADO_PARCIAL'
    assert result['motivo_parada'] == 'MAX_ITER'
    assert result['iteracoes_executadas'] == 2
    assert mock_bulk.call_count == 2


def test_resume_excecao_no_bulk_retorna_parcial_com_motivo_excecao():
    """Excecao no bulk pega no try/except e retorna motivo_parada=EXCECAO.

    Erro preservado em result['erro'] (truncado em 300 chars).
    """
    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_contar_pendentes_por_etapa', return_value=5,
    ), patch.object(
        executor, 'executar_pipeline_bulk',
        side_effect=RuntimeError('XML-RPC connection refused'),
    ):
        result = executor.executar_pipeline_resume(
            ciclo='TEST_RESUME',
            apenas_etapa='C',
            dry_run=True,
            max_iter=3,
        )
    assert result['status'] == 'DRY_RUN_PARCIAL'
    assert result['motivo_parada'] == 'EXCECAO'
    assert result['iteracoes_executadas'] == 1
    assert 'XML-RPC connection refused' in result['erro']


def test_resume_sem_stagnation_continua_ate_max_iter():
    """detector_stagnation=False ignora pendentes iguais, vai ate max_iter.

    Util quando operador sabe que ETAPA D tem timing irregular (Playwright
    SEFAZ pode demorar variavelmente) e quer dar mais chances.
    """
    executor = FaturamentoPipelineExecutor()
    contagens = [5, 5, 5]  # iter 1 e 2 mesmos
    with patch.object(
        executor, '_contar_pendentes_por_etapa',
        side_effect=lambda **kw: contagens.pop(0),
    ), patch.object(
        executor, 'executar_pipeline_bulk',
        return_value={'status': 'DRY_RUN_OK', 'etapas_executadas': {'D': {}}},
    ) as mock_bulk:
        result = executor.executar_pipeline_resume(
            ciclo='TEST_RESUME',
            apenas_etapa='D',
            dry_run=True,
            detector_stagnation=False,
            max_iter=2,
        )
    assert result['motivo_parada'] == 'MAX_ITER'
    assert mock_bulk.call_count == 2


# ============================================================
# v20+ S3 — opt-in `usar_fluxo_l3_v19` (substitui ETAPAS E+F legacy)
# ============================================================

# ============================================================
# v28+ S7 — opt-in `usar_fluxo_l3_v19` na ETAPA E (substitui SKIP legado)
# ============================================================
# Resolução do CR-v27+-Finding2-S4 (Rafael 2026-05-27):
# Helper `_executar_etapa_e_via_fluxo_l3` espelha helper F filtrando
# ACOES_ENTRADA_FB. Destrava 4 acoes (PERDA_LF_FB + TRANSFERIR_CD_FB +
# DEV_LF_FB destino=FB; DEV_CD_LF destino=LF). Substitui retorno
# SKIP_NAO_SUPORTADA_V20_FLUXO_L3 do test_v20_s3_etapa_e_skip_quando_flag_v19
# (legado pre-v28+ S7).


def test_v28_s7_etapa_e_via_fluxo_l3_lf_destino_dry_run(db):
    """v28+ S7: ETAPA E com flag=True + ajuste DEV_CD_LF (destino LF=5)
    invoca `_executar_etapa_e_via_fluxo_l3` que chama `executar_fluxo_l3_1_2_x`
    com constants LF (team STATIC 143 F4 v25+, picking_type LF=19).

    DEV_CD_LF eh a unica acao em ACOES_ENTRADA_FB com destino LF (5).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V28_S7_LF'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='105000007',
        tipo_produto=4,
        company_id=4,  # CD origem
        acao_decidida='DEV_CD_LF',  # destino LF=5
        qtd_inventario=100.0,
        qtd_odoo=0,
        qtd_ajuste=100.0,
        lote_destino='MIGRAÇÃO',
        invoice_id_odoo=700001,
        chave_nfe='35260561724241000178550010000700001006273480',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v28_s7',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'105000007': 11111},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(None, None),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'DRY_RUN_OK',
            'caminho': 'A',
            'dfe_id': None,
            'po_id': None,
            'picking_id': None,
            'invoice_id': None,
            'passos': [],
            'tempo_ms': 50,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_e(
            ciclo=ciclo_test,
            dry_run=True,
            usar_fluxo_l3_v19=True,
        )

    # Cleanup
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert res['status'] == 'DRY_RUN_OK'
    assert res['modo'] == 'fluxo_l3_v19'
    assert res['etapa'] == 'E'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['nao_suportada_v20'] == 0
    assert 700001 in res['invoices_ok']
    # CRUCIAL: chamou executar_fluxo_l3_1_2_x com constants LF (F4 STATIC=143)
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert kwargs['invoice_id_saida'] == 700001
    assert kwargs['company_destino'] == 5  # LF
    assert kwargs['team_id'] == 143  # F4 v25+ STATIC LF
    assert kwargs['picking_type_id'] == 19  # LF Recebimento
    assert kwargs['dry_run'] is True


def test_v28_s7_etapa_e_via_fluxo_l3_fb_destino_dry_run(db):
    """v28+ S7: ETAPA E com flag=True + ajuste TRANSFERIR_CD_FB (destino
    FB=1) invoca helper E + chama executar_fluxo_l3_1_2_x com constants
    FB. G039 dinamico (FB nao tem team STATIC — usa _resolver_team_g039
    para Rafael+FB).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V28_S7_FB'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='208000001',
        tipo_produto=4,
        company_id=4,  # CD origem (TRANSFERIR_CD_FB)
        acao_decidida='TRANSFERIR_CD_FB',  # destino FB=1
        qtd_inventario=50.0,
        qtd_odoo=0,
        qtd_ajuste=50.0,
        lote_destino='AJ-28-05',
        invoice_id_odoo=700002,
        chave_nfe='35260518467441000163550010000132455007099002',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v28_s7',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # G039 dinamico p/ FB (Rafael uid + company=1) — mockar retorno team
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'208000001': 22222},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(155, 'CRIADO'),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'DRY_RUN_OK',
            'caminho': 'A', 'dfe_id': None, 'po_id': None,
            'picking_id': None, 'invoice_id': None,
            'passos': [], 'tempo_ms': 75,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_e(
            ciclo=ciclo_test,
            dry_run=True,
            usar_fluxo_l3_v19=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert res['status'] == 'DRY_RUN_OK'
    assert res['modo'] == 'fluxo_l3_v19'
    assert res['etapa'] == 'E'
    assert res['contadores']['ok'] == 1
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert kwargs['invoice_id_saida'] == 700002
    assert kwargs['company_destino'] == 1  # FB
    assert kwargs['picking_type_id'] == 1  # FB Recebimentos discovery v27+ S4
    assert kwargs['team_id'] == 155  # G039 dinamico (mocked)
    # TRANSFERIR_CD_FB: tipos {dfe: compra, po: transf-filial}
    assert kwargs['l10n_br_tipo_pedido_dfe'] == 'compra'
    assert kwargs['l10n_br_tipo_pedido_po'] == 'transf-filial'
    # lote_destino preservado (nao 'MIGRAÇÃO' nem vazio)
    lotes = kwargs['lotes_data']
    assert len(lotes) == 1
    assert lotes[0]['product_id'] == 22222
    assert lotes[0]['lote_nome'] == 'AJ-28-05'  # preservado da planilha
    assert lotes[0]['quantidade'] == 50.0


def test_v28_s7_etapa_e_via_fluxo_l3_perda_lf_fb_real_run_mockado(db):
    """v28+ S7: ETAPA E real-run PERDA_LF_FB (LF->FB destino FB=1) via
    FLUXO L3 1.2.x. Mock retorna FLUXO_OK; status final = EXECUTADO_OK +
    invoice em invoices_ok.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V28_S7_PERDA'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='309001000',
        tipo_produto=4,
        company_id=5,  # LF origem
        acao_decidida='PERDA_LF_FB',  # destino FB=1
        qtd_inventario=0,
        qtd_odoo=25.0,
        qtd_ajuste=-25.0,  # perda
        lote_destino='LOTE-PERDA-X',
        invoice_id_odoo=700003,
        chave_nfe='35260561724241000178550010000700003007099003',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v28_s7',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'309001000': 33333},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(155, 'CACHE'),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FLUXO_OK', 'caminho': 'B',
            'dfe_id': 50001, 'po_id': 60001, 'picking_id': 70001,
            'invoice_id': 80001, 'passos': [], 'tempo_ms': 2500,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_e(
            ciclo=ciclo_test,
            dry_run=False,
            usar_fluxo_l3_v19=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert res['status'] == 'EXECUTADO_OK'
    assert res['etapa'] == 'E'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['falha'] == 0
    assert 700003 in res['invoices_ok']
    assert res['invoices_ok'][700003]['caminho'] == 'B'
    assert res['invoices_ok'][700003]['invoice_id_destino'] == 80001
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert kwargs['company_destino'] == 1  # FB
    assert kwargs['dry_run'] is False
    # qty_ajuste -25 -> abs(25) preservada
    lotes = kwargs['lotes_data']
    assert len(lotes) == 1
    assert lotes[0]['quantidade'] == 25.0
    assert lotes[0]['lote_nome'] == 'LOTE-PERDA-X'


def test_v28_s7_etapa_e_via_fluxo_l3_dev_cd_lf_real_run_mockado(db):
    """v28+ S7: ETAPA E real-run DEV_CD_LF (CD->LF destino LF=5) via
    FLUXO L3 1.2.x. Tipos PO: dfe='compra' + po='retorno'.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V28_S7_DEV_CD_LF'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='410001000',
        tipo_produto=2,
        company_id=4,  # CD origem
        acao_decidida='DEV_CD_LF',  # destino LF=5
        qtd_inventario=15.0,
        qtd_odoo=0,
        qtd_ajuste=15.0,
        lote_destino='',  # vazio -> INV-{cod}-{HOJE}
        invoice_id_odoo=700004,
        chave_nfe='35260561724241000178550010000700004007099004',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v28_s7',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'410001000': 44444},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(None, None),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FLUXO_OK', 'caminho': 'A',
            'dfe_id': 50002, 'po_id': 60002, 'picking_id': 70002,
            'invoice_id': 80002, 'passos': [], 'tempo_ms': 1850,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_e(
            ciclo=ciclo_test,
            dry_run=False,
            usar_fluxo_l3_v19=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert res['status'] == 'EXECUTADO_OK'
    assert res['contadores']['ok'] == 1
    assert 700004 in res['invoices_ok']
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert kwargs['company_destino'] == 5  # LF (DEV_CD_LF)
    assert kwargs['team_id'] == 143  # F4 v25+ STATIC LF
    # DEV_CD_LF: tipos {dfe: compra, po: retorno}
    assert kwargs['l10n_br_tipo_pedido_dfe'] == 'compra'
    assert kwargs['l10n_br_tipo_pedido_po'] == 'retorno'
    # lote vazio -> 'INV-410001000-{HOJE}'
    lotes = kwargs['lotes_data']
    assert len(lotes) == 1
    assert lotes[0]['lote_nome'].startswith('INV-410001000-')


def test_v28_s7_default_off_preserva_etapa_e_legacy(db):
    """v28+ S7: ETAPA E com flag=False (default) NAO dispatcha helper E —
    preserva 100% comportamento legacy (Skill 7 V1 STRICT
    `criar_recebimento_orchestrado`). Garante zero risco de regressao.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V28_S7_LEGACY'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='309001000',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=0, qtd_odoo=10.0, qtd_ajuste=-10.0,
        lote_destino='LOTE-LEG',
        invoice_id_odoo=700005,
        chave_nfe='35260561724241000178550010000700005007099005',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v28_s7',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # Helper E NUNCA invocado quando flag=False
    with patch.object(
        executor, '_executar_etapa_e_via_fluxo_l3',
    ) as mock_helper_e:
        # Default flag=False -> caminho legacy (dry_run=True usa branch
        # DRY_RUN_OK_ETAPA_E que nao toca EscrituracaoLfService)
        res = executor.executar_etapa_e(
            ciclo=ciclo_test,
            dry_run=True,
            # usar_fluxo_l3_v19=False (default)
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    # CRUCIAL: helper NOVO NAO foi invocado
    mock_helper_e.assert_not_called()
    # Caminho legacy retorna DRY_RUN_OK_ETAPA_E
    assert res['status'] == 'DRY_RUN_OK_ETAPA_E'
    assert res['etapa'] == 'E'
    # 1 invoice esperado (planejamento legacy)
    assert 700005 in res['invoices_pendentes']


def test_v28_s7_etapa_e_via_fluxo_l3_skip_nenhum_ajuste(db):
    """v28+ S7: ETAPA E com flag=True mas zero ajustes elegiveis
    retorna SKIP_NENHUM_AJUSTE (espelha helper F).
    """
    # Sem inserir ajuste — DB limpo

    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_resolver_pids_em_batch', return_value={},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(None, None),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
    ) as mock_fluxo:
        res = executor.executar_etapa_e(
            ciclo='TEST_V28_S7_VAZIO',  # ciclo sem ajustes
            dry_run=True,
            usar_fluxo_l3_v19=True,
        )

    assert res['status'] == 'SKIP_NENHUM_AJUSTE'
    assert res['etapa'] == 'E'
    assert res['ajustes_total'] == 0
    # CRUCIAL: executar_fluxo_l3_1_2_x NAO invocado (sem ajustes)
    mock_fluxo.assert_not_called()


def test_v28_s7_etapa_e_via_fluxo_l3_falha_etapa_e_quando_todos_falham(db):
    """v28+ S7 (CR Finding 2 — paridade vs helper F branch FALHA_ETAPA_F):
    ETAPA E com flag=True + 1 ajuste mas `executar_fluxo_l3_1_2_x`
    retorna status nao-OK -> status agregado=FALHA_ETAPA_E (n_ok==0,
    n_falha>0). Espelha helper F branch `FALHA_ETAPA_F` linha 3656.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V28_S7_FALHA'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='309001000',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=0, qtd_odoo=10.0, qtd_ajuste=-10.0,
        lote_destino='LOTE-FALHA',
        invoice_id_odoo=700006,
        chave_nfe='35260561724241000178550010000700006007099006',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v28_s7',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'309001000': 33333},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(155, 'CACHE'),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FALHA_PASSO_5_PREENCHER_PO',  # erro qualquer
            'caminho': 'A', 'dfe_id': 50001, 'po_id': 60001,
            'picking_id': None, 'invoice_id': None,
            'passos': [], 'tempo_ms': 800,
            'erro': 'mock_erro_passo5_preencher_po_falhou',
        },
    ):
        res = executor.executar_etapa_e(
            ciclo=ciclo_test,
            dry_run=False,
            usar_fluxo_l3_v19=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    # Branch n_ok==0 + n_falha>0 -> FALHA_ETAPA_E
    assert res['status'] == 'FALHA_ETAPA_E'
    assert res['etapa'] == 'E'
    assert res['contadores']['ok'] == 0
    assert res['contadores']['falha'] == 1
    assert 700006 in res['invoices_falha']
    # Erro preservado com prefixo do status do fluxo
    assert 'FALHA_PASSO_5_PREENCHER_PO' in res['invoices_falha'][700006]


def test_v20_s3_etapa_f_via_fluxo_l3_lf_destino(db):
    """v20+ S3: ETAPA F com flag=True + ajuste destino LF (5) invoca
    `_executar_etapa_f_via_fluxo_l3` que chama `executar_fluxo_l3_1_2_x`
    com constants resolvidos (canary validado caso INDUSTRIALIZACAO_FB_LF).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V20_S3_LF'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=1,  # FB origem
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_inventario=168.11,
        qtd_odoo=0,
        qtd_ajuste=168.11,
        lote_destino='MIGRAÇÃO',
        invoice_id_odoo=627348,
        chave_nfe='35260561724241000178550010000944701006273480',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v20_s3',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # F4 v25+: G039 nao e' mais chamado para LF=5 (team STATIC fixo 143);
    # patch defensivo mantido para garantir zero side-effect com Odoo PROD
    # caso ramo G039 seja acionado para outros destinos no futuro.
    # F1 v25+: `_executar_etapa_f_via_fluxo_l3` agora resolve `lotes_data`
    # via `_resolver_pids_em_batch` ANTES de chamar `executar_fluxo_l3_1_2_x`.
    # Patch _resolver_pids_em_batch para evitar conexao Odoo real no teste.
    with patch.object(
        executor, '_resolver_team_g039', return_value=(None, None),
    ), patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'103000011': 12345},  # pid sintetico
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FLUXO_OK',
            'caminho': 'A',
            'dfe_id': 42868,
            'po_id': 42122,
            'picking_id': 320393,
            'invoice_id': 688686,
            'passos': [],
            'tempo_ms': 1190,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_f(
            ciclo=ciclo_test,
            dry_run=False,
            usar_fluxo_l3_v19=True,
        )

    # Cleanup
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert res['status'] == 'EXECUTADO_OK'
    assert res['modo'] == 'fluxo_l3_v19'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['falha'] == 0
    assert res['contadores']['nao_suportada_v20'] == 0
    assert 627348 in res['invoices_ok']
    assert res['invoices_ok'][627348]['caminho'] == 'A'
    # CRUCIAL: chamou executar_fluxo_l3_1_2_x com constants LF
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert kwargs['invoice_id_saida'] == 627348
    assert kwargs['company_destino'] == 5  # LF
    # F1 v25+: lotes_data resolvido a partir do AjusteEstoque
    # ('MIGRAÇÃO' -> 'INV-103000011-{HOJE}', qty=168.11)
    assert 'lotes_data' in kwargs
    lotes = kwargs['lotes_data']
    assert len(lotes) == 1
    assert lotes[0]['product_id'] == 12345
    assert lotes[0]['lote_nome'].startswith('INV-103000011-')
    assert lotes[0]['quantidade'] == 168.11
    # Correcao Rafael 2026-06-02: INDUSTRIALIZACAO_FB_LF usa
    # 'serv-industrializacao' tanto em DFe quanto em PO/Fatura (o 'compra'
    # do F3a era conclusao erronea). Expresso em
    # L10N_BR_TIPO_PEDIDO_POR_ACAO['INDUSTRIALIZACAO_FB_LF'].
    assert kwargs['l10n_br_tipo_pedido_dfe'] == 'serv-industrializacao'
    assert kwargs['l10n_br_tipo_pedido_po'] == 'serv-industrializacao'
    # F4 v25+: team_id fixo 143 (Rafael) para LF — G039 override desligado
    # apenas para destino LF=5. Antes era 41 STATIC + override G039 dinamico.
    assert kwargs['team_id'] == 143
    assert kwargs['payment_term_id'] == 2791
    assert kwargs['picking_type_id'] == 19
    assert kwargs['payment_provider_id'] == 38


def test_v24_1_etapa_f_via_fluxo_l3_filtra_meta_keys_g039_status(db):
    """v24.1+ REGRESSION: `_executar_etapa_f_via_fluxo_l3` deve FILTRAR
    meta-keys prefixadas '_' (ex: '_team_g039_status' adicionado v23+ G039)
    ANTES do splat em `executar_fluxo_l3_1_2_x` (assinatura strict sem
    **kwargs). Sem filtro: `TypeError: unexpected keyword argument
    '_team_g039_status'`.

    Bug descoberto v24+ canary REAL PROD operacao avulsa
    INDUSTRIALIZACAO_FB_LF 37688un cod 210030009 (NF SEFAZ autorizada
    chave 35260561724241000178550010000945741007183640 pendente
    escrituracao por ETAPA F crash em 47ms).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V24_1_FILTRA_META_KEYS'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='210030009',
        tipo_produto=2,  # INSUMO
        company_id=1,
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_inventario=37688.0,
        qtd_odoo=0,
        qtd_ajuste=37688.0,
        lote_destino='AJ-27-05',
        invoice_id_odoo=718364,
        chave_nfe='35260561724241000178550010000945741007183640',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v24_1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # F4 v25+ contexto: para LF=5, G039 esta DESLIGADO (team STATIC=143).
    # Mas o filtro de meta-keys '_' continua sendo defesa generica (futuras
    # direcoes FB/CD podem reintroduzir override G039 ou outras meta-keys).
    # Forcamos artificialmente uma meta-key '_team_g039_status' via patch
    # de `_resolver_constants_fluxo_l3` para validar que continua sendo
    # filtrada antes do splat (regression v24.1+).
    def _fake_resolver_constants(*, acao_decidida, company_destino):
        return {
            'company_destino': 5,
            # INDUSTRIALIZACAO_FB_LF: serv-industrializacao em DFe + PO
            # (correcao Rafael 2026-06-02)
            'l10n_br_tipo_pedido_dfe': 'serv-industrializacao',
            'l10n_br_tipo_pedido_po': 'serv-industrializacao',
            'team_id': 143,
            'payment_term_id': 2791,
            'picking_type_id': 19,
            'payment_provider_id': 38,
            '_team_g039_status': 'OK_EXISTENTE',  # meta-key que DEVE ser filtrada
        }
    with patch.object(
        executor, '_resolver_constants_fluxo_l3',
        side_effect=_fake_resolver_constants,
    ), patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'210030009': 54321},
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FLUXO_OK',
            'caminho': 'B',
            'dfe_id': 99999,
            'po_id': 88888,
            'picking_id': 77777,
            'invoice_id': 66666,
            'passos': [],
            'tempo_ms': 5000,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_f(
            ciclo=ciclo_test,
            dry_run=False,
            usar_fluxo_l3_v19=True,
        )

    # Cleanup
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    # Status FLUXO_OK -> fix funcionou (sem TypeError)
    assert res['status'] == 'EXECUTADO_OK'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['falha'] == 0

    # CRUCIAL: kwargs splatted NAO contem meta-key '_team_g039_status'
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert '_team_g039_status' not in kwargs, (
        "Regression v24.1+: meta-key '_team_g039_status' vazou para o "
        "splat de executar_fluxo_l3_1_2_x (TypeError esperado)."
    )
    # team_id chega corretamente
    assert kwargs['team_id'] == 143
    assert kwargs['invoice_id_saida'] == 718364
    assert kwargs['company_destino'] == 5  # LF


def test_v20_s3_etapa_f_via_fluxo_l3_cd_destino_nao_suportada(db):
    """v20+ S3 — v27+ S4 UPDATE: CD destino agora SUPORTADO (constants
    mapeadas em CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[4] — discovery
    XML-RPC 2026-05-27). Antes (v20-v26) retornava NAO_SUPORTADA_V20;
    agora invoca `executar_fluxo_l3_1_2_x` normalmente com constants
    CD (picking_type_id=13 'Recebimento CD', team_id=None p/ G039
    dinamico). CANDIDATE — pendente canary REAL PROD TRANSFERIR_FB_CD
    para validar paridade vs legacy.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V20_S3_CD'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='999999',
        tipo_produto=4,
        company_id=1,  # FB origem (TRANSFERIR_FB_CD)
        acao_decidida='TRANSFERIR_FB_CD',  # destino CD=4
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        invoice_id_odoo=999999,
        chave_nfe='35260518467441000163550010000132451007099001',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',
        criado_por='test_v20_s3',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # F1 v25+: mock _resolver_pids_em_batch p/ evitar Odoo real
    # v27+ S4: mock _resolver_team_g039 p/ evitar auth real (CD G039 dinamico)
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'999999': 77777},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(150, 'OK_EXISTENTE'),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FLUXO_OK', 'caminho': 'A',
            'dfe_id': 99, 'po_id': 88, 'picking_id': 77,
            'invoice_id': 66, 'passos': [], 'tempo_ms': 100,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_f(
            ciclo=ciclo_test,
            dry_run=False,
            usar_fluxo_l3_v19=True,
        )

    # Cleanup
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    # v27+ S4: CD destino agora SUPORTADO (constants mapeadas)
    assert res['status'] == 'EXECUTADO_OK'
    assert res['modo'] == 'fluxo_l3_v19'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['nao_suportada_v20'] == 0
    assert res['contadores']['falha'] == 0
    assert 999999 in res['invoices_ok']
    # CRUCIAL: chamou executar_fluxo_l3_1_2_x com constants CD
    mock_fluxo.assert_called_once()
    kwargs = mock_fluxo.call_args.kwargs
    assert kwargs['invoice_id_saida'] == 999999
    assert kwargs['company_destino'] == 4  # CD
    assert kwargs['picking_type_id'] == 13  # Recebimento (CD)
    assert kwargs['payment_term_id'] == 2791  # A VISTA
    assert kwargs['payment_provider_id'] == 38  # SEM PAGAMENTO
    # team_id derivado via G039 (mocked retorna 150)
    assert kwargs['team_id'] == 150
    # TRANSFERIR_FB_CD: tipos {dfe: compra, po: transf-filial}
    assert kwargs['l10n_br_tipo_pedido_dfe'] == 'compra'
    assert kwargs['l10n_br_tipo_pedido_po'] == 'transf-filial'


def test_v20_s3_etapa_f_via_fluxo_l3_excecao_continua_proximo(db):
    """v20+ S3 HIGH-1 (code-reviewer 2026-05-26): exception em
    executar_fluxo_l3_1_2_x num invoice NAO aborta loop. Proximo invoice
    eh processado normalmente. Status final EXECUTADO_PARCIAL.

    Caso PROD critico: transient Odoo RPC error em 1 de N invoices nao
    deve abortar a onda inteira.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V20_S3_EXC'
    # 2 invoices INDUSTRIALIZACAO_FB_LF (ambos destino LF=5 suportado)
    aj1 = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='AAA', tipo_produto=4, company_id=1,
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_inventario=10, qtd_odoo=0, qtd_ajuste=10,
        lote_destino='MIGRAÇÃO', invoice_id_odoo=111111,
        chave_nfe='35260561724241000178550010000111111006273480',
        fase_pipeline='F5e_SEFAZ_OK', status='EXECUTADO',
        criado_por='test_v20_s3',
    )
    aj2 = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='BBB', tipo_produto=4, company_id=1,
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_inventario=20, qtd_odoo=0, qtd_ajuste=20,
        lote_destino='MIGRAÇÃO', invoice_id_odoo=222222,
        chave_nfe='35260561724241000178550010000222222006273480',
        fase_pipeline='F5e_SEFAZ_OK', status='EXECUTADO',
        criado_por='test_v20_s3',
    )
    db.session.add_all([aj1, aj2])
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # 1o invoice raise; 2o retorna FLUXO_OK
    side_effects = [
        RuntimeError('odoo_rpc_timeout_transient'),
        {
            'status': 'FLUXO_OK', 'caminho': 'A',
            'dfe_id': 999, 'po_id': 888, 'picking_id': 777,
            'invoice_id': 666, 'passos': [], 'tempo_ms': 100,
        },
    ]
    # F1 v25+: mock _resolver_pids_em_batch p/ evitar Odoo real
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'AAA': 100, 'BBB': 200},
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        side_effect=side_effects,
    ) as mock_fluxo:
        res = executor.executar_etapa_f(
            ciclo=ciclo_test, dry_run=False, usar_fluxo_l3_v19=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    # CRUCIAL: loop continuou apos exception no 1o
    assert mock_fluxo.call_count == 2
    # Status PARCIAL (1 ok + 1 falha)
    assert res['status'] == 'EXECUTADO_PARCIAL'
    assert res['contadores']['ok'] == 1
    assert res['contadores']['falha'] == 1
    # invoice que falhou registrado em invoices_falha
    assert 111111 in res['invoices_falha']
    assert 'odoo_rpc_timeout_transient' in res['invoices_falha'][111111]
    # invoice OK registrado em invoices_ok
    assert 222222 in res['invoices_ok']


def test_v20_s3_etapa_f_via_fluxo_l3_misto_lf_e_cd_destino(db):
    """v20+ S3 — v27+ S4 UPDATE: onda mista LF + CD ambos SUPORTADOS
    (CD destino mapeado em v27+ S4). Antes (v20-v26) este teste validava
    LF OK + CD NAO_SUPORTADA = EXECUTADO_PARCIAL. Agora ambos passam
    pelo fluxo L3 = EXECUTADO_OK.

    Topologia PROD esperada quando canary REAL PROD validar CD destino
    (TRANSFERIR_FB_CD ou DEV_LF_CD). v27+ S4 expandiu constants CD;
    teste valida que dispatch agora roteia ambos via fluxo L3.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V20_S3_MISTO'
    aj_lf = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='LF1', tipo_produto=4, company_id=1,
        acao_decidida='INDUSTRIALIZACAO_FB_LF',  # destino LF=5 (SUPORTADO)
        qtd_inventario=10, qtd_odoo=0, qtd_ajuste=10,
        lote_destino='MIGRAÇÃO', invoice_id_odoo=333333,
        chave_nfe='35260561724241000178550010000333333006273480',
        fase_pipeline='F5e_SEFAZ_OK', status='EXECUTADO',
        criado_por='test_v20_s3',
    )
    aj_cd = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='CD1', tipo_produto=4, company_id=1,
        acao_decidida='TRANSFERIR_FB_CD',  # destino CD=4 (NAO SUPORTADO)
        qtd_inventario=20, qtd_odoo=0, qtd_ajuste=20,
        lote_destino='MIGRAÇÃO', invoice_id_odoo=444444,
        chave_nfe='35260561724241000178550010000444444006273480',
        fase_pipeline='F5e_SEFAZ_OK', status='EXECUTADO',
        criado_por='test_v20_s3',
    )
    db.session.add_all([aj_lf, aj_cd])
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # F1 v25+: mock _resolver_pids_em_batch p/ evitar Odoo real
    # v27+ S4: mock _resolver_team_g039 p/ CD G039 dinamico (LF tem STATIC=143)
    with patch.object(
        executor, '_resolver_pids_em_batch',
        return_value={'LF1': 555, 'CD1': 666},
    ), patch.object(
        executor, '_resolver_team_g039', return_value=(150, 'OK_EXISTENTE'),
    ), patch.object(
        executor, 'executar_fluxo_l3_1_2_x',
        return_value={
            'status': 'FLUXO_OK', 'caminho': 'A',
            'dfe_id': 333, 'po_id': 222, 'picking_id': 111,
            'invoice_id': 100, 'passos': [], 'tempo_ms': 100,
        },
    ) as mock_fluxo:
        res = executor.executar_etapa_f(
            ciclo=ciclo_test, dry_run=False, usar_fluxo_l3_v19=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    # v27+ S4: LF e CD ambos chamam executar_fluxo_l3_1_2_x
    assert mock_fluxo.call_count == 2
    # Status OK: ambos OK (sem nao_suportada_v20 nem falha)
    assert res['status'] == 'EXECUTADO_OK'
    assert res['contadores']['ok'] == 2
    assert res['contadores']['nao_suportada_v20'] == 0
    assert res['contadores']['falha'] == 0
    assert 333333 in res['invoices_ok']
    assert 444444 in res['invoices_ok']
    # Validar que cada invoice foi com company_destino correto
    call_kwargs = [c.kwargs for c in mock_fluxo.call_args_list]
    destinations = sorted(kw['company_destino'] for kw in call_kwargs)
    assert destinations == [4, 5]  # CD + LF


# ============================================================
# v23+ G039 — _resolver_team_g039 + _resolver_constants_fluxo_l3 hook
# ============================================================

def test_resolver_team_g039_cache_hit():
    """Segunda chamada com mesma (uid, company) usa cache (sem Odoo call)."""
    odoo = MagicMock()
    odoo._uid = 42  # Rafael
    executor = FaturamentoPipelineExecutor(odoo=odoo)
    # Pre-popula cache
    executor._g039_team_cache = {(42, 5): 143}

    team_id, status = executor._resolver_team_g039(company_id=5)

    assert team_id == 143
    assert status == 'CACHE'
    # Sem nova chamada Odoo
    assert not odoo.execute_kw.called


def test_resolver_team_g039_cache_miss_chama_garantir():
    """Cache vazio -> chama garantir_purchase_team via Skill 7 service."""
    odoo = MagicMock()
    odoo._uid = 42
    # search_read retorna team existente -> OK_EXISTENTE
    odoo.execute_kw.return_value = [{
        'id': 143, 'name': 'Aprovação LF - RAFAEL',
        'user_id': [42, 'Rafael'], 'company_id': [5, 'LF'],
        'active': True,
    }]
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    team_id, status = executor._resolver_team_g039(company_id=5)

    assert team_id == 143
    assert status == 'OK_EXISTENTE'
    # Cache populado para proxima chamada
    assert executor._g039_team_cache == {(42, 5): 143}


def test_resolver_team_g039_falha_garantir_retorna_none():
    """garantir_purchase_team FALHA -> retorna (None, None) p/ fallback."""
    odoo = MagicMock()
    odoo._uid = 42
    odoo.execute_kw.side_effect = Exception('Odoo down')
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    team_id, status = executor._resolver_team_g039(company_id=5)

    assert team_id is None
    assert status is None
    # Cache NAO populado em falha
    assert (42, 5) not in executor._g039_team_cache


def test_resolver_team_g039_uid_zero_retorna_none():
    """uid=0 (auth nao feita) -> tenta authenticate; se falha, fallback."""
    odoo = MagicMock()
    odoo._uid = 0  # nao autenticado
    odoo.authenticate.return_value = False  # auth falha
    # apos authenticate, _uid permanece 0
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    team_id, status = executor._resolver_team_g039(company_id=5)

    # uid invalido apos auth -> None
    assert team_id is None
    assert status is None


def test_resolver_constants_fluxo_l3_lf_team_fixo_143_g039_desligado():
    """F4 v25+ (Rafael 2026-05-27): team_id FIXO 143 para LF=5 + G039 hook
    DESLIGADO neste destino. Antes (v23+): STATIC=41 + override G039 dinamico.
    Decisao explicita pos-cirurgia AVULSO_FRASCO — todas as POs LF inter-
    company desta skill devem nascer com team=143 (Rafael)."""
    odoo = MagicMock()
    odoo._uid = 42
    # G039 search_read retornaria team — mas G039 NAO deve ser chamado para LF
    odoo.execute_kw.return_value = [{
        'id': 999, 'name': 'fake_team_nao_deve_ser_usado',
        'user_id': [42, 'Rafael'], 'company_id': [5, 'LF'],
        'active': True,
    }]
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    constants = executor._resolver_constants_fluxo_l3(
        acao_decidida='INDUSTRIALIZACAO_FB_LF', company_destino=5,
    )

    assert constants is not None
    # F4: team_id FIXO 143 STATIC (nao override G039)
    assert constants['team_id'] == 143
    # F4: G039 hook NAO chamado para LF -> sem marcador _team_g039_status
    assert '_team_g039_status' not in constants
    # outros constants preservados
    assert constants['payment_term_id'] == 2791
    assert constants['picking_type_id'] == 19
    assert constants['payment_provider_id'] == 38
    # Correcao Rafael 2026-06-02: INDUSTRIALIZACAO_FB_LF usa
    # 'serv-industrializacao' em DFe e PO (o 'compra' do F3a era erro).
    assert constants['l10n_br_tipo_pedido_dfe'] == 'serv-industrializacao'
    assert constants['l10n_br_tipo_pedido_po'] == 'serv-industrializacao'
    # G039 search NAO foi chamado (LF by-pass)
    assert not odoo.execute_kw.called


def test_resolver_constants_fluxo_l3_lf_team_fixo_imune_a_g039_falha():
    """F4 v25+: Odoo down -> team_id LF continua 143 (FIXO STATIC, sem
    dependencia de G039)."""
    odoo = MagicMock()
    odoo._uid = 42
    odoo.execute_kw.side_effect = Exception('Connection refused')
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    constants = executor._resolver_constants_fluxo_l3(
        acao_decidida='INDUSTRIALIZACAO_FB_LF', company_destino=5,
    )

    assert constants is not None
    # team_id STATIC 143 (FIXO F4); imune a falha G039 porque G039 nao roda
    assert constants['team_id'] == 143
    assert '_team_g039_status' not in constants


def test_resolver_constants_fluxo_l3_acao_nao_suportada_retorna_none():
    """Pre-existente: acao nao mapeada -> None (sem chamar hook G039)."""
    odoo = MagicMock()
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    constants = executor._resolver_constants_fluxo_l3(
        acao_decidida='ACAO_INEXISTENTE', company_destino=5,
    )

    assert constants is None
    # Hook G039 NAO chamado quando direcao nao suportada (early return)
    assert not odoo.execute_kw.called


# ============================================================
# v23+ S2 — _contar_pendentes_por_etapa fix status='EXECUTADO' ETAPA F
# ============================================================

def test_contar_pendentes_por_etapa_f_aceita_status_executado(db):
    """v23+ S2: ETAPA F conta ajustes status='EXECUTADO' + fase=F5e_SEFAZ_OK.

    Sem este fix, contador retornava 0 para ajustes pos-SEFAZ pendentes
    de criar invoice de ENTRADA (passo 9 FLUXO L3 1.2.x). Workaround
    manual `UPDATE status='APROVADO'` era necessario antes do retry F.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V23_S2_F_EXECUTADO'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='100000001',
        tipo_produto=4,
        company_id=1,  # FB origem
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        invoice_id_odoo=999999,
        chave_nfe='35260561724241000178550010000999999007099001',
        fase_pipeline='F5e_SEFAZ_OK',
        status='EXECUTADO',  # v23+ S2: deveria contar mesmo com EXECUTADO
        criado_por='test_v23_s2',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    count = executor._contar_pendentes_por_etapa(
        etapa='F', ciclo=ciclo_test,
    )

    # Cleanup
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert count == 1, (
        f'Esperado 1 pendente F com status=EXECUTADO, recebi {count}. '
        f'v23+ S2 fix raiz NAO aplicado.'
    )


def test_contar_pendentes_por_etapa_b_nao_aceita_status_executado(db):
    """v23+ S2: ETAPA B NAO conta ajustes status='EXECUTADO' (sem regressao).

    Apenas ETAPA F aceita EXECUTADO; demais etapas mantem PROPOSTO/APROVADO
    porque status nao deveria avancar para EXECUTADO antes do SEFAZ-OK.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V23_S2_B_EXECUTADO'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='100000002',
        tipo_produto=4,
        company_id=1,
        acao_decidida='INDUSTRIALIZACAO_FB_LF',  # ACOES_PICKING (B/C/D)
        qtd_inventario=5.0,
        qtd_odoo=0,
        qtd_ajuste=5.0,
        lote_destino='MIGRAÇÃO',
        fase_pipeline=None,  # B = fase nao-terminal (inclui None)
        status='EXECUTADO',  # nao deveria contar em B
        criado_por='test_v23_s2',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    count_b = executor._contar_pendentes_por_etapa(
        etapa='B', ciclo=ciclo_test,
    )

    # Cleanup
    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert count_b == 0, (
        f'Esperado 0 pendentes B com status=EXECUTADO (status invalido '
        f'para B), recebi {count_b}. Regressao S2: filtro ampliado '
        f'vazando para etapas B/C/D/E.'
    )


def test_contar_pendentes_por_etapa_f_status_aprovado_ainda_conta(db):
    """v23+ S2: regressao check — ETAPA F com status='APROVADO' ainda
    conta (comportamento legacy preservado).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V23_S2_F_APROVADO'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='100000003',
        tipo_produto=4,
        company_id=1,
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        qtd_inventario=8.0,
        qtd_odoo=0,
        qtd_ajuste=8.0,
        lote_destino='MIGRAÇÃO',
        invoice_id_odoo=888888,
        chave_nfe='35260561724241000178550010000888888007099001',
        fase_pipeline='F5e_SEFAZ_OK',
        status='APROVADO',  # legacy: ainda deve contar
        criado_por='test_v23_s2',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    count = executor._contar_pendentes_por_etapa(
        etapa='F', ciclo=ciclo_test,
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    assert count == 1, (
        f'Esperado 1 pendente F com status=APROVADO (legacy), recebi '
        f'{count}. Regressao S2: removeu compatibilidade APROVADO.'
    )


# ============================================================
# v25+ S1 — opt-in `usar_skill8_atomica_v25` (substitui ETAPAs C+D legacy)
# ============================================================

def test_v25_s1_etapa_c_via_skill8_dispatch_dry_run(db):
    """v25+ S1: ETAPA C com `usar_skill8_atomica_v25=True` em dry-run invoca
    `_executar_etapa_c_via_skill8_atomica` (helper novo) em vez de
    `executar_etapa_c` legacy. Validacao via campo `modo` no output.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_C_DRY'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        picking_id_odoo=999001,
        fase_pipeline='F5c_LIBERADO',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    res = executor.executar_pipeline_bulk(
        ciclo=ciclo_test,
        etapas=('C',),
        dry_run=True,
        pular_pre_flight=True,
        usar_skill8_atomica_v25=True,
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_c = res['etapas_executadas']['C']
    assert etapa_c['modo'] == 'skill8_atomica_v25', (
        f'flag=True deveria invocar helper v25+, mas modo={etapa_c.get("modo")!r}'
    )
    assert etapa_c['status'] == 'DRY_RUN_OK_ETAPA_C'
    assert etapa_c['etapa'] == 'C'
    assert etapa_c['ajustes_total'] == 1
    assert etapa_c['pickings_pendentes'] == [999001]


def test_v25_s1_etapa_d_via_skill8_dispatch_dry_run(db):
    """v25+ S1: ETAPA D com `usar_skill8_atomica_v25=True` em dry-run invoca
    `_executar_etapa_d_via_skill8_atomica` (helper novo).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_D_DRY'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        picking_id_odoo=999002,
        invoice_id_odoo=888001,
        fase_pipeline='F5d_INVOICE_GERADA',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    res = executor.executar_pipeline_bulk(
        ciclo=ciclo_test,
        etapas=('D',),
        dry_run=True,
        pular_pre_flight=True,
        usar_skill8_atomica_v25=True,
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_d = res['etapas_executadas']['D']
    assert etapa_d['modo'] == 'skill8_atomica_v25'
    assert etapa_d['status'] == 'DRY_RUN_OK_ETAPA_D'
    assert etapa_d['etapa'] == 'D'
    assert etapa_d['ajustes_total'] == 1
    assert etapa_d['invoices_pendentes'] == [888001]


def test_v25_s1_default_off_preserva_legacy_etapa_c(db):
    """v25+ S1: SEM flag (default OFF) preserva path legacy `executar_etapa_c`.
    Output legacy NAO tem chave `modo`.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_LEGACY_C'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        picking_id_odoo=999003,
        fase_pipeline='F5c_LIBERADO',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    res = executor.executar_pipeline_bulk(
        ciclo=ciclo_test,
        etapas=('C',),
        dry_run=True,
        pular_pre_flight=True,
        # SEM usar_skill8_atomica_v25=True
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_c = res['etapas_executadas']['C']
    assert 'modo' not in etapa_c, (
        f'Default OFF deveria preservar legacy (sem chave modo). '
        f'Recebi: {etapa_c.get("modo")!r}'
    )
    assert etapa_c['status'] == 'DRY_RUN_OK_ETAPA_C'


def test_v25_s1_etapa_c_via_skill8_real_run_invoca_atomos(db):
    """v25+ S1: real-run com flag=True invoca polling_invoice +
    validar_invoice_pos_robo da `FaturamentoInvoiceService` por picking.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_C_REAL'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        picking_id_odoo=999004,
        fase_pipeline='F5c_LIBERADO',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # Mock Skill 8 ATOMICA + commit_resilient (real-run nao deve commitar
    # de verdade; teste roda dentro transaction).
    fake_svc = MagicMock()
    fake_svc.polling_invoice.return_value = {
        'status': 'OK', 'invoice_id': 707070, 'tempo_ms': 100,
    }
    fake_svc.validar_invoice_pos_robo.return_value = {
        'status': 'OK',
        'sub_etapas': {
            'f5d5_payment_provider_ok': 1,
            'f5d5_payment_provider_falha': 0,
            'f5d6_price_zero_corrigidas': 0,
            'f5d6_price_zero_falha': 0,
            'f5d7_fiscal_setup_ok': 0,
            'f5d7_fiscal_setup_skip': 1,
            'f5d7_fiscal_setup_falha': 0,
        },
        'tempo_ms': 50,
    }

    # CR-v27+-C1 (95% conf): import lazy de FaturamentoInvoiceService dentro
    # do helper. Patch via path do modulo fonte funciona PORQUE o helper
    # importa dentro da funcao e ai resolve via sys.modules['...faturamento']
    # — mas dependendo de ordem de carregamento o `return_value` pode ser
    # ignorado. `side_effect=lambda **kw: fake_svc` garante que CADA chamada
    # do construtor (FaturamentoInvoiceService(odoo=..., picking_svc=...))
    # retorna fake_svc, independente de como o import resolve.
    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.FaturamentoInvoiceService',
        side_effect=lambda **kw: fake_svc,
    ):
        res = executor.executar_pipeline_bulk(
            ciclo=ciclo_test,
            etapas=('C',),
            dry_run=False,
            pular_pre_flight=True,
            usar_skill8_atomica_v25=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_c = res['etapas_executadas']['C']
    assert etapa_c['modo'] == 'skill8_atomica_v25'
    assert etapa_c['status'] == 'EXECUTADO_ETAPA_C'
    assert etapa_c['pickings_resolvidos'] == {999004: 707070}
    assert etapa_c['sub_etapas']['f5d5_payment_provider_ok'] == 1
    assert etapa_c['sub_etapas']['f5d7_fiscal_setup_skip'] == 1
    # CRUCIAL: atomos invocados
    fake_svc.polling_invoice.assert_called_once()
    fake_svc.validar_invoice_pos_robo.assert_called_once()


def test_v25_s1_etapa_d_via_skill8_real_run_invoca_atomo(db):
    """v25+ S1: real-run com flag=True invoca transmitir_sefaz da
    FaturamentoInvoiceService por invoice.
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_D_REAL'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        picking_id_odoo=999005,
        invoice_id_odoo=888002,
        fase_pipeline='F5d_INVOICE_GERADA',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    fake_svc = MagicMock()
    chave_test = '35260561724241000178550010000999999007099001'
    fake_svc.transmitir_sefaz.return_value = {
        'status': 'OK',
        'chave_nfe': chave_test,
        'situacao_nf': 'autorizado',
        'tempo_ms': 5000,
    }

    # CR-v27+-C1 (95% conf): side_effect=lambda garante intercepta\xc3\xa7\xc3\xa3o
    # mesmo com import lazy do helper (ver test_v25_s1_etapa_c_via_skill8_real_run)
    with patch(
        'app.odoo.estoque.scripts.faturamento.FaturamentoInvoiceService',
        side_effect=lambda **kw: fake_svc,
    ):
        res = executor.executar_pipeline_bulk(
            ciclo=ciclo_test,
            etapas=('D',),
            dry_run=False,
            confirmar_sefaz=True,
            pular_pre_flight=True,
            usar_skill8_atomica_v25=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_d = res['etapas_executadas']['D']
    assert etapa_d['modo'] == 'skill8_atomica_v25'
    assert etapa_d['status'] == 'EXECUTADO_ETAPA_D'
    assert etapa_d['invoices_resolvidas'] == {888002: chave_test}
    assert etapa_d['contadores']['sucesso'] == 1
    assert etapa_d['contadores']['falha'] == 0
    fake_svc.transmitir_sefaz.assert_called_once()
    kwargs = fake_svc.transmitir_sefaz.call_args.kwargs
    assert kwargs['invoice_id'] == 888002
    assert kwargs['confirmar_sefaz'] is True


def test_v25_s1_etapa_d_via_skill8_bloqueado_sem_confirmar_sefaz(db):
    """v25+ S1: ETAPA D real-run sem `confirmar_sefaz` retorna
    BLOQUEADO_SEM_CONFIRMAR_SEFAZ (paridade legacy D18).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_D_NO_CONF'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        invoice_id_odoo=888003,
        fase_pipeline='F5d_INVOICE_GERADA',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    # Real-run sem --confirmar-sefaz deveria bater CR-H4 ANTES do helper
    # (sequencial: confirmar_sefaz=False trava em executar_etapa_d original).
    # Ao chamar via bulk com etapas=('D',), CR-H4 (B falhou) NAO se aplica
    # porque B nao esta nas etapas solicitadas. Entao o dispatch chega ao
    # helper que tem D18 propria.
    res = executor.executar_pipeline_bulk(
        ciclo=ciclo_test,
        etapas=('D',),
        dry_run=False,
        confirmar_sefaz=False,  # sem confirmacao 2 nivel
        pular_pre_flight=True,
        usar_skill8_atomica_v25=True,
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_d = res['etapas_executadas']['D']
    assert etapa_d['modo'] == 'skill8_atomica_v25'
    assert etapa_d['status'] == 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'
    assert 'IRREVERSIVEL' in etapa_d['erro']


# ============================================================
# v27+ S4 — Expand CONSTANTS FB+CD em CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO
# + L10N_BR_TIPO_PEDIDO_POR_ACAO para todas direcoes MATRIZ_INTERCOMPANY
# ============================================================

def test_v27_s4_resolver_constants_fluxo_l3_fb_destino():
    """v27+ S4: CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[1] (FB) mapeado.
    Validacao via `_resolver_constants_fluxo_l3` com acao PERDA_LF_FB
    (destino FB=1) — agora retorna dict completo (antes retornava None).
    """
    odoo = MagicMock()
    odoo._uid = 42
    executor = FaturamentoPipelineExecutor(odoo=odoo)
    # Mock G039 (destino FB usa G039 dinamico — team_id=None nos CONSTANTS)
    with patch.object(
        executor, '_resolver_team_g039', return_value=(99, 'OK_EXISTENTE'),
    ):
        resolved = executor._resolver_constants_fluxo_l3(
            acao_decidida='PERDA_LF_FB',
            company_destino=1,
        )
    assert resolved is not None, (
        'FB destino agora SUPORTADO via v27+ S4 expand'
    )
    assert resolved['company_destino'] == 1
    assert resolved['picking_type_id'] == 1   # Recebimento (FB)
    assert resolved['payment_term_id'] == 2791
    assert resolved['payment_provider_id'] == 38
    # team_id: G039 dinamico (mock 99) sobrescreve None default
    assert resolved['team_id'] == 99
    assert resolved['_team_g039_status'] == 'OK_EXISTENTE'
    # PERDA_LF_FB: tipos {dfe: compra, po: retorno}
    assert resolved['l10n_br_tipo_pedido_dfe'] == 'compra'
    assert resolved['l10n_br_tipo_pedido_po'] == 'retorno'


def test_v27_s4_resolver_constants_fluxo_l3_cd_destino():
    """v27+ S4: CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[4] (CD) mapeado.
    Validacao via TRANSFERIR_FB_CD (destino CD=4).
    """
    odoo = MagicMock()
    odoo._uid = 42
    executor = FaturamentoPipelineExecutor(odoo=odoo)
    with patch.object(
        executor, '_resolver_team_g039', return_value=(125, 'CRIADO'),
    ):
        resolved = executor._resolver_constants_fluxo_l3(
            acao_decidida='TRANSFERIR_FB_CD',
            company_destino=4,
        )
    assert resolved is not None
    assert resolved['company_destino'] == 4
    assert resolved['picking_type_id'] == 13  # Recebimento (CD)
    assert resolved['payment_term_id'] == 2791
    assert resolved['payment_provider_id'] == 38
    assert resolved['team_id'] == 125  # G039 dinamico
    # TRANSFERIR_FB_CD: tipos {dfe: compra, po: transf-filial}
    assert resolved['l10n_br_tipo_pedido_dfe'] == 'compra'
    assert resolved['l10n_br_tipo_pedido_po'] == 'transf-filial'


def test_v27_s4_l10n_br_tipo_pedido_cobre_todas_acoes_matriz():
    """v27+ S4: L10N_BR_TIPO_PEDIDO_POR_ACAO mapeia todas as 8 acoes do
    ACAO_PARA_DIRECAO (mineracao MATRIZ_INTERCOMPANY).

    Garante que mapeamento e' completo — onda PROD com qualquer combinacao
    de acoes nao bate em direcao nao mapeada.

    dfe por acao: INDUSTRIALIZACAO_FB_LF usa 'serv-industrializacao'
    (correcao Rafael 2026-06-02 — alinha com escriturar_dfe + canary 627348);
    as 7 OUTRAS acoes mantem dfe='compra' (decisao separada). po derivado de
    MATRIZ[op]['entrada'][(co_origem, co_destino)]['l10n_br_tipo_pedido_entrada'].
    """
    executor = FaturamentoPipelineExecutor()
    mapping = executor.L10N_BR_TIPO_PEDIDO_POR_ACAO

    # 8 acoes esperadas (mineracao ACAO_PARA_DIRECAO)
    acoes_esperadas = {
        'INDUSTRIALIZACAO_FB_LF',  # entrada serv-industrializacao
        'PERDA_LF_FB',             # entrada retorno
        'DEV_LF_FB',               # entrada outro
        'DEV_CD_LF',               # entrada retorno
        'DEV_LF_CD',               # entrada outro
        'DEV_FB_LF',               # entrada retorno
        'TRANSFERIR_FB_CD',        # entrada transf-filial
        'TRANSFERIR_CD_FB',        # entrada transf-filial
    }
    assert set(mapping.keys()) >= acoes_esperadas, (
        f'Faltam acoes em L10N_BR_TIPO_PEDIDO_POR_ACAO: '
        f'{acoes_esperadas - set(mapping.keys())}'
    )

    # dfe esperado por acao: INDUSTRIALIZACAO_FB_LF -> serv-industrializacao
    # (Rafael 2026-06-02); as 7 OUTRAS -> 'compra'.
    dfe_esperado = {acao: 'compra' for acao in acoes_esperadas}
    dfe_esperado['INDUSTRIALIZACAO_FB_LF'] = 'serv-industrializacao'
    for acao in acoes_esperadas:
        entry = mapping[acao]
        assert entry['dfe'] == dfe_esperado[acao], (
            f'{acao}: dfe={entry["dfe"]!r} esperado {dfe_esperado[acao]!r}'
        )
        assert 'po' in entry and entry['po'], (
            f'{acao}: po nao mapeado'
        )

    # Casos especificos (validado contra MATRIZ_INTERCOMPANY)
    assert mapping['INDUSTRIALIZACAO_FB_LF']['dfe'] == 'serv-industrializacao'
    assert mapping['INDUSTRIALIZACAO_FB_LF']['po'] == 'serv-industrializacao'
    assert mapping['PERDA_LF_FB']['po'] == 'retorno'
    assert mapping['DEV_CD_LF']['po'] == 'retorno'
    assert mapping['DEV_FB_LF']['po'] == 'retorno'
    assert mapping['DEV_LF_FB']['po'] == 'outro'
    assert mapping['DEV_LF_CD']['po'] == 'outro'
    assert mapping['TRANSFERIR_FB_CD']['po'] == 'transf-filial'
    assert mapping['TRANSFERIR_CD_FB']['po'] == 'transf-filial'


def test_v27_s4_constants_fluxo_l3_cobre_3_companies():
    """v27+ S4: CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO cobre 3 companies
    (FB=1, CD=4, LF=5). Antes v27+ S4 cobria apenas LF=5.

    LF=5: team_id=143 STATIC (F4 v25+ — decisao operacional).
    FB=1: team_id=None (G039 dinamico — pendente canary).
    CD=4: team_id=None (G039 dinamico — pendente canary).
    """
    executor = FaturamentoPipelineExecutor()
    constants = executor.CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO

    # 3 companies mapeadas
    assert set(constants.keys()) == {1, 4, 5}

    # LF=5: STATIC team_id=143 (F4 v25+)
    assert constants[5]['team_id'] == 143
    assert constants[5]['picking_type_id'] == 19  # Recebimento LF
    assert constants[5]['payment_term_id'] == 2791
    assert constants[5]['payment_provider_id'] == 38

    # FB=1: G039 dinamico
    assert constants[1]['team_id'] is None
    assert constants[1]['picking_type_id'] == 1  # Recebimento FB
    assert constants[1]['payment_term_id'] == 2791
    assert constants[1]['payment_provider_id'] == 38

    # CD=4: G039 dinamico
    assert constants[4]['team_id'] is None
    assert constants[4]['picking_type_id'] == 13  # Recebimento CD
    assert constants[4]['payment_term_id'] == 2791
    assert constants[4]['payment_provider_id'] == 38


# ============================================================
# v27+ post-code-review fixes (M1 + Finding 3 S4 + H2)
# ============================================================

def test_v25_s1_default_off_preserva_legacy_etapa_d(db):
    """CR-v27+-M1 (80% conf): assimetria — antes existia teste default-off
    apenas para ETAPA C. ETAPA D (SEFAZ IRREVERSIVEL) merece teste equivalente
    de regressao garantindo que sem flag o path legacy `executar_etapa_d`
    e' chamado (sem chave 'modo' no output).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V25_S1_LEGACY_D'
    aj = AjusteEstoqueInventario(
        ciclo=ciclo_test,
        cod_produto='103000011',
        tipo_produto=4,
        company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10.0,
        qtd_odoo=0,
        qtd_ajuste=10.0,
        lote_destino='MIGRAÇÃO',
        picking_id_odoo=999103,
        invoice_id_odoo=888103,
        fase_pipeline='F5d_INVOICE_GERADA',
        status='APROVADO',
        criado_por='test_v25_s1',
    )
    db.session.add(aj)
    db.session.commit()

    executor = FaturamentoPipelineExecutor()
    res = executor.executar_pipeline_bulk(
        ciclo=ciclo_test,
        etapas=('D',),
        dry_run=True,
        pular_pre_flight=True,
        # SEM usar_skill8_atomica_v25=True
    )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_d = res['etapas_executadas']['D']
    assert 'modo' not in etapa_d, (
        f'Default OFF deveria preservar legacy (sem chave modo). '
        f'Recebi: {etapa_d.get("modo")!r}'
    )
    assert etapa_d['status'] == 'DRY_RUN_OK_ETAPA_D'


def test_v27_s4_resolver_constants_fluxo_l3_acao_desconhecida_retorna_none():
    """CR-v27+-Finding3-S4 (80% conf): regressao de cobertura — antes
    test_v20_s3_etapa_f_via_fluxo_l3_cd_destino_nao_suportada exercitava
    o path None (CD destino sem CONSTANTS). Apos v27+ S4 expand, CD ESTA
    mapeado. Teste novo cobre o path None via acao_decidida nao mapeada
    em L10N_BR_TIPO_PEDIDO_POR_ACAO (8 acoes da MATRIZ). Ex.: acao tipica
    NAO inter-company ('AJUSTE_LOCAL' ou typo).
    """
    odoo = MagicMock()
    odoo._uid = 42
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    # company_destino valido (LF=5) mas acao_decidida NAO mapeada
    resolved = executor._resolver_constants_fluxo_l3(
        acao_decidida='ACAO_INVALIDA_PARA_TESTE',
        company_destino=5,
    )
    assert resolved is None, (
        f'acao_decidida desconhecida deveria retornar None '
        f'(L10N_BR_TIPO_PEDIDO_POR_ACAO.get retorna None). Recebi: {resolved!r}'
    )


def test_v27_s4_resolver_constants_fluxo_l3_company_invalida_retorna_none():
    """CR-v27+-Finding3-S4 (80% conf): path None via company_destino NAO
    mapeada em CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO (v27+ S4 cobre 1, 4, 5).
    Antes v27+ S4 isso retornava None para CD=4; agora apenas para companies
    fora do dict (ex: SC=3 ou inexistente=999).
    """
    odoo = MagicMock()
    odoo._uid = 42
    executor = FaturamentoPipelineExecutor(odoo=odoo)

    # acao valida + company_destino fora do dict v27+ S4
    resolved = executor._resolver_constants_fluxo_l3(
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        company_destino=999,  # company inexistente
    )
    assert resolved is None


def test_v27_h2_pickings_falha_excecao_separado_de_timeout(db):
    """CR-v27+-H2 (83% conf): apos v27+ S1+H2 fix, o output do helper
    `_executar_etapa_c_via_skill8_atomica` separa pickings_timeout (robo
    nao criou invoice) de pickings_falha_excecao (atomo polling_invoice
    raise OU retornou status != OK/TIMEOUT).

    Teste real-run com 2 pickings: 1 polling raise + 1 polling timeout.
    Apos: pickings_timeout=[1 pid] + pickings_falha_excecao=[1 pid] +
    status=FALHA_MISTO_TOTAL (ambos sem resolver).
    """
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    ciclo_test = 'TEST_V27_H2'
    aj1 = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='AAA', tipo_produto=4, company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=10, qtd_odoo=0, qtd_ajuste=10,
        lote_destino='MIGRAÇÃO', picking_id_odoo=997001,
        fase_pipeline='F5c_LIBERADO', status='APROVADO',
        criado_por='test_v27_h2',
    )
    aj2 = AjusteEstoqueInventario(
        ciclo=ciclo_test, cod_produto='BBB', tipo_produto=4, company_id=5,
        acao_decidida='PERDA_LF_FB',
        qtd_inventario=20, qtd_odoo=0, qtd_ajuste=20,
        lote_destino='MIGRAÇÃO', picking_id_odoo=997002,
        fase_pipeline='F5c_LIBERADO', status='APROVADO',
        criado_por='test_v27_h2',
    )
    db.session.add_all([aj1, aj2])
    db.session.commit()

    executor = FaturamentoPipelineExecutor()

    # 1o picking raise; 2o retorna TIMEOUT
    fake_svc = MagicMock()
    fake_svc.polling_invoice.side_effect = [
        RuntimeError('odoo_rpc_timeout_transient'),  # picking 997001
        {'status': 'TIMEOUT', 'invoice_id': None,    # picking 997002
         'tempo_ms': 1800000},
    ]

    with patch(
        'app.odoo.estoque.orchestrators.inventario_pipeline.'
        '_commit_resilient',
        return_value=True,
    ), patch(
        'app.odoo.estoque.scripts.faturamento.FaturamentoInvoiceService',
        side_effect=lambda **kw: fake_svc,
    ):
        res = executor.executar_pipeline_bulk(
            ciclo=ciclo_test, etapas=('C',),
            dry_run=False, pular_pre_flight=True,
            usar_skill8_atomica_v25=True,
        )

    AjusteEstoqueInventario.query.filter_by(ciclo=ciclo_test).delete()
    db.session.commit()

    etapa_c = res['etapas_executadas']['C']
    assert etapa_c['modo'] == 'skill8_atomica_v25'
    # H2: separacao
    assert 'pickings_falha_excecao' in etapa_c
    assert sorted(etapa_c['pickings_timeout']) == [997002]
    assert sorted(etapa_c['pickings_falha_excecao']) == [997001]
    assert etapa_c['pickings_resolvidos'] == {}
    # Status final: ambos falharam (timeout + excecao) = MISTO_TOTAL
    assert etapa_c['status'] == 'FALHA_MISTO_TOTAL'
    # Atomo invocado 2x
    assert fake_svc.polling_invoice.call_count == 2


# ============================================================
# F1 v29+ (2026-05-29) — agregado executar_pipeline_bulk nao deixa
# EXECUTADO_PARCIAL de etapa escapar para EXECUTADO_OK
# ============================================================

def test_v29_f1_executado_parcial_de_etapa_nao_escapa_agregado():
    """CR-F1 v29+ (Rafael 2026-05-29): uma ETAPA retornando EXECUTADO_PARCIAL
    deve fazer o pipeline reportar EXECUTADO_PARCIAL (nao EXECUTADO_OK).
    ANTES do fix, 'PARCIAL' escapava (so startswith('FALHA') + STATUS_FALHA
    eram detectados no agregado) -> onda mista (parte OK + parte nao-mapeada)
    reportava OK mascarando pendencias."""
    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, 'executar_etapa_a',
        return_value={'etapa': 'A', 'status': 'EXECUTADO_PARCIAL'},
    ):
        res = executor.executar_pipeline_bulk(
            ciclo='TEST_F1_PARCIAL',
            etapas=('A',),
            dry_run=False,
            pular_pre_flight=True,
        )
    assert res['status'] == 'EXECUTADO_PARCIAL', (
        f"EXECUTADO_PARCIAL de etapa nao pode escapar p/ EXECUTADO_OK; "
        f"got {res['status']!r}"
    )


def test_v29_f1_variantes_parcial_timeout_misto_detectadas():
    """CR-F1 v29+: variantes EXECUTADO_PARCIAL_TIMEOUT/_MISTO/_FALHA/_ETAPA_A
    (ETAPAs A/C/D) tambem disparam PARCIAL no agregado via `'PARCIAL' in s`."""
    executor = FaturamentoPipelineExecutor()
    for status_etapa in (
        'EXECUTADO_PARCIAL_TIMEOUT',
        'EXECUTADO_PARCIAL_MISTO',
        'EXECUTADO_PARCIAL_FALHA',
        'EXECUTADO_PARCIAL_ETAPA_A',
    ):
        with patch.object(
            executor, 'executar_etapa_a',
            return_value={'etapa': 'A', 'status': status_etapa},
        ):
            res = executor.executar_pipeline_bulk(
                ciclo='TEST_F1_VARIANTE',
                etapas=('A',),
                dry_run=False,
                pular_pre_flight=True,
            )
        assert res['status'] == 'EXECUTADO_PARCIAL', (
            f'{status_etapa} deveria disparar PARCIAL; got {res["status"]!r}'
        )


def test_v29_f1_dry_run_parcial_propaga():
    """CR-F1 v29+: em dry-run, etapa parcial -> DRY_RUN_PARCIAL (nao
    DRY_RUN_OK)."""
    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, 'executar_etapa_a',
        return_value={'etapa': 'A', 'status': 'EXECUTADO_PARCIAL'},
    ):
        res = executor.executar_pipeline_bulk(
            ciclo='TEST_F1_DRY',
            etapas=('A',),
            dry_run=True,
            pular_pre_flight=True,
        )
    assert res['status'] == 'DRY_RUN_PARCIAL'


def test_v29_f1_etapa_ok_continua_executado_ok_nao_regressao():
    """CR-F1 v29+ NAO-REGRESSAO: etapa 100% OK continua EXECUTADO_OK
    (o fix `'PARCIAL' in s` nao deve afetar status OK limpos)."""
    executor = FaturamentoPipelineExecutor()
    with patch.object(
        executor, 'executar_etapa_a',
        return_value={'etapa': 'A', 'status': 'EXECUTADO_OK'},
    ):
        res = executor.executar_pipeline_bulk(
            ciclo='TEST_F1_OK',
            etapas=('A',),
            dry_run=False,
            pular_pre_flight=True,
        )
    assert res['status'] == 'EXECUTADO_OK'
