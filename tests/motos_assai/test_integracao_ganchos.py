"""TDD Task 10: ganchos de integracao (emissores criam fichas de pendencia)."""

import uuid
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_PENDENTE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services import registrar_montagem
from app.motos_assai.services.moto_evento_service import emitir_evento


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_estoque(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    db.session.commit()


def _fichas_abertas(chassi):
    return AssaiPendencia.query.filter(
        AssaiPendencia.chassi == chassi,
        AssaiPendencia.resolvida_em.is_(None),
        AssaiPendencia.cancelada_em.is_(None),
    ).all()


def test_montagem_pendente_abre_ficha(app, admin_user):
    with app.app_context():
        chassi = f'TST_IG_{_uid()}'
        _moto_estoque(chassi, admin_user)
        r = registrar_montagem(chassi, True, 'Bateria com defeito', None, admin_user.id)
        try:
            assert r['tipo'] == EVENTO_PENDENTE
            fichas = _fichas_abertas(chassi)
            assert len(fichas) == 1
            f = fichas[0]
            assert f.categoria == PENDENCIA_CATEGORIA_INDETERMINADA
            assert f.origem == PENDENCIA_ORIGEM_GALPAO
            assert f.descricao == 'Bateria com defeito'
            assert f.evento_pendente_id == r['evento_id']
            # nenhum 2o PENDENTE emitido
            from app.motos_assai.models import AssaiMotoEvento
            n_pend = AssaiMotoEvento.query.filter_by(
                chassi=chassi, tipo=EVENTO_PENDENTE).count()
            assert n_pend == 1
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()
