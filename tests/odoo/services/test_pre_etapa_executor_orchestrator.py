"""Tests para pre_etapa_executor.py (orchestrator C3 macro Skill 6).

Capina 09b_executar_pre_etapa.py. Compoe Skills 1+2:
- POS/NEG: Skill 2 transferir_quantidade_para_lote_v2 (delta_esperado propagado)
- PURO: Skill 1 ajustar_quant (criar_se_faltar=True, delta_esperado=qty)

Cenarios cobertos:
1-2.  _resolver_product_id (found/not-found)
3.    _buscar_quants_produto_cid (normaliza dict Odoo)
4-7.  _localizar_doador (match exato/parcial/fallback/nenhum)
8-12. _avaliar_sucesso_v2 (DRY_RUN_OK, EXECUTADO, FALHAS — flat status)
13-15. _executar_transferencia_interna dry-run (doador OK / sem doador / insuficiente)
16.   _executar_positivo_puro dry-run (composicao Skill 1)
17-18. executar_onda_pre_etapa (FALHA_USO company_id, FALHA_NENHUM_APROVADO)
"""
from unittest.mock import MagicMock

from app.odoo.estoque.orchestrators.pre_etapa_executor import (
    ACAO_AUDIT_CURTA,
    ACOES_INTERNAS_POR_CID,
    LOTE_MIGRACAO,
    _avaliar_sucesso_v2,
    _buscar_quants_produto_cid,
    _executar_positivo_puro,
    _executar_transferencia_interna,
    _localizar_doador,
    _resolver_product_id,
    executar_onda_pre_etapa,
)


# ============================================================
# Helpers de mock
# ============================================================

def _quant(quant_id, lote_nome, qty, lot_id=10, location_id=32):
    """Quant normalizado (saida de _buscar_quants_produto_cid)."""
    return {
        'quant_id': quant_id,
        'lot_id': lot_id,
        'lote_nome': lote_nome,
        'location_id': location_id,
        'location_nome': f'LOC_{location_id}',
        'quantity': float(qty),
        'reserved': 0.0,
    }


def _ajuste_mock(
    acao='AJUSTE_CD_TRANSF_INTERNA_POS',
    qtd_inventario=10.0,
    qtd_odoo=10.0,
    qtd_ajuste=10.0,
    lote_origem='LOTE_X',
    lote_destino='LOTE_Y',
    company_id=4,
    cod_produto='4310177',
    ajuste_id=1,
):
    """Mock de AjusteEstoqueInventario com atributos necessarios."""
    m = MagicMock()
    m.id = ajuste_id
    m.acao_decidida = acao
    m.qtd_inventario = qtd_inventario
    m.qtd_odoo = qtd_odoo
    m.qtd_ajuste = qtd_ajuste
    m.lote_origem = lote_origem
    m.lote_destino = lote_destino
    m.company_id = company_id
    m.cod_produto = cod_produto
    return m


# ============================================================
# 1-2. _resolver_product_id
# ============================================================

def test_resolver_product_id_found():
    odoo = MagicMock()
    odoo.search_read.return_value = [{'id': 999, 'name': 'PALMITO 12X300'}]
    res = _resolver_product_id(odoo, '4310177')
    assert res == (999, 'PALMITO 12X300')


def test_resolver_product_id_not_found():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    res = _resolver_product_id(odoo, '9999999')
    assert res is None


# ============================================================
# 3. _buscar_quants_produto_cid
# ============================================================

def test_buscar_quants_produto_cid_normaliza_dict():
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {
            'id': 1, 'lot_id': [10, 'LOTE_X'], 'location_id': [32, 'CD/Estoque'],
            'quantity': 100.0, 'reserved_quantity': 0.0,
        },
        {
            'id': 2, 'lot_id': False, 'location_id': [33, 'CD/Pre-Producao'],
            'quantity': 50.0, 'reserved_quantity': 5.0,
        },
    ]
    res = _buscar_quants_produto_cid(odoo, 999, 4)
    assert len(res) == 2
    assert res[0]['lot_id'] == 10
    assert res[0]['lote_nome'] == 'LOTE_X'
    assert res[0]['quantity'] == 100.0
    assert res[1]['lot_id'] is None  # lot_id=False vira None
    assert res[1]['lote_nome'] == ''
    assert res[1]['reserved'] == 5.0


# ============================================================
# 4-7. _localizar_doador
# ============================================================

def test_localizar_doador_match_exato():
    quants = [_quant(1, 'LOTE_X', 100, lot_id=10)]
    res = _localizar_doador(quants, 'LOTE_X', 50)
    assert res is not None
    assert res['quant_id'] == 1


