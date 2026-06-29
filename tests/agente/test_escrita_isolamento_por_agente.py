"""F2 Fase 1 — fundação de isolamento de ESCRITA de memória por agente.

Pré-requisito de F3 (motor único): quando o agente lojas gravar memória, deve
gravar com agente='lojas' e COEXISTIR com memória 'web' no mesmo path. Cobre:
  - ContextVar _current_agent_id (permissions.py) — default 'web' fail-closed.
  - AgentMemory.create_file/create_directory propagam `agente`.
  - UNIQUE(user_id, path, agente) — web e lojas coexistem no mesmo path.
"""
import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    email = 'test_escrita_agente@test.com'
    user = Usuario.query.filter_by(email=email).first()
    if user:
        return user
    user = Usuario(email=email, nome='Test Escrita Agente', perfil='agente', status='ativo')
    user.set_senha('x')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def limpa(app, test_user):
    """Remove memórias do prefixo de teste antes e depois."""
    prefix = '/memories/_pytest_escrita'

    def _cleanup():
        AgentMemory.query.filter(
            AgentMemory.user_id == test_user.id,
            AgentMemory.path.like(f'{prefix}%'),
        ).delete(synchronize_session=False)
        db.session.commit()

    _cleanup()
    yield prefix
    _cleanup()


def test_context_var_agente_default_web():
    from app.agente.config import permissions
    permissions.clear_current_agent_id()
    assert permissions.get_current_agent_id() == 'web', "default fail-closed deve ser 'web'"
    permissions.set_current_agent_id('lojas')
    assert permissions.get_current_agent_id() == 'lojas'
    permissions.clear_current_agent_id()
    assert permissions.get_current_agent_id() == 'web', "clear volta p/ 'web'"


def test_create_file_grava_agente(limpa, test_user):
    path = f'{limpa}/cf.xml'
    m = AgentMemory.create_file(test_user.id, path, 'conteudo', agente='lojas')
    db.session.commit()
    assert m.agente == 'lojas'
    # default permanece 'web'
    m2 = AgentMemory.create_file(test_user.id, f'{limpa}/cf2.xml', 'c')
    db.session.commit()
    assert m2.agente == 'web'


def test_constraint_permite_coexistencia_por_agente(limpa, test_user):
    path = f'{limpa}/dup.xml'
    w = AgentMemory.create_file(test_user.id, path, 'conteudo_web', agente='web')
    l = AgentMemory.create_file(test_user.id, path, 'conteudo_loja', agente='lojas')
    db.session.commit()  # NAO deve violar UNIQUE(user_id, path, agente)
    assert w.agente == 'web' and l.agente == 'lojas'
    assert w.id != l.id, "web e lojas devem coexistir no mesmo path"
