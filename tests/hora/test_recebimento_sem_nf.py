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
