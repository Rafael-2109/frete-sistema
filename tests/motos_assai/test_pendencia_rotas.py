"""Smoke tests para rotas de pendencias (Spec 2 Task 7)."""
import uuid
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_ORIGEM_GALPAO,
    EVENTO_MONTADA,
)
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.moto_evento_service import status_efetivo


def _moto(chassi):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.commit()


def test_get_resolver_200(login_admin, app, admin_user):
    with app.app_context():
        chassi = f'TSTRT{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='fio solto',
                            operador_id=admin_user.id)
        db.session.commit(); pid = f.id
    resp = login_admin.get(f'/motos-assai/pendencias/{pid}/resolver')
    assert resp.status_code == 200


def test_post_resolver_consertar_monta(login_admin, app, admin_user):
    with app.app_context():
        chassi = f'TSTRT{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='fio',
                            operador_id=admin_user.id)
        db.session.commit(); pid = f.id; ch = chassi
    resp = login_admin.post(f'/motos-assai/pendencias/{pid}/resolver', data={
        'acao': 'resolver', 'tratativa': 'CONSERTAR', 'resolucao_descricao': 'soldado'})
    assert resp.status_code in (302, 200)
    with app.app_context():
        assert status_efetivo(ch) == EVENTO_MONTADA
