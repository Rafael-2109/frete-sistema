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


def test_conferencia_provisoria_casa_modelo_e_chassi_extra(db, loja_factory, pedido_compra_factory, modelo_moto):
    chassi_ped = _chassi('PED')           # item do pedido COM chassi
    pedido = pedido_compra_factory([chassi_ped])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=2, usuario='tester')

    # (a) chassi do snapshot -> RECEBIDA/CONFERIDA, sem CHASSI_EXTRA
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    # (b) chassi fora do snapshot -> CHASSI_EXTRA, sem bloquear
    chassi_extra = _chassi('EXT')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_extra,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    _db.session.expire_all()
    assert status_atual(chassi_ped) in ('RECEBIDA', 'CONFERIDA')
    assert HoraMoto.query.get(chassi_ped) is not None
    # chassi do snapshot CASA (nao vira CHASSI_EXTRA) e consome o slot
    conf_ped = next(c for c in rec.conferencias if c.numero_chassi == chassi_ped)
    assert not any(d.tipo == 'CHASSI_EXTRA' for d in conf_ped.divergencias)
    esperado = HoraRecebimentoEsperado.query.filter_by(
        recebimento_id=rec.id, chassi_esperado=chassi_ped).first()
    assert esperado is not None and esperado.consumido_por_conferencia_id == conf_ped.id
    conf_extra = next(c for c in rec.conferencias if c.numero_chassi == chassi_extra)
    assert any(d.tipo == 'CHASSI_EXTRA' for d in conf_extra.divergencias)

    rec = recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')
    _db.session.expire_all()
    # D8: provisorio NAO gera MOTO_FALTANDO
    faltando = [c for c in rec.conferencias if c.tipo_divergencia == 'MOTO_FALTANDO']
    assert faltando == []


def test_anexar_nf_real_promove_e_reprocessa(db, loja_factory, pedido_compra_factory, modelo_moto):
    chassi = _chassi('REAL')
    pedido = pedido_compra_factory([chassi])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='tester')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')

    payload = {
        'nf': {'chave_44': uuid.uuid4().hex.zfill(44), 'numero_nf': '12345',
               'cnpj_emitente': '12345678000199', 'cnpj_destinatario': '00000000000000',
               'data_emissao': _date.today(), 'valor_total': 5000},
        'itens': [{'numero_chassi': chassi, 'preco_real': 5000,
                   'modelo_texto_original': modelo_moto.nome_modelo, 'cor_texto_original': 'PRETA'}],
    }
    nf = recebimento_service.anexar_nf_real_ao_recebimento(
        recebimento_id=rec.id, pdf_bytes=b'', operador='tester', payload=payload)
    _db.session.expire_all()
    assert nf.tipo == 'REAL'
    assert nf.numero_nf == '12345'
    from app.hora.models import HoraNfEntradaItem
    assert HoraNfEntradaItem.query.filter_by(nf_id=nf.id, numero_chassi=chassi).count() == 1