def test_localizar_doador_prefere_menor_sobra():
    """Multiplos candidatos: pega o de menor saldo que ainda cobre."""
    quants = [
        _quant(1, 'LOTE_X', 200, lot_id=10),
        _quant(2, 'LOTE_X', 60, lot_id=11),
        _quant(3, 'LOTE_X', 500, lot_id=12),
    ]
    res = _localizar_doador(quants, 'LOTE_X', 50)
    assert res['quant_id'] == 2  # menor sobra (60)


def test_localizar_doador_fallback_qty_insuficiente():
    """Sem candidatos com qty suficiente: fallback retorna primeiro do lote."""
    quants = [
        _quant(1, 'LOTE_X', 30, lot_id=10),
        _quant(2, 'LOTE_X', 20, lot_id=11),
    ]
    res = _localizar_doador(quants, 'LOTE_X', 100)
    # Fallback retorna primeiro do mesmo lote (caller deve checar saldo)
    assert res is not None
    assert res['lote_nome'] == 'LOTE_X'


def test_localizar_doador_sem_candidatos():
    quants = [_quant(1, 'LOTE_OUTRO', 100, lot_id=10)]
    res = _localizar_doador(quants, 'LOTE_X', 50)
    assert res is None


# ============================================================
# 8-12. _avaliar_sucesso_v2
# ============================================================

def test_avaliar_sucesso_v2_executado_real():
    assert _avaliar_sucesso_v2({'status': 'EXECUTADO'}, dry_run=False) is True


def test_avaliar_sucesso_v2_dry_run_ok():
    assert _avaliar_sucesso_v2({'status': 'DRY_RUN_OK'}, dry_run=True) is True


def test_avaliar_sucesso_v2_dry_run_ok_em_modo_real_eh_falha():
    """DRY_RUN_OK em dry_run=False NAO conta como sucesso real."""
    assert _avaliar_sucesso_v2({'status': 'DRY_RUN_OK'}, dry_run=False) is False


def test_avaliar_sucesso_v2_falha_reducao():
    assert _avaliar_sucesso_v2(
        {'status': 'FALHA_REDUCAO', 'erro': 'qty negativa'},
        dry_run=False,
    ) is False


def test_avaliar_sucesso_v2_falha_aumento():
    assert _avaliar_sucesso_v2(
        {'status': 'FALHA_AUMENTO', 'erro': 'lote inexistente'},
        dry_run=False,
    ) is False


# ============================================================
# 13-15. _executar_transferencia_interna (dry-run — sem db.session.commit)
# ============================================================

def test_executar_transferencia_interna_dry_run_doador_ok():
    """Dry-run com doador OK: invoca transferir_quantidade_para_lote_v2 e retorna sucesso=None."""
    transfer_svc = MagicMock()
    transfer_svc.transferir_quantidade_para_lote_v2.return_value = {
        'status': 'DRY_RUN_OK',
        'reducao_origem': {'status': 'DRY_RUN_OK'},
        'aumento_destino': {'status': 'DRY_RUN_OK'},
        'qty_transferida': 10.0,
        'lot_id_origem': 10,
        'lot_id_destino': 99,
        'tempo_ms': 5,
    }
    quants = [_quant(1, 'LOTE_X', 100, lot_id=10)]
    ajuste = _ajuste_mock(
        acao='AJUSTE_CD_TRANSF_INTERNA_POS',
        qtd_inventario=10.0,
        lote_origem='LOTE_X', lote_destino='LOTE_Y',
    )
    res = _executar_transferencia_interna(
        transfer_svc, ajuste, product_id=999, quants_atuais=quants,
        dry_run=True, executado_por='test',
    )
    assert res['sucesso'] is None  # dry-run nao confirma
    assert 'plano' in res
    transfer_svc.transferir_quantidade_para_lote_v2.assert_called_once()
    call_kwargs = transfer_svc.transferir_quantidade_para_lote_v2.call_args.kwargs
    assert call_kwargs['dry_run'] is True
    assert call_kwargs['qty'] == 10.0
    assert call_kwargs['nome_lote_destino'] == 'LOTE_Y'
    assert call_kwargs['lot_id_origem'] == 10


