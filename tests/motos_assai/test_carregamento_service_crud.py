"""Testes CRUD basico de carregamento_service.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Tasks 1-4
"""
import pytest
from app import db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiCarregamento,
    AssaiCarregamentoItem, AssaiMoto,
    AssaiSeparacao, AssaiSeparacaoItem,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
    SEPARACAO_STATUS_CARREGADA,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA, EVENTO_CARREGADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item,
    cancelar_carregamento_item, cancelar_carregamento,
    CarregamentoValidationError, CarregamentoConflictError, CarregamentoStateError,
)
from app.utils.timezone import agora_brasil_naive


# NOTA: este arquivo usava um fixture `app` local com create_app('testing')
# (SQLite in-memory) + db.create_all(). O SQLite nao renderiza o tipo ARRAY
# (agent_improvement_dialogue.affected_files e Postgres-only) -> 14 ERROR no
# setup. Migrado para o fixture `db` do conftest (Postgres local + SAVEPOINT
# robusto), consistente com o resto da suite. Os db.session.commit() abaixo
# viram commits de savepoint, revertidos no teardown.


@pytest.fixture(autouse=True)
def _garantir_operador_2(db):
    """assai_carregamento.iniciado_por_id/cancelado_por_id tem FK -> usuarios.
    Os testes usam operador_id=1 (Rafael, existe) e operador_id=2. No SQLite
    anterior nao havia FK enforcement; no Postgres garantimos que o usuario 2
    exista (clona o 1). Revertido pelo SAVEPOINT no teardown.
    """
    from sqlalchemy import text
    ja_existe = db.session.execute(
        text("SELECT 1 FROM usuarios WHERE id = 2")
    ).scalar()
    if not ja_existe:
        db.session.execute(text(
            "INSERT INTO usuarios (id, nome, email, senha_hash) "
            "SELECT 2, nome || ' [TEST-OP2]', 'test_op2@savepoint.local', senha_hash "
            "FROM usuarios WHERE id = 1"
        ))
        db.session.flush()


@pytest.fixture
def setup_pedido_loja(db):
    import uuid
    uid = uuid.uuid4().hex[:8].upper()

    def _get_or_create(model, defaults=None, **kw):
        obj = model.query.filter_by(**kw).first()
        if obj:
            return obj
        obj = model(**kw, **(defaults or {}))
        db.session.add(obj)
        db.session.flush()
        return obj

    # Reusa cadastros canonicos quando ja existem (codigo/nome/numero sao
    # UNIQUE) — evita colisao com seeds reais do Postgres (ex: modelo 'SOL').
    _get_or_create(AssaiCd, {'cnpj': '12345678000100'}, nome='CD')
    loja = _get_or_create(
        AssaiLoja,
        {'cnpj': '98765432000100', 'nome': 'Loja Teste',
         'razao_social': 'Loja Teste LTDA'},
        numero='999',
    )
    modelo = _get_or_create(AssaiModelo, {'nome': 'Sol'}, codigo='SOL')
    pedido = AssaiPedidoVenda(numero=f'TEST-{uid}', status=PEDIDO_STATUS_ABERTO)
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
    with pytest.raises(CarregamentoConflictError, match='ja esta no Carregamento'):
        escanear_carregamento_item(car2.id, 'TESTC001', operador_id=2)


def test_escanear_carregamento_finalizado_falha(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='FINALIZADO'):
        escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)


# ============================================================
# Task 3: cancelar_carregamento_item
# ============================================================

def test_cancelar_item_sucesso(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    item = escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    cancelar_carregamento_item(item.id, operador_id=1)
    db.session.commit()

    # Item deletado
    assert AssaiCarregamentoItem.query.get(item.id) is None

    # A1: chassi nunca mudou de evento — continua DISPONIVEL
    assert status_efetivo('TESTC001') == EVENTO_DISPONIVEL


def test_cancelar_item_carregamento_finalizado_falha(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    item = escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='FINALIZADO'):
        cancelar_carregamento_item(item.id, operador_id=1)


# ============================================================
# Task 4: cancelar_carregamento (S5 distincao EM_CARREGAMENTO vs FINALIZADO)
# ============================================================

def test_cancelar_carregamento_em_carregamento_chassi_volta_anterior(setup_pedido_loja, chassi_disponivel):
    """S5: Cancelar Carregamento EM_CARREGAMENTO — chassi volta ao estado anterior (DISPONIVEL)."""
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    cancelar_carregamento(car.id, motivo='Teste cancel', operador_id=2)
    db.session.commit()

    car_ref = AssaiCarregamento.query.get(car.id)
    assert car_ref.status == CARREGAMENTO_STATUS_CANCELADO
    assert car_ref.motivo_cancelamento == 'Teste cancel'
    assert car_ref.cancelado_por_id == 2
    assert car_ref.cancelado_em is not None

    # Chassi volta DISPONIVEL (era DISPONIVEL antes do escaneio — A1 sem evento)
    assert status_efetivo('TESTC001') == EVENTO_DISPONIVEL


def test_cancelar_carregamento_finalizado_chassis_mantem_separada(setup_pedido_loja, chassi_disponivel):
    """S5=b: Cancelar Carregamento FINALIZADO — chassis MANTEM SEPARADA (nao desfaz adicoes)."""
    pedido, loja, modelo = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    # Simular finalizacao manual (sem rodar finalize completo): emitir SEPARADA + CARREGADA
    sep = AssaiSeparacao(
        pedido_id=pedido.id, loja_id=loja.id,
        status=SEPARACAO_STATUS_CARREGADA,
        iniciada_em=agora_brasil_naive(), fechada_em=agora_brasil_naive(),
        fechada_por_id=1,
    )
    db.session.add(sep)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi='TESTC001', modelo_id=modelo.id,
        valor_unitario_qpa=1000.0,
    ))
    emitir_evento('TESTC001', EVENTO_SEPARADA, operador_id=1)
    emitir_evento('TESTC001', EVENTO_CARREGADA, operador_id=1)
    car.separacao_id = sep.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    db.session.commit()

    cancelar_carregamento(car.id, motivo='Erro de carregamento', operador_id=2)
    db.session.commit()

    car_ref = AssaiCarregamento.query.get(car.id)
    assert car_ref.status == CARREGAMENTO_STATUS_CANCELADO

    # Chassi DEVE manter SEPARADA (S5=b — nao desfaz adicoes na sep)
    assert status_efetivo('TESTC001') == EVENTO_CARREGADA

    # Sep NAO foi cancelada (so o carregamento)
    sep_ref = AssaiSeparacao.query.get(sep.id)
    assert sep_ref.status == SEPARACAO_STATUS_CARREGADA  # mantem


def test_cancelar_carregamento_motivo_obrigatorio(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.commit()

    with pytest.raises(CarregamentoValidationError, match='[Mm]otivo'):
        cancelar_carregamento(car.id, motivo='', operador_id=1)


def test_cancelar_carregamento_ja_cancelado_nao_idempotente(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.commit()

    cancelar_carregamento(car.id, motivo='primeiro', operador_id=1)
    db.session.commit()

    # Segunda chamada deve raise (nao e idempotente — ver plano)
    with pytest.raises(CarregamentoStateError, match='ja CANCELADO'):
        cancelar_carregamento(car.id, motivo='segundo', operador_id=1)
