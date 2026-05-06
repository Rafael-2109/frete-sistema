"""Fixtures compartilhadas dos testes HORA."""
import pytest

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraMoto  # noqa: F401
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _nova_loja(cnpj, apelido, nome):
    from app.utils.timezone import agora_utc_naive
    return HoraLoja(
        cnpj=cnpj,
        apelido=apelido,
        nome=nome,
        razao_social=f'{nome} LTDA',
        nome_fantasia=nome,
        ativa=True,
        atualizado_em=agora_utc_naive(),
    )


@pytest.fixture
def loja_origem(db):
    loja = _nova_loja('11111111000101', 'LojaOrigemTest', 'Loja Origem')
    _db.session.add(loja)
    _db.session.flush()
    return loja


@pytest.fixture
def loja_destino(db):
    loja = _nova_loja('22222222000102', 'LojaDestinoTest', 'Loja Destino')
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
def peca_factory(db):
    """Cria pecas com codigo unico por chamada (uuid p/ evitar colisao entre testes)."""
    import uuid
    from app.hora.services import peca_service

    def make(**kw):
        uid = uuid.uuid4().hex[:8].upper()
        defaults = {
            'codigo_interno': f'TST-{uid}',
            'descricao': f'Peca teste {uid}',
        }
        defaults.update(kw)
        return peca_service.criar_peca(**defaults)
    return make


@pytest.fixture
def loja_factory(db):
    """Cria lojas com CNPJ unico por chamada."""
    import uuid

    def make(**kw):
        uid = uuid.uuid4().hex[:8]
        cnpj_digits = ''.join(c for c in uid if c.isdigit()).ljust(14, '0')[:14]
        defaults = {
            'cnpj': cnpj_digits,
            'apelido': f'Loja{uid}',
            'nome': f'Loja {uid}',
        }
        defaults.update(kw)
        loja = _nova_loja(defaults['cnpj'], defaults['apelido'], defaults['nome'])
        _db.session.add(loja)
        _db.session.flush()
        return loja
    return make


@pytest.fixture
def pedido_compra_factory(db, loja_origem, modelo_moto):
    """Cria pedido de compra com chassis especificados (lista de strings)."""
    import uuid
    from app.hora.models import HoraPedido, HoraPedidoItem, HoraMoto
    from app.utils.timezone import agora_utc_naive
    from datetime import date as _date

    def make(chassis: list[str], **kw):
        uid = uuid.uuid4().hex[:8].upper()
        pedido = HoraPedido(
            numero_pedido=f'TST-PED-{uid}',
            cnpj_destino='99999999000199',
            loja_destino_id=loja_origem.id,
            data_pedido=_date.today(),
            status='ABERTO',
            criado_em=agora_utc_naive(),
        )
        _db.session.add(pedido)
        _db.session.flush()
        for chassi in chassis:
            # garante moto existe
            if not HoraMoto.query.get(chassi):
                m = HoraMoto(numero_chassi=chassi, modelo_id=modelo_moto.id, cor='PRETA')
                _db.session.add(m)
                _db.session.flush()
            item = HoraPedidoItem(
                pedido_id=pedido.id, numero_chassi=chassi,
                modelo_id=modelo_moto.id, preco_compra_esperado=1000,
            )
            _db.session.add(item)
        _db.session.flush()
        return pedido
    return make


@pytest.fixture
def nf_entrada_factory(db, loja_origem, modelo_moto):
    """Cria NF entrada com chassis especificados."""
    import uuid
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem, HoraMoto
    from app.utils.timezone import agora_utc_naive
    from datetime import date as _date

    def make(chassis: list[str], **kw):
        uid = uuid.uuid4().hex[:12].upper()
        nf = HoraNfEntrada(
            chave_44=uid.zfill(44),
            numero_nf=uid[:8],
            cnpj_emitente='12345678000199',
            cnpj_destinatario=loja_origem.cnpj,
            loja_destino_id=loja_origem.id,
            data_emissao=_date.today(),
            valor_total=1000,
            criado_em=agora_utc_naive(),
        )
        _db.session.add(nf)
        _db.session.flush()
        for chassi in chassis:
            if not HoraMoto.query.get(chassi):
                m = HoraMoto(numero_chassi=chassi, modelo_id=modelo_moto.id, cor='PRETA')
                _db.session.add(m)
                _db.session.flush()
            item = HoraNfEntradaItem(
                nf_id=nf.id, numero_chassi=chassi, preco_real=1000,
            )
            _db.session.add(item)
        _db.session.flush()
        return nf
    return make


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
