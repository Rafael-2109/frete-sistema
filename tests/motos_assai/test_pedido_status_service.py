"""Testes para recalcular_status_pedido.

Spec: §14
Plano: Task 17
"""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiPedidoVendaLoja,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCd, AssaiLoja, AssaiModelo, AssaiMoto,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_FECHADA,
)
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_pedido(app):
    """Cria pedido com 10 motos pedidas, 2 seps."""
    cd = AssaiCd(nome='CD Teste', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja Teste')
    modelo = AssaiModelo(codigo='SOL', regex_chassi=r'^TEST\d+$')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()

    pedido = AssaiPedidoVenda(numero='TEST001', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()

    pedido_loja = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pedido_loja)
    db.session.flush()

    item = AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pedido_loja.id,
        loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0,
    )
    db.session.add(item)
    db.session.commit()

    return pedido, modelo, loja


def test_recalcular_zero_faturada_retorna_aberto(setup_pedido):
    pedido, modelo, loja = setup_pedido
    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_ABERTO


def test_recalcular_parcial_retorna_parcialmente_faturado(setup_pedido):
    pedido, modelo, loja = setup_pedido

    # Criar sep FATURADA com 3 chassis (parcial: 3/10)
    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()

    for i in range(3):
        moto = AssaiMoto(chassi=f'TEST00{i}', modelo_id=modelo.id, cor='Preto')
        db.session.add(moto)
        db.session.flush()
        sep_item = AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=moto.chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        )
        db.session.add(sep_item)
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_PARCIALMENTE_FATURADO


def test_recalcular_total_retorna_faturado(setup_pedido):
    pedido, modelo, loja = setup_pedido

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()

    for i in range(10):
        moto = AssaiMoto(chassi=f'TEST10{i}', modelo_id=modelo.id, cor='Preto')
        db.session.add(moto)
        db.session.flush()
        sep_item = AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=moto.chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        )
        db.session.add(sep_item)
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_FATURADO


def test_recalcular_pedido_cancelado_nao_muda(setup_pedido):
    pedido, modelo, loja = setup_pedido
    pedido.status = PEDIDO_STATUS_CANCELADO
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_CANCELADO  # Status manual nao muda


def test_recalcular_sep_fechada_nao_conta(setup_pedido):
    """Sep FECHADA (sem NF batida) NAO conta como faturada."""
    pedido, modelo, loja = setup_pedido

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep)
    db.session.flush()

    for i in range(5):
        moto = AssaiMoto(chassi=f'TESTF0{i}', modelo_id=modelo.id, cor='Preto')
        db.session.add(moto)
        db.session.flush()
        sep_item = AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=moto.chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        )
        db.session.add(sep_item)
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_ABERTO  # FECHADA nao conta
