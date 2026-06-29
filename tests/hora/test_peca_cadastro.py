"""Testes do peca_service (cadastro de pecas)."""
from decimal import Decimal

import pytest

from app.hora.models import HoraPeca, HoraTagPlusPecaMap


def test_criar_peca_minima(db):
    import uuid
    from app.hora.services import peca_service
    cod = f'CAP-{uuid.uuid4().hex[:6].upper()}'
    p = peca_service.criar_peca(
        codigo_interno=cod,
        descricao='Capacete preto tamanho M',
    )
    assert p.id is not None
    assert p.codigo_interno == cod
    assert p.cfop_default == '5.102'
    assert p.unidade == 'UN'
    assert p.preco_venda_padrao == Decimal('0')
    assert p.custo == Decimal('0')  # default (hora_59)
    assert p.ativo is True


def test_criar_e_editar_custo(db):
    import uuid
    from app.hora.services import peca_service
    cod = f'CUS-{uuid.uuid4().hex[:6].upper()}'
    p = peca_service.criar_peca(
        codigo_interno=cod, descricao='Bateria',
        preco_venda_padrao=Decimal('200'), custo=Decimal('120'),
    )
    assert p.custo == Decimal('120')
    peca_service.editar_peca(peca_id=p.id, custo=Decimal('135'))
    assert HoraPeca.query.get(p.id).custo == Decimal('135')


def test_codigo_interno_unique(db):
    import uuid
    from app.hora.services import peca_service
    cod = f'DUP-{uuid.uuid4().hex[:6].upper()}'
    peca_service.criar_peca(codigo_interno=cod, descricao='1')
    with pytest.raises(ValueError, match='ja existe'):
        peca_service.criar_peca(codigo_interno=cod, descricao='2')


def test_set_tagplus_map(db, peca_factory):
    from app.hora.services import peca_service
    p = peca_factory()
    peca_service.set_tagplus_map(
        peca_id=p.id, tagplus_produto_id='999', tagplus_codigo='CAP-X',
    )
    m = HoraTagPlusPecaMap.query.filter_by(peca_id=p.id).first()
    assert m is not None
    assert m.tagplus_produto_id == '999'


def test_inativar_peca(db, peca_factory):
    from app.hora.services import peca_service
    p = peca_factory()
    peca_service.inativar_peca(p.id)
    p2 = HoraPeca.query.get(p.id)
    assert p2.ativo is False


def test_descricao_obrigatoria(db):
    from app.hora.services import peca_service
    with pytest.raises(ValueError, match='descricao'):
        peca_service.criar_peca(codigo_interno='X', descricao='')


def test_codigo_obrigatorio(db):
    from app.hora.services import peca_service
    with pytest.raises(ValueError, match='codigo_interno'):
        peca_service.criar_peca(codigo_interno='', descricao='X')


def test_listar_filtra_ativo(db, peca_factory):
    from app.hora.services import peca_service
    p1 = peca_factory()
    p2 = peca_factory()
    peca_service.inativar_peca(p2.id)
    so_ativas = peca_service.listar_pecas(ativo=True)
    ids = {p.id for p in so_ativas}
    assert p1.id in ids
    assert p2.id not in ids