def test_executar_transferencia_interna_sem_doador():
    """Sem quant com lote_origem: retorna falha sem invocar Skill 2."""
    transfer_svc = MagicMock()
    quants = [_quant(1, 'LOTE_OUTRO', 100, lot_id=10)]
    ajuste = _ajuste_mock(lote_origem='LOTE_X')
    res = _executar_transferencia_interna(
        transfer_svc, ajuste, product_id=999, quants_atuais=quants,
        dry_run=True, executado_por='test',
    )
    assert res['sucesso'] is False
    assert 'quant origem nao encontrado' in res['erro']
    assert res['transferido_qty'] == 0
    transfer_svc.transferir_quantidade_para_lote_v2.assert_not_called()


def test_executar_transferencia_interna_doador_insuficiente():
    """Doador encontrado mas qty < pedida: falha bloqueante."""
    transfer_svc = MagicMock()
    quants = [_quant(1, 'LOTE_X', 5.0, lot_id=10)]  # so 5 un
    ajuste = _ajuste_mock(
        lote_origem='LOTE_X', qtd_inventario=10.0,
    )
    res = _executar_transferencia_interna(
        transfer_svc, ajuste, product_id=999, quants_atuais=quants,
        dry_run=True, executado_por='test',
    )
    assert res['sucesso'] is False
    assert 'pede 10' in res['erro']
    assert 'tem 5.0' in res['erro']
    transfer_svc.transferir_quantidade_para_lote_v2.assert_not_called()


# ============================================================
# 16. _executar_positivo_puro (dry-run — Skill 1 mock)
# ============================================================

def test_executar_positivo_puro_dry_run_via_skill1():
    """Dry-run PURO: resolve lote_destino + invoca ajustar_quant com guard delta_esperado."""
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.return_value = {
        'status': 'DRY_RUN_OK',
        'qty_antes': 0,
        'qty_apos': 25.0,
        'ajuste_aplicado': 25.0,
        'quant_id': None,  # nao existe ainda — criar_se_faltar=True
    }
    transfer_svc = MagicMock()
    transfer_svc.resolver_lote_destino.return_value = (50, 'P-2026-05', False)
    ajuste = _ajuste_mock(
        acao='AJUSTE_CD_POSITIVO_PURO',
        qtd_ajuste=25.0, lote_destino='P-2026-05',
    )
    res = _executar_positivo_puro(
        quant_svc, transfer_svc, ajuste, product_id=999,
        location_principal=32, dry_run=True, executado_por='test',
    )
    assert res['sucesso'] is None  # dry-run
    assert res['lote_destino_nome'] == 'P-2026-05'
    transfer_svc.resolver_lote_destino.assert_called_once()
    call_kwargs_resolver = transfer_svc.resolver_lote_destino.call_args.kwargs
    assert call_kwargs_resolver['criar_se_faltar'] is False  # dry-run: nao cria

    # Verificar guard delta_esperado propagado para Skill 1
    quant_svc.ajustar_quant.assert_called_once()
    call_kwargs_skill1 = quant_svc.ajustar_quant.call_args.kwargs
    assert call_kwargs_skill1['delta'] == 25.0
    assert call_kwargs_skill1['delta_esperado'] == 25.0  # GUARD ATIVO
    assert call_kwargs_skill1['criar_se_faltar'] is True
    assert call_kwargs_skill1['lot_id'] == 50
    assert call_kwargs_skill1['location_id'] == 32
    assert call_kwargs_skill1['dry_run'] is True


# ============================================================
# 17-18. executar_onda_pre_etapa (entry-point) — usa app_context
# ============================================================

def test_executar_onda_pre_etapa_company_id_invalido():
    """company_id != 4/1: retorna FALHA_USO sem tocar Odoo nem DB."""
    res = executar_onda_pre_etapa(company_id=999, dry_run=True)
    assert res['status'] == 'FALHA_USO'
    assert 'company_id=999' in res['erro']
    assert res['modo'] == 'executar-onda'


def test_executar_onda_pre_etapa_sem_aprovados(db):
    """Sem ajustes APROVADO: retorna FALHA_NENHUM_APROVADO.

    Usa fixture `db` (conftest) que abre app_context + savepoint.
    Ciclo improvavel garante zero ajustes (sem necessidade de DELETE).
    """
    _ = db  # fixture ativa app_context (necessario para query Flask-SQLAlchemy)
    res = executar_onda_pre_etapa(
        ciclo='CICLO_INEXISTENTE_TEST_999_v9',
        company_id=4,
        dry_run=True,
    )
    assert res['status'] == 'FALHA_NENHUM_APROVADO'
    assert res['ajustes_total'] == 0
    assert res['produtos_total'] == 0
    assert 'aprovar-onda' in res['erro']  # menciona pre-req


# ============================================================
# Constantes — smoke check
# ============================================================

