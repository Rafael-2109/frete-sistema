"""Testes do peca_estoque_service (saldo derivado por SUM)."""
from decimal import Decimal

import pytest

from app.hora.models import HoraPecaMovimento


def test_saldo_inicial_zero(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l = loja_factory()
    assert peca_estoque_service.saldo(p.id, l.id) == Decimal('0')


def test_registrar_entrada(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l = loja_factory()
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=l.id, tipo='ENTRADA_NF',
        qtd=Decimal('5'), motivo='teste',
    )
    db.session.commit()
    assert peca_estoque_service.saldo(p.id, l.id) == Decimal('5')


def test_saida_subtrai(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l = loja_factory()
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=l.id, tipo='ENTRADA_NF', qtd=Decimal('10'),
    )
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=l.id, tipo='SAIDA_VENDA', qtd=Decimal('-3'),
    )
    db.session.commit()
    assert peca_estoque_service.saldo(p.id, l.id) == Decimal('7')


def test_ajuste_manual_positivo(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l = loja_factory()
    peca_estoque_service.ajuste_manual(
        peca_id=p.id, loja_id=l.id,
        qtd_signed=Decimal('5'), motivo='inventario inicial', operador='admin',
    )
    movs = HoraPecaMovimento.query.filter_by(peca_id=p.id).all()
    assert len(movs) == 1
    assert movs[0].tipo == 'AJUSTE_POS'


def test_transferencia_atomica(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l_origem = loja_factory()
    l_destino = loja_factory()
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=l_origem.id, tipo='ENTRADA_NF', qtd=Decimal('10'),
    )
    db.session.commit()
    peca_estoque_service.transferencia(
        peca_id=p.id, loja_origem_id=l_origem.id, loja_destino_id=l_destino.id,
        qtd=Decimal('3'), motivo='transf teste', operador='admin',
    )
    assert peca_estoque_service.saldo(p.id, l_origem.id) == Decimal('7')
    assert peca_estoque_service.saldo(p.id, l_destino.id) == Decimal('3')


def test_transferencia_sem_saldo_falha(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l1 = loja_factory()
    l2 = loja_factory()
    with pytest.raises(ValueError, match='saldo insuficiente'):
        peca_estoque_service.transferencia(
            peca_id=p.id, loja_origem_id=l1.id, loja_destino_id=l2.id,
            qtd=Decimal('5'), motivo='x', operador='admin',
        )


def test_listar_estoque_agregado(db, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    p = peca_factory()
    l = loja_factory()
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=l.id, tipo='ENTRADA_NF', qtd=Decimal('10'),
    )
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=l.id, tipo='ENTRADA_NF', qtd=Decimal('5'),
    )
    db.session.commit()
    rows = peca_estoque_service.listar_estoque(loja_id=l.id, peca_id=p.id)
    assert len(rows) == 1
    assert rows[0]['saldo'] == Decimal('15')
