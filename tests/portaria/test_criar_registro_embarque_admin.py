"""Testes da rota ADMIN `portaria.criar_registro_embarque`.

Cobre o atalho administrativo que cria um ControlePortaria direto do embarque, ja
com chegada/entrada/saida (datas manuais), disparando a cadeia de efeitos da saida
(`_aplicar_efeitos_saida`):
  (a) cria o registro e carimba data_embarque no Embarque + Separacao (Nacom VM);
  (b) gate admin: perfil nao-administrador e bloqueado (nada criado);
  (c) validacao de coerencia: saida < entrada e rejeitada (nada criado).

Padroes herdados de test_portaria_local_cd.py: cenario via SQL bruto (evita o mapper
de Cotacao), login via patch de flask_login.utils._get_user, hooks de saida mockados.
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import text

from app.portaria.models import ControlePortaria
from app.separacao.models import Separacao
from app.utils.local_cd import LOCAL_CD_VICTORIO_MARCHEZINE


# --------------------------------------------------------------------------- #
# Helpers de cenario (SQL bruto)
# --------------------------------------------------------------------------- #

def _novo_motorista(db):
    suf = uuid.uuid4().hex[:8]
    cpf = f'{suf[:3]}.{suf[3:6]}.{suf[6:8]}0-00'
    return db.session.execute(text("""
        INSERT INTO motoristas (nome_completo, rg, cpf, telefone)
        VALUES (:nome, :rg, :cpf, :tel) RETURNING id
    """), {'nome': f'Motorista {suf}', 'rg': f'RG{suf}', 'cpf': cpf,
           'tel': '(11) 99999-9999'}).scalar()


def _novo_embarque(db):
    return db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga, tipo_cotacao)
        VALUES (:numero, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA')
        RETURNING id
    """), {'numero': int(uuid.uuid4().int % 9_000_000) + 1_000_000}).scalar()


