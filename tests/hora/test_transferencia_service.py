"""Tests do transferencia_service."""
import pytest

from app import db as _db
from app.hora.models import HoraMotoEvento, HoraTransferenciaAuditoria
from app.hora.services import transferencia_service
from app.hora.services.moto_service import registrar_evento, get_or_create_moto


# ---------- criar_transferencia ----------

def test_criar_transferencia_sucesso(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id,
        loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque],
        usuario='joao',
    )
    assert t.status == 'EM_TRANSITO'
    assert t.emitida_por == 'joao'
    assert len(t.itens) == 1
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='EM_TRANSITO')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.loja_id == loja_destino.id
    assert ev.origem_tabela == 'hora_transferencia_item'


def test_criar_lista_vazia_falha(db, loja_origem, loja_destino):
    with pytest.raises(ValueError, match=r"pelo menos 1 chassi"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
            chassis=[], usuario='x',
        )


def test_criar_mesma_loja_falha(db, chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match=r"origem.*destino"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_origem.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_chassi_fora_de_estoque_falha(db, chassi_em_estoque, loja_origem, loja_destino):
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='VENDIDA',
        loja_id=loja_origem.id, operador='pre',
    )
    _db.session.flush()
    with pytest.raises(ValueError, match=r"estoque"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_chassi_em_outra_loja_falha(db, chassi_em_estoque, loja_origem, loja_destino):
    with pytest.raises(ValueError, match=r"nao esta na loja origem"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_destino.id,
            loja_destino_id=loja_origem.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_chassi_em_transito_duplicado_falha(db, chassi_em_estoque, loja_origem, loja_destino):
    transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='x',
    )
    _db.session.flush()
    with pytest.raises(ValueError, match=r"ja esta em transito"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_registra_auditoria_EMITIU(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='joao',
    )
    aud = HoraTransferenciaAuditoria.query.filter_by(
        transferencia_id=t.id, acao='EMITIU',
    ).first()
    assert aud is not None
    assert aud.usuario == 'joao'


# ---------- confirmar_item_destino + finalizar ----------

def test_confirmar_item_emite_TRANSFERIDA(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    item = t.itens[0]
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id,
        numero_chassi=chassi_em_estoque,
        usuario='recebedor',
        qr_code_lido=True,
    )
    _db.session.refresh(item)
    assert item.conferido_destino_em is not None
    assert item.qr_code_lido is True
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='TRANSFERIDA')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.loja_id == loja_destino.id


def test_confirmar_idempotente(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='r1', qr_code_lido=False,
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='r2', qr_code_lido=True,
    )
    _db.session.flush()
    item = t.itens[0]
    _db.session.refresh(item)
    assert item.conferido_destino_por == 'r1'
    evs = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi_em_estoque, tipo='TRANSFERIDA',
    ).count()
    assert evs == 1


def test_finalizar_muda_status_para_CONFIRMADA(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='recebedor', qr_code_lido=True,
    )
    ok = transferencia_service.finalizar_se_tudo_confirmado(t.id)
    assert ok is True
    _db.session.refresh(t)
    assert t.status == 'CONFIRMADA'
    assert t.confirmada_em is not None
    assert t.confirmada_por == 'recebedor'


def test_finalizar_nao_altera_se_falta_item(
    db, chassi_em_estoque, loja_origem, loja_destino, modelo_moto,
):
    chassi2 = '9OUTROCHASSITEST200000000000'
    get_or_create_moto(
        numero_chassi=chassi2, modelo_nome=modelo_moto.nome_modelo,
        cor='BRANCA', criado_por='fix',
    )
    registrar_evento(chassi2, 'RECEBIDA', loja_id=loja_origem.id, operador='fix')
    registrar_evento(chassi2, 'CONFERIDA', loja_id=loja_origem.id, operador='fix')
    _db.session.flush()

    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque, chassi2], usuario='emissor',
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='r1', qr_code_lido=True,
    )
    ok = transferencia_service.finalizar_se_tudo_confirmado(t.id)
    assert ok is False
    _db.session.refresh(t)
    assert t.status == 'EM_TRANSITO'


# ---------- cancelar_transferencia ----------

def test_cancelar_em_transito_volta_moto_para_origem(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    transferencia_service.cancelar_transferencia(
        transferencia_id=t.id, motivo='enviado por engano', usuario='chefe',
    )
    _db.session.refresh(t)
    assert t.status == 'CANCELADA'
    assert t.cancelada_em is not None
    assert t.cancelada_por == 'chefe'
    assert t.motivo_cancelamento == 'enviado por engano'
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='CANCELADA')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.loja_id == loja_origem.id


def test_cancelar_exige_motivo_com_3_chars(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='x',
    )
    with pytest.raises(ValueError, match=r"motivo"):
        transferencia_service.cancelar_transferencia(t.id, motivo='ok', usuario='y')


def test_cancelar_so_em_transito(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='x',
    )
    transferencia_service.confirmar_item_destino(
        t.id, chassi_em_estoque, usuario='r1', qr_code_lido=True,
    )
    transferencia_service.finalizar_se_tudo_confirmado(t.id)
    with pytest.raises(ValueError, match=r"nao pode cancelar"):
        transferencia_service.cancelar_transferencia(
            t.id, motivo='muito tarde', usuario='y',
        )


def test_cancelar_nao_emite_CANCELADA_para_item_ja_confirmado(
    db, chassi_em_estoque, loja_origem, loja_destino, modelo_moto,
):
    chassi2 = '9OUTROCHASSITEST300000000000'
    get_or_create_moto(
        numero_chassi=chassi2, modelo_nome=modelo_moto.nome_modelo,
        cor='BRANCA', criado_por='fix',
    )
    registrar_evento(chassi2, 'RECEBIDA', loja_id=loja_origem.id, operador='fix')
    registrar_evento(chassi2, 'CONFERIDA', loja_id=loja_origem.id, operador='fix')
    _db.session.flush()

    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque, chassi2], usuario='x',
    )
    transferencia_service.confirmar_item_destino(
        t.id, chassi2, usuario='r1', qr_code_lido=True,
    )
    transferencia_service.cancelar_transferencia(
        t.id, motivo='parcialmente errado', usuario='y',
    )
    evs_c1 = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi_em_estoque, tipo='CANCELADA',
    ).count()
    evs_c2 = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi2, tipo='CANCELADA',
    ).count()
    assert evs_c1 == 1
    assert evs_c2 == 0
