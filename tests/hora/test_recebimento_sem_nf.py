import uuid
from datetime import date as _date
from app import db as _db
from app.hora.models import (
    HoraNfEntrada, HoraRecebimento, HoraRecebimentoEsperado, HoraMoto,
)
from app.hora.services import recebimento_service
from app.hora.services.moto_service import status_atual
from app.utils.timezone import agora_utc_naive


def _chassi(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def test_nf_provisoria_property(db, loja_factory):
    loja = loja_factory()
    nf = HoraNfEntrada(
        chave_44='PROV' + uuid.uuid4().hex, numero_nf='PROV-1',
        cnpj_emitente='', cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id, data_emissao=_date.today(),
        valor_total=0, tipo='PROVISORIA', criado_em=agora_utc_naive(),
    )
    _db.session.add(nf); _db.session.flush()
    assert nf.provisoria is True
    nf.tipo = 'REAL'
    assert nf.provisoria is False


def test_criar_recebimento_sem_nf_materializa_snapshot(db, loja_factory, pedido_compra_factory):
    from app.hora.models import HoraPedido
    chassi_a = _chassi('AAA')
    pedido = pedido_compra_factory([chassi_a])          # status ABERTO, loja = loja_origem
    loja_id = pedido.loja_destino_id

    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    _db.session.expire_all()

    nf = HoraNfEntrada.query.get(rec.nf_id)
    assert nf.provisoria is True
    esperados = HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec.id).all()
    assert len(esperados) == 1
    assert esperados[0].chassi_esperado == chassi_a
    assert esperados[0].pedido_id == pedido.id
