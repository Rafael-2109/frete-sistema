"""Fase 1 — reconciliar_embarque_carvia: orquestrador idempotente do embarque CarVia.

Em vez de cada porta lembrar de chamar N helpers (local_cd, totais, entregas, frete),
existe UM ponto: reconciliar_embarque_carvia(embarque_id). Testa a ORQUESTRACAO
(idempotencia, gatilhos, ordem/commit) — os helpers em si ja tem testes proprios.
Ordem: local_cd -> totais -> entregas (commita) -> [commit-trava] -> frete (por ULTIMO,
rollback InFailedSqlTransaction). A via de criacao de frete e exercida E2E pelos testes
de portaria (F3).
"""
import uuid

from app.utils.local_cd import LOCAL_CD_TENENTE_MARQUES, LOCAL_CD_VICTORIO_MARCHEZINE
from app.utils.timezone import agora_utc_naive
from tests.carvia._embarque_builders import (
    mk_transportadora, mk_embarque, mk_nf, mk_embarque_item, mk_frete_simples,
)


def _reconciliar(**kw):
    from app.carvia.services.documentos.embarque_carvia_service import (
        reconciliar_embarque_carvia,
    )
    return reconciliar_embarque_carvia(**kw)


def test_reconciliar_recalcula_totais(db):
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp)
    nf1 = mk_nf(db, 'NF-R1-' + uuid.uuid4().hex[:6])
    nf2 = mk_nf(db, 'NF-R2-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb, nf1.numero_nf, peso=100, valor=1000)
    mk_embarque_item(db, emb, nf2.numero_nf, peso=50, valor=500)

    _reconciliar(embarque_id=emb.id, gatilhos={'totais'})

    db.session.refresh(emb)
    assert float(emb.peso_total) == 150
    assert float(emb.valor_total) == 1500


def test_reconciliar_realinha_local_cd_via_nf(db):
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp)
    nf = mk_nf(db, 'NF-LC-' + uuid.uuid4().hex[:6], local_cd=LOCAL_CD_TENENTE_MARQUES)
    item = mk_embarque_item(db, emb, nf.numero_nf, local_cd=LOCAL_CD_VICTORIO_MARCHEZINE)

    _reconciliar(embarque_id=emb.id, gatilhos={'local_cd'})

    db.session.refresh(item)
    assert item.local_cd == LOCAL_CD_TENENTE_MARQUES


def test_reconciliar_idempotente(db):
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp)
    nf = mk_nf(db, 'NF-ID-' + uuid.uuid4().hex[:6], local_cd=LOCAL_CD_TENENTE_MARQUES)
    item = mk_embarque_item(db, emb, nf.numero_nf,
                            local_cd=LOCAL_CD_VICTORIO_MARCHEZINE, peso=70, valor=700)
    gat = {'local_cd', 'totais', 'entregas'}

    _reconciliar(embarque_id=emb.id, gatilhos=gat)
    db.session.refresh(emb)
    db.session.refresh(item)
    snap = (float(emb.peso_total), float(emb.valor_total), item.local_cd)

    _reconciliar(embarque_id=emb.id, gatilhos=gat)
    db.session.refresh(emb)
    db.session.refresh(item)
    assert (float(emb.peso_total), float(emb.valor_total), item.local_cd) == snap


def test_reconciliar_mixed_embarque_soma_ambos(db):
    """Embarque misto Nacom+CarVia: header soma os 2; item Nacom intocado."""
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp)
    nf = mk_nf(db, 'NF-MX-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb, nf.numero_nf, peso=100, valor=1000)  # CarVia
    nacom = mk_embarque_item(db, emb, 'NAC-' + uuid.uuid4().hex[:6], peso=200, valor=2000,
                             lote_prefixo='LOTE_')  # Nacom-style
    nacom_local = nacom.local_cd

    _reconciliar(embarque_id=emb.id, gatilhos={'totais'})

    db.session.refresh(emb)
    db.session.refresh(nacom)
    assert float(emb.peso_total) == 300
    assert float(emb.valor_total) == 3000
    assert nacom.local_cd == nacom_local


def test_reconciliar_gatilho_totais_nao_toca_frete(db):
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    nf = mk_nf(db, 'NF-GT-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb, nf.numero_nf, status='cancelado', cnpj_dest='33333333000133')
    frete = mk_frete_simples(db, transp, emb, numero_nf=nf.numero_nf, cnpj_dest='33333333000133')

    _reconciliar(embarque_id=emb.id, gatilhos={'totais'})

    db.session.refresh(frete)
    assert frete.status == 'PENDENTE'  # passo frete NAO rodou


def test_reconciliar_frete_cancela_orfao(db):
    """Passo frete roda: item cancelado + frete orfao PENDENTE sem operacao -> CANCELADO."""
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    nf = mk_nf(db, 'NF-OR-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb, nf.numero_nf, status='cancelado', cnpj_dest='33333333000133')
    frete = mk_frete_simples(db, transp, emb, numero_nf=nf.numero_nf, cnpj_dest='33333333000133')

    _reconciliar(embarque_id=emb.id)  # default inclui frete

    db.session.refresh(frete)
    assert frete.status == 'CANCELADO'


def test_reconciliar_embarque_inexistente_nao_quebra(db):
    rel = _reconciliar(embarque_id=999_999_999)
    assert rel is not None
