"""
F2/M3 — teste-contrato de isolamento de memoria por agente.

Prova que `_load_user_memories_for_context(..., agente_id='lojas')` NAO injeta
memoria `agente='web'` (heuristica/perfil Nacom) e vice-versa. Foca no Tier 1
(deterministico — sempre injetado, sem depender de embedding/flags).

Com `agente_id='web'` (default), o comportamento do agente web e PRESERVADO: o
isolamento so "liga" quando 'lojas' e passado explicitamente (F3).
"""
import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.sdk import memory_injection


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    email = 'test_iso_agente@test.com'
    user = Usuario.query.filter_by(email=email).first()
    if user:
        return user
    user = Usuario(email=email, nome='Test Iso Agente', perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def seed_mem(app, test_user):
    """Cria AgentMemory com `agente=` (create_file nao aceita o campo)."""
    criados = []

    def _criar(path, content, agente):
        m = AgentMemory(user_id=test_user.id, path=path, content=content,
                        agente=agente, is_directory=False)
        db.session.add(m)
        db.session.commit()
        criados.append(m.id)
        return m

    yield _criar

    for mid in criados:
        obj = AgentMemory.query.get(mid)
        if obj:
            db.session.delete(obj)
    db.session.commit()


def _ids(user_id, agente_id):
    _main, _tail, ids = memory_injection._load_user_memories_for_context(
        user_id=user_id, agente_id=agente_id,
    )
    return set(ids or [])


def test_sessao_lojas_nao_injeta_memoria_web_tier1(seed_mem, test_user):
    m_web = seed_mem('/memories/user.xml', 'SEGREDO_NACOM_WEB_XYZ', agente='web')
    m_lojas = seed_mem('/memories/preferences.xml', 'DADO_DA_LOJA_XYZ', agente='lojas')

    ids = _ids(test_user.id, 'lojas')
    assert m_web.id not in ids, "id de memoria 'web' vazou p/ sessao 'lojas'"
    assert m_lojas.id in ids


def test_sessao_web_nao_injeta_memoria_lojas_tier1(seed_mem, test_user):
    m_web = seed_mem('/memories/user.xml', 'PERFIL_WEB_NACOM_XYZ', agente='web')
    m_lojas = seed_mem('/memories/preferences.xml', 'PERFIL_LOJA_HORA_XYZ', agente='lojas')

    ids = _ids(test_user.id, 'web')
    assert m_web.id in ids
    assert m_lojas.id not in ids, "id de memoria 'lojas' vazou p/ sessao 'web'"
