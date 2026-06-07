"""Testes da aprovacao de desconto acima do teto (roadmap #28, Fatia 2).

confirmar_venda BLOQUEIA quando ha item-moto com desconto acima do teto do
modelo, ate aprovacao. Auto-contidos com uuid. Ver [[gotcha_testes_hora_residuo]].
"""
import uuid
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services import venda_service, aprovacao_desconto_service
from app.hora.models import (
    HoraVenda, HoraVendaItem, HoraMoto, HoraModelo, HoraAprovacaoDesconto,
)
from app.utils.timezone import agora_utc_naive


def _chassi():
    return f'AP{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def _venda_item_desconto(loja, desconto, teto):
    modelo = HoraModelo(
        nome_modelo=f'TST-{uuid.uuid4().hex[:8].upper()}', ativo=True,
        desconto_maximo=teto,
    )
    _db.session.add(modelo)
    _db.session.flush()
    chassi = _chassi()
    _db.session.add(HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA'))
    _db.session.flush()
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cli',
        valor_total=Decimal('1000') - desconto, status='COTACAO',
        data_venda=agora_utc_naive().date(), origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    item = HoraVendaItem(
        venda_id=v.id, numero_chassi=chassi,
        preco_tabela_referencia=Decimal('1000'),
        desconto_aplicado=desconto, desconto_percentual=0,
        preco_final=Decimal('1000') - desconto,
    )
    _db.session.add(item)
    _db.session.flush()
    return v


def test_descontos_acima_teto_detecta(db, loja_factory):
    v = _venda_item_desconto(loja_factory(), desconto=Decimal('200'), teto=Decimal('100'))
    estourados = aprovacao_desconto_service.descontos_acima_teto(v)
    assert len(estourados) == 1
    assert estourados[0]['desconto'] == Decimal('200')
    assert estourados[0]['teto'] == Decimal('100')


def test_sem_teto_nao_estoura(db, loja_factory):
    v = _venda_item_desconto(loja_factory(), desconto=Decimal('999'), teto=None)
    assert aprovacao_desconto_service.descontos_acima_teto(v) == []


def test_confirmar_bloqueia_desconto_acima_teto(db, loja_factory):
    v = _venda_item_desconto(loja_factory(), desconto=Decimal('200'), teto=Decimal('100'))
    with pytest.raises(venda_service.TransicaoInvalidaError, match='aprovacao'):
        venda_service.confirmar_venda(v.id, usuario='vendedor')
    # criou solicitacao PENDENTE
    ap = HoraAprovacaoDesconto.query.filter_by(venda_id=v.id, status='PENDENTE').first()
    assert ap is not None
    # e a venda continua em COTACAO (nao confirmou)
    assert HoraVenda.query.get(v.id).status == 'COTACAO'


def test_confirmar_libera_apos_aprovacao(db, loja_factory):
    v = _venda_item_desconto(loja_factory(), desconto=Decimal('200'), teto=Decimal('100'))
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.confirmar_venda(v.id, usuario='vendedor')
    ap = HoraAprovacaoDesconto.query.filter_by(venda_id=v.id, status='PENDENTE').first()
    aprovacao_desconto_service.aprovar(ap.id, usuario='gerente')
    # agora confirma normalmente
    venda_service.confirmar_venda(v.id, usuario='vendedor')
    assert HoraVenda.query.get(v.id).status == 'CONFIRMADO'


def test_desconto_dentro_do_teto_confirma_direto(db, loja_factory):
    v = _venda_item_desconto(loja_factory(), desconto=Decimal('50'), teto=Decimal('100'))
    venda_service.confirmar_venda(v.id, usuario='vendedor')
    assert HoraVenda.query.get(v.id).status == 'CONFIRMADO'
    assert HoraAprovacaoDesconto.query.filter_by(venda_id=v.id).count() == 0


def test_rejeitar_desconto(db, loja_factory):
    v = _venda_item_desconto(loja_factory(), desconto=Decimal('200'), teto=Decimal('100'))
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.confirmar_venda(v.id, usuario='vendedor')
    ap = HoraAprovacaoDesconto.query.filter_by(venda_id=v.id, status='PENDENTE').first()
    aprovacao_desconto_service.rejeitar(ap.id, usuario='gerente', motivo='fora da alcada')
    assert HoraAprovacaoDesconto.query.get(ap.id).status == 'REJEITADO'
