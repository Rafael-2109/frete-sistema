import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
)
from app.motos_assai.services import (
    registrar_montagem, resolver_pendencia, historico_3_ultimas_montagens,
    emitir_evento, status_efetivo, MontagemValidationError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _criar_moto_em_estoque(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto); db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    db.session.commit()
    return moto


def test_montagem_simples(app, admin_user):
    with app.app_context():
        chassi = f'TST_M_{_uid()}'
        _criar_moto_em_estoque(chassi, admin_user)
        r = registrar_montagem(chassi, False, None, None, admin_user.id)
        assert r['tipo'] == EVENTO_MONTADA
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


def test_montagem_pendente_com_descricao(app, admin_user):
    with app.app_context():
        chassi = f'TST_M_{_uid()}'
        _criar_moto_em_estoque(chassi, admin_user)
        r = registrar_montagem(chassi, True, 'Bateria com defeito', None, admin_user.id)
        assert r['tipo'] == EVENTO_PENDENTE
        assert status_efetivo(chassi) == EVENTO_PENDENTE
        db.session.rollback()


def test_montagem_pendente_sem_descricao_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_M_{_uid()}'
        _criar_moto_em_estoque(chassi, admin_user)
        with pytest.raises(MontagemValidationError, match='≥3'):
            registrar_montagem(chassi, True, 'AB', None, admin_user.id)
        db.session.rollback()


def test_montagem_chassi_inexistente_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(MontagemValidationError, match='não está'):
            registrar_montagem('NAO_EXISTE_999', False, None, None, admin_user.id)


def test_montagem_status_invalido_falha(app, admin_user):
    """Não pode montar uma moto que já está MONTADA."""
    with app.app_context():
        chassi = f'TST_M_{_uid()}'
        _criar_moto_em_estoque(chassi, admin_user)
        registrar_montagem(chassi, False, None, None, admin_user.id)
        with pytest.raises(MontagemValidationError, match='ESTOQUE'):
            registrar_montagem(chassi, False, None, None, admin_user.id)
        db.session.rollback()


def test_resolver_pendencia(app, admin_user):
    with app.app_context():
        chassi = f'TST_M_{_uid()}'
        _criar_moto_em_estoque(chassi, admin_user)
        registrar_montagem(chassi, True, 'Defeito X', None, admin_user.id)
        resolver_pendencia(chassi, 'Peça trocada', admin_user.id)
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()
