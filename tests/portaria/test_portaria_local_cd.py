"""Testes da bifurcacao da portaria por CD (local_cd).

Cobre o stream "Portaria" do redesign CarVia (Etapas 5-7):
  (a) veiculos_do_dia(local_cd=...) filtra por CD; sem filtro retorna todos.
  (b) saida de um registro VM num embarque MISTO (1 item VM + 1 item TM) propaga
      Separacao.data_embarque SOMENTE do item VM; o item TM fica sem data ate a saida TM.
  (c) regressao Nacom: embarque 100% VM, 1 registro VM, saida -> TODOS os itens
      recebem data_embarque (comportamento identico ao codigo anterior).

GOTCHA: instanciar Embarque via ORM pode falhar pelo mapper de Cotacao
(memory gotcha_query_mapper_init_test). Por isso os cenarios sao montados via SQL
bruto (db.session.execute(text(...))) e reconsultados via ORM.

Login: patch('flask_login.utils._get_user') com MagicMock (padrao do projeto, ver
tests/agente/test_approval_inbox.py). require_portaria() chama
current_user.pode_acessar_portaria() — MagicMock retorna truthy.
"""
import uuid
from datetime import date, time
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import text

from app.portaria.models import ControlePortaria
from app.separacao.models import Separacao
from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE,
    LOCAL_CD_TENENTE_MARQUES,
)


# ---------------------------------------------------------------------------
# Helpers — montagem de cenario via SQL bruto
# ---------------------------------------------------------------------------

def _novo_motorista(db):
    """Cria um motorista minimo e retorna o id."""
    suf = uuid.uuid4().hex[:8]
    cpf = f'{suf[:3]}.{suf[3:6]}.{suf[6:8]}0-00'
    row = db.session.execute(text("""
        INSERT INTO motoristas (nome_completo, rg, cpf, telefone)
        VALUES (:nome, :rg, :cpf, :tel)
        RETURNING id
    """), {
        'nome': f'Motorista {suf}', 'rg': f'RG{suf}',
        'cpf': cpf, 'tel': '(11) 99999-9999',
    }).scalar()
    return row


def _novo_embarque(db):
    """Cria um embarque ativo minimo (SQL bruto, sem ORM/Cotacao) e retorna o id."""
    row = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga, tipo_cotacao)
        VALUES (:numero, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA')
        RETURNING id
    """), {'numero': int(uuid.uuid4().int % 9_000_000) + 1_000_000}).scalar()
    return row


def _novo_item(db, embarque_id, local_cd, lote, nota_fiscal):
    """Cria um EmbarqueItem ativo do local informado."""
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             nota_fiscal, uf_destino, cidade_destino, status)
        VALUES
            (:eid, :lote, :local, 'Cliente Teste', :pedido,
             :nf, 'SP', 'Sao Paulo', 'ativo')
    """), {
        'eid': embarque_id, 'lote': lote, 'local': local_cd,
        'pedido': f'PED-{lote}', 'nf': nota_fiscal,
    })


def _nova_separacao(db, lote, nota_fiscal):
    """Cria uma linha de Separacao do lote, sem data_embarque (NOT NULL: cod_uf)."""
    db.session.execute(text("""
        INSERT INTO separacao
            (separacao_lote_id, cod_uf, numero_nf, data_embarque, nf_cd)
        VALUES
            (:lote, 'SP', :nf, NULL, true)
    """), {'lote': lote, 'nf': nota_fiscal})


def _registro_portaria(db, motorista_id, embarque_id, local_cd, com_entrada=True):
    """Cria um ControlePortaria ja com chegada (e opcionalmente entrada), pronto p/ saida."""
    reg = ControlePortaria(
        motorista_id=motorista_id,
        placa='ABC-1234',
        tipo_carga='Entrega',
        empresa='Empresa Teste',
        embarque_id=embarque_id,
        local_cd=local_cd,
        data_chegada=date(2026, 1, 10),
        hora_chegada=time(8, 0),
    )
    if com_entrada:
        reg.data_entrada = date(2026, 1, 10)
        reg.hora_entrada = time(9, 0)
    db.session.add(reg)
    db.session.flush()
    return reg


