"""Testes do gate "frete dispara na ULTIMA saida" (embarque bifurcado por local_cd).

Regra de negocio (item 2 do redesign CarVia, decisao Rafael 2026-06-18):
  Um embarque pode ter itens de 2 CDs (VICTORIO_MARCHEZINE e TENENTE_MARQUES).
  A portaria de cada CD da saida SOMENTE dos seus itens (1 registro por CD).
  O frete (Nacom E CarVia) NAO pode mais disparar na 1a saida — deve esperar a
  ULTIMA saida, isto e, quando TODOS os CDs com itens ativos ja registraram saida.
  Embarque de 1 unico CD (Nacom puro / Op. Assai): a unica saida ja satisfaz (sem regressao).

Cobre:
  (1) `embarque_todos_cds_sairam` (helper puro) — todos os cenarios.
  (2) `verificar_requisitos_para_lancamento_frete` (gate Nacom central) — bloqueia
      enquanto falta saida de algum CD; libera (sai do requisito 0.1) quando todos sairam.
"""
import uuid
from datetime import date, time
from types import SimpleNamespace

from sqlalchemy import text

from app.portaria.models import ControlePortaria
from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE,
    LOCAL_CD_TENENTE_MARQUES,
    cds_pendentes_de_saida,
)


# ---------------------------------------------------------------------------
# (1) Helper puro cds_pendentes_de_saida — fakes via SimpleNamespace
#     Conjunto NAO-vazio => frete deve AGUARDAR. Vazio => liberado.
# ---------------------------------------------------------------------------

def _item(local_cd, status='ativo'):
    return SimpleNamespace(local_cd=local_cd, status=status)


def _reg(local_cd, data_saida):
    return SimpleNamespace(local_cd=local_cd, data_saida=data_saida)


def _emb(itens, registros):
    return SimpleNamespace(itens=itens, registros_portaria=registros)


def test_misto_saida_parcial_retorna_cd_pendente():
    """Embarque VM+TM com so VM saido -> falta TM (bloqueia)."""
    emb = _emb(
        itens=[_item(LOCAL_CD_VICTORIO_MARCHEZINE), _item(LOCAL_CD_TENENTE_MARQUES)],
        registros=[_reg(LOCAL_CD_VICTORIO_MARCHEZINE, date(2026, 1, 10))],
    )
    assert cds_pendentes_de_saida(emb) == {LOCAL_CD_TENENTE_MARQUES}


def test_misto_saida_completa_sem_pendencia():
    """Embarque VM+TM com ambos saidos -> liberado (vazio)."""
    emb = _emb(
        itens=[_item(LOCAL_CD_VICTORIO_MARCHEZINE), _item(LOCAL_CD_TENENTE_MARQUES)],
        registros=[
            _reg(LOCAL_CD_VICTORIO_MARCHEZINE, date(2026, 1, 10)),
            _reg(LOCAL_CD_TENENTE_MARQUES, date(2026, 1, 11)),
        ],
    )
    assert cds_pendentes_de_saida(emb) == set()


def test_nacom_puro_uma_saida_sem_pendencia():
    """Regressao: embarque 100% VM, 1 saida VM -> liberado (comportamento legado)."""
    emb = _emb(
        itens=[_item(LOCAL_CD_VICTORIO_MARCHEZINE), _item(LOCAL_CD_VICTORIO_MARCHEZINE)],
        registros=[_reg(LOCAL_CD_VICTORIO_MARCHEZINE, date(2026, 1, 10))],
    )
    assert cds_pendentes_de_saida(emb) == set()


def test_nacom_puro_sem_registro_portaria_nao_bloqueia():
    """ANTI-REGRESSAO: embarque de 1 CD com data_embarque mas SEM registro de saida
    na portaria NAO deve bloquear (nao-misto -> comportamento legado, frete dispara)."""
    emb = _emb(itens=[_item(LOCAL_CD_VICTORIO_MARCHEZINE)], registros=[])
    assert cds_pendentes_de_saida(emb) == set()


def test_item_sem_flag_conta_como_default_vm():
    """Item local_cd None -> VM (default); embarque de 1 CD -> sem pendencia."""
    emb = _emb(itens=[_item(None)], registros=[])
    assert cds_pendentes_de_saida(emb) == set()


def test_item_cancelado_nao_torna_misto():
    """Item TM CANCELADO nao conta -> embarque vira 1 CD (VM) -> sem pendencia."""
    emb = _emb(
        itens=[
            _item(LOCAL_CD_VICTORIO_MARCHEZINE),
            _item(LOCAL_CD_TENENTE_MARQUES, status='cancelado'),
        ],
        registros=[_reg(LOCAL_CD_VICTORIO_MARCHEZINE, date(2026, 1, 10))],
    )
    assert cds_pendentes_de_saida(emb) == set()