def test_constantes_acoes_internas_por_cid():
    assert 4 in ACOES_INTERNAS_POR_CID
    assert 1 in ACOES_INTERNAS_POR_CID
    assert ACOES_INTERNAS_POR_CID[4]['POS'] == 'AJUSTE_CD_TRANSF_INTERNA_POS'
    assert ACOES_INTERNAS_POR_CID[1]['NEG'] == 'AJUSTE_FB_TRANSF_INTERNA_NEG'


def test_constantes_acao_audit_curta_cobre_todas():
    """ACAO_AUDIT_CURTA deve cobrir todas as 6 acoes (3 por cid x 2 cids)."""
    todas = set()
    for cid_acoes in ACOES_INTERNAS_POR_CID.values():
        todas.update(cid_acoes.values())
    for acao in todas:
        assert acao in ACAO_AUDIT_CURTA, f'ACAO_AUDIT_CURTA nao cobre {acao}'


def test_lote_migracao_constante():
    assert LOTE_MIGRACAO == 'MIGRAÇÃO'


# ============================================================
# CR v9 — fixes aplicados pos-code-review
# ============================================================

def test_acao_audit_curta_importada_de_pre_etapa():
    """CR-PATTERN-2 v9: ACAO_AUDIT_CURTA deve ser a MESMA instancia
    importada de pre_etapa.py (fonte unica), nao duplicada no orchestrator.
    """
    from app.odoo.estoque.scripts.pre_etapa import (
        ACAO_AUDIT_CURTA as ACAO_AUDIT_CURTA_PRE_ETAPA,
    )
    # Mesma referencia (single source of truth)
    assert ACAO_AUDIT_CURTA is ACAO_AUDIT_CURTA_PRE_ETAPA


def test_acao_audit_curta_preserva_nomes_legacy_09b():
    """CR-PATTERN-2 v9: gerador programatico deve preservar EXATAMENTE
    os mesmos nomes curtos usados no 09b legacy (compat. com
    registros historicos em operacao_odoo_auditoria).
    """
    expected = {
        'AJUSTE_CD_TRANSF_INTERNA_POS': 'cd_pre_pos',
        'AJUSTE_CD_TRANSF_INTERNA_NEG': 'cd_pre_neg',
        'AJUSTE_CD_POSITIVO_PURO': 'cd_pos_puro',
        'AJUSTE_FB_TRANSF_INTERNA_POS': 'fb_pre_pos',
        'AJUSTE_FB_TRANSF_INTERNA_NEG': 'fb_pre_neg',
        'AJUSTE_FB_POSITIVO_PURO': 'fb_pos_puro',
    }
    assert ACAO_AUDIT_CURTA == expected
    for v in ACAO_AUDIT_CURTA.values():
        assert len(v) <= 20  # VARCHAR(20) constraint


def test_executar_positivo_puro_dry_run_lote_inexistente_nao_engana():
    """CR-BUG-1 v9: dry-run com lote_destino nominal que nao existe
    deve retornar DRY_RUN_OK_LOTE_A_CRIAR (NAO chamar Skill 1 com
    lot_id=None, que simularia ajuste no quant SEM lote — enganando
    operador).
    """
    quant_svc = MagicMock()
    transfer_svc = MagicMock()
    # resolver_lote_destino com criar_se_faltar=False retorna (None, ..., False)
    transfer_svc.resolver_lote_destino.return_value = (None, 'LOTE_NOVO_2026', False)
    ajuste = _ajuste_mock(
        acao='AJUSTE_CD_POSITIVO_PURO',
        qtd_ajuste=50.0, lote_destino='LOTE_NOVO_2026',
    )
    res = _executar_positivo_puro(
        quant_svc, transfer_svc, ajuste, product_id=999,
        location_principal=32, dry_run=True, executado_por='test',
    )
    # Skill 1 NAO deve ter sido chamada — guard CR-BUG-1
    quant_svc.ajustar_quant.assert_not_called()
    # Retorno deve indicar o guard
    assert res['sucesso'] is None  # dry-run
    assert res['plano']['status'] == 'DRY_RUN_OK_LOTE_A_CRIAR'
    assert res['plano']['qty_antes'] == 0.0
    assert res['plano']['qty_apos'] == 50.0
    assert res['lote_destino_criado_agora'] is True
    assert 'LOTE_NOVO_2026' in res['plano']['observacao']


