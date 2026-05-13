"""Testes alterar_carregamento (S6=a reabre).

Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md (Task 13)

Os fixtures montam o estado FINALIZADO diretamente (sem depender de
escanear_carregamento_item/finalizar_carregamento que sao desenvolvidos
em paralelo nas Tasks 5-12).
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiLoja, AssaiModelo, AssaiMoto,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCarregamento, AssaiCarregamentoItem,
    PEDIDO_STATUS_ABERTO,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_CARREGADA,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO, CARREGAMENTO_STATUS_CANCELADO,
)
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, alterar_carregamento,
    CarregamentoStateError,
)
from app.utils.timezone import agora_brasil_naive


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_finalizado(app, admin):
    """Monta Carregamento FINALIZADO + Sep CARREGADA + 1 chassi."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()

    uid = _uid()
    pedido = AssaiPedidoVenda(numero=f'TST-AC-{uid}', status=PEDIDO_STATUS_ABERTO,
                              criado_por_id=admin.id)
    db.session.add(pedido); db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl); db.session.flush()

    chassi = f'TST_AC_{_uid()}'
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto); db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                         status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep); db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id,
        valor_unitario_qpa=1000.0,
    ))

    car = criar_carregamento(pedido.id, loja.id, operador_id=admin.id)
    db.session.flush()
    db.session.add(AssaiCarregamentoItem(
        carregamento_id=car.id, chassi=chassi, modelo_id=modelo.id,
        escaneado_por_id=admin.id,
    ))

    # Marca como FINALIZADO + vincula a sep
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    car.finalizado_por_id = admin.id
    car.separacao_id = sep.id
    db.session.commit()
    return car, pedido, loja, modelo, sep


def test_alterar_carregamento_finalizado_volta_em_carregamento(app, admin_user):
    """S6=a: alterar reabre Carregamento (FINALIZADO -> EM_CARREGAMENTO)."""
    with app.app_context():
        car, _, _, _, _ = _setup_finalizado(app, admin_user)
        assert car.status == CARREGAMENTO_STATUS_FINALIZADO

        alterar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        car_ref = AssaiCarregamento.query.get(car.id)
        assert car_ref.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
        assert car_ref.finalizado_em is None  # reset
        assert car_ref.finalizado_por_id is None
        db.session.rollback()


def test_alterar_carregamento_em_carregamento_falha(app, admin_user):
    """Carregamento ja EM_CARREGAMENTO nao pode ser 'reaberto'."""
    with app.app_context():
        car, _, _, _, _ = _setup_finalizado(app, admin_user)
        car.status = CARREGAMENTO_STATUS_EM_CARREGAMENTO
        db.session.commit()

        with pytest.raises(CarregamentoStateError, match='ja EM_CARREGAMENTO'):
            alterar_carregamento(car.id, operador_id=admin_user.id)
        db.session.rollback()


def test_alterar_carregamento_cancelado_falha(app, admin_user):
    """Carregamento CANCELADO nao pode ser reaberto — operador deve criar outro."""
    with app.app_context():
        car, _, _, _, _ = _setup_finalizado(app, admin_user)
        car.status = CARREGAMENTO_STATUS_CANCELADO
        db.session.commit()

        with pytest.raises(CarregamentoStateError, match='CANCELADO'):
            alterar_carregamento(car.id, operador_id=admin_user.id)
        db.session.rollback()


def test_alterar_carregamento_regrede_sep_carregada_para_fechada(app, admin_user):
    """H3 fix: Sep vinculada CARREGADA regrede para FECHADA quando Carregamento reabre.

    Mantem invariante "Sep CARREGADA <-> Carregamento FINALIZADO".
    """
    with app.app_context():
        car, _, _, _, sep = _setup_finalizado(app, admin_user)
        sep_id = car.separacao_id
        assert sep_id is not None

        sep_antes = AssaiSeparacao.query.get(sep_id)
        assert sep_antes.status == SEPARACAO_STATUS_CARREGADA

        alterar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # H3: Sep regrediu para FECHADA
        sep_depois = AssaiSeparacao.query.get(sep_id)
        assert sep_depois.status == SEPARACAO_STATUS_FECHADA
        # Carregamento esta EM_CARREGAMENTO
        car_ref = AssaiCarregamento.query.get(car.id)
        assert car_ref.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
        # Vinculo FK preservado (separacao_id continua apontando para mesma sep)
        assert car_ref.separacao_id == sep_id
        db.session.rollback()