def _user_portaria():
    u = MagicMock()
    u.is_authenticated = True
    u.id = 1
    u.nome = 'Porteiro Teste'
    u.email = 'porteiro@test.com'
    u.perfil = 'logistica'
    u.perfil_nome = 'Logistica'
    u.pode_acessar_portaria = lambda: True
    return u


# ---------------------------------------------------------------------------
# (a) veiculos_do_dia filtrado por local_cd
# ---------------------------------------------------------------------------

def test_veiculos_do_dia_filtra_por_local_cd(db):
    """veiculos_do_dia(local_cd='TENENTE_MARQUES') retorna so TM; sem filtro, todos."""
    mid = _novo_motorista(db)

    # Dois registros pendentes (data_saida NULL): 1 VM, 1 TM
    reg_vm = _registro_portaria(db, mid, None, LOCAL_CD_VICTORIO_MARCHEZINE)
    reg_tm = _registro_portaria(db, mid, None, LOCAL_CD_TENENTE_MARQUES)
    db.session.flush()

    todos = ControlePortaria.veiculos_do_dia()
    ids_todos = {r.id for r in todos}
    assert reg_vm.id in ids_todos
    assert reg_tm.id in ids_todos

    so_tm = ControlePortaria.veiculos_do_dia(local_cd=LOCAL_CD_TENENTE_MARQUES)
    ids_tm = {r.id for r in so_tm}
    assert reg_tm.id in ids_tm
    assert reg_vm.id not in ids_tm
    assert all(r.local_cd == LOCAL_CD_TENENTE_MARQUES for r in so_tm)

    so_vm = ControlePortaria.veiculos_do_dia(local_cd=LOCAL_CD_VICTORIO_MARCHEZINE)
    ids_vm = {r.id for r in so_vm}
    assert reg_vm.id in ids_vm
    assert reg_tm.id not in ids_vm


def test_historico_filtra_por_local_cd(db):
    """historico(local_cd='TENENTE_MARQUES') retorna so registros TM."""
    mid = _novo_motorista(db)
    reg_vm = _registro_portaria(db, mid, None, LOCAL_CD_VICTORIO_MARCHEZINE)
    reg_tm = _registro_portaria(db, mid, None, LOCAL_CD_TENENTE_MARQUES)
    db.session.flush()

    pag_tm = ControlePortaria.historico(local_cd=LOCAL_CD_TENENTE_MARQUES, per_page=100)
    ids_tm = {r.id for r in pag_tm.items}
    assert reg_tm.id in ids_tm
    assert reg_vm.id not in ids_tm

    pag_todos = ControlePortaria.historico(per_page=100)
    ids_todos = {r.id for r in pag_todos.items}
    assert reg_vm.id in ids_todos
    assert reg_tm.id in ids_todos


# ---------------------------------------------------------------------------
# Hooks externos (CarVia/Nacom/Assai/sincronizar) — no-op para isolar o invariante
# ---------------------------------------------------------------------------

@pytest.fixture
def _mock_hooks_saida():
    """Neutraliza os hooks externos chamados na saida (services Odoo/monitoramento).

    Eles ja sao try/except na rota, mas mockar evita lentidao/IO e ruido.
    A propagacao de Separacao.data_embarque (sob teste) NAO e mockada.
    """
    patches = [
        # CSRF nao e o objeto deste teste; validate_api_csrf usa validate_csrf direto
        # (ignora WTF_CSRF_ENABLED=False) e e importado localmente na rota -> patch na origem.
        patch('app.utils.csrf_helper.validate_api_csrf', lambda *a, **k: True),
        patch('app.portaria.routes.sincronizar_entrega_por_nf', lambda *a, **k: None),
        patch('app.carvia.services.documentos.carvia_frete_service.CarviaFreteService.lancar_frete_carvia',
              staticmethod(lambda *a, **k: [])),
        patch('app.fretes.routes.processar_lancamento_automatico_fretes',
              lambda *a, **k: (True, '')),
        patch('app.utils.sincronizar_entregas_carvia.sincronizar_entrega_carvia_por_nf',
              lambda *a, **k: None),
        patch('app.utils.sincronizar_entregas_op_assai.sincronizar_entregas_op_assai_por_embarque',
              lambda *a, **k: 0),
    ]
    started = [p.start() for p in patches]
    try:
        yield
    finally:
        for p in patches:
            p.stop()


