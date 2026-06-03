"""Guarda anti-ressurreicao no recebimento automatico (2026-06-03).

Cobre o bug do backfill 2026-05-16: `criar_recebimento_automatico_da_nf`
re-processava TODAS as NFs de entrada sem olhar o estado atual do chassi,
emitindo um evento RECEBIDA por cima de motos ja VENDIDAS. Como o estado da
moto = ultimo evento, isso revertia a moto para "em estoque" (505 motos
afetadas em PROD).

A guarda: chassi cujo `status_atual` esta em EVENTOS_FORA_ESTOQUE |
EVENTOS_EM_TRANSITO e PULADO — nao cria conferencia, nao emite RECEBIDA e
(via `ignorar_chassis`) NAO vira MOTO_FALTANDO no fechamento.
"""
import uuid
from datetime import date as _date

from app import db as _db
from app.hora.models import (
    HoraModelo,
    HoraMoto,
    HoraMotoEvento,
    HoraNfEntrada,
    HoraNfEntradaItem,
)
from app.hora.services import recebimento_service
from app.hora.services.moto_service import registrar_evento, status_atual
from app.utils.timezone import agora_utc_naive


def _chassi(prefix: str) -> str:
    uid = uuid.uuid4().hex.upper()
    return f'{prefix}{uid}'[:25].ljust(25, '0')


def _criar_modelo() -> HoraModelo:
    nome = f'TST-MODEL-{uuid.uuid4().hex[:8].upper()}'
    m = HoraModelo(nome_modelo=nome, ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


def _criar_nf_local(loja, modelo, chassis: list[str]) -> HoraNfEntrada:
    uid = uuid.uuid4().hex[:12].upper()
    nf = HoraNfEntrada(
        chave_44=uid.zfill(44),
        numero_nf=uid[:8],
        cnpj_emitente='12345678000199',
        cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id,
        data_emissao=_date.today(),
        valor_total=1000,
        criado_em=agora_utc_naive(),
    )
    _db.session.add(nf)
    _db.session.flush()
    for chassi in chassis:
        if not HoraMoto.query.get(chassi):
            m = HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA')
            _db.session.add(m)
            _db.session.flush()
        item = HoraNfEntradaItem(
            nf_id=nf.id, numero_chassi=chassi, preco_real=1000,
            modelo_texto_original=modelo.nome_modelo,
            cor_texto_original='PRETA',
        )
        _db.session.add(item)
    _db.session.flush()
    return nf


def _tipos_eventos(chassi: str) -> set:
    return {
        e.tipo for e in
        HoraMotoEvento.query.filter_by(numero_chassi=chassi).all()
    }


def test_recebimento_automatico_pula_chassi_vendido(db, loja_factory):
    """Chassi VENDIDA na NF nao recebe RECEBIDA nem MOTO_FALTANDO;
    chassi neutro recebe normalmente."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_vendido = _chassi('VEND')
    chassi_novo = _chassi('NOVO')

    nf = _criar_nf_local(loja, modelo, [chassi_vendido, chassi_novo])

    # chassi_vendido ja saiu do estoque
    registrar_evento(
        numero_chassi=chassi_vendido, tipo='VENDIDA',
        loja_id=loja.id, operador='tester',
    )
    _db.session.flush()
    assert status_atual(chassi_vendido) == 'VENDIDA'

    res = recebimento_service.criar_recebimento_automatico_da_nf(
        nf_id=nf.id, operador='tester',
    )

    # Vendido: permanece VENDIDA, sem RECEBIDA, sem MOTO_FALTANDO.
    assert chassi_vendido in res['chassis_pulados_ja_fora']
    assert status_atual(chassi_vendido) == 'VENDIDA'
    eventos_vendido = _tipos_eventos(chassi_vendido)
    assert 'RECEBIDA' not in eventos_vendido
    assert 'MOTO_FALTANDO' not in eventos_vendido

    # Novo: recebido normalmente.
    assert chassi_novo not in res['chassis_pulados_ja_fora']
    assert status_atual(chassi_novo) == 'RECEBIDA'
    assert res['conferencias_criadas'] == 1
    assert res['status_final'] == 'CONCLUIDO'


def test_recebimento_automatico_pula_reservado_e_em_transito(db, loja_factory):
    """RESERVADA e EM_TRANSITO tambem sao pulados (EVENTOS_FORA_ESTOQUE |
    EVENTOS_EM_TRANSITO). Nenhum vira MOTO_FALTANDO."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_res = _chassi('RES')
    chassi_trans = _chassi('TRANS')

    nf = _criar_nf_local(loja, modelo, [chassi_res, chassi_trans])
    registrar_evento(
        numero_chassi=chassi_res, tipo='RESERVADA',
        loja_id=loja.id, operador='tester',
    )
    registrar_evento(
        numero_chassi=chassi_trans, tipo='EM_TRANSITO',
        loja_id=loja.id, operador='tester',
    )
    _db.session.flush()

    res = recebimento_service.criar_recebimento_automatico_da_nf(
        nf_id=nf.id, operador='tester',
    )

    assert set(res['chassis_pulados_ja_fora']) == {chassi_res, chassi_trans}
    assert res['conferencias_criadas'] == 0
    assert status_atual(chassi_res) == 'RESERVADA'
    assert status_atual(chassi_trans) == 'EM_TRANSITO'
    for ch in (chassi_res, chassi_trans):
        tipos = _tipos_eventos(ch)
        assert 'RECEBIDA' not in tipos
        assert 'MOTO_FALTANDO' not in tipos


def test_finalizar_recebimento_ignora_chassis_nao_marca_faltante(db, loja_factory):
    """finalizar_recebimento(ignorar_chassis=...): chassi declarado na NF sem
    conferencia, se ignorado NAO vira MOTO_FALTANDO; se nao-ignorado vira
    (comportamento historico preservado)."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_ign = _chassi('IGN')
    chassi_falt = _chassi('FALT')

    nf = _criar_nf_local(loja, modelo, [chassi_ign, chassi_falt])
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=loja.id, operador='tester',
    )
    recebimento_service.definir_qtd_declarada(
        recebimento_id=rec.id, qtd=2, usuario='tester',
    )
    # Nenhuma conferencia registrada; finaliza ignorando so chassi_ign.
    rec = recebimento_service.finalizar_recebimento(
        recebimento_id=rec.id, operador='tester',
        ignorar_chassis={chassi_ign},
    )

    assert 'MOTO_FALTANDO' not in _tipos_eventos(chassi_ign)
    assert 'MOTO_FALTANDO' in _tipos_eventos(chassi_falt)


def test_finalizar_recebimento_default_marca_todos_faltantes(db, loja_factory):
    """Sem ignorar_chassis (default None), todo chassi da NF sem conferencia
    vira MOTO_FALTANDO — regressao do comportamento historico."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_a = _chassi('FA')
    chassi_b = _chassi('FB')

    nf = _criar_nf_local(loja, modelo, [chassi_a, chassi_b])
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=loja.id, operador='tester',
    )
    recebimento_service.definir_qtd_declarada(
        recebimento_id=rec.id, qtd=2, usuario='tester',
    )
    rec = recebimento_service.finalizar_recebimento(
        recebimento_id=rec.id, operador='tester',
    )

    assert 'MOTO_FALTANDO' in _tipos_eventos(chassi_a)
    assert 'MOTO_FALTANDO' in _tipos_eventos(chassi_b)
    assert rec.status == 'COM_DIVERGENCIA'
