import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    emitir_evento, ultimo_evento, status_efetivo, eventos_chassi,
    EventoInvalidoError,
)


def _criar_moto(app, chassi='ZZZ_TEST_001'):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    assert modelo, 'Pré-requisito: modelo DOT seeded'
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id)
    db.session.add(m); db.session.flush()
    return m


def test_emitir_tipo_invalido(app, admin_user):
    with app.app_context():
        with pytest.raises(EventoInvalidoError):
            emitir_evento('XXX', 'INEXISTENTE', admin_user.id)
        db.session.rollback()


def test_emitir_e_consultar_ultimo(app, admin_user):
    with app.app_context():
        _criar_moto(app, 'TST_ULTIMO_001')
        emitir_evento('TST_ULTIMO_001', EVENTO_ESTOQUE, admin_user.id)
        emitir_evento('TST_ULTIMO_001', EVENTO_MONTADA, admin_user.id)
        emitir_evento('TST_ULTIMO_001', EVENTO_DISPONIVEL, admin_user.id)
        last = ultimo_evento('TST_ULTIMO_001')
        assert last is not None
        assert last.tipo == EVENTO_DISPONIVEL
        assert status_efetivo('TST_ULTIMO_001') == EVENTO_DISPONIVEL
        db.session.rollback()


def test_status_chassi_sem_eventos(app):
    with app.app_context():
        assert status_efetivo('NAO_EXISTE_999') is None


def test_eventos_ordem_decrescente(app, admin_user):
    with app.app_context():
        _criar_moto(app, 'TST_HISTORICO_001')
        emitir_evento('TST_HISTORICO_001', EVENTO_ESTOQUE, admin_user.id)
        emitir_evento('TST_HISTORICO_001', EVENTO_MONTADA, admin_user.id)
        hist = eventos_chassi('TST_HISTORICO_001')
        assert len(hist) == 2
        assert hist[0].tipo == EVENTO_MONTADA  # mais recente primeiro
        db.session.rollback()


def test_chassi_normalizado_uppercase(app, admin_user):
    with app.app_context():
        _criar_moto(app, 'UPPER_001')
        emitir_evento('upper_001', EVENTO_ESTOQUE, admin_user.id)  # lowercase
        last = ultimo_evento('UPPER_001')
        assert last.chassi == 'UPPER_001'
        db.session.rollback()


def test_ocorrido_em_default_usa_agora(app, admin_user):
    """Sem ocorrido_em, o model aplica o default (agora_brasil_naive) — não None."""
    with app.app_context():
        _criar_moto(app, 'TST_DEFAULT_DT_001')
        ev = emitir_evento('TST_DEFAULT_DT_001', EVENTO_ESTOQUE, admin_user.id)
        assert ev.ocorrido_em is not None
        db.session.rollback()


def test_ocorrido_em_retroativo_preservado(app, admin_user):
    """Carga histórica: ocorrido_em retroativo é gravado tal qual (backfill)."""
    from datetime import datetime
    with app.app_context():
        _criar_moto(app, 'TST_RETRO_001')
        data_chegada = datetime(2026, 4, 15, 8, 30, 0)  # Brasil naive
        ev = emitir_evento(
            'TST_RETRO_001', EVENTO_ESTOQUE, admin_user.id,
            ocorrido_em=data_chegada,
        )
        assert ev.ocorrido_em == data_chegada
        # Persistiu e é recuperável como último evento
        assert ultimo_evento('TST_RETRO_001').ocorrido_em == data_chegada
        db.session.rollback()
