"""Rota /auth/vincular-teams — geração de código de pareamento (Task A6).

Usa fixtures globais do conftest (app session-scoped com LOGIN_DISABLED=True):
login simulado via sess['_user_id'] (mesmo padrão de test_admin_teams_route.py).
"""
import uuid

import pytest


@pytest.fixture()
def usuario_teste(app):
    from app import db
    from app.auth.models import Usuario
    with app.app_context():
        suf = uuid.uuid4().hex[:8]
        u = Usuario(
            nome=f'Rota Vinc {suf}',
            email=f'rota_{suf}@teste.local',
            perfil='logistica',
            status='ativo',
        )
        u.set_senha(uuid.uuid4().hex)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield uid
    with app.app_context():
        from app.auth.models import Usuario, TeamsVinculoCodigo
        TeamsVinculoCodigo.query.filter_by(user_id=uid).delete()
        u = db.session.get(Usuario, uid)
        if u:
            db.session.delete(u)
        db.session.commit()


def test_rota_registrada(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert '/auth/vincular-teams' in rules
    assert '/auth/usuarios/<int:user_id>/desvincular-teams' in rules


def test_get_sem_login_redireciona(client):
    resp = client.get('/auth/vincular-teams')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_post_gera_codigo_e_invalida_anterior(client, app, usuario_teste):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(usuario_teste)
        sess['_fresh'] = True

    resp1 = client.post('/auth/vincular-teams', data={})
    assert resp1.status_code == 200
    assert b'vincular' in resp1.data

    resp2 = client.post('/auth/vincular-teams', data={})
    assert resp2.status_code == 200

    with app.app_context():
        from app.auth.models import TeamsVinculoCodigo
        ativos = TeamsVinculoCodigo.query.filter(
            TeamsVinculoCodigo.user_id == usuario_teste,
            TeamsVinculoCodigo.used_at.is_(None),
        ).count()
        # 2o POST invalidou (deletou) o codigo do 1o — apenas 1 ativo
        assert ativos == 1


def test_codigo_comeca_com_letra(app, usuario_teste, client):
    """Garante o contrato com o fast-path (1o char letra, 6 chars)."""
    import re
    with client.session_transaction() as sess:
        sess['_user_id'] = str(usuario_teste)
        sess['_fresh'] = True
    resp = client.post('/auth/vincular-teams', data={})
    m = re.search(rb'vincular ([A-Z][A-Z0-9]{5})<', resp.data)
    assert m, 'codigo nao encontrado no HTML ou formato invalido'
