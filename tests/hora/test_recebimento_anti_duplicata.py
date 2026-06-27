"""Guarda anti-recebimento-duplicado (2026-06-27).

Um chassi com conferencia ATIVA em OUTRO recebimento ja foi recebido e nao
pode ser recebido de novo (causa-raiz: chassi 92WMCX113SM000988 recebido nos
recebimentos 120 e 121). A trava vive no ramo is_new de registrar_conferencia_cega;
o aviso em validar_chassi_contra_recebimento; o pre-filtro no recebimento automatico.
Reconferencia/update no MESMO recebimento e re-entradas legitimas por outro fluxo
(devolucao/transferencia) NAO sao afetadas.
"""
import uuid

import pytest

from app import db as _db
from app.hora.services import recebimento_service
from app.hora.services.recebimento_service import RecebimentoDuplicadoError
from app.hora.services.moto_service import status_atual


def _chassi(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def _receber(nf, modelo, chassi, *, finalizar=True):
    """Recebe um chassi numa NF (iniciar -> qtd -> conferir -> [finalizar])."""
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=nf.loja_destino_id, operador='tester')
    recebimento_service.definir_qtd_declarada(
        recebimento_id=rec.id, qtd=1, usuario='tester')
    conf = recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    if finalizar:
        recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')
    return rec, conf


def test_bloqueia_recebimento_duplicado_cross_rec(db, modelo_moto, nf_entrada_factory):
    chassi = _chassi('DUP')
    nf1 = nf_entrada_factory([chassi])
    recA, _ = _receber(nf1, modelo_moto, chassi)

    nf2 = nf_entrada_factory([chassi])           # mesma moto, outra NF
    recB = recebimento_service.iniciar_recebimento(
        nf_id=nf2.id, loja_id=nf2.loja_destino_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=recB.id, qtd=1, usuario='tester')

    with pytest.raises(RecebimentoDuplicadoError) as exc:
        recebimento_service.registrar_conferencia_cega(
            recebimento_id=recB.id, numero_chassi=chassi,
            modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
            avaria_fisica=False, qr_code_lido=True, operador='tester')
    assert str(recA.id) in str(exc.value)


def test_permite_reconferencia_mesmo_recebimento(db, modelo_moto, nf_entrada_factory):
    chassi = _chassi('REC')
    nf = nf_entrada_factory([chassi])
    rec, conf = _receber(nf, modelo_moto, chassi, finalizar=False)
    # reconferencia do MESMO recebimento -> nao deve bloquear (cai no else)
    recebimento_service.reiniciar_conferencia_para_chassis(
        recebimento_id=rec.id, conferencia_ids=[conf.id], operador='tester')
    conf2 = recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    assert conf2 is not None


def test_primeiro_recebimento_normal_ok(db, modelo_moto, nf_entrada_factory):
    chassi = _chassi('NEW')
    nf = nf_entrada_factory([chassi])
    rec, conf = _receber(nf, modelo_moto, chassi)
    assert conf is not None
    _db.session.expire_all()
    assert status_atual(chassi) in ('RECEBIDA', 'CONFERIDA')


def test_aviso_validar_chassi_ja_recebido_outro(db, modelo_moto, nf_entrada_factory):
    chassi = _chassi('AVI')
    nf1 = nf_entrada_factory([chassi])
    recA, _ = _receber(nf1, modelo_moto, chassi)

    nf2 = nf_entrada_factory([chassi])
    recB = recebimento_service.iniciar_recebimento(
        nf_id=nf2.id, loja_id=nf2.loja_destino_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=recB.id, qtd=1, usuario='tester')

    ctx = recebimento_service.validar_chassi_contra_recebimento(recB.id, chassi)
    assert ctx['ja_recebido_outro'] is True
    assert ctx['outro_recebimento_id'] == recA.id
    assert 'JA FOI RECEBIDO' in ctx['mensagem']


def test_automatico_pula_ja_recebido_sem_abortar(db, modelo_moto, nf_entrada_factory):
    chassi_x = _chassi('AX')
    chassi_y = _chassi('AY')
    nf1 = nf_entrada_factory([chassi_x])
    _receber(nf1, modelo_moto, chassi_x)

    nf2 = nf_entrada_factory([chassi_x, chassi_y])   # X ja recebido + Y novo
    res = recebimento_service.criar_recebimento_automatico_da_nf(nf_id=nf2.id, operador='tester')
    assert res['ok'] is True
    assert chassi_x in res['chassis_pulados_ja_recebido']
    assert res['conferencias_criadas'] == 1          # so o Y