def _novo_item(db, embarque_id, local_cd, lote, nf):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             nota_fiscal, uf_destino, cidade_destino, status)
        VALUES (:eid, :lote, :local, 'Cliente Teste', :pedido, :nf, 'SP', 'Sao Paulo', 'ativo')
    """), {'eid': embarque_id, 'lote': lote, 'local': local_cd,
           'pedido': f'PED-{lote}', 'nf': nf})


def _nova_separacao(db, lote, nf):
    db.session.execute(text("""
        INSERT INTO separacao (separacao_lote_id, cod_uf, numero_nf, data_embarque, nf_cd)
        VALUES (:lote, 'SP', :nf, NULL, true)
    """), {'lote': lote, 'nf': nf})


def _user(perfil='administrador'):
    u = MagicMock()
    u.is_authenticated = True
    u.id = 1
    u.nome = 'Admin Teste'
    u.email = 'admin@test.com'
    u.perfil = perfil
    u.perfil_nome = perfil.title()
    u.pode_acessar_portaria = lambda: True
    return u


@pytest.fixture
def _mock_hooks_saida():
    """Neutraliza os hooks externos da saida (mesmo do test_portaria_local_cd)."""
    patches = [
        patch('app.portaria.routes.sincronizar_entrega_por_nf', lambda *a, **k: None),
        patch('app.carvia.services.documentos.carvia_frete_service.CarviaFreteService.lancar_frete_carvia',
              staticmethod(lambda *a, **k: [])),
        patch('app.fretes.routes.processar_lancamento_automatico_fretes', lambda *a, **k: (True, '')),
        patch('app.utils.sincronizar_entregas_carvia.sincronizar_entrega_carvia_por_nf', lambda *a, **k: None),
        patch('app.utils.sincronizar_entregas_op_assai.sincronizar_entregas_op_assai_por_embarque', lambda *a, **k: 0),
    ]
    started = [p.start() for p in patches]
    try:
        yield
    finally:
        for p in patches:
            p.stop()


def _payload(motorista_id, local_cd=LOCAL_CD_VICTORIO_MARCHEZINE, **over):
    data = {
        'motorista_id': str(motorista_id),
        'placa': 'ABC-1234',
        'tipo_carga': 'Entrega',
        'empresa': 'Transportadora Teste',
        'local_cd': local_cd,
        'data_chegada': '2026-01-10', 'hora_chegada': '08:00',
        'data_entrada': '2026-01-10', 'hora_entrada': '09:00',
        'data_saida': '2026-01-10', 'hora_saida': '17:00',
    }
    data.update(over)
    return data


# --------------------------------------------------------------------------- #
# (a) cria registro + carimba data_embarque
# --------------------------------------------------------------------------- #

def test_admin_cria_registro_e_carimba_data_embarque(db, client, _mock_hooks_saida):
    suf = uuid.uuid4().hex[:8]
    lote = f'LOTE-{suf}'
    nf = f'NF{suf[:6]}'

    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, lote, nf)
    _nova_separacao(db, lote, nf)
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user('administrador')):
        resp = client.post(
            f'/portaria/admin/criar-registro-embarque/{eid}',
            data=_payload(mid), follow_redirects=False,
        )

    assert resp.status_code in (302, 303), resp.data[:500]

    registro = ControlePortaria.query.filter_by(embarque_id=eid).first()
    assert registro is not None, "ControlePortaria deveria ter sido criado"
    assert registro.motorista_id == mid
    assert registro.local_cd == LOCAL_CD_VICTORIO_MARCHEZINE
    assert registro.status == 'SAIU', "Os 3 carimbos -> status SAIU"
    assert registro.data_saida is not None
    assert registro.registrado_por_id == 1

    # Cadeia de efeitos: data_embarque carimbada no Embarque e na Separacao do item
    emb_data = db.session.execute(
        text("SELECT data_embarque FROM embarques WHERE id = :id"), {'id': eid}
    ).scalar()
    assert emb_data is not None, "Embarque.data_embarque deveria ter sido carimbado"

    sep = Separacao.query.filter_by(separacao_lote_id=lote).first()
    assert sep.data_embarque is not None, "Separacao do item deveria receber data_embarque"
    assert sep.nf_cd is False, "nf_cd deveria ter sido resetado na saida"


# --------------------------------------------------------------------------- #
# (b) gate admin
# --------------------------------------------------------------------------- #

def test_gate_admin_bloqueia_nao_administrador(db, client, _mock_hooks_saida):
    suf = uuid.uuid4().hex[:8]
    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'L-{suf}', f'NF{suf[:6]}')
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user('logistica')):
        resp = client.post(
            f'/portaria/admin/criar-registro-embarque/{eid}',
            data=_payload(mid), follow_redirects=False,
        )

    # require_admin redireciona para main.dashboard (302) e NAO cria registro
    assert resp.status_code in (302, 303)
    assert ControlePortaria.query.filter_by(embarque_id=eid).first() is None


# --------------------------------------------------------------------------- #
# (c) coerencia das datas
# --------------------------------------------------------------------------- #

def test_datas_incoerentes_sao_rejeitadas(db, client, _mock_hooks_saida):
    suf = uuid.uuid4().hex[:8]
    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'L-{suf}', f'NF{suf[:6]}')
    db.session.commit()

    # Saida ANTES da entrada -> deve ser rejeitado (re-render 200, nada criado)
    payload = _payload(mid, hora_saida='08:30')  # 08:30 < entrada 09:00
    with patch('flask_login.utils._get_user', return_value=_user('administrador')):
        resp = client.post(
            f'/portaria/admin/criar-registro-embarque/{eid}',
            data=payload, follow_redirects=False,
        )

    assert resp.status_code == 200, "form invalido -> re-render, nao redirect"
    assert ControlePortaria.query.filter_by(embarque_id=eid).first() is None


# --------------------------------------------------------------------------- #
# (d) guard R3 — nao duplica saida do mesmo CD
# --------------------------------------------------------------------------- #

def test_guard_nao_duplica_saida_do_mesmo_cd(db, client, _mock_hooks_saida):
    suf = uuid.uuid4().hex[:8]
    lote = f'LOTE-{suf}'
    nf = f'NF{suf[:6]}'
    mid = _novo_motorista(db)
    eid = _novo_embarque(db)
    _novo_item(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, lote, nf)
    _nova_separacao(db, lote, nf)
    db.session.commit()

    with patch('flask_login.utils._get_user', return_value=_user('administrador')):
        # 1a saida VM -> cria
        r1 = client.post(f'/portaria/admin/criar-registro-embarque/{eid}',
                         data=_payload(mid), follow_redirects=False)
        assert r1.status_code in (302, 303)
        # 2a saida VM -> bloqueada (re-render 200, sem novo registro)
        r2 = client.post(f'/portaria/admin/criar-registro-embarque/{eid}',
                         data=_payload(mid), follow_redirects=False)
        assert r2.status_code == 200

    assert ControlePortaria.query.filter_by(embarque_id=eid).count() == 1
