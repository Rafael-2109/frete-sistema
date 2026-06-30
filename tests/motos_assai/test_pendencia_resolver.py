"""TDD Task 7: resolver_pendencia + cancelar_pendencia — gate de fechamento.

Cenarios cobertos:
  1. Resolver a unica pendencia fisica → MONTADA
  2. Resolver 1 de 2 fisicas → segue PENDENTE; resolver a 2a → MONTADA
  3. Idempotencia: resolver ja-resolvida = no-op (nao emite 2o MONTADA)
  4. Pos-venda resolve sem tocar evento de moto
  5. Cancelar a ultima fisica → MONTADA
  6. Cancelar com motivo muito curto → PendenciaError

Nota: _moto usa estado=EVENTO_ESTOQUE como default para que as contagens de
EVENTO_MONTADA sejam exclusivamente dos eventos emitidos pelo gate de fechamento.
"""
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_FATURADA,
    EVENTO_PENDENCIA_RESOLVIDA,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_TRATATIVA_CONSERTAR, PENDENCIA_TRATATIVA_REVISAR,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, resolver_pendencia, cancelar_pendencia, PendenciaError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto(chassi, admin_user, estado=EVENTO_ESTOQUE):
    """Cria moto e leva ao estado desejado.

    Default ESTOQUE (nao MONTADA) para que _conta(EVENTO_MONTADA) seja zero
    antes do gate de fechamento — torna as assertivas de contagem inequivocas.
    """
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    if estado != EVENTO_ESTOQUE:
        emitir_evento(chassi, estado, admin_user.id)
    db.session.flush()
    return moto


def _conta(chassi, tipo):
    return AssaiMotoEvento.query.filter_by(chassi=chassi, tipo=tipo).count()


# ---------------------------------------------------------------------------
# Cenario 1: resolver a unica pendencia fisica → MONTADA
# ---------------------------------------------------------------------------

def test_resolver_ultima_de_uma_vira_montada(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        r = resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='Consertado no galpao', operador_id=admin_user.id,
        )
        assert r.resolvida_em is not None
        assert r.tratativa == PENDENCIA_TRATATIVA_CONSERTAR
        assert status_efetivo(chassi) == EVENTO_MONTADA
        assert _conta(chassi, EVENTO_MONTADA) == 1  # so o da resolucao (moto entrou em ESTOQUE)
        db.session.rollback()


# ---------------------------------------------------------------------------
# Cenario 2: resolver 1 de 2 → segue PENDENTE; resolver a 2a → MONTADA
# ---------------------------------------------------------------------------

def test_resolver_uma_de_duas_segue_pendente_depois_montada(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        f1 = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta A',
            operador_id=admin_user.id,
        )
        f2 = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Revisar B',
            operador_id=admin_user.id,
        )
        resolver_pendencia(
            pendencia_id=f1.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='ok A', operador_id=admin_user.id,
        )
        assert status_efetivo(chassi) == EVENTO_PENDENTE  # f2 ainda aberta
        assert _conta(chassi, EVENTO_MONTADA) == 0
        resolver_pendencia(
            pendencia_id=f2.id, tratativa=PENDENCIA_TRATATIVA_REVISAR,
            resolucao_descricao='ok B', operador_id=admin_user.id,
        )
        assert status_efetivo(chassi) == EVENTO_MONTADA
        assert _conta(chassi, EVENTO_PENDENCIA_RESOLVIDA) == 1
        db.session.rollback()


# ---------------------------------------------------------------------------
# Cenario 3: idempotencia — resolver ja-resolvida nao re-grava nem emite 2o MONTADA
# ---------------------------------------------------------------------------

def test_resolver_idempotente(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='1a vez', operador_id=admin_user.id,
        )
        marca = ficha.resolvida_em
        r2 = resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_REVISAR,
            resolucao_descricao='2a vez', operador_id=admin_user.id,
        )
        assert r2.resolvida_em == marca          # nao re-grava
        assert r2.tratativa == PENDENCIA_TRATATIVA_CONSERTAR
        assert _conta(chassi, EVENTO_MONTADA) == 1  # nao emitiu 2o MONTADA
        db.session.rollback()


# ---------------------------------------------------------------------------
# Cenario 4: pos-venda resolve sem tocar evento de moto
# ---------------------------------------------------------------------------

def test_resolver_pos_venda_nao_toca_evento(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user, estado=EVENTO_FATURADA)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, descricao='Pos venda loja',
            operador_id=admin_user.id, retorno_fisico=False,
        )
        resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='resolvido sem retorno', operador_id=admin_user.id,
        )
        assert status_efetivo(chassi) == EVENTO_FATURADA
        assert _conta(chassi, EVENTO_MONTADA) == 0
        assert _conta(chassi, EVENTO_PENDENCIA_RESOLVIDA) == 0
        db.session.rollback()


# ---------------------------------------------------------------------------
# Cenario 5: cancelar a ultima fisica → MONTADA
# ---------------------------------------------------------------------------

def test_cancelar_ultima_fisica_vira_montada(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        c = cancelar_pendencia(
            pendencia_id=ficha.id, motivo='Aberta por engano',
            operador_id=admin_user.id,
        )
        assert c.cancelada_em is not None
        assert c.detalhes.get('cancelamento_motivo') == 'Aberta por engano'
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


# ---------------------------------------------------------------------------
# Cenario 6: cancelar com motivo curto → PendenciaError
# ---------------------------------------------------------------------------

def test_cancelar_motivo_curto_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        with pytest.raises(PendenciaError, match='Motivo'):
            cancelar_pendencia(pendencia_id=ficha.id, motivo='x', operador_id=admin_user.id)
        db.session.rollback()