def test_executar_positivo_puro_dry_run_lote_p15_nao_dispara_guard_bug1():
    """CR-BUG-1 v9: o guard NAO deve disparar para lote_destino_nome
    'P-15/05' ou vazio (esses sao proxies para 'quant SEM lote', e
    lot_id=None e' semanticamente correto nesse caso).
    """
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.return_value = {
        'status': 'DRY_RUN_OK', 'qty_antes': 0, 'qty_apos': 25.0,
    }
    transfer_svc = MagicMock()
    transfer_svc.resolver_lote_destino.return_value = (None, 'P-15/05(sem-lote)', False)
    ajuste = _ajuste_mock(
        acao='AJUSTE_CD_POSITIVO_PURO',
        qtd_ajuste=25.0, lote_destino='P-15/05',
    )
    res = _executar_positivo_puro(
        quant_svc, transfer_svc, ajuste, product_id=999,
        location_principal=32, dry_run=True, executado_por='test',
    )
    # Skill 1 DEVE ser chamada (P-15/05 e proxy valido para quant sem lote)
    quant_svc.ajustar_quant.assert_called_once()
    call_kwargs = quant_svc.ajustar_quant.call_args.kwargs
    assert call_kwargs['lot_id'] is None  # OK — proxy P-15/05
    # NAO retornou o guard BUG-1 (sucesso=None ok; status NAO eh
    # DRY_RUN_OK_LOTE_A_CRIAR — caiu no caminho normal Skill 1)
    assert res['sucesso'] is None
    assert res.get('plano', {}).get('status') != 'DRY_RUN_OK_LOTE_A_CRIAR'


def test_avaliar_sucesso_v2_simplificado_sem_auto_corrigido():
    """CR-PATTERN-1 v9: EXECUTADO_AUTO_CORRIGIDO removido do set (nunca
    propagado pelo flat status do v2). Mantido como sinonimo de EXECUTADO
    nos sub-dicts internos, mas nao no avaliador flat.
    """
    # FLAT status EXECUTADO (caminho normal) — sucesso real
    assert _avaliar_sucesso_v2({'status': 'EXECUTADO'}, dry_run=False) is True
    # FLAT status DRY_RUN_OK em dry-run — sucesso dry
    assert _avaliar_sucesso_v2({'status': 'DRY_RUN_OK'}, dry_run=True) is True
    # FALHAS (transfer.py retorna esses flat)
    assert _avaliar_sucesso_v2({'status': 'FALHA_REDUCAO'}, dry_run=False) is False
    assert _avaliar_sucesso_v2({'status': 'FALHA_AUMENTO'}, dry_run=False) is False
    # EXECUTADO_AUTO_CORRIGIDO no flat (NUNCA acontece, mas se acontecer):
    # comportamento conservador — NAO conta como sucesso (mudanca CR v9).
    assert _avaliar_sucesso_v2({'status': 'EXECUTADO_AUTO_CORRIGIDO'}, dry_run=False) is False


# ============================================================
# Contadores *_dry (CR-BUG-2/EDGE-2 v9)
# ============================================================

def test_contadores_iniciais_incluem_dry_e_sem_ajuste():
    """CR-BUG-2/EDGE-2 v9: _novos_contadores deve incluir contadores
    novos: pos_dry/neg_dry/puro_dry/produtos_dry/produtos_sem_ajuste.
    """
    from app.odoo.estoque.orchestrators.pre_etapa_executor import (
        _novos_contadores,
    )
    c = _novos_contadores()
    # Contadores antigos preservados
    assert 'produtos_ok' in c and c['produtos_ok'] == 0
    assert 'produtos_parcial' in c and c['produtos_parcial'] == 0
    assert 'produtos_falha' in c and c['produtos_falha'] == 0
    assert 'pos_ok' in c and 'pos_falha' in c
    assert 'neg_ok' in c and 'neg_falha' in c
    assert 'puro_ok' in c and 'puro_falha' in c
    # Contadores NOVOS v9
    assert c['produtos_dry'] == 0
    assert c['produtos_sem_ajuste'] == 0
    assert c['pos_dry'] == 0
    assert c['neg_dry'] == 0
    assert c['puro_dry'] == 0


def test_novos_contadores_fabrica_dicts_independentes():
    """_novos_contadores deve retornar dicts NOVOS (nao referencia para
    _CONTADORES_INICIAIS) — mutacao em um nao afeta outro.
    """
    from app.odoo.estoque.orchestrators.pre_etapa_executor import (
        _CONTADORES_INICIAIS, _novos_contadores,
    )
    c1 = _novos_contadores()
    c2 = _novos_contadores()
    c1['pos_ok'] = 99
    assert c2['pos_ok'] == 0  # nao foi afetado
    assert _CONTADORES_INICIAIS['pos_ok'] == 0  # original intacto
