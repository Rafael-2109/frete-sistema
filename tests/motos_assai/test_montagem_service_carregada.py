"""Testes A6: montagem_service deve emitir mensagem especifica conforme o
status efetivo do chassi (CARREGADA/SEPARADA/FATURADA/DISPONIVEL) em
registrar_montagem.

Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md (Task 22)
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA,
)
from app.motos_assai.services import (
    registrar_montagem, emitir_evento,
    MontagemValidationError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _criar_moto(chassi):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    return moto


def _avancar_ate(chassi, eventos, admin_id):
    """Emite a sequencia de eventos pedida (ordem cronologica)."""
    for ev in eventos:
        emitir_evento(chassi, ev, admin_id)
    db.session.commit()


# ---- registrar_montagem ----

def test_registrar_montagem_chassi_carregada_levanta_mensagem_especifica(app, admin_user):
    """A6: tentar montar chassi CARREGADA orienta a cancelar/substituir."""
    with app.app_context():
        chassi = f'TST_MC_{_uid()}'
        _criar_moto(chassi)
        _avancar_ate(
            chassi,
            [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
             EVENTO_SEPARADA, EVENTO_CARREGADA],
            admin_user.id,
        )

        with pytest.raises(MontagemValidationError) as exc_info:
            registrar_montagem(chassi, False, None, None, admin_user.id)

        msg = str(exc_info.value)
        assert 'CARREGADA' in msg
        assert ('cancele o Carregamento' in msg) or ('substitua' in msg)
        db.session.rollback()


def test_registrar_montagem_chassi_separada_orienta_cancelar_sep(app, admin_user):
    with app.app_context():
        chassi = f'TST_MC_{_uid()}'
        _criar_moto(chassi)
        _avancar_ate(
            chassi,
            [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA],
            admin_user.id,
        )

        with pytest.raises(MontagemValidationError) as exc_info:
            registrar_montagem(chassi, False, None, None, admin_user.id)

        msg = str(exc_info.value)
        assert 'SEPARADA' in msg
        assert ('cancele a Sep' in msg) or ('desfaca' in msg)
        db.session.rollback()


def test_registrar_montagem_chassi_faturada_orienta_cancelar_nf(app, admin_user):
    with app.app_context():
        chassi = f'TST_MC_{_uid()}'
        _criar_moto(chassi)
        _avancar_ate(
            chassi,
            [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
             EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA],
            admin_user.id,
        )

        with pytest.raises(MontagemValidationError) as exc_info:
            registrar_montagem(chassi, False, None, None, admin_user.id)

        msg = str(exc_info.value)
        assert 'FATURADA' in msg
        assert 'cancele a NF' in msg
        db.session.rollback()


def test_registrar_montagem_chassi_disponivel_mensagem_especifica(app, admin_user):
    with app.app_context():
        chassi = f'TST_MC_{_uid()}'
        _criar_moto(chassi)
        _avancar_ate(
            chassi,
            [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL],
            admin_user.id,
        )

        with pytest.raises(MontagemValidationError) as exc_info:
            registrar_montagem(chassi, False, None, None, admin_user.id)

        msg = str(exc_info.value)
        assert 'DISPONIVEL' in msg
        assert 'ja esta DISPONIVEL' in msg
        db.session.rollback()