def test_misto_registro_sem_data_saida_conta_como_pendente():
    """Misto VM+TM: registro TM presente mas sem data_saida -> TM ainda pendente."""
    emb = _emb(
        itens=[_item(LOCAL_CD_VICTORIO_MARCHEZINE), _item(LOCAL_CD_TENENTE_MARQUES)],
        registros=[
            _reg(LOCAL_CD_VICTORIO_MARCHEZINE, date(2026, 1, 10)),
            _reg(LOCAL_CD_TENENTE_MARQUES, None),
        ],
    )
    assert cds_pendentes_de_saida(emb) == {LOCAL_CD_TENENTE_MARQUES}


def test_sem_itens_ativos_sem_pendencia():
    emb = _emb(itens=[], registros=[])
    assert cds_pendentes_de_saida(emb) == set()


def test_embarque_none_sem_pendencia():
    assert cds_pendentes_de_saida(None) == set()


# ---------------------------------------------------------------------------
# (2) Integracao — gate Nacom em verificar_requisitos_para_lancamento_frete
# ---------------------------------------------------------------------------

def _novo_embarque_com_data(db):
    """Embarque ativo COM data_embarque preenchido (= ja passou a 1a saida)."""
    row = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga,
                               tipo_cotacao, data_embarque)
        VALUES (:numero, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA', :de)
        RETURNING id
    """), {
        'numero': int(uuid.uuid4().int % 9_000_000) + 1_000_000,
        'de': date(2026, 1, 10),
    }).scalar()
    return row


def _novo_item_nacom(db, embarque_id, local_cd, lote, nf, cnpj):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             nota_fiscal, cnpj_cliente, uf_destino, cidade_destino, status)
        VALUES
            (:eid, :lote, :local, 'Cliente Teste', :pedido,
             :nf, :cnpj, 'SP', 'Sao Paulo', 'ativo')
    """), {
        'eid': embarque_id, 'lote': lote, 'local': local_cd,
        'pedido': f'PED-{lote}', 'nf': nf, 'cnpj': cnpj,
    })


def _novo_motorista(db):
    suf = uuid.uuid4().hex[:8]
    return db.session.execute(text("""
        INSERT INTO motoristas (nome_completo, rg, cpf, telefone)
        VALUES (:nome, :rg, :cpf, :tel) RETURNING id
    """), {
        'nome': f'Motorista {suf}', 'rg': f'RG{suf}',
        'cpf': f'{suf[:3]}.{suf[3:6]}.{suf[6:8]}0-00', 'tel': '(11) 99999-9999',
    }).scalar()


def _registro_saida(db, motorista_id, embarque_id, local_cd, saiu):
    """ControlePortaria do CD; saiu=True grava data_saida/hora_saida."""
    reg = ControlePortaria(
        motorista_id=motorista_id, placa='ABC-1234', tipo_carga='Entrega',
        empresa='Empresa Teste', embarque_id=embarque_id, local_cd=local_cd,
        data_chegada=date(2026, 1, 10), hora_chegada=time(8, 0),
        data_entrada=date(2026, 1, 10), hora_entrada=time(9, 0),
    )
    if saiu:
        reg.data_saida = date(2026, 1, 10)
        reg.hora_saida = time(17, 0)
    db.session.add(reg)
    db.session.flush()
    return reg


def test_verificar_requisitos_bloqueia_quando_falta_saida_de_um_cd(db):
    """Embarque misto VM+TM, so VM saiu -> gate bloqueia citando o CD pendente."""
    from app.fretes.routes import verificar_requisitos_para_lancamento_frete

    suf = uuid.uuid4().hex[:8]
    cnpj = '12345678000199'
    mid = _novo_motorista(db)
    eid = _novo_embarque_com_data(db)
    _novo_item_nacom(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'LOTE-VM-{suf}', f'NFVM{suf[:6]}', cnpj)
    _novo_item_nacom(db, eid, LOCAL_CD_TENENTE_MARQUES, f'LOTE-TM-{suf}', f'NFTM{suf[:6]}', cnpj)
    _registro_saida(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE, saiu=True)
    _registro_saida(db, mid, eid, LOCAL_CD_TENENTE_MARQUES, saiu=False)
    db.session.flush()

    pode, motivo = verificar_requisitos_para_lancamento_frete(eid, cnpj)
    assert pode is False
    assert 'CD' in motivo and 'TENENTE_MARQUES' in motivo, motivo


def test_verificar_requisitos_passa_do_gate_quando_todos_cds_sairam(db):
    """Apos ambos CDs sairem, o gate 0.1 nao e mais o bloqueador (passa para os
    requisitos seguintes — falha por outro motivo, nunca por 'saida de CD')."""
    from app.fretes.routes import verificar_requisitos_para_lancamento_frete

    suf = uuid.uuid4().hex[:8]
    cnpj = '12345678000199'
    mid = _novo_motorista(db)
    eid = _novo_embarque_com_data(db)
    _novo_item_nacom(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'LOTE-VM-{suf}', f'NFVM{suf[:6]}', cnpj)
    _novo_item_nacom(db, eid, LOCAL_CD_TENENTE_MARQUES, f'LOTE-TM-{suf}', f'NFTM{suf[:6]}', cnpj)
    _registro_saida(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE, saiu=True)
    _registro_saida(db, mid, eid, LOCAL_CD_TENENTE_MARQUES, saiu=True)
    db.session.flush()

    _pode, motivo = verificar_requisitos_para_lancamento_frete(eid, cnpj)
    # Pode falhar nos requisitos de faturamento/NF, mas NUNCA mais pelo gate de CD.
    assert 'Aguardando saída dos CDs' not in motivo, motivo


