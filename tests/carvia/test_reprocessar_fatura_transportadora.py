"""Reprocessamento de itens de fatura transportadora ao re-vincular operacao.

IMP-2026-06-19-004 (fatura 83 / Talita): subcontrato anexado a fatura ANTES de
ter operacao_id gera item com nf_id/nf_numero/operacao_id NULL. A rota
vincular_operacao_subcontrato setava operacao_id sem reprocessar os itens — a UI
mostrava "1 NF(s)" com numero "-". O wiring na rota agora chama
reprocessar_itens_fatura_transportadora_por_subcontrato. Aqui testamos o metodo.

Usa o fixture `db` do conftest.py — cada teste em transacao revertida.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime


def _chave_44(prefixo: str = '3525') -> str:
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_operacao(db, valor_merc: float = 5000.0, peso: float = 120.0):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero='CTE' + uuid.uuid4().hex[:6],
        cte_chave_acesso=_chave_44(),
        cte_valor=Decimal('1000.0'),
        cte_data_emissao=datetime(2026, 4, 1).date(),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente Teste',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
        valor_mercadoria=Decimal(str(valor_merc)),
        peso_utilizado=Decimal(str(peso)),
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_nf(db, numero: str):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='12345678000100',
        tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _vincular_nf_operacao(db, op, nf):
    from app.carvia.models import CarviaOperacaoNf
    j = CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id)
    db.session.add(j)
    db.session.flush()
    return j


def _criar_transportadora(db):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj=str(uuid.uuid4().int)[:14], razao_social='Transp Teste',
        cidade='SAO PAULO', uf='SP',
    )
    db.session.add(t)
    db.session.flush()
    return t


def _criar_subcontrato(db):
    from app.carvia.models import CarviaSubcontrato
    transp = _criar_transportadora(db)
    sub = CarviaSubcontrato(
        cte_numero='SUB' + uuid.uuid4().hex[:6],
        transportadora_id=transp.id,
        status='PENDENTE', criado_por='test',
    )
    db.session.add(sub)
    db.session.flush()
    return sub


def _criar_fatura_transp(db):
    from app.carvia.models import CarviaFaturaTransportadora
    transp = _criar_transportadora(db)
    fat = CarviaFaturaTransportadora(
        numero_fatura='FT' + uuid.uuid4().hex[:6],
        transportadora_id=transp.id,
        data_emissao=datetime(2026, 4, 10).date(),
        valor_total=Decimal('500.0'), criado_por='test',
    )
    db.session.add(fat)
    db.session.flush()
    return fat


def _criar_item_orfao(db, fatura, sub):
    """Item como criar_itens_fatura_transportadora gera quando sub.operacao=None."""
    from app.carvia.models import CarviaFaturaTransportadoraItem
    it = CarviaFaturaTransportadoraItem(
        fatura_transportadora_id=fatura.id, subcontrato_id=sub.id,
        operacao_id=None, nf_id=None, nf_numero=None,
        contraparte_cnpj=None, contraparte_nome=None,
        valor_mercadoria=None, peso_kg=None,
        valor_frete=Decimal('500.0'),  # frete fica no item principal
    )
    db.session.add(it)
    db.session.flush()
    return it


def test_reprocessar_preenche_item_orfao(db):
    from app.carvia.services.documentos.linking_service import LinkingService

    op = _criar_operacao(db)
    nf = _criar_nf(db, '700001')
    _vincular_nf_operacao(db, op, nf)
    sub = _criar_subcontrato(db)
    fat = _criar_fatura_transp(db)
    it = _criar_item_orfao(db, fat, sub)
    assert it.nf_id is None and it.operacao_id is None  # orfao

    sub.operacao_id = op.id  # re-vinculacao (como a rota faz)
    db.session.flush()

    stats = LinkingService().reprocessar_itens_fatura_transportadora_por_subcontrato(
        sub.id)
    assert stats['itens_atualizados'] == 1
    db.session.refresh(it)
    assert it.operacao_id == op.id
    assert it.nf_id == nf.id
    assert it.nf_numero == '700001'
    assert it.contraparte_nome == 'Cliente Teste'
    assert it.valor_mercadoria == Decimal('5000.0')
    assert it.valor_frete == Decimal('500.0')  # frete NAO zerado


def test_reprocessar_idempotente(db):
    from app.carvia.models import CarviaFaturaTransportadoraItem
    from app.carvia.services.documentos.linking_service import LinkingService

    op = _criar_operacao(db)
    nf = _criar_nf(db, '700002')
    _vincular_nf_operacao(db, op, nf)
    sub = _criar_subcontrato(db)
    fat = _criar_fatura_transp(db)
    _criar_item_orfao(db, fat, sub)
    sub.operacao_id = op.id
    db.session.flush()

    svc = LinkingService()
    svc.reprocessar_itens_fatura_transportadora_por_subcontrato(sub.id)
    total1 = CarviaFaturaTransportadoraItem.query.filter_by(
        subcontrato_id=sub.id).count()
    stats2 = svc.reprocessar_itens_fatura_transportadora_por_subcontrato(sub.id)
    total2 = CarviaFaturaTransportadoraItem.query.filter_by(
        subcontrato_id=sub.id).count()
    assert total1 == total2  # nao duplica
    assert stats2['itens_criados'] == 0
    assert stats2['itens_atualizados'] == 0  # ja preenchido


def test_reprocessar_cria_suplementar_2a_nf_financeiro_null(db):
    """2a NF da operacao vira item suplementar com financeiros NULL (anti dupla contagem)."""
    from app.carvia.models import CarviaFaturaTransportadoraItem
    from app.carvia.services.documentos.linking_service import LinkingService

    op = _criar_operacao(db)
    nf1 = _criar_nf(db, '700010')
    nf2 = _criar_nf(db, '700011')
    _vincular_nf_operacao(db, op, nf1)
    _vincular_nf_operacao(db, op, nf2)
    sub = _criar_subcontrato(db)
    fat = _criar_fatura_transp(db)
    _criar_item_orfao(db, fat, sub)
    sub.operacao_id = op.id
    db.session.flush()

    stats = LinkingService().reprocessar_itens_fatura_transportadora_por_subcontrato(
        sub.id)
    assert stats['nfs_operacao'] == 2
    assert stats['itens_criados'] == 1  # 1 suplementar para a 2a NF
    itens = CarviaFaturaTransportadoraItem.query.filter_by(
        subcontrato_id=sub.id).all()
    assert len(itens) == 2
    suplementar = [i for i in itens if i.valor_frete is None]
    assert len(suplementar) == 1
    assert suplementar[0].valor_mercadoria is None  # financeiro NULL
    assert suplementar[0].nf_id in (nf1.id, nf2.id)
