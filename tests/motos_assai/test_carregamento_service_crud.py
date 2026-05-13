"""Testes CRUD basico de carregamento_service.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Tasks 1-4
"""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiCarregamento,
    AssaiMoto,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_FINALIZADO,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item,
    CarregamentoValidationError, CarregamentoConflictError, CarregamentoStateError,
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


# ============================================================
# Task 2: escanear_carregamento_item (lock pessimista S3=c)
# ============================================================

@pytest.fixture
def chassi_disponivel(setup_pedido_loja):
    pedido, loja, modelo = setup_pedido_loja
    moto = AssaiMoto(chassi='TESTC001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    emitir_evento('TESTC001', EVENTO_ESTOQUE, operador_id=1)
    emitir_evento('TESTC001', EVENTO_MONTADA, operador_id=1)
    emitir_evento('TESTC001', EVENTO_DISPONIVEL, operador_id=1)
    db.session.commit()
    return moto


def test_escanear_chassi_disponivel_sucesso(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()

    item = escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    assert item.id is not None
    assert item.carregamento_id == car.id
    assert item.chassi == 'TESTC001'
    assert item.escaneado_por_id == 1
    # A1: NAO emite evento durante escaneio (apenas no finalize)
    assert status_efetivo('TESTC001') == EVENTO_DISPONIVEL


def test_escanear_chassi_inexistente_falha(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()

    with pytest.raises(CarregamentoValidationError, match='Chassi'):
        escanear_carregamento_item(car.id, 'INEXISTENTE', operador_id=1)


def test_escanear_chassi_em_outro_carregamento_ativo_falha(setup_pedido_loja, chassi_disponivel):
    """S3=c: chassi nao pode estar em 2 carregamentos ativos."""
    pedido, loja, _ = setup_pedido_loja
    car1 = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car1.id, 'TESTC001', operador_id=1)
    db.session.commit()

    car2 = criar_carregamento(pedido.id, loja.id, operador_id=2)
    db.session.flush()
    with pytest.raises(CarregamentoConflictError, match='outro carregamento'):
        escanear_carregamento_item(car2.id, 'TESTC001', operador_id=2)


def test_escanear_carregamento_finalizado_falha(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='FINALIZADO'):
        escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
