"""Testes da feature de desconsiderar item de NF de entrada (auto-contidos, uuid)."""
import uuid
from datetime import date

import pytest

from app import db
from app.hora.models import (
    HoraLoja, HoraModelo, HoraMoto, HoraNfEntrada, HoraNfEntradaItem,
    HoraPedido, HoraPedidoItem,
)
from app.hora.services.moto_service import registrar_evento
from app.utils.timezone import agora_utc_naive


# ---------------------------------------------------------------------------
# Helpers locais com IDs únicos (não dependem das fixtures de ID fixo do conftest)
# ---------------------------------------------------------------------------
def _uid():
    return uuid.uuid4().hex[:12].upper()


def _chassi():
    return ('9T' + _uid())[:17]


def _loja():
    u = _uid()
    cnpj = ''.join(c for c in u if c.isdigit()).ljust(14, '0')[:14]
    loja = HoraLoja(
        cnpj=cnpj, apelido=f'L{u[:6]}', nome=f'Loja {u}',
        razao_social=f'Loja {u} LTDA', nome_fantasia=f'Loja {u}',
        ativa=True, atualizado_em=agora_utc_naive(),
    )
    db.session.add(loja)
    db.session.flush()
    return loja


def _modelo():
    m = HoraModelo(nome_modelo=f'MOD-{_uid()}', ativo=True)
    db.session.add(m)
    db.session.flush()
    return m


def _moto(chassi, modelo):
    m = HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA')
    db.session.add(m)
    db.session.flush()
    return m


def _nf(loja, chassis, modelo, criar_motos=True):
    u = _uid()
    nf = HoraNfEntrada(
        chave_44=u.zfill(44), numero_nf=u[:8], cnpj_emitente='12345678000199',
        cnpj_destinatario=loja.cnpj, loja_destino_id=loja.id,
        data_emissao=date.today(), valor_total=1000, criado_em=agora_utc_naive(),
    )
    db.session.add(nf)
    db.session.flush()
    for c in chassis:
        if criar_motos and not HoraMoto.query.get(c):
            _moto(c, modelo)
        db.session.add(HoraNfEntradaItem(nf_id=nf.id, numero_chassi=c, preco_real=1000))
    db.session.flush()
    return nf


def _pedido(loja, chassis, modelo):
    u = _uid()
    p = HoraPedido(
        numero_pedido=f'PED-{u}', cnpj_destino=loja.cnpj, loja_destino_id=loja.id,
        data_pedido=date.today(), status='ABERTO', criado_em=agora_utc_naive(),
    )
    db.session.add(p)
    db.session.flush()
    for c in chassis:
        if not HoraMoto.query.get(c):
            _moto(c, modelo)
        db.session.add(HoraPedidoItem(
            pedido_id=p.id, numero_chassi=c, modelo_id=modelo.id, preco_compra_esperado=1000,
        ))
    db.session.flush()
    return p


# ---------------------------------------------------------------------------
# Task 2 — Modelo
# ---------------------------------------------------------------------------
def test_item_flag_desconsiderado_default_false(db):
    loja, mod = _loja(), _modelo()
    nf = _nf(loja, [_chassi()], mod)
    assert nf.itens[0].desconsiderado is False


def test_itens_considerados_exclui_desconsiderado(db):
    loja, mod = _loja(), _modelo()
    c1, c2 = _chassi(), _chassi()
    nf = _nf(loja, [c1, c2], mod)
    nf.itens[0].desconsiderado = True
    db.session.flush()
    db.session.refresh(nf)
    assert len(nf.itens) == 2
    assert len(nf.itens_considerados) == 1
    assert nf.itens_considerados[0].numero_chassi == c2


# ---------------------------------------------------------------------------
# Task 3 — Helpers de validação
# ---------------------------------------------------------------------------
def test_chassi_em_pedido(db):
    from app.hora.services.chassi_protecao_service import chassi_em_pedido
    loja, mod = _loja(), _modelo()
    c = _chassi()
    _pedido(loja, [c], mod)
    assert chassi_em_pedido(c) is True
    assert chassi_em_pedido(_chassi()) is False


def test_motivo_bloqueio_em_pedido(db):
    from app.hora.services.nf_entrada_service import _motivo_bloqueio_desconsiderar
    loja, mod = _loja(), _modelo()
    c = _chassi()
    _pedido(loja, [c], mod)
    nf = _nf(loja, [c], mod)  # mesma moto na NF
    assert _motivo_bloqueio_desconsiderar(nf.itens[0]) is not None


def test_motivo_bloqueio_recebido(db):
    from app.hora.services.nf_entrada_service import _motivo_bloqueio_desconsiderar
    loja, mod = _loja(), _modelo()
    c = _chassi()
    nf = _nf(loja, [c], mod)
    item = nf.itens[0]
    assert _motivo_bloqueio_desconsiderar(item) is None  # liberado
    registrar_evento(numero_chassi=c, tipo='RECEBIDA', loja_id=loja.id)
    db.session.flush()
    assert _motivo_bloqueio_desconsiderar(item) is not None  # bloqueado por evento


def test_assert_item_moto_consistente(db):
    from app.hora.services.nf_entrada_service import assert_item_moto_consistente
    loja, mod = _loja(), _modelo()
    nf = _nf(loja, [_chassi()], mod)
    item = nf.itens[0]
    assert_item_moto_consistente(item)  # considerado + moto existe -> ok
