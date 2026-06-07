"""Testes dos quick-wins do roadmap HORA.

Cobre:
  #6 — origem do lead (normalizacao + regra OUTROS exige obs).
  #8 — foto do chassi obrigatoria na conferencia manual (com isencao do
       fluxo automatico via exigir_foto=False).
  #4 — pre-condicoes do envio de NF por e-mail (sem rede).

Deterministicos, sem rede/SMTP/TagPlus.

NOTA: testes que tocam recebimento sao AUTO-CONTIDOS com uuid (loja/modelo/NF
unicos) porque `iniciar_recebimento` faz commit() — fura o savepoint do teste e
fixtures de CNPJ/nome FIXO colidiriam (UniqueViolation). Ver memoria
[[gotcha_testes_hora_residuo]].
"""
import uuid
from datetime import date as _date

import pytest

from app import db as _db
from app.hora.services import recebimento_service
from app.hora.services.venda_service import _normalizar_origem_lead
from app.hora.services.nf_email_service import enviar_nf_por_email, NfEmailError
from app.hora.models import (
    HoraModelo, HoraMoto, HoraNfEntrada, HoraNfEntradaItem, HoraVenda,
)
from app.utils.timezone import agora_utc_naive


def _chassi(prefix='FT'):
    return f'{prefix}{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def _modelo():
    m = HoraModelo(nome_modelo=f'TST-{uuid.uuid4().hex[:8].upper()}', ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


def _nf(loja, modelo, chassis):
    uid = uuid.uuid4().hex[:12].upper()
    nf = HoraNfEntrada(
        chave_44=uid.zfill(44), numero_nf=uid[:8],
        cnpj_emitente='12345678000199', cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id, data_emissao=_date.today(),
        valor_total=1000, criado_em=agora_utc_naive(),
    )
    _db.session.add(nf)
    _db.session.flush()
    for c in chassis:
        if not HoraMoto.query.get(c):
            _db.session.add(HoraMoto(numero_chassi=c, modelo_id=modelo.id, cor='PRETA'))
            _db.session.flush()
        _db.session.add(HoraNfEntradaItem(
            nf_id=nf.id, numero_chassi=c, preco_real=1000,
            modelo_texto_original=modelo.nome_modelo, cor_texto_original='PRETA',
        ))
    _db.session.flush()
    return nf


def _recebimento_em_conferencia(nf, loja):
    rec = recebimento_service.iniciar_recebimento(nf.id, loja.id, operador='tester')
    recebimento_service.definir_qtd_declarada(rec.id, 1, usuario='tester')
    return rec


# --------------------------- #6 origem do lead ---------------------------

def test_normalizar_origem_lead_canonico_sem_obs():
    assert _normalizar_origem_lead('GOOGLE', None) == ('GOOGLE', None)
    # uppercase + obs descartada quando nao e OUTROS.
    assert _normalizar_origem_lead('instagram', 'ignorado') == ('INSTAGRAM', None)


def test_normalizar_origem_lead_outros_exige_obs():
    assert _normalizar_origem_lead('OUTROS', 'feira de motos') == ('OUTROS', 'feira de motos')
    with pytest.raises(ValueError):
        _normalizar_origem_lead('OUTROS', '   ')


def test_normalizar_origem_lead_valor_invalido():
    with pytest.raises(ValueError):
        _normalizar_origem_lead('TIKTOK', None)


def test_normalizar_origem_lead_vazio_vira_none():
    assert _normalizar_origem_lead(None, None) == (None, None)
    assert _normalizar_origem_lead('', 'x') == (None, None)


# --------------------------- #8 foto do chassi ---------------------------

def test_conferencia_manual_sem_qr_sem_foto_falha(db, loja_factory):
    loja = loja_factory()
    modelo = _modelo()
    chassi = _chassi()
    rec = _recebimento_em_conferencia(_nf(loja, modelo, [chassi]), loja)
    with pytest.raises(ValueError, match='Foto do chassi obrigatoria'):
        recebimento_service.registrar_conferencia_cega(
            recebimento_id=rec.id, numero_chassi=chassi,
            modelo_id_conferido=modelo.id, cor_conferida='PRETA',
            avaria_fisica=False, qr_code_lido=False, operador='tester',
        )


def test_conferencia_com_qr_dispensa_foto(db, loja_factory):
    loja = loja_factory()
    modelo = _modelo()
    chassi = _chassi()
    rec = _recebimento_em_conferencia(_nf(loja, modelo, [chassi]), loja)
    conf = recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    assert conf.id is not None
    assert conf.qr_code_lido is True


def test_conferencia_com_foto_dispensa_qr(db, loja_factory):
    loja = loja_factory()
    modelo = _modelo()
    chassi = _chassi()
    rec = _recebimento_em_conferencia(_nf(loja, modelo, [chassi]), loja)
    conf = recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=False,
        foto_s3_key='hora/recebimentos/1/foto.jpg', operador='tester',
    )
    assert conf.foto_s3_key == 'hora/recebimentos/1/foto.jpg'


def test_conferencia_automatica_isenta_foto(db, loja_factory):
    loja = loja_factory()
    modelo = _modelo()
    chassi = _chassi()
    rec = _recebimento_em_conferencia(_nf(loja, modelo, [chassi]), loja)
    conf = recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=False, exigir_foto=False,
        operador='auto',
    )
    assert conf.id is not None


# --------------------------- #4 envio NF por e-mail ---------------------------

def _venda_minima(loja, **kw):
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=1000, status='COTACAO', data_venda=agora_utc_naive().date(),
        origem_criacao='MANUAL',
    )
    for k, val in kw.items():
        setattr(v, k, val)
    _db.session.add(v)
    _db.session.flush()
    return v


def test_enviar_nf_email_venda_nao_faturada_falha(db, loja_factory):
    v = _venda_minima(loja_factory(), email_cliente='cli@ex.com')  # status COTACAO
    with pytest.raises(NfEmailError, match='faturamento'):
        enviar_nf_por_email(v.id, usuario='tester')


def test_enviar_nf_email_sem_email_cliente_falha(db, loja_factory):
    v = _venda_minima(loja_factory(), email_cliente=None)
    with pytest.raises(NfEmailError, match='e-mail'):
        enviar_nf_por_email(v.id, usuario='tester')