def _post_saida(client, registro_id, local_cd):
    return client.post('/portaria/registrar_movimento', data={
        'acao': 'saida',
        'registro_id': registro_id,
        'local_cd': local_cd,
    }, follow_redirects=False)


# ---------------------------------------------------------------------------
# (b) embarque MISTO — saida VM propaga so itens VM
# ---------------------------------------------------------------------------

def test_saida_vm_em_embarque_misto_propaga_so_item_vm(db, client, _mock_hooks_saida):
    suf = uuid.uuid4().hex[:8]
    lote_vm = f'LOTE-VM-{suf}'
    lote_tm = f'LOTE-TM-{suf}'
    nf_vm = f'NFVM{suf[:6]}'
    nf_tm = f'NFTM{suf[:6]}'

    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, lote_vm, nf_vm)
    _novo_item(db, eid, LOCAL_CD_TENENTE_MARQUES, lote_tm, nf_tm)
    _nova_separacao(db, lote_vm, nf_vm)
    _nova_separacao(db, lote_tm, nf_tm)

    reg_vm = _registro_portaria(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE)
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user_portaria()):
        resp = _post_saida(client, reg_vm.id, LOCAL_CD_VICTORIO_MARCHEZINE)
    assert resp.status_code in (302, 303)

    sep_vm = Separacao.query.filter_by(separacao_lote_id=lote_vm).first()
    sep_tm = Separacao.query.filter_by(separacao_lote_id=lote_tm).first()

    # Item VM recebeu data_embarque; item TM continua sem data (espera a saida TM)
    assert sep_vm.data_embarque is not None, "Separacao do item VM deveria ter data_embarque"
    assert sep_tm.data_embarque is None, "Separacao do item TM NAO deveria ter data ainda"


def test_saida_tm_posterior_propaga_item_tm(db, client, _mock_hooks_saida):
    """Continuacao do cenario misto: a saida TM (2o registro) propaga o item TM,
    mesmo com Embarque.data_embarque ja preenchido pela saida VM (idempotencia por local)."""
    suf = uuid.uuid4().hex[:8]
    lote_vm = f'LOTE-VM-{suf}'
    lote_tm = f'LOTE-TM-{suf}'
    nf_vm = f'NFVM{suf[:6]}'
    nf_tm = f'NFTM{suf[:6]}'

    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, lote_vm, nf_vm)
    _novo_item(db, eid, LOCAL_CD_TENENTE_MARQUES, lote_tm, nf_tm)
    _nova_separacao(db, lote_vm, nf_vm)
    _nova_separacao(db, lote_tm, nf_tm)

    reg_vm = _registro_portaria(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE)
    reg_tm = _registro_portaria(db, mid, eid, LOCAL_CD_TENENTE_MARQUES)
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user_portaria()):
        _post_saida(client, reg_vm.id, LOCAL_CD_VICTORIO_MARCHEZINE)
        # Apos VM: cabecalho data_embarque preenchido, TM ainda NULL
        assert Separacao.query.filter_by(separacao_lote_id=lote_tm).first().data_embarque is None
        # Agora a saida TM
        resp = _post_saida(client, reg_tm.id, LOCAL_CD_TENENTE_MARQUES)
    assert resp.status_code in (302, 303)

    sep_tm = Separacao.query.filter_by(separacao_lote_id=lote_tm).first()
    assert sep_tm.data_embarque is not None, "Saida TM deveria propagar data_embarque do item TM"


# ---------------------------------------------------------------------------
# (c) regressao Nacom — embarque 100% VM, 1 registro VM
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# (d) embarques_pendentes_do_cd_query — seletor de embarque 2CD-aware
#     Regressao do bug: a 1a saida de QUALQUER CD carimba Embarque.data_embarque
#     (cabecalho agregado) e os seletores legados (`data_embarque IS NULL`)
#     escondiam o embarque misto do 2o CD. O helper usa o criterio por-CD.
# ---------------------------------------------------------------------------

def _marcar_saida(db, registro):
    """Carimba data/hora de saida num registro existente (sem passar pela rota)."""
    registro.data_saida = date(2026, 1, 10)
    registro.hora_saida = time(17, 0)
    db.session.flush()


