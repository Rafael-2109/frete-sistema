import uuid
import pytest
from app.veiculos.models import Veiculo
from app.carteira.services.roteirizacao_service import selecionar_veiculo


@pytest.fixture(autouse=True)
def _isola_veiculos(db):
    """Desativa os veiculos pre-existentes do banco local (savepoint reverte no
    fim) para que cada teste controle o universo de candidatos."""
    Veiculo.query.update({Veiculo.ativo: False})
    db.session.flush()
    yield


def _mk(db, nome, peso, pallets=None, m3=None, ativo=True):
    v = Veiculo(nome=f'{nome}_{uuid.uuid4().hex[:6]}', peso_maximo=peso,
                capacidade_pallets=pallets, capacidade_m3=m3, ativo=ativo)
    db.session.add(v)
    db.session.flush()
    return v


def test_escolhe_menor_que_comporta_peso(db):
    _mk(db, 'TOCO', 6500, pallets=14)
    _mk(db, 'TRUCK', 14500, pallets=28)
    v = selecionar_veiculo(5000, pallets=10)
    assert v.peso_maximo == 6500


def test_pula_quem_nao_comporta_pallets(db):
    _mk(db, 'TOCO', 6500, pallets=14)
    truck = _mk(db, 'TRUCK', 14500, pallets=28)
    v = selecionar_veiculo(3000, pallets=20)  # peso cabe no TOCO, pallets nao
    assert v.id == truck.id


def test_ignora_inativos(db):
    _mk(db, 'TOCO', 6500, pallets=14, ativo=False)
    truck = _mk(db, 'TRUCK', 14500, pallets=28)
    v = selecionar_veiculo(3000, pallets=10)
    assert v.id == truck.id


def test_fallback_maior_quando_nada_comporta(db):
    _mk(db, 'TOCO', 6500)
    truck = _mk(db, 'TRUCK', 14500)
    v = selecionar_veiculo(99999)
    assert v.id == truck.id
