"""TDD Task 10: ganchos de integracao (3 emissores criam fichas) + shim resolver_pendencia."""

import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_PENDENTE, EVENTO_MONTADA,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services import (
    registrar_montagem, resolver_pendencia, MontagemValidationError,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


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


def test_shim_resolver_resolve_unica_ficha(app, admin_user):
    with app.app_context():
        chassi = f'TST_IG_{_uid()}'
        _moto_estoque(chassi, admin_user)
        registrar_montagem(chassi, True, 'Defeito X', None, admin_user.id)
        resolver_pendencia(chassi, 'Peca trocada', admin_user.id)
        try:
            assert status_efetivo(chassi) == EVENTO_MONTADA
            assert _fichas_abertas(chassi) == []
            f = AssaiPendencia.query.filter_by(chassi=chassi).first()
            assert f.resolvida_em is not None
            assert f.resolucao_descricao == 'Peca trocada'
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_shim_resolver_multiplas_fichas_erro(app, admin_user):
    with app.app_context():
        chassi = f'TST_IG_{_uid()}'
        _moto_estoque(chassi, admin_user)
        registrar_montagem(chassi, True, 'Defeito A', None, admin_user.id)
        # 2a ficha fisica aberta no mesmo chassi (cenario Spec 2)
        from app.motos_assai.services import pendencia_service
        from app.motos_assai.models import AssaiMotoEvento
        ev = AssaiMotoEvento.query.filter_by(
            chassi=chassi, tipo=EVENTO_PENDENTE).first()
        pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Defeito B',
            evento_pendente_id=ev.id, operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            with pytest.raises(MontagemValidationError, match='[Mm].ltiplas'):
                resolver_pendencia(chassi, 'tenta resolver', admin_user.id)
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()