# ---------------------------------------------------------------------------
# (3) Integracao — gate CarVia em CarviaFreteService._processar
# ---------------------------------------------------------------------------

def _nova_transportadora(db):
    suf = uuid.uuid4().hex[:8]
    return db.session.execute(text("""
        INSERT INTO transportadoras (cnpj, razao_social, cidade, uf, ativo)
        VALUES (:cnpj, :rs, 'Sao Paulo', 'SP', true) RETURNING id
    """), {'cnpj': f'{suf}000199', 'rs': f'Transp {suf}'}).scalar()


def _novo_item_carvia(db, embarque_id, local_cd, lote, nf, cnpj):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             nota_fiscal, cnpj_cliente, uf_destino, cidade_destino, status, provisorio)
        VALUES
            (:eid, :lote, :local, 'Cliente CarVia', :pedido,
             :nf, :cnpj, 'SP', 'Sao Paulo', 'ativo', false)
    """), {
        'eid': embarque_id, 'lote': lote, 'local': local_cd,
        'pedido': f'PED-{lote}', 'nf': nf, 'cnpj': cnpj,
    })


def test_carvia_nao_gera_frete_com_saida_parcial(db):
    """CarviaFreteService._processar retorna [] e NAO cria CarviaFrete quando ainda
    falta a saida de um CD (embarque CARVIA misto VM+TM, so VM saiu)."""
    from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService
    from app.carvia.models import CarviaFrete

    suf = uuid.uuid4().hex[:8]
    cnpj = '98765432000111'
    tid = _nova_transportadora(db)
    mid = _novo_motorista(db)
    eid = _novo_embarque_com_data(db)
    db.session.execute(text("UPDATE embarques SET transportadora_id = :tid WHERE id = :eid"),
                       {'tid': tid, 'eid': eid})
    _novo_item_carvia(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'CARVIA-VM-{suf}', f'NFCV{suf[:6]}', cnpj)
    _novo_item_carvia(db, eid, LOCAL_CD_TENENTE_MARQUES, f'CARVIA-TM-{suf}', f'NFCT{suf[:6]}', cnpj)
    _registro_saida(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE, saiu=True)
    _registro_saida(db, mid, eid, LOCAL_CD_TENENTE_MARQUES, saiu=False)
    db.session.flush()

    resultado = CarviaFreteService._processar(eid, 'test@nacom.com')
    assert resultado == []
    assert CarviaFrete.query.filter_by(embarque_id=eid).count() == 0


# ---------------------------------------------------------------------------
# (4) Integracao — gate Op. Assai em verificar_requisitos_op_assai
# ---------------------------------------------------------------------------

def _novo_item_op_assai(db, embarque_id, local_cd, lote, nf, cnpj):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido,
             nota_fiscal, cnpj_cliente, uf_destino, cidade_destino, status)
        VALUES
            (:eid, :lote, :local, 'Cliente Assai', :pedido,
             :nf, :cnpj, 'SP', 'Sao Paulo', 'ativo')
    """), {'eid': embarque_id, 'lote': lote, 'local': local_cd,
           'pedido': f'PED-{lote}', 'nf': nf, 'cnpj': cnpj})


def test_op_assai_bloqueia_quando_falta_saida_de_um_cd(db):
    """Embarque MISTO com item Op. Assai (ASSAI-SEP) VM saido + item TM nao-saido:
    verificar_requisitos_op_assai deve BLOQUEAR (fail-safe do gate)."""
    from app.fretes.routes import verificar_requisitos_op_assai

    suf = uuid.uuid4().hex[:8]
    cnpj = '12345678000199'
    mid = _novo_motorista(db)
    eid = _novo_embarque_com_data(db)
    _novo_item_op_assai(db, eid, LOCAL_CD_VICTORIO_MARCHEZINE, f'ASSAI-SEP-{suf}', f'NFA{suf[:6]}', cnpj)
    _novo_item_carvia(db, eid, LOCAL_CD_TENENTE_MARQUES, f'CARVIA-TM-{suf}', f'NFT{suf[:6]}', cnpj)
    _registro_saida(db, mid, eid, LOCAL_CD_VICTORIO_MARCHEZINE, saiu=True)
    _registro_saida(db, mid, eid, LOCAL_CD_TENENTE_MARQUES, saiu=False)
    db.session.flush()

    pode, motivo = verificar_requisitos_op_assai(eid, cnpj)
    assert pode is False
    assert 'CD' in motivo and 'TENENTE_MARQUES' in motivo, motivo