def test_helper_misto_pos_saida_tm_continua_pendente_vm(db):
    """Apos a saida TM (que ja carimbou Embarque.data_embarque), o embarque misto
    DEVE continuar pendente para a VM e NAO mais para a TM."""
    suf = uuid.uuid4().hex[:8]
    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'L-VM-{suf}', f'NFVM{suf[:6]}')
    _novo_item(db, eid, LOCAL_CD_TENENTE_MARQUES, f'L-TM-{suf}', f'NFTM{suf[:6]}')

    # 1a saida pela TM: registro TM com saida + cabecalho data_embarque preenchido
    reg_tm = _registro_portaria(db, mid, eid, LOCAL_CD_TENENTE_MARQUES)
    _marcar_saida(db, reg_tm)
    db.session.execute(
        text("UPDATE embarques SET data_embarque = :d WHERE id = :id"),
        {'d': date(2026, 1, 10), 'id': eid},
    )
    db.session.flush()

    pend_vm = {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_VICTORIO_MARCHEZINE).all()}
    pend_tm = {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_TENENTE_MARQUES).all()}

    assert eid in pend_vm, "Embarque misto deveria seguir pendente para a VM apos a saida TM"
    assert eid not in pend_tm, "TM ja deu saida -> nao deveria mais constar como pendente TM"


def test_helper_apos_ambas_saidas_nao_lista(db):
    """Com saida registrada nos DOIS CDs, o embarque some de ambos os seletores."""
    suf = uuid.uuid4().hex[:8]
    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'L-VM-{suf}', f'NFVM{suf[:6]}')
    _novo_item(db, eid, LOCAL_CD_TENENTE_MARQUES, f'L-TM-{suf}', f'NFTM{suf[:6]}')

    reg_vm = _registro_portaria(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE)
    reg_tm = _registro_portaria(db, mid, eid, LOCAL_CD_TENENTE_MARQUES)
    _marcar_saida(db, reg_vm)
    _marcar_saida(db, reg_tm)
    db.session.flush()

    pend_vm = {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_VICTORIO_MARCHEZINE).all()}
    pend_tm = {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_TENENTE_MARQUES).all()}

    assert eid not in pend_vm
    assert eid not in pend_tm


def test_helper_regressao_nacom_puro(db):
    """Nacom puro (100% VM): pendente VM antes da saida; some apos a saida VM."""
    suf = uuid.uuid4().hex[:8]
    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'L-A-{suf}', f'NFA{suf[:6]}')
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'L-B-{suf}', f'NFB{suf[:6]}')

    antes = {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_VICTORIO_MARCHEZINE).all()}
    assert eid in antes, "Embarque Nacom novo deveria estar pendente para a VM"
    # Nunca foi pendente da TM (sem itens TM)
    assert eid not in {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_TENENTE_MARQUES).all()}

    reg_vm = _registro_portaria(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE)
    _marcar_saida(db, reg_vm)
    db.session.flush()

    depois = {e.id for e in ControlePortaria.embarques_pendentes_do_cd_query(
        LOCAL_CD_VICTORIO_MARCHEZINE).all()}
    assert eid not in depois, "Apos a saida VM o embarque nao deve mais constar pendente"


def test_regressao_nacom_100pct_vm_propaga_todos_itens(db, client, _mock_hooks_saida):
    suf = uuid.uuid4().hex[:8]
    lote_1 = f'LOTE-A-{suf}'
    lote_2 = f'LOTE-B-{suf}'
    nf_1 = f'NFA{suf[:6]}'
    nf_2 = f'NFB{suf[:6]}'

    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, lote_1, nf_1)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, lote_2, nf_2)
    _nova_separacao(db, lote_1, nf_1)
    _nova_separacao(db, lote_2, nf_2)

    reg_vm = _registro_portaria(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE)
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user_portaria()):
        resp = _post_saida(client, reg_vm.id, LOCAL_CD_VICTORIO_MARCHEZINE)
    assert resp.status_code in (302, 303)

    sep_1 = Separacao.query.filter_by(separacao_lote_id=lote_1).first()
    sep_2 = Separacao.query.filter_by(separacao_lote_id=lote_2).first()

    # Comportamento atual: 1 saida VM carimba TODOS os itens (todos sao VM)
    assert sep_1.data_embarque is not None
    assert sep_2.data_embarque is not None
    # nf_cd foi resetado (regra Nacom: sincronizacao de entregas)
    assert sep_1.nf_cd is False
    assert sep_2.nf_cd is False
