"""F2 Fase 1 — isolamento de LISTAGEM (UI) de sessão por agente.

As rotas /agente/api/sessions* servem o agente logístico (web). Hoje
AgentSession.list_for_user(user_id) NÃO filtra agente — um usuário DUAL (admin
com acesso web + lojas) veria sessões 'lojas' misturadas na tela web. As rotas
do fork (/agente-lojas/*) já filtram agente='lojas'.

Cobre o núcleo da lógica: list_for_user(agente=...) isola por agente.
"""
import uuid

import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentSession


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    email = 'test_ui_iso_agente@test.com'
    user = Usuario.query.filter_by(email=email).first()
    if user:
        return user
    user = Usuario(email=email, nome='Test UI Iso', perfil='administrador', status='ativo')
    user.set_senha('x')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def seed_sessions(app, test_user):
    criados = []

    def _criar(agente):
        sid = f'uiiso-{agente}-{uuid.uuid4().hex[:10]}'
        s = AgentSession(session_id=sid, user_id=test_user.id, agente=agente,
                         title=f'titulo {agente}')
        db.session.add(s)
        db.session.commit()
        criados.append(s.id)
        return s

    yield _criar

    for pk in criados:
        obj = AgentSession.query.get(pk)
        if obj:
            db.session.delete(obj)
    db.session.commit()


def test_list_for_user_isola_por_agente(seed_sessions, test_user):
    s_web = seed_sessions('web')
    s_lojas = seed_sessions('lojas')

    web_ids = {s.id for s in AgentSession.list_for_user(test_user.id, agente='web')}
    lojas_ids = {s.id for s in AgentSession.list_for_user(test_user.id, agente='lojas')}

    assert s_web.id in web_ids
    assert s_lojas.id not in web_ids, "sessao 'lojas' vazou na listagem web (usuario dual)"
    assert s_lojas.id in lojas_ids
    assert s_web.id not in lojas_ids


def test_list_for_user_sem_agente_preserva_legado(seed_sessions, test_user):
    """Sem o parâmetro agente, comportamento legado (todas as sessões)."""
    s_web = seed_sessions('web')
    s_lojas = seed_sessions('lojas')
    todas = {s.id for s in AgentSession.list_for_user(test_user.id)}
    assert s_web.id in todas and s_lojas.id in todas
