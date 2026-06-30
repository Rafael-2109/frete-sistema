import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_FATURADA,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, count_fisicas_abertas, afeta_estado_moto, PendenciaError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto(chassi, admin_user, estado=EVENTO_MONTADA):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    if estado != EVENTO_ESTOQUE:
        emitir_evento(chassi, estado, admin_user.id)
    db.session.flush()
    return moto


def _conta_pendentes(chassi):
    return AssaiMotoEvento.query.filter_by(chassi=chassi, tipo=EVENTO_PENDENTE).count()


def test_pendencia_fisica_emite_pendente(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta retrovisor',
            operador_id=admin_user.id,
        )
        assert ficha.evento_pendente_id is not None
        assert afeta_estado_moto(ficha) is True
        assert status_efetivo(chassi) == EVENTO_PENDENTE
        assert _conta_pendentes(chassi) == 1
        db.session.rollback()


def test_segunda_fisica_reusa_evento(app, admin_user):
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
        assert f1.evento_pendente_id == f2.evento_pendente_id
        assert _conta_pendentes(chassi) == 1
        assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 2
        assert count_fisicas_abertas(chassi) == 2
        db.session.rollback()


def test_pos_venda_nao_emite_evento(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user, estado=EVENTO_FATURADA)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, descricao='Cliente reclamou',
            operador_id=admin_user.id, retorno_fisico=False,
            pos_venda_ocorrencia_id=None,
        )
        assert ficha.evento_pendente_id is None
        assert afeta_estado_moto(ficha) is False
        assert status_efetivo(chassi) == EVENTO_FATURADA
        assert _conta_pendentes(chassi) == 0
        db.session.rollback()


def test_pos_venda_com_retorno_fisico_emite(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user, estado=EVENTO_FATURADA)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_CLIENTE, descricao='Retornou fisico',
            operador_id=admin_user.id, retorno_fisico=True,
        )
        assert ficha.evento_pendente_id is not None
        assert afeta_estado_moto(ficha) is True
        assert status_efetivo(chassi) == EVENTO_PENDENTE
        db.session.rollback()


def test_evento_explicito_e_reusado_sem_segundo_pendente(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ev = emitir_evento(chassi, EVENTO_PENDENTE, admin_user.id)
        db.session.flush()
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Revisao devolucao',
            operador_id=admin_user.id, evento_pendente_id=ev.id,
        )
        assert ficha.evento_pendente_id == ev.id
        assert _conta_pendentes(chassi) == 1
        db.session.rollback()


def test_descricao_curta_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        with pytest.raises(PendenciaError, match='Descricao'):
            abrir_pendencia(
                chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                origem=PENDENCIA_ORIGEM_GALPAO, descricao='ab',
                operador_id=admin_user.id,
            )
        db.session.rollback()
