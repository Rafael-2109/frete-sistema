"""Testes CRUD basico de carregamento_service.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Tasks 1-4
"""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiCarregamento,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    PEDIDO_STATUS_ABERTO,
)
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, CarregamentoValidationError,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_pedido_loja(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(
        numero='999', cnpj='98765432000100', nome='Loja Teste',
        razao_social='Loja Teste LTDA',
    )
    modelo = AssaiModelo(codigo='SOL', nome='Sol')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='TEST001', status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.commit()
    return pedido, loja, modelo


# ============================================================
# Task 1: criar_carregamento
# ============================================================

def test_criar_carregamento_sucesso(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.commit()

    assert car.id is not None
    assert car.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
    assert car.pedido_id == pedido.id
    assert car.loja_id == loja.id
    assert car.iniciado_por_id == 1
    assert car.iniciado_em is not None
    assert car.separacao_id is None  # so vincula no finalize
    assert car.finalizado_em is None
    assert car.cancelado_em is None


def test_criar_carregamento_pedido_inexistente(setup_pedido_loja):
    _, loja, _ = setup_pedido_loja
    with pytest.raises(CarregamentoValidationError, match='Pedido'):
        criar_carregamento(99999, loja.id, operador_id=1)


def test_criar_carregamento_loja_inexistente(setup_pedido_loja):
    pedido, _, _ = setup_pedido_loja
    with pytest.raises(CarregamentoValidationError, match='Loja'):
        criar_carregamento(pedido.id, 99999, operador_id=1)


def test_criar_carregamento_dois_paralelos_mesma_loja_OK(setup_pedido_loja):
    """A2: 2 carregamentos paralelos no mesmo (pedido, loja) sao permitidos."""
    pedido, loja, _ = setup_pedido_loja
    car1 = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    car2 = criar_carregamento(pedido.id, loja.id, operador_id=2)
    db.session.commit()

    assert car1.id != car2.id
    assert car1.status == car2.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
