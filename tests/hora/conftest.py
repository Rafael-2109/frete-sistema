"""Fixtures compartilhadas dos testes HORA."""
import pytest

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraMoto  # noqa: F401
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


@pytest.fixture
def loja_origem(db):
    loja = HoraLoja(
        cnpj='11111111000101',
        apelido='LojaOrigemTest',
        razao_social='Loja Origem LTDA',
        nome_fantasia='Loja Origem',
        ativa=True,
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


@pytest.fixture
def loja_destino(db):
    loja = HoraLoja(
        cnpj='22222222000102',
        apelido='LojaDestinoTest',
        razao_social='Loja Destino LTDA',
        nome_fantasia='Loja Destino',
        ativa=True,
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


@pytest.fixture
def modelo_moto(db):
    m = HoraModelo(nome_modelo='TESTE-MODEL', ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


@pytest.fixture
def chassi_em_estoque(db, loja_origem, modelo_moto):
    """Cria moto e registra RECEBIDA + CONFERIDA na loja_origem."""
    chassi = '9ABCDTESTFIXTURE0000000000'
    get_or_create_moto(
        numero_chassi=chassi,
        modelo_nome=modelo_moto.nome_modelo,
        cor='PRETA',
        criado_por='fixture',
    )
    registrar_evento(
        numero_chassi=chassi, tipo='RECEBIDA',
        loja_id=loja_origem.id, operador='fixture',
    )
    registrar_evento(
        numero_chassi=chassi, tipo='CONFERIDA',
        loja_id=loja_origem.id, operador='fixture',
    )
    _db.session.flush()
    return chassi
