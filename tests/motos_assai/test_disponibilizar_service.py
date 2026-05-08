import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_REVERTIDA_PARA_MONTADA,
)
from app.motos_assai.services import (
    disponibilizar, reverter_para_montada, emitir_evento, status_efetivo,
    DisponibilizarValidationError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_montada(chassi, admin):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(m); db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    db.session.commit()


def test_disponibilizar_sucesso(app, admin_user):
    with app.app_context():
        chassi = f'TST_D_{_uid()}'
        _moto_montada(chassi, admin_user)
        r = disponibilizar(chassi, admin_user.id)
        assert r['tipo'] == EVENTO_DISPONIVEL
        db.session.rollback()


def test_disponibilizar_estoque_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_D_{_uid()}'
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        m = AssaiMoto(chassi=chassi, modelo_id=modelo.id)
        db.session.add(m); db.session.flush()
        emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
        db.session.commit()

        with pytest.raises(DisponibilizarValidationError, match='ESTOQUE'):
            disponibilizar(chassi, admin_user.id)
        db.session.rollback()


def test_reverter_sucesso(app, admin_user):
    with app.app_context():
        chassi = f'TST_D_{_uid()}'
        _moto_montada(chassi, admin_user)
        disponibilizar(chassi, admin_user.id)
        reverter_para_montada(chassi, 'Cliente cancelou', admin_user.id)
        assert status_efetivo(chassi) == EVENTO_REVERTIDA_PARA_MONTADA
        db.session.rollback()


def test_reverter_motivo_curto_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_D_{_uid()}'
        _moto_montada(chassi, admin_user)
        disponibilizar(chassi, admin_user.id)
        with pytest.raises(DisponibilizarValidationError, match='≥3'):
            reverter_para_montada(chassi, 'AB', admin_user.id)
        db.session.rollback()


def test_disponibilizar_apos_reverter(app, admin_user):
    """Após reverter, pode disponibilizar de novo."""
    with app.app_context():
        chassi = f'TST_D_{_uid()}'
        _moto_montada(chassi, admin_user)
        disponibilizar(chassi, admin_user.id)
        reverter_para_montada(chassi, 'Tag faltando', admin_user.id)
        # Status efetivo é REVERTIDA_PARA_MONTADA → aceita disponibilizar
        r = disponibilizar(chassi, admin_user.id)
        assert r['tipo'] == EVENTO_DISPONIVEL
        db.session.rollback()
